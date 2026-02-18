"""Weekly activity bar chart (Mon-Sun)."""

from __future__ import annotations

from collections import defaultdict

from ..models import AgentStats

_DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def render_weekly(stats: AgentStats, theme: str = "dark") -> str:
    bg = "#0d1117" if theme == "dark" else "#ffffff"
    border = "#30363d" if theme == "dark" else "#d0d7de"
    text_color = "#c9d1d9" if theme == "dark" else "#1f2328"
    muted = "#8b949e" if theme == "dark" else "#656d76"
    title_color = "#58a6ff" if theme == "dark" else "#0969da"
    bar_color = "#3fb950" if theme == "dark" else "#1a7f37"
    bar_bg = "#21262d" if theme == "dark" else "#f6f8fa"

    # Aggregate daily data by day-of-week (0=Mon, 6=Sun)
    dow_sessions: dict[int, int] = defaultdict(int)
    dow_minutes: dict[int, float] = defaultdict(float)
    for d in stats.daily:
        dow = d.date.weekday()
        dow_sessions[dow] += d.session_count
        dow_minutes[dow] += d.total_minutes

    max_sessions = max(dow_sessions.values()) if dow_sessions else 1

    width = 495
    chart_top = 45
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
        minutes = dow_minutes.get(i, 0)
        bar_h = (sessions / max_sessions) * chart_height if max_sessions else 0
        y = bottom - bar_h

        hours = minutes / 60

        # Background
        bars.append(
            f'<rect x="{x:.1f}" y="{chart_top}" width="{bar_w:.1f}" '
            f'height="{chart_height}" rx="3" fill="{bar_bg}"/>'
        )
        # Value bar
        if bar_h > 0:
            bars.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" '
                f'height="{bar_h:.1f}" rx="3" fill="{bar_color}">'
                f'<title>{_DAYS[i]}: {sessions} sessions, {hours:.1f}h</title></rect>'
            )
            # Count label above bar
            bars.append(
                f'<text x="{x + bar_w / 2:.1f}" y="{y - 4:.1f}" '
                f'text-anchor="middle" fill="{muted}" font-size="9">'
                f'{sessions}</text>'
            )

        # Day label
        labels.append(
            f'<text x="{x + bar_w / 2:.1f}" y="{bottom + 14}" '
            f'text-anchor="middle" fill="{text_color}" font-size="10">'
            f'{_DAYS[i]}</text>'
        )

    bars_str = "\n    ".join(bars)
    labels_str = "\n    ".join(labels)

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="{width - 2}" height="{height - 2}" x="1" y="1" rx="4.5" fill="{bg}" stroke="{border}"/>
  <text x="20" y="28" fill="{title_color}" font-size="14" font-weight="700" font-family="Arial, Helvetica, sans-serif">
    Activity by Day of Week
  </text>
  <g font-family="Courier New, Courier, monospace">
    {bars_str}
    {labels_str}
  </g>
</svg>'''
