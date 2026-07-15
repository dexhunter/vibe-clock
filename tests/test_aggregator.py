"""Tests for aggregator and sanitizer."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from vibe_clock.aggregator import aggregate
from vibe_clock.config import Config
from vibe_clock.models import Session, TokenUsage
from vibe_clock.sanitizer import sanitize


def _make_session(
    sid: str = "s1",
    agent: str = "claude_code",
    model: str = "claude-opus-4-6",
    project: str = "/home/user/myproject",
    start: str | None = None,
    end: str | None = None,
    messages: int = 10,
    input_tok: int = 1000,
    output_tok: int = 500,
) -> Session:
    start = start or _recent_iso(hour=10)
    end = end or _recent_iso(hour=10, minute=30)
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


def _recent_iso(days_ago: int = 1, hour: int = 10, minute: int = 0) -> str:
    value = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return value.replace(
        hour=hour,
        minute=minute,
        second=0,
        microsecond=0,
    ).isoformat()


def test_aggregate_basic() -> None:
    sessions = [
        _make_session(sid="s1", start=_recent_iso(days_ago=2, hour=10), end=_recent_iso(days_ago=2, hour=10, minute=30)),
        _make_session(sid="s2", agent="codex", model="gpt-5.1", start=_recent_iso(days_ago=2, hour=14), end=_recent_iso(days_ago=2, hour=14, minute=45)),
        _make_session(sid="s3", start=_recent_iso(hour=9), end=_recent_iso(hour=9, minute=10), messages=5),
    ]

    config = Config(default_days=30)
    stats = aggregate(sessions, config)

    assert stats.total_sessions == 3
    assert stats.total_messages == 25  # 10 + 10 + 5
    assert len(stats.daily) == 2
    assert len(stats.models) == 2  # claude-opus-4-6, gpt-5.1
    assert set(stats.active_agents) == {"claude_code", "codex"}


def test_aggregate_filters_old_sessions() -> None:
    old = _make_session(
        start=_recent_iso(days_ago=31, hour=10),
        end=_recent_iso(days_ago=31, hour=10, minute=30),
    )
    recent = _make_session(sid="s2")

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
        _make_session(sid="s1", start=_recent_iso(hour=14), end=_recent_iso(hour=14, minute=30)),
        _make_session(sid="s2", start=_recent_iso(hour=14, minute=30), end=_recent_iso(hour=15)),
        _make_session(sid="s3", start=_recent_iso(hour=9), end=_recent_iso(hour=9, minute=30)),
    ]
    config = Config(default_days=30)
    stats = aggregate(sessions, config)
    assert stats.peak_hour == 14


def test_aggregate_preserves_per_model_token_usage() -> None:
    session = _make_session(model="claude-test", input_tok=150, output_tok=0)
    session.model_tokens = {
        "claude-test": TokenUsage(input_tokens=100),
        "gpt-test": TokenUsage(input_tokens=50),
    }

    stats = aggregate([session], Config(default_days=30))
    models = {item.model: item for item in stats.models}

    assert models["claude-test"].tokens.total == 100
    assert models["gpt-test"].tokens.total == 50
    assert models["claude-test"].session_count == 1
    assert models["gpt-test"].session_count == 0


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
