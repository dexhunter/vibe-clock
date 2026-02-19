"""GitHub-style contribution heatmap SVG renderer."""

from __future__ import annotations

from datetime import date, timedelta
from html import escape

from ..models import AgentStats

_DARK_LEVELS = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
_LIGHT_LEVELS = ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"]

_MONTHS = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]
_DAYS = ["Mon", "", "Wed", "", "Fri", "", ""]


def render_heatmap(stats: AgentStats, theme: str = "dark") -> str:
    levels = _DARK_LEVELS if theme == "dark" else _LIGHT_LEVELS
    bg = "#0d1117" if theme == "dark" else "#ffffff"
    border = "#30363d" if theme == "dark" else "#d0d7de"
    text_color = "#8b949e" if theme == "dark" else "#656d76"

    # Build date -> session count map
    date_map: dict[date, int] = {}
    for d in stats.daily:
        date_map[d.date] = d.session_count

    # Calculate date range (last N days, aligned to weeks)
    today = date.today()
    # Go back to the start of the week (Monday) ~52 weeks ago
    start = today - timedelta(days=today.weekday()) - timedelta(weeks=52)

    # Find max for scaling
    max_count = max(date_map.values()) if date_map else 1

    def _level(count: int) -> int:
        if count == 0:
            return 0
        ratio = count / max_count
        if ratio <= 0.25:
            return 1
        if ratio <= 0.50:
            return 2
        if ratio <= 0.75:
            return 3
        return 4

    # Generate cells
    cells = []
    month_labels = []
    last_month = -1
    cell_size = 11
    gap = 2

    current = start
    col = 0
    while current <= today:
        dow = current.weekday()  # 0=Mon, 6=Sun
        if dow == 0 and current.month != last_month:
            x = 35 + col * (cell_size + gap)
            month_labels.append(
                f'<text x="{x}" y="20" fill="{text_color}" '
                f'font-size="10">{_MONTHS[current.month - 1]}</text>'
            )
            last_month = current.month

        count = date_map.get(current, 0)
        color = levels[_level(count)]
        x = 35 + col * (cell_size + gap)
        y = 30 + dow * (cell_size + gap)
        cells.append(
            f'<rect x="{x}" y="{y}" width="{cell_size}" height="{cell_size}" '
            f'rx="2" fill="{color}">'
            f'<title>{escape(str(current))}: {count} sessions</title></rect>'
        )

        # Move to next day
        current += timedelta(days=1)
        if current.weekday() == 0:
            col += 1

    width = 35 + (col + 1) * (cell_size + gap) + 15
    height = 30 + 7 * (cell_size + gap) + 30

    # Day labels
    day_labels = []
    for i, label in enumerate(_DAYS):
        if label:
            y = 30 + i * (cell_size + gap) + 9
            day_labels.append(
                f'<text x="5" y="{y}" fill="{text_color}" '
                f'font-size="9">{label}</text>'
            )

    # Legend
    legend_x = width - 120
    legend_y = height - 18
    legend = [
        f'<text x="{legend_x - 30}" y="{legend_y + 9}" fill="{text_color}" '
        f'font-size="9">Less</text>'
    ]
    for i, color in enumerate(levels):
        lx = legend_x + i * 15
        legend.append(
            f'<rect x="{lx}" y="{legend_y}" width="11" height="11" '
            f'rx="2" fill="{color}"/>'
        )
    legend.append(
        f'<text x="{legend_x + 80}" y="{legend_y + 9}" fill="{text_color}" '
        f'font-size="9">More</text>'
    )

    cells_str = "\n    ".join(cells)
    months_str = "\n    ".join(month_labels)
    days_str = "\n    ".join(day_labels)
    legend_str = "\n    ".join(legend)

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="{width - 2}" height="{height - 2}" x="1" y="1" rx="4.5" fill="{bg}" stroke="{border}"/>
  <g font-family="Arial, Helvetica, sans-serif">
    {months_str}
    {days_str}
    {cells_str}
    {legend_str}
  </g>
</svg>'''
