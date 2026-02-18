"""Tests for aggregator and sanitizer."""

from __future__ import annotations

from datetime import datetime

from vibe_clock.aggregator import aggregate
from vibe_clock.config import Config
from vibe_clock.models import Session, TokenUsage
from vibe_clock.sanitizer import sanitize


def _make_session(
    sid: str = "s1",
    agent: str = "claude_code",
    model: str = "claude-opus-4-6",
    project: str = "/home/user/myproject",
    start: str = "2026-02-10T10:00:00Z",
    end: str = "2026-02-10T10:30:00Z",
    messages: int = 10,
    input_tok: int = 1000,
    output_tok: int = 500,
) -> Session:
    return Session(
        session_id=sid,
        agent=agent,
        model=model,
        project=project,
        start_time=datetime.fromisoformat(start.replace("Z", "+00:00")),
        end_time=datetime.fromisoformat(end.replace("Z", "+00:00")),
        message_count=messages,
        tokens=TokenUsage(input_tokens=input_tok, output_tokens=output_tok),
    )


def test_aggregate_basic() -> None:
    sessions = [
        _make_session(sid="s1", start="2026-02-10T10:00:00Z", end="2026-02-10T10:30:00Z"),
        _make_session(sid="s2", agent="codex", model="gpt-5.1", start="2026-02-10T14:00:00Z", end="2026-02-10T14:45:00Z"),
        _make_session(sid="s3", start="2026-02-11T09:00:00Z", end="2026-02-11T09:10:00Z", messages=5),
    ]

    config = Config(default_days=30)
    stats = aggregate(sessions, config)

    assert stats.total_sessions == 3
    assert stats.total_messages == 25  # 10 + 10 + 5
    assert len(stats.daily) == 2  # Feb 10, Feb 11
    assert len(stats.models) == 2  # claude-opus-4-6, gpt-5.1
    assert set(stats.active_agents) == {"claude_code", "codex"}


def test_aggregate_filters_old_sessions() -> None:
    old = _make_session(start="2025-01-01T10:00:00Z", end="2025-01-01T10:30:00Z")
    recent = _make_session(sid="s2", start="2026-02-10T10:00:00Z", end="2026-02-10T10:30:00Z")

    config = Config(default_days=30)
    stats = aggregate([old, recent], config)
    assert stats.total_sessions == 1


def test_aggregate_exclude_projects() -> None:
    sessions = [
        _make_session(sid="s1", project="/home/user/secret-project"),
        _make_session(sid="s2", project="/home/user/public-project"),
    ]

    config = Config(default_days=30)
    config.privacy.exclude_projects = ["*/secret-*"]
    stats = aggregate(sessions, config)
    assert stats.total_sessions == 1


def test_aggregate_peak_hour() -> None:
    sessions = [
        _make_session(sid="s1", start="2026-02-10T14:00:00Z", end="2026-02-10T14:30:00Z"),
        _make_session(sid="s2", start="2026-02-10T14:30:00Z", end="2026-02-10T15:00:00Z"),
        _make_session(sid="s3", start="2026-02-10T09:00:00Z", end="2026-02-10T09:30:00Z"),
    ]
    config = Config(default_days=30)
    stats = aggregate(sessions, config)
    assert stats.peak_hour == 14


def test_sanitize_anonymizes_projects() -> None:
    sessions = [
        _make_session(sid="s1", project="/home/user/project-alpha"),
        _make_session(sid="s2", project="/home/user/project-beta"),
        _make_session(sid="s3", project="/home/user/project-alpha"),
    ]

    config = Config(default_days=30)
    stats = aggregate(sessions, config)
    safe = sanitize(stats, config)

    project_names = {p.project for p in safe.projects}
    assert all(p.startswith("Project ") for p in project_names)
    # No paths should remain
    assert all("/" not in p.project for p in safe.projects)


def test_sanitize_detects_pii() -> None:
    sessions = [_make_session(project="safe-name")]
    config = Config(default_days=30)
    config.privacy.anonymize_projects = False
    stats = aggregate(sessions, config)
    # This should work fine — no PII
    safe = sanitize(stats, config)
    assert safe.total_sessions == 1
