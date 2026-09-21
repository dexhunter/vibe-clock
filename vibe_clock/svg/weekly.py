"""Weekly activity bar chart (Mon-Sun)."""

from __future__ import annotations

from collections import defaultdict
from html import escape

from ..formatting import format_number
from ..models import AgentStats
from .style import colors, frame, motion

_DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def render_weekly(stats: AgentStats, theme: str = "dark") -> str:
    c = colors(theme)
    muted = c["muted"]
    bar_bg = c["panel"]
    text_color = c["text"]

    # Aggregate daily data by day-of-week (0=Mon, 6=Sun)
    dow_sessions: dict[int, int] = defaultdict(int)
    for d in stats.daily:
        dow = d.date.weekday()
        dow_sessions[dow] += d.session_count

    max_sessions = max(dow_sessions.values()) if dow_sessions else 1

    width = 495
    chart_top = 80
    chart_height = 120
    chart_left = 50
    chart_right = width - 20
    chart_width = chart_right - chart_left
    bar_gap = 12
    bar_w = (chart_width - bar_gap * 6) / 7
    bottom = chart_top + chart_height
    height = bottom + 35

    bars = []
    labels = []
    for i in range(7):
        x = chart_left + i * (bar_w + bar_gap)
        sessions = dow_sessions.get(i, 0)
        bar_h = (sessions / max_sessions) * chart_height if max_sessions else 0
        y = bottom - bar_h

        # Background
        bars.append(
            f'<rect x="{x:.1f}" y="{chart_top}" width="{bar_w:.1f}" '
            f'height="{chart_height}" rx="3" fill="{bar_bg}"/>'
        )
        # Value bar
        if bar_h > 0:
            bars.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" '
                f'height="{bar_h:.1f}" rx="3" fill="url(#vc-green)" {motion("y", i)}>'
                f'<title>{escape(_DAYS[i])}: {sessions} sessions</title></rect>'
            )
            # Count label above bar
            bars.append(
                f'<text x="{x + bar_w / 2:.1f}" y="{y - 4:.1f}" '
                f'text-anchor="middle" fill="{muted}" font-size="9">'
                f'{format_number(sessions)}</text>'
            )

        # Day label
        labels.append(
            f'<text x="{x + bar_w / 2:.1f}" y="{bottom + 14}" '
            f'text-anchor="middle" fill="{text_color}" font-size="10">'
            f'{_DAYS[i]}</text>'
        )

    bars_str = "\n    ".join(bars)
    labels_str = "\n    ".join(labels)

    subtitle = f"Sessions · last {stats.days_covered} complete days"
    return frame(width, height, "Activity by Day of Week", subtitle, theme) + f'''
{bars_str}
{labels_str}
</svg>'''
