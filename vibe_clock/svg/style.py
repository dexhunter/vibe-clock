"""Shared presentation for the profile charts; no scripts or external assets."""

from html import escape


def colors(theme: str) -> dict[str, str]:
    if theme == "dark":
        return dict(bg="#0d1117", panel="#161e2b", border="#293548",
                    text="#e6edf3", muted="#9daec3", blue="#79b8ff", green="#56d4b0")
    return dict(bg="#ffffff", panel="#f0f5fb", border="#d0dbe8",
                text="#182b43", muted="#52647a", blue="#0969da", green="#087f66")


def motion(kind: str, index: int = 0) -> str:
    """Stagger repeating highlights without delaying long lists indefinitely."""
    return f'class="vc-{kind}" style="animation-delay:{min(index, 12) * 120}ms"'


def frame(width: int, height: int, title: str, subtitle: str, theme: str) -> str:
    """Open an SVG in its final, readable state when CSS motion is unavailable."""
    c = colors(theme)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="vc-title vc-desc">
  <title id="vc-title">{escape(title)}</title>
  <desc id="vc-desc">{escape(subtitle)}</desc>
  <defs>
    <linearGradient id="vc-blue" x1="0" y1="1" x2="1" y2="0">
      <stop stop-color="{c['blue']}" stop-opacity="0.6"/>
      <stop offset="1" stop-color="{c['blue']}"/>
    </linearGradient>
    <linearGradient id="vc-green" x1="0" y1="1" x2="1" y2="0">
      <stop stop-color="{c['green']}" stop-opacity="0.6"/>
      <stop offset="1" stop-color="{c['green']}"/>
    </linearGradient>
  </defs>
  <style>
    text {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif; }}
    @media (prefers-reduced-motion: no-preference) {{
      .vc-x, .vc-y, .vc-reveal {{ animation: vc-highlight 5s ease-in-out infinite both; }}
    }}
    @keyframes vc-highlight {{
      0%, 100% {{ opacity: 0.65; }}
      35%, 65% {{ opacity: 1; }}
    }}
  </style>
  <rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="14" fill="{c['bg']}" stroke="{c['border']}"/>
  <rect x="22" y="23" width="3" height="17" rx="1.5" fill="{c['blue']}"/>
  <text x="35" y="36" fill="{c['text']}" font-size="16" font-weight="650">{escape(title)}</text>
  <text x="22" y="56" fill="{c['muted']}" font-size="11">{escape(subtitle)}</text>
'''
