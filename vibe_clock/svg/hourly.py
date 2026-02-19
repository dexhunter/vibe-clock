"""Hourly activity bar chart (0-23h)."""

from __future__ import annotations

from html import escape

from ..formatting import format_number
from ..models import AgentStats


def render_hourly(stats: AgentStats, theme: str = "dark") -> str:
    bg = "#0d1117" if theme == "dark" else "#ffffff"
    border = "#30363d" if theme == "dark" else "#d0d7de"
    muted = "#8b949e" if theme == "dark" else "#656d76"
    title_color = "#58a6ff" if theme == "dark" else "#0969da"
    bar_color = "#58a6ff" if theme == "dark" else "#0969da"
    bar_bg = "#21262d" if theme == "dark" else "#f6f8fa"

    hourly = stats.hourly if len(stats.hourly) == 24 else [0] * 24
    max_val = max(hourly) if any(hourly) else 1

    width = 495
    chart_top = 45
    chart_height = 120
    chart_left = 35
    chart_right = width - 20
    chart_width = chart_right - chart_left
    bar_gap = 2
    bar_w = (chart_width - bar_gap * 23) / 24
    bottom = chart_top + chart_height
    height = bottom + 35

    bars = []
    labels = []
    for h in range(24):
        x = chart_left + h * (bar_w + bar_gap)
        count = hourly[h]
        bar_h = (count / max_val) * chart_height if max_val else 0
        y = bottom - bar_h

        # Background bar
        bars.append(
            f'<rect x="{x:.1f}" y="{chart_top}" width="{bar_w:.1f}" '
            f'height="{chart_height}" rx="2" fill="{bar_bg}"/>'
        )
        # Value bar
        if bar_h > 0:
            bars.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" '
                f'height="{bar_h:.1f}" rx="2" fill="{bar_color}">'
                f'<title>{escape(f"{h}:00")} — {count} sessions</title></rect>'
            )

        # Hour labels (show every 3 hours)
        if h % 3 == 0:
            label_x = x + bar_w / 2
            labels.append(
                f'<text x="{label_x:.1f}" y="{bottom + 14}" '
                f'text-anchor="middle" fill="{muted}" font-size="9">'
                f'{h}:00</text>'
            )

    # Y-axis labels
    y_labels = []
    for frac, label in [(0, format_number(max_val)), (0.5, format_number(max_val // 2)), (1.0, "0")]:
        y = chart_top + frac * chart_height
        y_labels.append(
            f'<text x="{chart_left - 5}" y="{y + 3:.1f}" '
            f'text-anchor="end" fill="{muted}" font-size="9">{label}</text>'
        )

    bars_str = "\n    ".join(bars)
    labels_str = "\n    ".join(labels)
    y_labels_str = "\n    ".join(y_labels)

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="{width - 2}" height="{height - 2}" x="1" y="1" rx="4.5" fill="{bg}" stroke="{border}"/>
  <text x="20" y="28" fill="{title_color}" font-size="14" font-weight="700" font-family="Arial, Helvetica, sans-serif">
    Activity by Hour
  </text>
  <g font-family="Courier New, Courier, monospace">
    {y_labels_str}
    {bars_str}
    {labels_str}
  </g>
</svg>'''
