"""Human-readable number formatting utilities."""

from __future__ import annotations


def format_number(n: int | float) -> str:
    """Format large numbers with K/M/B suffixes."""
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.1f}B".replace(".0B", "B")
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M".replace(".0M", "M")
    if n >= 1_000:
        return f"{n / 1_000:.1f}K".replace(".0K", "K")
    return str(int(n))


def format_bar(
    value: float,
    max_value: float,
    width: int = 20,
    filled_style: str = "cyan",
    empty_style: str = "dim",
) -> str:
    """Return a Rich-markup Unicode bar: ████░░░░."""
    if max_value <= 0:
        filled = 0
    else:
        filled = round(width * value / max_value)
    filled = max(0, min(width, filled))
    empty = width - filled
    return (
        f"[{filled_style}]{'█' * filled}[/{filled_style}]"
        f"[{empty_style}]{'░' * empty}[/{empty_style}]"
    )


def format_hours(minutes: float) -> str:
    """Format minutes as 'X.Y hrs'."""
    return f"{minutes / 60:.1f} hrs"


def format_hourly_chart(
    hourly: list[int],
    height: int = 6,
    peak_hour: int = -1,
) -> str:
    """Build a vertical Unicode bar chart for 24 hourly buckets.

    Returns a multi-line string with Rich markup.
    Uses block characters: ▁▂▃▄▅▆▇█
    """
    blocks = " ▁▂▃▄▅▆▇█"
    max_val = max(hourly) if hourly else 0
    if max_val == 0:
        return "[dim]No hourly data[/dim]"

    lines: list[str] = []

    # Build rows from top to bottom
    for row in range(height, 0, -1):
        label = ""
        if row == height:
            label = f"{max_val:>3} ┤"
        elif row == height // 2:
            label = f"{max_val // 2:>3} ┤"
        else:
            label = "    │"

        chars: list[str] = []
        for h in range(24):
            val = hourly[h]
            # Fraction of this bar that falls in this row
            row_bottom = max_val * (row - 1) / height
            row_top = max_val * row / height
            if val >= row_top:
                block = blocks[8]  # full
            elif val > row_bottom:
                frac = (val - row_bottom) / (row_top - row_bottom)
                idx = max(1, round(frac * 8))
                block = blocks[idx]
            else:
                block = " "

            style = "bold yellow" if h == peak_hour else "cyan"
            chars.append(f"[{style}]{block}[/{style}] ")

        lines.append(f"{label} {''.join(chars)}")

    # X-axis
    x_axis = "    └─"
    for h in range(24):
        if h % 6 == 0:
            x_axis += f"{h:02d}───"
        else:
            x_axis += "─────"
    lines.append(x_axis)

    return "\n".join(lines)
