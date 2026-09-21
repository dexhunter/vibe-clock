"""Hourly activity bar chart (0-23h)."""

from __future__ import annotations

from html import escape

from ..formatting import format_number
from ..models import AgentStats
from .style import colors, frame, motion


def render_hourly(stats: AgentStats, theme: str = "dark") -> str:
    c = colors(theme)
    muted = c["muted"]
    bar_bg = c["panel"]

    hourly = stats.hourly if len(stats.hourly) == 24 else [0] * 24
    max_val = max(hourly) if any(hourly) else 1

    width = 495
    chart_top = 80
    chart_height = 120
    chart_left = 35
    chart_right = width - 20
    chart_width = chart_right - chart_left
    bar_gap = 4
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
                f'height="{bar_h:.1f}" rx="2" fill="url(#vc-blue)" {motion("y", h // 2)}>'
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

    subtitle = f"Sessions · last {stats.days_covered} complete days"
    return frame(width, height, "Activity by Hour", subtitle, theme) + f'''
{y_labels_str}
{bars_str}
{labels_str}
</svg>'''
