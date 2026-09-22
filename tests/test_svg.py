"""Tests for SVG renderers."""

from __future__ import annotations

from datetime import date
import xml.etree.ElementTree as ET

import pytest

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
from vibe_clock.svg.hourly import render_hourly
from vibe_clock.svg.token_bars import render_token_bars
from vibe_clock.svg.weekly import render_weekly


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
        longest_stretch_minutes=120.0,
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


def test_card_shows_agent_time_instead_of_active_agents() -> None:
    svg = render_card(_sample_stats(), theme="dark")

    assert "Active Agents" not in svg
    assert "claude_code, codex" not in svg
    # "Agent Time", not "Active Time": no log can tell whether a person was at
    # the keyboard, so the card must not imply one was.
    assert "Agent Time" in svg
    assert "Active Time" not in svg
    assert "10.0 hrs" in svg  # 600 minutes
    assert "Active Days" in svg


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


def test_donut_groups_models_beyond_eight() -> None:
    stats = AgentStats(
        models=[
            ModelBreakdown(model=f"model-{index}", session_count=1)
            for index in range(9)
        ]
    )

    svg = render_donut(stats)

    assert svg.count("<path") == 8
    assert "model-7" not in svg
    assert "model-8" not in svg
    assert "Other" in svg
    assert ">9</text>" in svg


def test_bars_renders_valid_svg() -> None:
    svg = render_bars(_sample_stats(), theme="dark")
    assert svg.startswith("<svg")
    assert "</svg>" in svg
    assert "Project A" in svg


def test_bars_uses_gemini_color() -> None:
    stats = AgentStats(
        projects=[
            ProjectBreakdown(
                project="Project Gemini",
                agent="gemini_cli",
                session_count=1,
            )
        ]
    )

    svg = render_bars(stats, theme="dark")

    assert 'fill="#8957e5"' in svg


def test_bars_empty() -> None:
    svg = render_bars(AgentStats(), theme="dark")
    assert "No project data" in svg


@pytest.mark.parametrize("theme", ["dark", "light"])
@pytest.mark.parametrize("renderer", [render_card, render_donut, render_token_bars, render_hourly, render_weekly])
def test_profile_charts_are_self_contained_and_escape_labels(renderer, theme) -> None:
    stats = _sample_stats()
    stats.favorite_model = '<model & "family">'
    stats.models[0].model = stats.favorite_model
    svg = renderer(stats, theme=theme)
    root = ET.fromstring(svg)
    ns = {"s": "http://www.w3.org/2000/svg"}
    assert root.find("s:title", ns) is not None
    assert root.find("s:desc", ns) is not None
    assert root.find(".//s:script", ns) is None
    assert root.find(".//s:foreignObject", ns) is None
    css = root.find("s:style", ns).text
    assert "prefers-reduced-motion: no-preference" in css
    assert "3.5s linear infinite" in css
    assert "scaleX" not in css and "scaleY" not in css
    assert ".vc-sweep { opacity: 0; }" in css  # Motion is opt-in; data stays visible.
    # Every highlight reference resolves to a data shape, never a label.
    ids = {element.get("id"): element for element in root.iter() if element.get("id")}
    for reference in root.findall(".//s:use", ns):
        target = ids[reference.attrib["href"][1:]]
        assert target.find(".//s:text", ns) is None
    assert root.find('.//s:mask', ns).get('style') == 'mask-type:alpha'
    if renderer in (render_card, render_donut, render_token_bars):
        assert stats.favorite_model in "".join(root.itertext())


@pytest.mark.parametrize("renderer", [render_card, render_donut, render_token_bars, render_hourly, render_weekly])
def test_profile_chart_labels_stay_readable_and_below_section_headings(renderer) -> None:
    root = ET.fromstring(renderer(_sample_stats()))
    ns = {"s": "http://www.w3.org/2000/svg"}
    for label in root.findall(".//s:text", ns):
        assert float(label.attrib["font-size"]) <= 18
        assert label.get("class") is None
    for animated in root.iter():
        if animated.get("class") in {"vc-reveal", "vc-x", "vc-y"}:
            assert animated.find(".//s:text", ns) is None


def test_single_model_donut_has_same_ring_bounds_as_segments() -> None:
    svg = render_donut(AgentStats(models=[ModelBreakdown(model="Only", session_count=1)]))
    root = ET.fromstring(svg)
    circle = root.find(".//{http://www.w3.org/2000/svg}circle")
    radius, stroke = float(circle.attrib["r"]), float(circle.attrib["stroke-width"])
    assert radius + stroke / 2 == 76
    assert radius - stroke / 2 == 55


def test_zero_token_model_has_no_visible_usage_bar() -> None:
    svg = render_token_bars(AgentStats(models=[ModelBreakdown(model="Zero")]))
    root = ET.fromstring(svg)
    bars = [element for element in root.iter() if element.get("class") == "vc-x"]
    assert len(bars) == 1
    assert float(bars[0].attrib["width"]) == 0
