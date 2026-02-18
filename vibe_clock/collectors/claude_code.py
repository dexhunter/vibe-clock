"""Collector for Claude Code sessions.

Parses two data sources:
1. stats-cache.json — pre-aggregated daily stats (quick path)
2. projects/*/*.jsonl — individual session records (deep path)
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone

from ..models import Session, TokenUsage
from .base import BaseCollector


class ClaudeCodeCollector(BaseCollector):
    agent_name = "claude_code"

    def collect(self) -> list[Session]:
        """Collect sessions from Claude Code JSONL project files."""
        sessions: dict[str, _SessionAcc] = {}
        projects_dir = self.data_dir / "projects"
        if not projects_dir.exists():
            return []

        for jsonl_file in projects_dir.rglob("*.jsonl"):
            # Project name comes from parent directory slug
            project_slug = jsonl_file.parent.name
            try:
                with open(jsonl_file) as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            record = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        self._process_record(record, project_slug, sessions)
            except OSError:
                continue

        return [acc.to_session() for acc in sessions.values()]

    def _process_record(
        self,
        record: dict,
        project_slug: str,
        sessions: dict[str, _SessionAcc],
    ) -> None:
        session_id = record.get("sessionId")
        if not session_id:
            return

        # Only process assistant messages (they have token usage)
        if record.get("type") != "assistant":
            return

        msg = record.get("message", {})
        usage = msg.get("usage", {})
        model = msg.get("model", "unknown")
        timestamp_str = record.get("timestamp")
        if not timestamp_str:
            return

        try:
            ts = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except ValueError:
            return

        if session_id not in sessions:
            sessions[session_id] = _SessionAcc(
                session_id=session_id,
                project=project_slug,
            )

        acc = sessions[session_id]
        acc.message_count += 1
        acc.timestamps.append(ts)
        acc.tokens.input_tokens += usage.get("input_tokens", 0)
        acc.tokens.output_tokens += usage.get("output_tokens", 0)
        acc.tokens.cache_read_tokens += usage.get("cache_read_input_tokens", 0)
        acc.tokens.cache_write_tokens += usage.get(
            "cache_creation_input_tokens", 0
        )
        if model != "unknown":
            acc.models[model] += 1


class _SessionAcc:
    """Accumulator for building a Session from multiple JSONL records."""

    def __init__(self, session_id: str, project: str) -> None:
        self.session_id = session_id
        self.project = project
        self.message_count = 0
        self.timestamps: list[datetime] = []
        self.tokens = TokenUsage()
        self.models: dict[str, int] = defaultdict(int)

    def to_session(self) -> Session:
        if self.timestamps:
            start = min(self.timestamps)
            end = max(self.timestamps)
        else:
            start = datetime.now(timezone.utc)
            end = None

        # Most-used model
        model = "unknown"
        if self.models:
            model = max(self.models, key=self.models.get)  # type: ignore[arg-type]

        return Session(
            session_id=self.session_id,
            agent="claude_code",
            start_time=start,
            end_time=end,
            model=model,
            project=self.project,
            message_count=self.message_count,
            tokens=self.tokens,
        )
