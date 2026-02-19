"""CLI entry point for vibe-clock."""

from __future__ import annotations

import sys
from pathlib import Path

import click
import rich.box as box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from . import __version__
from .aggregator import aggregate
from .collectors import get_collectors
from .formatting import format_bar, format_hourly_chart, format_hours, format_number
from .config import Config, load_config, save_config
from .models import AgentStats
from .sanitizer import preview, sanitize
from .svg.bars import render_bars
from .svg.card import render_card
from .svg.donut import render_donut
from .svg.heatmap import render_heatmap
from .svg.hourly import render_hourly
from .svg.token_bars import render_token_bars
from .svg.weekly import render_weekly

console = Console()

SVG_RENDERERS = {
    "card": ("vibe-clock-card.svg", render_card),
    "heatmap": ("vibe-clock-heatmap.svg", render_heatmap),
    "donut": ("vibe-clock-donut.svg", render_donut),
    "bars": ("vibe-clock-bars.svg", render_bars),
    "token_bars": ("vibe-clock-token-bars.svg", render_token_bars),
    "hourly": ("vibe-clock-hourly.svg", render_hourly),
    "weekly": ("vibe-clock-weekly.svg", render_weekly),
}


@click.group()
@click.version_option(version=__version__)
def cli() -> None:
    """vibe-clock: Track AI coding agent usage."""


@cli.command()
def init() -> None:
    """Interactive setup — create config file."""
    console.print("[bold]vibe-clock init[/bold]")

    config = Config()

    # Auto-detect available agents
    available = []
    for name, path in [
        ("claude_code", config.paths.claude_code),
        ("codex", config.paths.codex),
        ("opencode", config.paths.opencode),
    ]:
        if path.exists():
            available.append(name)
            console.print(f"  [green]✓[/green] Found {name} at {path}")
        else:
            console.print(f"  [dim]✗ {name} not found at {path}[/dim]")

    config.enabled_agents = available

    # Ask for GitHub token
    token = click.prompt(
        "\nGitHub token (PAT with 'gist' scope, or press Enter to skip)",
        default="",
        show_default=False,
        hide_input=True,
    )
    if token:
        config.github.token = token

    save_config(config)
    from .config import CONFIG_PATH
    console.print(f"\n[green]Config saved to {CONFIG_PATH}[/green]")


@cli.command()
@click.option("--days", "-d", default=None, type=int, help="Number of days to include.")
def summary(days: int | None) -> None:
    """Show a summary of AI agent usage."""
    config = load_config()
    if days:
        config.default_days = days

    collectors = get_collectors(config)
    if not collectors:
        console.print("[yellow]No agent data found. Run 'vibe-clock init' first.[/yellow]")
        return

    all_sessions = []
    for c in collectors:
        sessions = c.collect()
        console.print(f"  [dim]{c.agent_name}: {len(sessions)} sessions[/dim]")
        all_sessions.extend(sessions)

    stats = aggregate(all_sessions, config)

    # Header
    header = Text()
    header.append("  ⏱  V I B E   C L O C K", style="bold cyan")
    header.append(f"  Last {config.default_days} Days", style="dim")
    console.print(Panel(header, box=box.ROUNDED, border_style="cyan"))

    # Overview
    _print_overview(stats)

    # Token Breakdown
    if stats.total_tokens.total > 0:
        _print_token_breakdown(stats)

    # Hourly Activity
    if any(stats.hourly):
        _print_hourly(stats)

    # Models
    if stats.models:
        _print_models(stats)

    # Projects
    if stats.projects:
        _print_projects(stats)

    # Footer
    console.print(f"[dim]Generated {stats.generated_at:%Y-%m-%d %H:%M} UTC[/dim]")


def _print_overview(stats: "AgentStats") -> None:
    t = Table(show_header=False, box=None, padding=(0, 2))
    t.add_column(style="cyan")
    t.add_column(style="bold white")
    t.add_column(style="cyan")
    t.add_column(style="bold white")
    t.add_row(
        "⏱  Total Time",
        format_hours(stats.total_minutes),
        "🤖 Favorite Model",
        stats.favorite_model or "—",
    )
    t.add_row(
        "💬 Sessions",
        str(stats.total_sessions),
        "🕐 Peak Hour",
        f"{stats.peak_hour}:00",
    )
    t.add_row(
        "📨 Messages",
        format_number(stats.total_messages),
        "🔥 Longest Session",
        f"{stats.longest_session_minutes:.0f} min",
    )
    t.add_row(
        "🔢 Tokens",
        format_number(stats.total_tokens.total),
        "🛠  Active Agents",
        ", ".join(stats.active_agents) or "—",
    )
    console.print(Panel(t, title="Overview", box=box.ROUNDED, border_style="blue"))


def _print_token_breakdown(stats: "AgentStats") -> None:
    total = stats.total_tokens.total
    parts = [
        ("Input", stats.total_tokens.input_tokens, "cyan"),
        ("Output", stats.total_tokens.output_tokens, "green"),
        ("Cache R", stats.total_tokens.cache_read_tokens, "yellow"),
        ("Cache W", stats.total_tokens.cache_write_tokens, "magenta"),
    ]
    t = Table(show_header=False, box=None, padding=(0, 1))
    t.add_column(style="bold", width=10)
    t.add_column(width=50)
    t.add_column(justify="right", width=8)
    t.add_column(justify="right", width=6)
    for label, value, color in parts:
        pct = (value / total * 100) if total > 0 else 0
        bar = format_bar(value, total, width=30, filled_style=color)
        t.add_row(label, bar, format_number(value), f"({pct:.0f}%)")
    console.print(Panel(t, title="Token Breakdown", box=box.ROUNDED, border_style="blue"))


def _print_hourly(stats: "AgentStats") -> None:
    chart = format_hourly_chart(stats.hourly, height=6, peak_hour=stats.peak_hour)
    console.print(Panel(chart, title="Hourly Activity", box=box.ROUNDED, border_style="blue"))


def _print_models(stats: "AgentStats") -> None:
    filtered = [
        m for m in stats.models if m.model not in ("unknown", "<synthetic>")
    ][:8]
    if not filtered:
        return
    total_tokens = sum(m.tokens.total for m in filtered)
    t = Table(box=None, padding=(0, 1))
    t.add_column("Model", style="bold")
    t.add_column("Sessions", justify="right")
    t.add_column("Messages", justify="right")
    t.add_column("Tokens", justify="right")
    t.add_column("Share", width=22)
    for m in filtered:
        share = (m.tokens.total / total_tokens * 100) if total_tokens > 0 else 0
        bar = format_bar(m.tokens.total, total_tokens, width=14, filled_style="cyan")
        t.add_row(
            m.model,
            f"{m.session_count:,}",
            f"{m.message_count:,}",
            format_number(m.tokens.total),
            f"{bar} {share:.0f}%",
        )
    console.print(Panel(t, title="Models", box=box.ROUNDED, border_style="blue"))


def _print_projects(stats: "AgentStats") -> None:
    projects = stats.projects[:8]
    if not projects:
        return
    t = Table(box=None, padding=(0, 1))
    t.add_column("Project", style="bold")
    t.add_column("Agent")
    t.add_column("Time", justify="right")
    t.add_column("Sessions", justify="right")
    t.add_column("Tokens", justify="right")
    for p in projects:
        name = p.project.split("/")[-1][:24]
        t.add_row(
            name,
            p.agent,
            format_hours(p.total_minutes),
            str(p.session_count),
            format_number(p.tokens.total),
        )
    console.print(Panel(t, title="Projects", box=box.ROUNDED, border_style="blue"))


@cli.command()
@click.option("--days", "-d", default=None, type=int, help="Number of days to include.")
def status(days: int | None) -> None:
    """Print a compact one-line status summary."""
    config = load_config()
    if days:
        config.default_days = days

    collectors = get_collectors(config)
    if not collectors:
        click.echo("No agent data found. Run 'vibe-clock init' first.")
        return

    all_sessions = []
    for c in collectors:
        all_sessions.extend(c.collect())

    stats = aggregate(all_sessions, config)
    hours = stats.total_minutes / 60
    model = stats.favorite_model or "—"
    peak = f"{stats.peak_hour}:00"

    click.echo(
        f"\u23f1 {hours:.1f} hrs | {stats.total_sessions} sessions"
        f" | {format_number(stats.total_messages)} msgs"
        f" | {format_number(stats.total_tokens.total)} tokens"
        f" | {model} | peak {peak}"
    )


@cli.command()
@click.option("--type", "-t", "chart_type", default="all", help="Chart type: card, heatmap, donut, bars, all")
@click.option("--output", "-o", "output_dir", default=".", help="Output directory for SVG files.")
@click.option("--from-json", "json_path", default=None, help="Generate from exported JSON instead of collecting.")
@click.option("--theme", default=None, help="Theme: dark or light.")
def render(chart_type: str, output_dir: str, json_path: str | None, theme: str | None) -> None:
    """Generate SVG visualizations."""
    config = load_config()
    th = theme or config.theme

    if json_path:
        with open(json_path) as f:
            stats = AgentStats.model_validate_json(f.read())
    else:
        collectors = get_collectors(config)
        all_sessions = []
        for c in collectors:
            all_sessions.extend(c.collect())
        stats = aggregate(all_sessions, config)
        stats = sanitize(stats, config)

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    types = list(SVG_RENDERERS.keys()) if chart_type == "all" else [t.strip() for t in chart_type.split(",")]
    for t in types:
        if t not in SVG_RENDERERS:
            console.print(f"[red]Unknown chart type: {t}[/red]")
            continue
        filename, renderer = SVG_RENDERERS[t]
        svg = renderer(stats, theme=th)
        path = out / filename
        path.write_text(svg)
        console.print(f"  [green]✓[/green] {path}")


@cli.command()
@click.option("--output", "-o", default="vibe-clock-data.json", help="Output file path.")
@click.option("--days", "-d", default=None, type=int)
def export(output: str, days: int | None) -> None:
    """Export AgentStats as JSON (local, unsanitized)."""
    config = load_config()
    if days:
        config.default_days = days

    collectors = get_collectors(config)
    all_sessions = []
    for c in collectors:
        all_sessions.extend(c.collect())

    stats = aggregate(all_sessions, config)
    Path(output).write_text(stats.model_dump_json(indent=2))
    console.print(f"[green]Exported to {output}[/green]")


@cli.command()
@click.option("--dry-run", is_flag=True, help="Preview what would be pushed without actually pushing.")
@click.option("--days", "-d", default=None, type=int)
def push(dry_run: bool, days: int | None) -> None:
    """Push sanitized stats to a GitHub gist."""
    import httpx

    config = load_config()
    if days:
        config.default_days = days

    token = config.github.token
    if not token:
        console.print("[red]No GitHub token configured. Run 'vibe-clock init' or set GITHUB_TOKEN.[/red]")
        sys.exit(1)

    # Collect and aggregate
    collectors = get_collectors(config)
    all_sessions = []
    for c in collectors:
        sessions = c.collect()
        console.print(f"  [dim]{c.agent_name}: {len(sessions)} sessions[/dim]")
        all_sessions.extend(sessions)

    stats = aggregate(all_sessions, config)
    safe_stats = sanitize(stats, config)

    if dry_run:
        console.print(preview(safe_stats))
        return

    payload_json = safe_stats.model_dump_json(indent=2)

    gist_data = {
        "description": "vibe-clock stats — AI coding agent usage",
        "public": True,
        "files": {
            "vibe-clock-data.json": {"content": payload_json},
        },
    }

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
    }

    client = httpx.Client(headers=headers, timeout=30, trust_env=False)
    gist_id = config.github.gist_id
    if gist_id:
        resp = client.patch(
            f"https://api.github.com/gists/{gist_id}",
            json=gist_data,
        )
    else:
        resp = client.post(
            "https://api.github.com/gists",
            json=gist_data,
        )
    client.close()

    if resp.status_code not in (200, 201):
        console.print(f"[red]GitHub API error ({resp.status_code}): {resp.text}[/red]")
        sys.exit(1)

    result = resp.json()
    new_gist_id = result["id"]

    if not gist_id:
        config.github.gist_id = new_gist_id
        save_config(config)
        console.print(f"[green]Created gist: {new_gist_id}[/green]")
    else:
        console.print(f"[green]Updated gist: {gist_id}[/green]")

    console.print(f"[dim]{result.get('html_url', '')}[/dim]")


@cli.command()
@click.option(
    "--interval",
    type=click.Choice(["hourly", "daily", "weekly"]),
    default="daily",
    help="How often to push stats.",
)
@click.option("--time", "run_time", default="00:00", help="Time of day to run (HH:MM, 24h). Ignored for hourly.")
@click.option("--force", is_flag=True, help="Overwrite existing schedule.")
def schedule(interval: str, run_time: str, force: bool) -> None:
    """Schedule automatic vibe-clock push."""
    import re

    from .scheduler import get_scheduler, resolve_binary

    config = load_config()

    if not config.github.token:
        console.print("[red]No GitHub token configured. Run 'vibe-clock init' first.[/red]")
        sys.exit(1)

    if not re.match(r"^\d{1,2}:\d{2}$", run_time):
        console.print("[red]Invalid time format. Use HH:MM (e.g. 08:00, 23:30).[/red]")
        sys.exit(1)

    scheduler = get_scheduler()

    if scheduler.is_scheduled() and not force:
        console.print(
            f"[yellow]Already scheduled via {scheduler.backend_name}. "
            f"Use --force to overwrite.[/yellow]"
        )
        return

    if scheduler.is_scheduled():
        scheduler.unschedule()

    binary = resolve_binary()
    verify_cmd = scheduler.schedule(binary, interval, run_time)

    config.schedule.enabled = True
    config.schedule.interval = interval
    config.schedule.time = run_time
    config.schedule.backend = scheduler.backend_name
    save_config(config)

    time_msg = "" if interval == "hourly" else f" at {run_time}"
    console.print(f"[green]Scheduled {interval} push{time_msg} via {scheduler.backend_name}.[/green]")
    console.print(f"[dim]Verify: {verify_cmd}[/dim]")


@cli.command()
def unschedule() -> None:
    """Remove scheduled vibe-clock push."""
    from .scheduler import get_scheduler

    config = load_config()
    scheduler = get_scheduler()

    if not scheduler.is_scheduled():
        console.print("[yellow]No active schedule found.[/yellow]")
        return

    scheduler.unschedule()

    config.schedule.enabled = False
    config.schedule.backend = ""
    save_config(config)

    console.print(f"[green]Unscheduled vibe-clock push ({scheduler.backend_name}).[/green]")
