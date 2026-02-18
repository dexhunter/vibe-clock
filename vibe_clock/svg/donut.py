"""Model usage donut chart SVG renderer."""

from __future__ import annotations

import math
from html import escape

from ..models import AgentStats

_PALETTE = [
    "#58a6ff", "#3fb950", "#d29922", "#f85149",
    "#bc8cff", "#39d353", "#db6d28", "#f778ba",
]


def render_donut(stats: AgentStats, theme: str = "dark") -> str:
    bg = "#0d1117" if theme == "dark" else "#ffffff"
    border = "#30363d" if theme == "dark" else "#d0d7de"
    text_color = "#c9d1d9" if theme == "dark" else "#1f2328"
    muted = "#8b949e" if theme == "dark" else "#656d76"
    title_color = "#58a6ff" if theme == "dark" else "#0969da"

    # Filter out placeholder/unknown models
    models = [m for m in stats.models if m.model not in ("unknown", "<synthetic>")]
    if not models:
        return _empty_donut(bg, border, text_color, title_color)

    total = sum(m.session_count for m in models)
    cx, cy, r = 120, 130, 70
    inner_r = 45

    # Build pie segments
    segments = []
    angle = -90  # Start at top

    for i, m in enumerate(models[:8]):  # Max 8 segments
        pct = m.session_count / total if total else 0
        sweep = pct * 360

        color = _PALETTE[i % len(_PALETTE)]
        segments.append(_arc_path(cx, cy, r, inner_r, angle, sweep, color))
        angle += sweep

    # Center text
    center = (
        f'<text x="{cx}" y="{cy - 5}" text-anchor="middle" '
        f'fill="{text_color}" font-size="18" font-weight="700">{total}</text>'
        f'<text x="{cx}" y="{cy + 12}" text-anchor="middle" '
        f'fill="{muted}" font-size="10">sessions</text>'
    )

    # Legend
    legend_items = []
    for i, m in enumerate(models[:8]):
        color = _PALETTE[i % len(_PALETTE)]
        y = 55 + i * 22
        pct = m.session_count / total * 100 if total else 0
        name = escape(m.model)
        legend_items.append(
            f'<rect x="260" y="{y - 8}" width="10" height="10" rx="2" fill="{color}"/>'
            f'<text x="276" y="{y}" fill="{text_color}" font-size="11">'
            f'{name}</text>'
            f'<text x="276" y="{y + 13}" fill="{muted}" font-size="9">'
            f'{m.session_count} ({pct:.0f}%)</text>'
        )

    segments_str = "\n    ".join(segments)
    legend_str = "\n    ".join(legend_items)
    width = 480
    height = max(260, 55 + len(models[:8]) * 22 + 20)

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="{width - 2}" height="{height - 2}" x="1" y="1" rx="4.5" fill="{bg}" stroke="{border}"/>
  <text x="20" y="28" fill="{title_color}" font-size="14" font-weight="700" font-family="Arial, Helvetica, sans-serif">
    Model Usage
  </text>
  <g font-family="Arial, Helvetica, sans-serif">
    {segments_str}
    {center}
    {legend_str}
  </g>
</svg>'''


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
            f'<circle cx="{cx}" cy="{cy}" r="{outer_r}" fill="none" '
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


def _empty_donut(bg: str, border: str, text: str, title: str) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="480" height="200" viewBox="0 0 480 200">
  <rect width="478" height="198" x="1" y="1" rx="4.5" fill="{bg}" stroke="{border}"/>
  <text x="240" y="100" text-anchor="middle" fill="{text}" font-size="14"
        font-family="Arial, Helvetica, sans-serif">No data available</text>
</svg>'''
