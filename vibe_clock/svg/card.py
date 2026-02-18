"""Stats summary card SVG renderer."""

from __future__ import annotations

from ..models import AgentStats

_DARK = {
    "bg": "#0d1117",
    "border": "#30363d",
    "title": "#58a6ff",
    "text": "#c9d1d9",
    "muted": "#8b949e",
    "icon": "#58a6ff",
}
_LIGHT = {
    "bg": "#ffffff",
    "border": "#d0d7de",
    "title": "#0969da",
    "text": "#1f2328",
    "muted": "#656d76",
    "icon": "#0969da",
}


def render_card(stats: AgentStats, theme: str = "dark") -> str:
    c = _DARK if theme == "dark" else _LIGHT
    hours = stats.total_minutes / 60
    tokens_k = stats.total_tokens.total / 1000

    rows = [
        ("Total Time", f"{hours:.1f} hrs"),
        ("Sessions", str(stats.total_sessions)),
        ("Messages", f"{stats.total_messages:,}"),
        ("Tokens", f"{tokens_k:,.0f}K"),
        ("Favorite Model", stats.favorite_model or "—"),
        ("Peak Hour", f"{stats.peak_hour}:00"),
        ("Active Agents", ", ".join(stats.active_agents) or "—"),
        ("Longest Session", f"{stats.longest_session_minutes:.0f} min"),
    ]

    row_svgs = []
    for i, (label, value) in enumerate(rows):
        col_x = 20 if i < 4 else 270
        row_y = 52 + (i % 4) * 22
        row_svgs.append(
            f'<text x="{col_x}" y="{row_y}" fill="{c["muted"]}" '
            f'font-size="12">{label}:</text>'
            f'<text x="{col_x + 120}" y="{row_y}" fill="{c["text"]}" '
            f'font-size="12" font-weight="600">{value}</text>'
        )

    body = "\n    ".join(row_svgs)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="495" height="155" viewBox="0 0 495 155">
  <rect width="493" height="153" x="1" y="1" rx="4.5" fill="{c["bg"]}" stroke="{c["border"]}"/>
  <text x="20" y="30" fill="{c["title"]}" font-size="16" font-weight="700" font-family="Arial, Helvetica, sans-serif">
    ⏱ Vibe Clock Stats
  </text>
  <line x1="20" y1="38" x2="475" y2="38" stroke="{c["border"]}" stroke-width="0.5"/>
  <g font-family="Courier New, Courier, monospace">
    {body}
  </g>
</svg>'''
