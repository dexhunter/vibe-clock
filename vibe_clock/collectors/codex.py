"""Collector for OpenAI Codex CLI sessions.

Parses rollout JSONL files at:
  {data_dir}/sessions/YYYY/MM/DD/rollout-*.jsonl

Each file contains typed records: session_meta, turn_context, event_msg, response_item.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from ..models import Session, TokenUsage
from .base import BaseCollector


class CodexCollector(BaseCollector):
    agent_name = "codex"

    def collect(self) -> list[Session]:
        sessions_dir = self.data_dir / "sessions"
        if not sessions_dir.exists():
            return []

        results: list[Session] = []
        for jsonl_file in sessions_dir.rglob("rollout-*.jsonl"):
            session = self._parse_rollout(jsonl_file)
            if session is not None:
                results.append(session)
        return results

    def _parse_rollout(self, path: Path) -> Session | None:
        session_id: str | None = None
        project: str = "unknown"
        model: str = "unknown"
        timestamps: list[datetime] = []
        tokens = TokenUsage()
        message_count = 0
        models: dict[str, int] = defaultdict(int)

        try:
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    rec_type = record.get("type")
                    payload = record.get("payload", {})
                    ts_str = record.get("timestamp")

                    if ts_str:
                        try:
                            timestamps.append(
                                datetime.fromisoformat(
                                    ts_str.replace("Z", "+00:00")
                                )
                            )
                        except ValueError:
                            pass

                    if rec_type == "session_meta":
                        session_id = payload.get("id", session_id)
                        project = payload.get("cwd", project)

                    elif rec_type == "turn_context":
                        m = payload.get("model")
                        if m:
                            models[m] += 1

                    elif rec_type == "event_msg":
                        evt_type = payload.get("type")
                        if evt_type == "token_count":
                            info = payload.get("info") or {}
                            last = info.get("last_token_usage", {})
                            if last:
                                tokens.input_tokens += last.get(
                                    "input_tokens", 0
                                )
                                tokens.output_tokens += last.get(
                                    "output_tokens", 0
                                )
                                tokens.cache_read_tokens += last.get(
                                    "cached_input_tokens", 0
                                )
                        elif evt_type == "user_message":
                            message_count += 1

                    elif rec_type == "response_item":
                        role = payload.get("role")
                        if role == "assistant":
                            message_count += 1

        except OSError:
            return None

        if session_id is None or not timestamps:
            return None

        if models:
            model = max(models, key=models.get)  # type: ignore[arg-type]

        return Session(
            session_id=session_id,
            agent="codex",
            start_time=min(timestamps),
            end_time=max(timestamps),
            model=model,
            project=project,
            message_count=message_count,
            tokens=tokens,
        )
