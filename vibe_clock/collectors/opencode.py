"""Collector for OpenCode sessions.

Supports two storage formats:

1. Current format — SQLite database at {data_dir}/opencode.db
   Tables: ``session`` (id, directory, time_created, time_updated) and
   ``message`` (id, session_id, time_created, time_updated, data).
   The ``data`` column contains JSON with the message payload; assistant
   messages carry ``modelID``, ``tokens.input``, ``tokens.output`` and
   ``tokens.cache.{read,write}``.

2. Legacy JSON format — files under {data_dir}/storage/:
   {data_dir}/storage/session/{projectID}/{sessionID}.json
   {data_dir}/storage/message/{sessionID}/{messageID}.json
"""

from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from ..models import Session, TokenUsage
from .base import BaseCollector


class OpenCodeCollector(BaseCollector):
    agent_name = "opencode"

    def is_available(self) -> bool:
        if not self.data_dir.exists():
            return False
        # Available if either the SQLite database or the legacy JSON storage exists.
        return (self.data_dir / "opencode.db").exists() or (
            self.data_dir / "storage" / "session"
        ).exists()

    def collect(self, days: int | None = None) -> list[Session]:
        db_path = self.data_dir / "opencode.db"
        if db_path.exists():
            return self._collect_from_db(db_path, days=days)
        return self._collect_from_json(days=days)

    # ------------------------------------------------------------------
    # SQLite (current format)
    # ------------------------------------------------------------------

    def _collect_from_db(self, db_path: Path, days: int | None = None) -> list[Session]:
        """Read sessions from the SQLite database used by current OpenCode."""
        try:
            # Open read-only; even though is_available() confirmed the file exists,
            # it may have been deleted concurrently or be unreadable due to permissions.
            con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        except sqlite3.OperationalError:
            return []

        results: list[Session] = []
        try:
            con.row_factory = sqlite3.Row
            cur = con.cursor()

            cutoff_ms: int | None = None
            if days is not None:
                cutoff_ms = int(self._cutoff_timestamp(days) * 1000)

            if cutoff_ms is not None:
                cur.execute(
                    "SELECT id, directory, time_created, time_updated"
                    " FROM session WHERE time_created >= ?",
                    (cutoff_ms,),
                )
            else:
                cur.execute(
                    "SELECT id, directory, time_created, time_updated FROM session"
                )

            for row in cur.fetchall():
                session = self._session_from_db_row(row, cur)
                if session is not None:
                    results.append(session)
        except sqlite3.Error:
            pass
        finally:
            con.close()

        return results

    def _session_from_db_row(
        self, row: sqlite3.Row, cur: sqlite3.Cursor
    ) -> Session | None:
        session_id = row["id"]
        created_ms = row["time_created"]
        updated_ms = row["time_updated"]
        if created_ms is None:
            return None

        project = row["directory"] or "unknown"
        start_time = datetime.fromtimestamp(created_ms / 1000, tz=timezone.utc)
        end_time = (
            datetime.fromtimestamp(updated_ms / 1000, tz=timezone.utc)
            if updated_ms
            else None
        )

        tokens = TokenUsage()
        message_count = 0
        models: dict[str, int] = defaultdict(int)

        try:
            cur.execute(
                "SELECT data FROM message WHERE session_id = ?", (session_id,)
            )
            for msg_row in cur.fetchall():
                try:
                    msg = json.loads(msg_row["data"])
                except (json.JSONDecodeError, TypeError):
                    continue

                if msg.get("role") == "assistant":
                    message_count += 1
                    model_id = msg.get("modelID", "unknown")
                    if model_id and model_id != "unknown":
                        models[model_id] += 1

                    tok = msg.get("tokens", {})
                    tokens.input_tokens += tok.get("input", 0)
                    tokens.output_tokens += tok.get("output", 0)
                    cache = tok.get("cache", {})
                    tokens.cache_read_tokens += cache.get("read", 0)
                    tokens.cache_write_tokens += cache.get("write", 0)

                    msg_time = msg.get("time", {})
                    completed = msg_time.get("completed")
                    if completed and end_time:
                        msg_end = datetime.fromtimestamp(
                            completed / 1000, tz=timezone.utc
                        )
                        if msg_end > end_time:
                            end_time = msg_end
        except sqlite3.Error:
            pass

        model = self._most_used_model(models)

        return Session(
            session_id=session_id,
            agent="opencode",
            start_time=start_time,
            end_time=end_time,
            model=model,
            project=project,
            message_count=message_count,
            tokens=tokens,
        )

    # ------------------------------------------------------------------
    # Legacy JSON format
    # ------------------------------------------------------------------

    def _collect_from_json(self, days: int | None = None) -> list[Session]:
        """Read sessions from the legacy JSON file storage."""
        storage = self.data_dir / "storage"
        session_dir = storage / "session"
        message_dir = storage / "message"

        if not session_dir.exists():
            return []

        cutoff_ms: int | None = None
        if days is not None:
            cutoff_ms = int(self._cutoff_timestamp(days) * 1000)

        results: list[Session] = []
        for ses_file in session_dir.rglob("*.json"):
            session = self._parse_json_session(ses_file, message_dir, cutoff_ms)
            if session is not None:
                results.append(session)
        return results

    def _parse_json_session(
        self, ses_path: Path, message_dir: Path, cutoff_ms: int | None = None
    ) -> Session | None:
        try:
            with open(ses_path) as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            return None

        session_id = data.get("id")
        if not session_id:
            return None

        project = data.get("directory", "unknown")
        time_info = data.get("time", {})

        # Timestamps are Unix milliseconds
        created_ms = time_info.get("created")
        updated_ms = time_info.get("updated")
        if created_ms is None:
            return None

        if cutoff_ms is not None and created_ms < cutoff_ms:
            return None

        start_time = datetime.fromtimestamp(created_ms / 1000, tz=timezone.utc)
        end_time = (
            datetime.fromtimestamp(updated_ms / 1000, tz=timezone.utc)
            if updated_ms
            else None
        )

        # Parse messages for this session
        tokens = TokenUsage()
        message_count = 0
        models: dict[str, int] = defaultdict(int)

        msg_session_dir = message_dir / session_id
        if msg_session_dir.exists():
            for msg_file in msg_session_dir.glob("*.json"):
                try:
                    with open(msg_file) as f:
                        msg = json.load(f)
                except (OSError, json.JSONDecodeError):
                    continue

                if msg.get("role") == "assistant":
                    message_count += 1

                    model_id = msg.get("modelID", "unknown")
                    if model_id and model_id != "unknown":
                        models[model_id] += 1

                    tok = msg.get("tokens", {})
                    tokens.input_tokens += tok.get("input", 0)
                    tokens.output_tokens += tok.get("output", 0)

                    cache = tok.get("cache", {})
                    tokens.cache_read_tokens += cache.get("read", 0)
                    tokens.cache_write_tokens += cache.get("write", 0)

                    # Update end_time from message completion time
                    msg_time = msg.get("time", {})
                    completed = msg_time.get("completed")
                    if completed and end_time:
                        msg_end = datetime.fromtimestamp(
                            completed / 1000, tz=timezone.utc
                        )
                        if msg_end > end_time:
                            end_time = msg_end

        model = self._most_used_model(models)

        return Session(
            session_id=session_id,
            agent="opencode",
            start_time=start_time,
            end_time=end_time,
            model=model,
            project=project,
            message_count=message_count,
            tokens=tokens,
        )

    @staticmethod
    def _most_used_model(models: dict[str, int]) -> str:
        """Return the model name with the highest usage count, or 'unknown'."""
        if not models:
            return "unknown"
        return max(models, key=models.__getitem__)
