"""Collector for OpenAI Codex CLI sessions.

Parses rollout JSONL files at:
  {data_dir}/sessions/YYYY/MM/DD/rollout-*.jsonl

Each file contains typed records: session_meta, turn_context, event_msg, response_item.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ..models import Session, TokenUsage
from .base import BaseCollector


class CodexCollector(BaseCollector):
    agent_name = "codex"

    def collect(self, days: int = 365) -> list[Session]:
        roots = [
            self.data_dir / "sessions",
            self.data_dir / "archived_sessions",
        ]
        if not any(root.exists() for root in roots):
            return []

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        paths = sorted(
            path
            for root in roots
            if root.exists()
            for path in root.rglob("rollout-*.jsonl")
        )
        recent_paths: list[Path] = []
        for path in paths:
            try:
                if path.stat().st_mtime >= cutoff.timestamp():
                    recent_paths.append(path)
            except OSError:
                continue

        lineage = {path: _session_lineage(path) for path in recent_paths}
        parents = {
            session_id: parent_id
            for session_id, parent_id in lineage.values()
            if session_id and parent_id
        }
        seen_by_family: dict[str, set[tuple[int, ...]]] = defaultdict(set)

        results: list[Session] = []
        for jsonl_file in recent_paths:
            session_id, _ = lineage[jsonl_file]
            family_id = _family_id(session_id, parents) or str(jsonl_file)
            session = self._parse_rollout(
                jsonl_file,
                cutoff=cutoff,
                seen_snapshots=seen_by_family[family_id],
            )
            if session is not None:
                results.append(session)
        return results

    def _parse_rollout(
        self,
        path: Path,
        cutoff: datetime | None = None,
        seen_snapshots: set[tuple[int, ...]] | None = None,
    ) -> Session | None:
        cutoff = cutoff or datetime.min.replace(tzinfo=timezone.utc)
        seen_snapshots = seen_snapshots if seen_snapshots is not None else set()
        session_id: str | None = None
        project: str = "unknown"
        model: str = "unknown"
        current_model: str = "unknown"
        timestamps: list[datetime] = []
        tokens = TokenUsage()
        model_tokens: dict[str, TokenUsage] = defaultdict(TokenUsage)
        message_count = 0
        models: dict[str, int] = defaultdict(int)
        previous_total: tuple[int, int, int] | None = None

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
                    timestamp = _parse_timestamp(ts_str)
                    in_window = timestamp is not None and timestamp >= cutoff
                    if in_window:
                        timestamps.append(timestamp)

                    if rec_type == "session_meta":
                        session_id = payload.get("id", session_id)
                        project = payload.get("cwd", project)

                    elif rec_type == "turn_context":
                        m = payload.get("model")
                        if m:
                            current_model = m
                            if in_window:
                                models[m] += 1

                    elif rec_type == "event_msg":
                        evt_type = payload.get("type")
                        if evt_type == "token_count":
                            info = payload.get("info") or {}
                            last = info.get("last_token_usage", {})
                            total = info.get("total_token_usage") or {}
                            if last or total:
                                raw_usage, previous_total = _usage_delta(
                                    last,
                                    total,
                                    previous_total,
                                )
                                if not in_window:
                                    continue
                                fingerprint = _snapshot_fingerprint(
                                    last,
                                    total,
                                )
                                if (
                                    fingerprint is not None
                                    and fingerprint in seen_snapshots
                                ):
                                    continue
                                if fingerprint is not None:
                                    seen_snapshots.add(fingerprint)

                                usage = _codex_token_usage(raw_usage)
                                _add_token_usage(tokens, usage)
                                event_model = info.get("model") or current_model
                                _add_token_usage(
                                    model_tokens[event_model],
                                    usage,
                                )
                                models[event_model] += 1
                        elif evt_type == "user_message" and in_window:
                            message_count += 1

                    elif rec_type == "response_item" and in_window:
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
            model_tokens=dict(model_tokens),
        )


def _parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp


def _session_lineage(path: Path) -> tuple[str | None, str | None]:
    try:
        with path.open() as handle:
            for line in handle:
                if '"session_meta"' not in line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if record.get("type") != "session_meta":
                    continue
                payload = record.get("payload", {})
                return (
                    payload.get("id"),
                    payload.get("forked_from_id")
                    or payload.get("forkedFromId")
                    or payload.get("parent_session_id")
                    or payload.get("parentSessionId"),
                )
    except OSError:
        pass
    return None, None


def _family_id(session_id: str | None, parents: dict[str, str]) -> str | None:
    if session_id is None:
        return None
    family_id = session_id
    visited: set[str] = set()
    while family_id in parents and family_id not in visited:
        visited.add(family_id)
        family_id = parents[family_id]
    return family_id


def _nonnegative_int(value: object) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _cached_input(usage: dict) -> int:
    return _nonnegative_int(
        usage.get("cached_input_tokens", usage.get("cache_read_input_tokens", 0))
    )


def _codex_token_usage(usage: dict) -> TokenUsage:
    input_tokens = _nonnegative_int(usage.get("input_tokens", 0))
    cached_input_tokens = min(_cached_input(usage), input_tokens)
    return TokenUsage(
        input_tokens=input_tokens - cached_input_tokens,
        output_tokens=_nonnegative_int(usage.get("output_tokens", 0)),
        cache_read_tokens=cached_input_tokens,
    )


def _usage_delta(
    last: dict,
    total: dict,
    previous_total: tuple[int, int, int] | None,
) -> tuple[dict[str, int], tuple[int, int, int] | None]:
    if not total:
        return last, previous_total

    current_total = (
        _nonnegative_int(total.get("input_tokens", 0)),
        _cached_input(total),
        _nonnegative_int(total.get("output_tokens", 0)),
    )
    if previous_total is None:
        return (last or total), current_total

    if all(current >= previous for current, previous in zip(current_total, previous_total)):
        delta = tuple(
            current - previous
            for current, previous in zip(current_total, previous_total)
        )
        return {
            "input_tokens": delta[0],
            "cached_input_tokens": delta[1],
            "output_tokens": delta[2],
        }, current_total

    return (last or total), current_total


def _snapshot_fingerprint(last: dict, total: dict) -> tuple[int, ...] | None:
    if not total:
        return None

    def values(usage: dict) -> tuple[int, ...]:
        return (
            _nonnegative_int(usage.get("input_tokens", 0)),
            _cached_input(usage),
            _nonnegative_int(usage.get("output_tokens", 0)),
            _nonnegative_int(usage.get("reasoning_output_tokens", 0)),
            _nonnegative_int(usage.get("total_tokens", 0)),
        )

    return values(last) + values(total)


def _add_token_usage(target: TokenUsage, source: TokenUsage) -> None:
    target.input_tokens += source.input_tokens
    target.output_tokens += source.output_tokens
    target.cache_read_tokens += source.cache_read_tokens
    target.cache_write_tokens += source.cache_write_tokens
