"""Tests for aggregator and sanitizer."""

from __future__ import annotations

import json
from datetime import datetime

from vibe_clock.aggregator import aggregate
from vibe_clock.config import Config
from vibe_clock.models import AgentStats, Session, TokenUsage
from vibe_clock.sanitizer import preview, public_payload, sanitize


_WINDOW_END = datetime.fromisoformat("2026-03-01T00:00:00+00:00")


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
    stats = aggregate(sessions, config, end_at=_WINDOW_END)

    assert stats.total_sessions == 3
    assert stats.total_messages == 25  # 10 + 10 + 5
    assert stats.active_days == 2
    assert len(stats.daily) == 2  # Feb 10, Feb 11
    assert len(stats.models) == 2  # claude-opus-4-6, gpt-5.1
    assert set(stats.active_agents) == {"claude_code", "codex"}


def test_aggregate_filters_old_sessions() -> None:
    old = _make_session(start="2025-01-01T10:00:00Z", end="2025-01-01T10:30:00Z")
    recent = _make_session(sid="s2", start="2026-02-10T10:00:00Z", end="2026-02-10T10:30:00Z")

    config = Config(default_days=30)
    stats = aggregate([old, recent], config, end_at=_WINDOW_END)
    assert stats.total_sessions == 1


def test_aggregate_supports_complete_day_window() -> None:
    sessions = [
        _make_session(
            sid="inside",
            start="2026-02-22T00:00:00Z",
            end="2026-02-22T00:30:00Z",
        ),
        _make_session(
            sid="today",
            start="2026-03-01T00:00:00Z",
            end="2026-03-01T00:30:00Z",
        ),
    ]
    config = Config(default_days=7)

    stats = aggregate(sessions, config, end_at=_WINDOW_END)

    assert stats.total_sessions == 1
    assert stats.daily[0].date.isoformat() == "2026-02-22"


def test_aggregate_exclude_projects() -> None:
    sessions = [
        _make_session(sid="s1", project="/home/user/secret-project"),
        _make_session(sid="s2", project="/home/user/public-project"),
    ]

    config = Config(default_days=30)
    config.privacy.exclude_projects = ["*/secret-*"]
    stats = aggregate(sessions, config, end_at=_WINDOW_END)
    assert stats.total_sessions == 1


def test_aggregate_peak_hour() -> None:
    sessions = [
        _make_session(sid="s1", start="2026-02-10T14:00:00Z", end="2026-02-10T14:30:00Z"),
        _make_session(sid="s2", start="2026-02-10T14:30:00Z", end="2026-02-10T15:00:00Z"),
        _make_session(sid="s3", start="2026-02-10T09:00:00Z", end="2026-02-10T09:30:00Z"),
    ]
    config = Config(default_days=30)
    stats = aggregate(sessions, config, end_at=_WINDOW_END)
    assert stats.peak_hour == 14


def test_aggregate_preserves_per_model_token_usage() -> None:
    session = _make_session(model="claude-test", input_tok=150, output_tok=0)
    session.model_tokens = {
        "claude-test": TokenUsage(input_tokens=100),
        "gpt-test": TokenUsage(input_tokens=50),
    }

    stats = aggregate([session], Config(default_days=30), end_at=_WINDOW_END)
    models = {item.model: item for item in stats.models}

    assert models["claude-test"].tokens.total == 100
    assert models["gpt-test"].tokens.total == 50
    assert models["claude-test"].session_count == 1
    assert models["gpt-test"].session_count == 0


def test_sanitize_hides_projects_by_default() -> None:
    sessions = [
        _make_session(sid="s1", project="/home/user/project-alpha"),
        _make_session(sid="s2", project="/home/user/project-beta"),
        _make_session(sid="s3", project="/home/user/project-alpha"),
    ]

    config = Config(default_days=30)
    stats = aggregate(sessions, config, end_at=_WINDOW_END)
    safe = sanitize(stats, config)

    assert safe.projects == []


def test_sanitize_normalizes_model_names() -> None:
    sessions = [
        _make_session(model="gpt-5.6-private-alias", project="safe-name"),
        _make_session(sid="s2", model="claude-internal", project="safe-name"),
    ]
    config = Config(default_days=30)
    stats = aggregate(sessions, config, end_at=_WINDOW_END)
    safe = sanitize(stats, config)

    assert safe.favorite_model in {"OpenAI", "Claude"}
    assert {item.model for item in safe.models} == {"OpenAI", "Claude"}
    assert "private-alias" not in safe.model_dump_json()
    assert "internal" not in safe.model_dump_json()


def test_sanitize_keeps_empty_favorite_model_empty() -> None:
    config = Config(default_days=30)

    safe = sanitize(AgentStats(), config)

    assert safe.favorite_model == ""


def test_public_payload_is_allowlisted() -> None:
    sessions = [
        _make_session(
            project="/home/user/secret-project",
            model="gpt-5.6-private-alias",
        )
    ]
    config = Config(default_days=30)
    stats = aggregate(sessions, config, end_at=_WINDOW_END)

    payload = public_payload(stats, config)
    serialized = json.dumps(payload)

    assert set(payload) == {
        "schema_version",
        "generated_at",
        "days_covered",
        "active_days",
        "total_sessions",
        "active_agents",
        "agents",
        "favorite_model",
        "models",
    }
    assert payload["schema_version"] == 2
    assert payload["favorite_model"] == "OpenAI"
    assert set(payload["models"][0]) == {"model", "session_count"}
    assert payload["agents"] == [{"agent": "claude_code", "session_count": 1}]
    assert "secret-project" not in serialized
    assert "private-alias" not in serialized
    assert "total_tokens" not in payload
    assert "daily" not in payload
    assert "hourly" not in payload
    rendered_stats = AgentStats.model_validate(payload)
    assert rendered_stats.total_sessions == 1
    assert rendered_stats.models[0].model == "OpenAI"


def test_preview_contains_the_exact_public_payload() -> None:
    sessions = [_make_session(model="gpt-private")]
    config = Config(default_days=30)
    config.privacy.share_token_counts = True
    stats = aggregate(sessions, config, end_at=_WINDOW_END)

    output = preview(stats, config)
    rendered_payload = json.loads(output.split("\n\n", 1)[1])

    assert rendered_payload == public_payload(stats, config)


def test_public_payload_optional_fields_are_explicit() -> None:
    sessions = [_make_session(project="/home/user/secret-project")]
    config = Config(default_days=30)
    config.privacy.share_daily_activity = True
    config.privacy.share_message_counts = True
    config.privacy.share_token_counts = True
    config.privacy.share_time_patterns = True
    config.privacy.share_project_aliases = True
    stats = aggregate(sessions, config, end_at=_WINDOW_END)

    payload = public_payload(stats, config)

    assert payload["total_messages"] == 10
    assert payload["total_tokens"]["input_tokens"] == 1000
    assert payload["daily"][0]["date"] == "2026-02-10"
    assert len(payload["hourly"]) == 24
    assert payload["projects"][0]["project"] == "Project A"
    assert "total_minutes" not in payload["daily"][0]
    assert "total_minutes" not in payload["models"][0]
    assert "total_minutes" not in payload["projects"][0]
    assert "secret-project" not in json.dumps(payload)
