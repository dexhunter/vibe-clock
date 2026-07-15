"""CLI entry point for vibe-clock."""

from __future__ import annotations

import json
import sys
from datetime import datetime, time, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import httpx

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
from .sanitizer import preview, public_payload
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
        sessions = c.collect(days=config.default_days)
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
        all_sessions.extend(c.collect(days=config.default_days))

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
@click.option(
    "--type",
    "-t",
    "chart_type",
    default="card,donut",
    show_default=True,
    help="Chart types: card, donut, heatmap, weekly, hourly, bars, token_bars, all",
)
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
        for collector in collectors:
            all_sessions.extend(collector.collect(days=config.default_days))
        stats = aggregate(all_sessions, config)

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
        all_sessions.extend(c.collect(days=config.default_days))

    stats = aggregate(all_sessions, config)
    Path(output).write_text(stats.model_dump_json(indent=2))
    console.print(f"[green]Exported to {output}[/green]")


def _trigger_render(client: httpx.Client, profile_repo: str) -> None:
    """Trigger the vibe-clock workflow on the profile repo via workflow_dispatch."""
    repo_resp = client.get(f"https://api.github.com/repos/{profile_repo}")
    if repo_resp.status_code != 200:
        console.print(f"[yellow]Could not find profile repo {profile_repo}[/yellow]")
        return

    default_branch = repo_resp.json().get("default_branch", "main")
    dispatch_resp = client.post(
        f"https://api.github.com/repos/{profile_repo}/actions/workflows/vibe-clock.yml/dispatches",
        json={"ref": default_branch},
    )

    if dispatch_resp.status_code == 204:
        console.print(f"[green]Triggered render workflow on {profile_repo}[/green]")
    else:
        console.print(f"[yellow]Could not trigger workflow ({dispatch_resp.status_code})[/yellow]")


def _collect_public_stats(config: Config) -> AgentStats:
    """Collect the last complete public reporting window in UTC."""
    public_config = config.model_copy(deep=True)
    public_config.default_days = config.privacy.public_days
    window_end = datetime.combine(
        datetime.now(timezone.utc).date(), time.min, tzinfo=timezone.utc
    )

    collectors = get_collectors(public_config)
    all_sessions = []
    for collector in collectors:
        sessions = collector.collect(days=public_config.default_days + 1)
        console.print(f"  [dim]{collector.agent_name}: {len(sessions)} sessions scanned[/dim]")
        all_sessions.extend(sessions)

    return aggregate(all_sessions, public_config, end_at=window_end)


def _publish_public_stats(config: Config, stats: AgentStats) -> None:
    """Publish an already-sanitized, allowlisted public snapshot."""
    import httpx

    token = config.github.token
    if not token:
        console.print("[red]No GitHub token configured. Run 'vibe-clock init' or set GITHUB_TOKEN.[/red]")
        sys.exit(1)

    payload_json = json.dumps(public_payload(stats, config), indent=2)

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

    client = httpx.Client(headers=headers, timeout=30)
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

    if resp.status_code not in (200, 201):
        client.close()
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

    # Trigger profile repo workflow to render SVGs
    profile_repo = config.github.profile_repo
    if not profile_repo:
        owner = result.get("owner", {}).get("login", "")
        if owner:
            profile_repo = f"{owner}/{owner}"

    if profile_repo:
        _trigger_render(client, profile_repo)

    client.close()


@cli.command()
@click.option("--dry-run", is_flag=True, help="Preview the public allowlist without pushing.")
@click.option("--days", "-d", default=None, type=click.IntRange(1, 365))
def push(dry_run: bool, days: int | None) -> None:
    """Update a public share previously enabled with `vibe-clock share`."""
    config = load_config()
    if days is not None:
        config.privacy.public_days = days

    if not dry_run and not config.privacy.public_sharing_enabled:
        console.print(
            "[yellow]Public sharing is disabled. Preview with 'vibe-clock push --dry-run', "
            "then opt in with 'vibe-clock share'.[/yellow]"
        )
        return

    stats = _collect_public_stats(config)
    if dry_run:
        console.print(preview(stats, config))
        return

    _publish_public_stats(config, stats)


@cli.command()
@click.option("--days", default=7, type=click.IntRange(1, 365), show_default=True)
@click.option("--daily-activity/--no-daily-activity", default=False)
@click.option("--message-counts/--no-message-counts", default=False)
@click.option("--token-counts/--no-token-counts", default=False)
@click.option("--time-patterns/--no-time-patterns", default=False)
@click.option("--project-aliases/--no-project-aliases", default=False)
@click.option("--yes", "assume_yes", is_flag=True, help="Skip the confirmation prompt.")
def share(
    days: int,
    daily_activity: bool,
    message_counts: bool,
    token_counts: bool,
    time_patterns: bool,
    project_aliases: bool,
    assume_yes: bool,
) -> None:
    """Explicitly opt in to a public GitHub profile share."""
    config = load_config()
    if config.github.gist_id and not config.privacy.public_sharing_enabled:
        console.print(
            "[yellow]A legacy public Gist is configured. Run 'vibe-clock unshare' first "
            "to delete its revision history, then run 'vibe-clock share' again.[/yellow]"
        )
        return
    config.privacy.public_days = days
    config.privacy.share_daily_activity = daily_activity
    config.privacy.share_message_counts = message_counts
    config.privacy.share_token_counts = token_counts
    config.privacy.share_time_patterns = time_patterns
    config.privacy.share_project_aliases = project_aliases

    stats = _collect_public_stats(config)
    console.print(preview(stats, config))
    if not assume_yes and not click.confirm(
        "Publish this snapshot to a public GitHub Gist? Updates remain in Gist revision history"
    ):
        console.print("[yellow]Public sharing remains disabled.[/yellow]")
        return

    config.privacy.public_sharing_enabled = True
    _publish_public_stats(config, stats)
    save_config(config)
    console.print("[green]Public sharing enabled. Future scheduled pushes use this allowlist.[/green]")


@cli.command()
@click.option("--yes", "assume_yes", is_flag=True, help="Skip the confirmation prompt.")
def unshare(assume_yes: bool) -> None:
    """Delete the public Gist and disable future public updates."""
    import httpx

    config = load_config()
    gist_id = config.github.gist_id
    if not gist_id:
        config.privacy.public_sharing_enabled = False
        save_config(config)
        console.print("[yellow]No public Gist is configured. Public sharing is disabled.[/yellow]")
        return
    if not config.github.token:
        console.print("[red]No GitHub token configured; cannot delete the public Gist.[/red]")
        sys.exit(1)
    if not assume_yes and not click.confirm(
        "Delete the public Gist and all of its revisions? Profile SVG commits are not removed"
    ):
        return

    response = httpx.delete(
        f"https://api.github.com/gists/{gist_id}",
        headers={
            "Authorization": f"token {config.github.token}",
            "Accept": "application/vnd.github+json",
        },
        timeout=30,
    )
    if response.status_code != 204:
        console.print(f"[red]GitHub API error ({response.status_code}): {response.text}[/red]")
        sys.exit(1)

    config.github.gist_id = ""
    config.privacy.public_sharing_enabled = False
    save_config(config)
    console.print("[green]Public Gist deleted and future public updates disabled.[/green]")


@cli.command()
@click.option(
    "--interval",
    type=click.Choice(["hourly", "daily", "weekly"]),
    default="daily",
    help="How often to push stats.",
)
@click.option("--time", "run_time", default=None, help="Time of day to run (HH:MM, 24h). Defaults to local equivalent of 00:00 UTC. Ignored for hourly.")
@click.option("--force", is_flag=True, help="Overwrite existing schedule.")
def schedule(interval: str, run_time: str | None, force: bool) -> None:
    """Schedule automatic vibe-clock push."""
    import re
    from datetime import datetime, timezone

    if run_time is None:
        utc_midnight = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        run_time = utc_midnight.astimezone().strftime("%H:%M")

    from .scheduler import get_scheduler, resolve_binary

    config = load_config()

    if not config.github.token:
        console.print("[red]No GitHub token configured. Run 'vibe-clock init' first.[/red]")
        sys.exit(1)
    if not config.privacy.public_sharing_enabled:
        console.print("[yellow]Run 'vibe-clock share' before scheduling public updates.[/yellow]")
        return

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
