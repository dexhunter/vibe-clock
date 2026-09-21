"""Horizontal bar chart for token usage per model."""

from __future__ import annotations

from html import escape

from ..formatting import format_number
from ..models import AgentStats
from .style import colors, frame, motion

_PALETTE = [
    "#58a6ff", "#3fb950", "#d29922", "#f85149",
    "#bc8cff", "#39d353", "#db6d28", "#f778ba",
]


def render_token_bars(stats: AgentStats, theme: str = "dark") -> str:
    c = colors(theme)
    text_color, muted, bar_bg = c["text"], c["muted"], c["panel"]

    models = sorted(
        (m for m in stats.models if m.model not in ("unknown", "<synthetic>")),
        key=lambda model: model.tokens.total,
        reverse=True,
    )
    if not models:
        return frame(495, 160, "Token Usage by Model", "No token data", theme) + "</svg>"

    max_tokens = max(m.tokens.total for m in models) or 1
    bar_width = 210
    bar_height = 18
    row_height = 36
    label_x = 20
    bar_x = 190
    width = 495
    height = 82 + len(models) * row_height + 10

    rows = []
    for i, m in enumerate(models):
        y = 78 + i * row_height
        pct = m.tokens.total / max_tokens
        w = pct * bar_width
        color = _PALETTE[i % len(_PALETTE)]
        label = format_number(m.tokens.total)

        short_name = m.model if len(m.model) <= 24 else m.model[:23] + "…"
        name = escape(short_name)
        rows.append(
            f'<g><title>{escape(m.model)}: {m.tokens.total} tokens</title>'
            f'<text x="{label_x}" y="{y + 13}" fill="{text_color}" '
            f'font-size="11">{name}</text>'
            f'<rect x="{bar_x}" y="{y}" width="{bar_width}" '
            f'height="{bar_height}" rx="3" fill="{bar_bg}"/>'
            f'<rect x="{bar_x}" y="{y}" width="{w:.0f}" '
            f'height="{bar_height}" rx="3" fill="{color}" {motion("x", i)}/>'
            f'<text x="475" text-anchor="end" y="{y + 13}" '
            f'fill="{muted}" font-size="10">{label}</text></g>'
        )

    rows_str = "\n    ".join(rows)

    subtitle = "Input + output + cached tokens"
    return frame(width, height, "Token Usage by Model", subtitle, theme) + rows_str + "</svg>"
