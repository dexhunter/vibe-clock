"""Horizontal bar chart for token usage per model."""

from __future__ import annotations

from html import escape

from ..formatting import format_number
from ..models import AgentStats

_PALETTE = [
    "#58a6ff", "#3fb950", "#d29922", "#f85149",
    "#bc8cff", "#39d353", "#db6d28", "#f778ba",
]


def render_token_bars(stats: AgentStats, theme: str = "dark") -> str:
    bg = "#0d1117" if theme == "dark" else "#ffffff"
    border = "#30363d" if theme == "dark" else "#d0d7de"
    text_color = "#c9d1d9" if theme == "dark" else "#1f2328"
    muted = "#8b949e" if theme == "dark" else "#656d76"
    title_color = "#58a6ff" if theme == "dark" else "#0969da"
    bar_bg = "#21262d" if theme == "dark" else "#f6f8fa"

    models = [m for m in stats.models if m.model not in ("unknown", "<synthetic>")]
    if not models:
        return _empty(bg, border, text_color, title_color)

    max_tokens = max(m.tokens.total for m in models) or 1
    bar_width = 250
    bar_height = 18
    row_height = 32
    label_x = 20
    bar_x = 190
    width = 495
    height = 50 + len(models) * row_height + 10

    rows = []
    for i, m in enumerate(models):
        y = 50 + i * row_height
        pct = m.tokens.total / max_tokens
        w = max(pct * bar_width, 2)
        color = _PALETTE[i % len(_PALETTE)]
        label = format_number(m.tokens.total)

        name = escape(m.model)
        rows.append(
            f'<text x="{label_x}" y="{y + 13}" fill="{text_color}" '
            f'font-size="11">{name}</text>'
            f'<rect x="{bar_x}" y="{y}" width="{bar_width}" '
            f'height="{bar_height}" rx="3" fill="{bar_bg}"/>'
            f'<rect x="{bar_x}" y="{y}" width="{w:.0f}" '
            f'height="{bar_height}" rx="3" fill="{color}"/>'
            f'<text x="{bar_x + bar_width + 8}" y="{y + 13}" '
            f'fill="{muted}" font-size="10">{label}</text>'
        )

    rows_str = "\n    ".join(rows)

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="{width - 2}" height="{height - 2}" x="1" y="1" rx="4.5" fill="{bg}" stroke="{border}"/>
  <text x="20" y="28" fill="{title_color}" font-size="14" font-weight="700" font-family="Arial, Helvetica, sans-serif">
    Token Usage by Model
  </text>
  <g font-family="Courier New, Courier, monospace">
    {rows_str}
  </g>
</svg>'''


def _empty(bg: str, border: str, text: str, title: str) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="495" height="200" viewBox="0 0 495 200">
  <rect width="493" height="198" x="1" y="1" rx="4.5" fill="{bg}" stroke="{border}"/>
  <text x="247" y="100" text-anchor="middle" fill="{text}" font-size="14"
        font-family="Arial, Helvetica, sans-serif">No token data</text>
</svg>'''
