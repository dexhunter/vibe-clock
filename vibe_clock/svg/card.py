"""Stats summary card SVG renderer."""

from __future__ import annotations

from html import escape

from ..formatting import format_hours
from ..models import AgentStats
from .style import colors, frame, motion


def render_card(stats: AgentStats, theme: str = "dark") -> str:
    c = colors(theme)
    # Agent time measures emitting agents, not a person's keyboard activity.
    metrics = [
        ("Agent Time", format_hours(stats.total_minutes)),
        ("Sessions", str(stats.total_sessions)),
        ("Active Days", str(stats.active_days)),
        ("Top Model Family", stats.favorite_model or "—"),
    ]
    body = []
    for i, (label, value) in enumerate(metrics):
        x, y = 22 + (i % 2) * 232, 74 + (i // 2) * 78
        short_value = value if len(value) <= 21 else value[:20] + "…"
        size = 18 if len(short_value) <= 14 else 15
        body.append(
            f'<g><title>{escape(label)}: {escape(value)}</title>'
            f'<rect x="{x}" y="{y}" width="219" height="66" rx="9" fill="{c["panel"]}" {motion("reveal", i * 2)}/>'
            f'<text x="{x + 14}" y="{y + 21}" fill="{c["muted"]}" font-size="11">{label}</text>'
            f'<text x="{x + 14}" y="{y + 49}" fill="{c["blue"] if i == 0 else c["text"]}" '
            f'font-size="{size}" font-weight="650">{escape(short_value)}</text></g>'
        )
    subtitle = f"Last {stats.days_covered} complete days · Updated {stats.generated_at.date()}"
    return frame(495, 236, "Vibe Clock Stats", subtitle, theme) + "\n".join(body) + "</svg>"
