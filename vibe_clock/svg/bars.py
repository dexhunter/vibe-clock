"""Horizontal bar chart for project breakdown."""

from __future__ import annotations

from ..models import AgentStats

_AGENT_COLORS = {
    "claude_code": "#58a6ff",
    "codex": "#3fb950",
    "opencode": "#d29922",
}


def render_bars(stats: AgentStats, theme: str = "dark") -> str:
    bg = "#0d1117" if theme == "dark" else "#ffffff"
    border = "#30363d" if theme == "dark" else "#d0d7de"
    text_color = "#c9d1d9" if theme == "dark" else "#1f2328"
    muted = "#8b949e" if theme == "dark" else "#656d76"
    title_color = "#58a6ff" if theme == "dark" else "#0969da"
    bar_bg = "#21262d" if theme == "dark" else "#f6f8fa"

    projects = stats.projects[:10]  # Top 10
    if not projects:
        return _empty_bars(bg, border, text_color, title_color)

    max_minutes = max(p.total_minutes for p in projects) or 1
    bar_width = 300
    bar_height = 18
    row_height = 32
    label_x = 20
    bar_x = 140
    width = 480
    height = 50 + len(projects) * row_height + 30

    rows = []
    for i, p in enumerate(projects):
        y = 50 + i * row_height
        pct = p.total_minutes / max_minutes
        w = max(pct * bar_width, 2)
        color = _AGENT_COLORS.get(p.agent, "#8b949e")
        hours = p.total_minutes / 60

        rows.append(
            f'<text x="{label_x}" y="{y + 13}" fill="{text_color}" '
            f'font-size="11">{p.project}</text>'
            f'<rect x="{bar_x}" y="{y}" width="{bar_width}" '
            f'height="{bar_height}" rx="3" fill="{bar_bg}"/>'
            f'<rect x="{bar_x}" y="{y}" width="{w:.0f}" '
            f'height="{bar_height}" rx="3" fill="{color}"/>'
            f'<text x="{bar_x + bar_width + 8}" y="{y + 13}" '
            f'fill="{muted}" font-size="10">{hours:.1f}h</text>'
        )

    # Legend
    legend_y = height - 22
    legend_items = []
    lx = 20
    for agent, color in _AGENT_COLORS.items():
        legend_items.append(
            f'<rect x="{lx}" y="{legend_y}" width="8" height="8" '
            f'rx="1" fill="{color}"/>'
            f'<text x="{lx + 12}" y="{legend_y + 8}" fill="{muted}" '
            f'font-size="9">{agent}</text>'
        )
        lx += len(agent) * 6 + 25

    rows_str = "\n    ".join(rows)
    legend_str = "\n    ".join(legend_items)

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="{width - 2}" height="{height - 2}" x="1" y="1" rx="4.5" fill="{bg}" stroke="{border}"/>
  <text x="20" y="28" fill="{title_color}" font-size="14" font-weight="700" font-family="Arial, Helvetica, sans-serif">
    Projects
  </text>
  <g font-family="Courier New, Courier, monospace">
    {rows_str}
    {legend_str}
  </g>
</svg>'''


def _empty_bars(bg: str, border: str, text: str, title: str) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="480" height="200" viewBox="0 0 480 200">
  <rect width="478" height="198" x="1" y="1" rx="4.5" fill="{bg}" stroke="{border}"/>
  <text x="240" y="100" text-anchor="middle" fill="{text}" font-size="14"
        font-family="Arial, Helvetica, sans-serif">No project data</text>
</svg>'''
