"""Tests for SVG renderers."""

from __future__ import annotations

from datetime import date

from vibe_clock.models import (
    AgentStats,
    DailyActivity,
    ModelBreakdown,
    ProjectBreakdown,
    TokenUsage,
)
from vibe_clock.svg.bars import render_bars
from vibe_clock.svg.card import render_card
from vibe_clock.svg.donut import render_donut
from vibe_clock.svg.heatmap import render_heatmap


def _sample_stats() -> AgentStats:
    return AgentStats(
        total_sessions=42,
        total_messages=1500,
        total_minutes=600.0,
        total_tokens=TokenUsage(
            input_tokens=50000,
            output_tokens=30000,
            cache_read_tokens=10000,
        ),
        active_agents=["claude_code", "codex"],
        favorite_model="claude-opus-4-6",
        peak_hour=14,
        longest_session_minutes=120.0,
        daily=[
            DailyActivity(
                date=date(2026, 2, 10),
                session_count=5,
                message_count=200,
                total_minutes=90.0,
            ),
            DailyActivity(
                date=date(2026, 2, 11),
                session_count=3,
                message_count=100,
                total_minutes=45.0,
            ),
        ],
        models=[
            ModelBreakdown(
                model="claude-opus-4-6",
                session_count=30,
                message_count=1000,
                total_minutes=400.0,
                tokens=TokenUsage(input_tokens=30000, output_tokens=20000),
            ),
            ModelBreakdown(
                model="gpt-5.1-codex",
                session_count=12,
                message_count=500,
                total_minutes=200.0,
                tokens=TokenUsage(input_tokens=20000, output_tokens=10000),
            ),
        ],
        projects=[
            ProjectBreakdown(
                project="Project A",
                agent="claude_code",
                session_count=20,
                total_minutes=300.0,
            ),
            ProjectBreakdown(
                project="Project B",
                agent="codex",
                session_count=12,
                total_minutes=200.0,
            ),
        ],
    )


def test_card_renders_valid_svg() -> None:
    svg = render_card(_sample_stats(), theme="dark")
    assert svg.startswith("<svg")
    assert "</svg>" in svg
    assert "Vibe Clock Stats" in svg
    assert "42" in svg  # total sessions


def test_card_light_theme() -> None:
    svg = render_card(_sample_stats(), theme="light")
    assert "#ffffff" in svg


def test_heatmap_renders_valid_svg() -> None:
    svg = render_heatmap(_sample_stats(), theme="dark")
    assert svg.startswith("<svg")
    assert "</svg>" in svg
    assert "Less" in svg
    assert "More" in svg


def test_donut_renders_valid_svg() -> None:
    svg = render_donut(_sample_stats(), theme="dark")
    assert svg.startswith("<svg")
    assert "</svg>" in svg
    assert "claude-opus-4-6" in svg
    assert "Model Usage" in svg


def test_donut_empty() -> None:
    svg = render_donut(AgentStats(), theme="dark")
    assert "No data" in svg


def test_bars_renders_valid_svg() -> None:
    svg = render_bars(_sample_stats(), theme="dark")
    assert svg.startswith("<svg")
    assert "</svg>" in svg
    assert "Project A" in svg


def test_bars_empty() -> None:
    svg = render_bars(AgentStats(), theme="dark")
    assert "No project data" in svg
