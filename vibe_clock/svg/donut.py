"""Model usage donut chart SVG renderer."""

from __future__ import annotations

import math
from html import escape

from ..formatting import format_number
from ..models import AgentStats, ModelBreakdown
from .style import colors, frame, motion

_PALETTE = [
    "#58a6ff", "#3fb950", "#d29922", "#f85149",
    "#bc8cff", "#39d353", "#db6d28", "#f778ba",
]


def render_donut(stats: AgentStats, theme: str = "dark") -> str:
    c = colors(theme)
    text_color, muted = c["text"], c["muted"]

    # Filter out placeholder/unknown models
    models = _display_models(stats)
    if not models:
        return frame(495, 180, "Model Usage", "No data available", theme) + "</svg>"

    total = sum(m.session_count for m in models)
    height = max(270, 85 + len(models) * 32)
    cx, cy, r = 120, (height + 65) / 2, 76
    inner_r = 55

    # Build pie segments
    segments = []
    angle = -90  # Start at top

    for i, m in enumerate(models):
        pct = m.session_count / total if total else 0
        sweep = pct * 360

        color = _PALETTE[i % len(_PALETTE)]
        if sweep > 0:
            segments.append(
                f'<g {motion("reveal", i)}><title>{escape(m.model)}: {m.session_count} sessions</title>'
                + _arc_path(cx, cy, r, inner_r, angle, sweep, color) + "</g>"
            )
        angle += sweep

    # Center text
    center = (
        f'<text x="{cx}" y="{cy - 5}" text-anchor="middle" '
        f'fill="{text_color}" font-size="18" font-weight="700">{format_number(total)}</text>'
        f'<text x="{cx}" y="{cy + 12}" text-anchor="middle" '
        f'fill="{muted}" font-size="11">sessions</text>'
    )

    # Legend
    legend_items = []
    for i, m in enumerate(models):
        color = _PALETTE[i % len(_PALETTE)]
        y = 85 + i * 32
        pct = m.session_count / total * 100 if total else 0
        short_name = m.model if len(m.model) <= 32 else m.model[:31] + "…"
        name = escape(short_name)
        legend_items.append(
            f'<g><title>{escape(m.model)}</title>'
            f'<rect x="230" y="{y - 8}" width="10" height="10" rx="2" fill="{color}"/>'
            f'<text x="246" y="{y}" fill="{text_color}" font-size="11">'
            f'{name}</text>'
            f'<text x="246" y="{y + 13}" fill="{muted}" font-size="9">'
            f'{format_number(m.session_count)} sessions · {pct:.0f}%</text></g>'
        )

    segments_str = "\n    ".join(segments)
    legend_str = "\n    ".join(legend_items)
    return (
        frame(495, height, "Model Usage", "Share of sessions by model", theme)
        + segments_str + center + legend_str + "</svg>"
    )


def _display_models(stats: AgentStats) -> list[ModelBreakdown]:
    """Limit the chart to eight complete categories without dropping sessions."""
    models = [
        model.model_copy(deep=True)
        for model in stats.models
        if model.model not in ("unknown", "<synthetic>")
    ]
    if len(models) <= 8:
        return models

    shown = models[:7]
    overflow_sessions = sum(model.session_count for model in models[7:])
    existing_other = next((model for model in shown if model.model == "Other"), None)
    if existing_other is not None:
        existing_other.session_count += overflow_sessions
    else:
        shown.append(ModelBreakdown(model="Other", session_count=overflow_sessions))
    return shown


def _arc_path(
    cx: float, cy: float,
    outer_r: float, inner_r: float,
    start_angle: float, sweep: float,
    color: str,
) -> str:
    """Create a donut arc path element."""
    if sweep >= 359.99:
        # Full circle — use two arcs
        return (
            f'<circle cx="{cx}" cy="{cy}" r="{(outer_r + inner_r) / 2}" fill="none" '
            f'stroke="{color}" stroke-width="{outer_r - inner_r}"/>'
        )

    sa = math.radians(start_angle)
    ea = math.radians(start_angle + sweep)
    large = 1 if sweep > 180 else 0

    ox1 = cx + outer_r * math.cos(sa)
    oy1 = cy + outer_r * math.sin(sa)
    ox2 = cx + outer_r * math.cos(ea)
    oy2 = cy + outer_r * math.sin(ea)
    ix1 = cx + inner_r * math.cos(ea)
    iy1 = cy + inner_r * math.sin(ea)
    ix2 = cx + inner_r * math.cos(sa)
    iy2 = cy + inner_r * math.sin(sa)

    d = (
        f"M {ox1:.1f} {oy1:.1f} "
        f"A {outer_r} {outer_r} 0 {large} 1 {ox2:.1f} {oy2:.1f} "
        f"L {ix1:.1f} {iy1:.1f} "
        f"A {inner_r} {inner_r} 0 {large} 0 {ix2:.1f} {iy2:.1f} Z"
    )
    return f'<path d="{d}" fill="{color}"/>'
