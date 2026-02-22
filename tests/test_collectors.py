"""Tests for agent data collectors."""

from __future__ import annotations

import json
from pathlib import Path

from vibe_clock.collectors.claude_code import ClaudeCodeCollector
from vibe_clock.collectors.codex import CodexCollector
from vibe_clock.collectors.gemini_cli import GeminiCliCollector
from vibe_clock.collectors.opencode import OpenCodeCollector


def test_claude_code_collector(tmp_path: Path) -> None:
    """Test Claude Code JSONL parsing."""
    project_dir = tmp_path / "projects" / "my-project"
    project_dir.mkdir(parents=True)
    jsonl = project_dir / "session.jsonl"

    records = [
        {
            "sessionId": "sess-001",
            "timestamp": "2026-02-10T10:00:00Z",
            "type": "assistant",
            "message": {
                "model": "claude-opus-4-6",
                "usage": {
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "cache_read_input_tokens": 200,
                    "cache_creation_input_tokens": 30,
                },
            },
        },
        {
            "sessionId": "sess-001",
            "timestamp": "2026-02-10T10:05:00Z",
            "type": "assistant",
            "message": {
                "model": "claude-opus-4-6",
                "usage": {
                    "input_tokens": 80,
                    "output_tokens": 40,
                    "cache_read_input_tokens": 150,
                    "cache_creation_input_tokens": 20,
                },
            },
        },
        # Non-assistant record should be skipped
        {
            "sessionId": "sess-001",
            "timestamp": "2026-02-10T10:02:00Z",
            "type": "progress",
            "message": {},
        },
    ]
    jsonl.write_text("\n".join(json.dumps(r) for r in records))

    collector = ClaudeCodeCollector(data_dir=tmp_path)
    assert collector.is_available()

    sessions = collector.collect()
    assert len(sessions) == 1

    s = sessions[0]
    assert s.session_id == "sess-001"
    assert s.agent == "claude_code"
    assert s.model == "claude-opus-4-6"
    assert s.message_count == 2
    assert s.tokens.input_tokens == 180
    assert s.tokens.output_tokens == 90
    assert s.tokens.cache_read_tokens == 350
    assert s.tokens.cache_write_tokens == 50
    assert s.project == "my-project"


def test_claude_code_not_available(tmp_path: Path) -> None:
    collector = ClaudeCodeCollector(data_dir=tmp_path / "nonexistent")
    assert not collector.is_available()


def test_codex_collector(tmp_path: Path) -> None:
    """Test Codex rollout JSONL parsing."""
    day_dir = tmp_path / "sessions" / "2026" / "02" / "10"
    day_dir.mkdir(parents=True)
    rollout = day_dir / "rollout-2026-02-10T10-00-00-abc123.jsonl"

    records = [
        {
            "timestamp": "2026-02-10T10:00:00Z",
            "type": "session_meta",
            "payload": {
                "id": "abc123",
                "cwd": "/home/user/project",
                "model_provider": "openai",
            },
        },
        {
            "timestamp": "2026-02-10T10:01:00Z",
            "type": "turn_context",
            "payload": {"model": "gpt-5.1-codex", "cwd": "/home/user/project"},
        },
        {
            "timestamp": "2026-02-10T10:01:30Z",
            "type": "event_msg",
            "payload": {"type": "user_message", "message": "hello"},
        },
        {
            "timestamp": "2026-02-10T10:02:00Z",
            "type": "event_msg",
            "payload": {
                "type": "token_count",
                "info": {
                    "last_token_usage": {
                        "input_tokens": 500,
                        "output_tokens": 200,
                        "cached_input_tokens": 100,
                    },
                },
            },
        },
        {
            "timestamp": "2026-02-10T10:05:00Z",
            "type": "response_item",
            "payload": {"role": "assistant", "content": []},
        },
    ]
    rollout.write_text("\n".join(json.dumps(r) for r in records))

    collector = CodexCollector(data_dir=tmp_path)
    sessions = collector.collect()
    assert len(sessions) == 1

    s = sessions[0]
    assert s.session_id == "abc123"
    assert s.agent == "codex"
    assert s.model == "gpt-5.1-codex"
    assert s.tokens.input_tokens == 500
    assert s.tokens.output_tokens == 200
    assert s.tokens.cache_read_tokens == 100
    assert s.message_count == 2  # 1 user_message + 1 assistant response_item


def test_gemini_cli_collector(tmp_path: Path) -> None:
    """Test Gemini CLI session JSON parsing."""
    chats_dir = tmp_path / "tmp" / "my-project" / "chats"
    chats_dir.mkdir(parents=True)

    session_data = {
        "sessionId": "abc-123",
        "projectHash": "deadbeef",
        "startTime": "2026-02-10T10:00:00Z",
        "lastUpdated": "2026-02-10T10:10:00Z",
        "messages": [
            {
                "id": "msg-1",
                "timestamp": "2026-02-10T10:00:00Z",
                "type": "user",
                "content": [{"text": "hello"}],
            },
            {
                "id": "msg-2",
                "timestamp": "2026-02-10T10:00:05Z",
                "type": "gemini",
                "content": "Hi there!",
                "tokens": {
                    "input": 500,
                    "output": 35,
                    "cached": 100,
                    "thoughts": 50,
                    "tool": 0,
                    "total": 685,
                },
                "model": "gemini-3-flash-preview",
            },
            {
                "id": "msg-3",
                "timestamp": "2026-02-10T10:05:00Z",
                "type": "user",
                "content": [{"text": "thanks"}],
            },
            {
                "id": "msg-4",
                "timestamp": "2026-02-10T10:05:10Z",
                "type": "gemini",
                "content": "You're welcome!",
                "tokens": {
                    "input": 600,
                    "output": 20,
                    "cached": 200,
                    "thoughts": 30,
                    "tool": 0,
                    "total": 850,
                },
                "model": "gemini-3-flash-preview",
            },
        ],
    }
    (chats_dir / "session-2026-02-10T10-00-abc123.json").write_text(
        json.dumps(session_data)
    )

    collector = GeminiCliCollector(data_dir=tmp_path)
    assert collector.is_available()

    sessions = collector.collect()
    assert len(sessions) == 1

    s = sessions[0]
    assert s.session_id == "abc-123"
    assert s.agent == "gemini_cli"
    assert s.model == "gemini-3-flash-preview"
    assert s.message_count == 4  # 2 user + 2 gemini
    assert s.tokens.input_tokens == 1100
    assert s.tokens.output_tokens == 55
    assert s.tokens.cache_read_tokens == 300
    assert s.project == "my-project"


def test_gemini_cli_not_available(tmp_path: Path) -> None:
    collector = GeminiCliCollector(data_dir=tmp_path / "nonexistent")
    assert not collector.is_available()


def test_opencode_collector(tmp_path: Path) -> None:
    """Test OpenCode session/message JSON parsing."""
    storage = tmp_path / "storage"
    session_dir = storage / "session" / "proj1"
    session_dir.mkdir(parents=True)
    message_dir = storage / "message" / "ses_001"
    message_dir.mkdir(parents=True)

    # Session file
    ses_data = {
        "id": "ses_001",
        "directory": "/home/user/myproject",
        "time": {"created": 1707560000000, "updated": 1707560300000},
    }
    (session_dir / "ses_001.json").write_text(json.dumps(ses_data))

    # Message files
    msg1 = {
        "id": "msg_001",
        "sessionID": "ses_001",
        "role": "assistant",
        "modelID": "minimax-m2.1",
        "time": {"created": 1707560100000, "completed": 1707560200000},
        "tokens": {"input": 300, "output": 100, "cache": {"read": 50, "write": 10}},
    }
    msg2 = {
        "id": "msg_002",
        "sessionID": "ses_001",
        "role": "user",
        "modelID": "minimax-m2.1",
        "time": {"created": 1707560050000},
        "tokens": {"input": 0, "output": 0, "cache": {"read": 0, "write": 0}},
    }
    (message_dir / "msg_001.json").write_text(json.dumps(msg1))
    (message_dir / "msg_002.json").write_text(json.dumps(msg2))

    collector = OpenCodeCollector(data_dir=tmp_path)
    sessions = collector.collect()
    assert len(sessions) == 1

    s = sessions[0]
    assert s.session_id == "ses_001"
    assert s.agent == "opencode"
    assert s.model == "minimax-m2.1"
    assert s.message_count == 1  # Only assistant messages counted
    assert s.tokens.input_tokens == 300
    assert s.tokens.output_tokens == 100
    assert s.tokens.cache_read_tokens == 50
    assert s.tokens.cache_write_tokens == 10
