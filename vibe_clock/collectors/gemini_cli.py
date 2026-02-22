"""Collector for Gemini CLI sessions.

Parses session JSON files at:
  {data_dir}/tmp/{project}/chats/session-*.json

Each file is a single JSON object with sessionId, startTime, lastUpdated,
and a messages array. Messages with type "gemini" contain token counts and
model info.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from ..models import Session, TokenUsage
from .base import BaseCollector


class GeminiCliCollector(BaseCollector):
    agent_name = "gemini_cli"

    def collect(self, days: int = 365) -> list[Session]:
        tmp_dir = self.data_dir / "tmp"
        if not tmp_dir.exists():
            return []

        mtime_cutoff = self._cutoff_timestamp(days)
        results: list[Session] = []

        for session_file in tmp_dir.rglob("session-*.json"):
            try:
                if session_file.stat().st_mtime < mtime_cutoff:
                    continue
            except OSError:
                continue
            session = self._parse_session(session_file)
            if session is not None:
                results.append(session)
        return results

    def _parse_session(self, path: Path) -> Session | None:
        try:
            data = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            return None

        session_id = data.get("sessionId")
        if not session_id:
            return None

        start_str = data.get("startTime")
        end_str = data.get("lastUpdated")
        if not start_str:
            return None

        try:
            start_time = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
        except ValueError:
            return None

        end_time = None
        if end_str:
            try:
                end_time = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
            except ValueError:
                pass

        # Project is the parent's parent directory name (tmp/{project}/chats/)
        project = path.parent.parent.name

        tokens = TokenUsage()
        models: dict[str, int] = defaultdict(int)
        message_count = 0

        for msg in data.get("messages", []):
            msg_type = msg.get("type")
            if msg_type == "gemini":
                message_count += 1
                tok = msg.get("tokens", {})
                tokens.input_tokens += tok.get("input", 0)
                tokens.output_tokens += tok.get("output", 0)
                tokens.cache_read_tokens += tok.get("cached", 0)
                model = msg.get("model", "unknown")
                if model != "unknown":
                    models[model] += 1
            elif msg_type == "user":
                message_count += 1

        model = "unknown"
        if models:
            model = max(models, key=models.get)  # type: ignore[arg-type]

        return Session(
            session_id=session_id,
            agent="gemini_cli",
            start_time=start_time,
            end_time=end_time,
            model=model,
            project=project,
            message_count=message_count,
            tokens=tokens,
        )
