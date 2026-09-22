"""Shared presentation for the profile charts; no scripts or external assets."""

from collections.abc import Iterable
from html import escape


def colors(theme: str) -> dict[str, str]:
    if theme == "dark":
        return dict(bg="#0d1117", panel="#161e2b", border="#293548",
                    text="#e6edf3", muted="#9daec3", blue="#79b8ff", green="#56d4b0")
    return dict(bg="#ffffff", panel="#f0f5fb", border="#d0dbe8",
                text="#182b43", muted="#52647a", blue="#0969da", green="#087f66")


def motion(kind: str, index: int = 0) -> str:
    """Give a data shape a stable reference for the moving highlight."""
    return f'id="vc-{kind}-{index}" class="vc-{kind}"'


def sheen(kind: str, indices: Iterable[int], width: int, height: int, opacity: float = 1) -> str:
    """Sweep a highlight over data shapes only, preserving their geometry."""
    shapes = "".join(f'<use href="#vc-{kind}-{index}"/>' for index in indices)
    return f'''<defs>
  <mask id="vc-data" maskUnits="userSpaceOnUse" x="0" y="0" width="{width}" height="{height}" style="mask-type:alpha">{shapes}</mask>
</defs>
<g mask="url(#vc-data)" opacity="{opacity}" aria-hidden="true" pointer-events="none">
  <rect class="vc-sweep" x="-130" y="0" width="130" height="{height}" fill="url(#vc-sheen)"/>
</g>'''


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
    <linearGradient id="vc-sheen">
      <stop stop-color="#ffffff" stop-opacity="0"/>
      <stop offset="0.5" stop-color="#ffffff" stop-opacity="0.85"/>
      <stop offset="1" stop-color="#ffffff" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <style>
    text {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif; }}
    .vc-sweep {{ opacity: 0; }}
    @media (prefers-reduced-motion: no-preference) {{
      .vc-sweep {{ opacity: 1; animation: vc-sweep 3.5s linear infinite; }}
    }}
    @keyframes vc-sweep {{
      from {{ transform: translateX(0); }}
      to {{ transform: translateX({width + 130}px); }}
    }}
  </style>
  <rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="14" fill="{c['bg']}" stroke="{c['border']}"/>
  <rect x="22" y="23" width="3" height="17" rx="1.5" fill="{c['blue']}"/>
  <text x="35" y="36" fill="{c['text']}" font-size="16" font-weight="650">{escape(title)}</text>
  <text x="22" y="56" fill="{c['muted']}" font-size="11">{escape(subtitle)}</text>
'''
