"""Collector for OpenCode sessions.

Data layout:
  {data_dir}/storage/session/{projectID}/ses_*.json  — session metadata
  {data_dir}/storage/message/{sessionID}/msg_*.json  — per-message token data
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from ..models import Session, TokenUsage
from .base import BaseCollector


class OpenCodeCollector(BaseCollector):
    agent_name = "opencode"

    def collect(self) -> list[Session]:
        storage = self.data_dir / "storage"
        session_dir = storage / "session"
        message_dir = storage / "message"

        if not session_dir.exists():
            return []

        results: list[Session] = []
        for ses_file in session_dir.rglob("ses_*.json"):
            session = self._parse_session(ses_file, message_dir)
            if session is not None:
                results.append(session)
        return results

    def _parse_session(
        self, ses_path: Path, message_dir: Path
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
            for msg_file in msg_session_dir.glob("msg_*.json"):
                try:
                    with open(msg_file) as f:
                        msg = json.load(f)
                except (OSError, json.JSONDecodeError):
                    continue

                if msg.get("role") == "assistant":
                    message_count += 1

                    model_id = msg.get("modelID", "unknown")
                    if model_id != "unknown":
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

        model = "unknown"
        if models:
            model = max(models, key=models.get)  # type: ignore[arg-type]

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
