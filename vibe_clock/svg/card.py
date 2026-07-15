"""Stats summary card SVG renderer."""

from __future__ import annotations

from html import escape

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

    rows = [
        ("Sessions", str(stats.total_sessions)),
        ("Active Days", str(stats.active_days)),
        ("Top Model Family", escape(stats.favorite_model) if stats.favorite_model else "—"),
        ("Active Agents", escape(", ".join(stats.active_agents)) or "—"),
    ]

    row_svgs = []
    for i, (label, value) in enumerate(rows):
        row_y = 52 + i * 22
        row_svgs.append(
            f'<text x="20" y="{row_y}" fill="{c["muted"]}" '
            f'font-size="12">{label}:</text>'
            f'<text x="170" y="{row_y}" fill="{c["text"]}" '
            f'font-size="12" font-weight="600">{value}</text>'
        )

    body = "\n    ".join(row_svgs)
    footer = f"Last {stats.days_covered} complete days · Updated {stats.generated_at.date()}"
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="495" height="158" viewBox="0 0 495 158">
  <rect width="493" height="156" x="1" y="1" rx="4.5" fill="{c["bg"]}" stroke="{c["border"]}"/>
  <text x="20" y="30" fill="{c["title"]}" font-size="16" font-weight="700" font-family="Arial, Helvetica, sans-serif">
    ⏱ Vibe Clock Stats
  </text>
  <line x1="20" y1="38" x2="475" y2="38" stroke="{c["border"]}" stroke-width="0.5"/>
  <g font-family="Courier New, Courier, monospace">
    {body}
  </g>
  <text x="20" y="146" fill="{c["muted"]}" font-size="10" font-family="Arial, Helvetica, sans-serif">
    {footer}
  </text>
</svg>'''
