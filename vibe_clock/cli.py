"""CLI entry point for vibe-clock."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from . import __version__
from .aggregator import aggregate
from .collectors import get_collectors
from .config import Config, load_config, save_config
from .models import AgentStats
from .sanitizer import preview, sanitize
from .svg.bars import render_bars
from .svg.card import render_card
from .svg.donut import render_donut
from .svg.heatmap import render_heatmap

console = Console()

SVG_RENDERERS = {
    "card": ("vibe-clock-card.svg", render_card),
    "heatmap": ("vibe-clock-heatmap.svg", render_heatmap),
    "donut": ("vibe-clock-donut.svg", render_donut),
    "bars": ("vibe-clock-bars.svg", render_bars),
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

    # Display summary
    table = Table(title=f"Vibe Clock — Last {config.default_days} Days")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="bold")

    hours = stats.total_minutes / 60
    table.add_row("Total Time", f"{hours:.1f} hrs")
    table.add_row("Sessions", str(stats.total_sessions))
    table.add_row("Messages", f"{stats.total_messages:,}")
    table.add_row("Tokens", f"{stats.total_tokens.total:,}")
    table.add_row("Favorite Model", stats.favorite_model or "—")
    table.add_row("Peak Hour", f"{stats.peak_hour}:00")
    table.add_row("Active Agents", ", ".join(stats.active_agents) or "—")
    table.add_row("Longest Session", f"{stats.longest_session_minutes:.0f} min")
    console.print(table)

    # Model breakdown
    if stats.models:
        mt = Table(title="Models")
        mt.add_column("Model")
        mt.add_column("Sessions", justify="right")
        mt.add_column("Messages", justify="right")
        mt.add_column("Tokens", justify="right")
        for m in stats.models:
            mt.add_row(m.model, str(m.session_count), str(m.message_count), f"{m.tokens.total:,}")
        console.print(mt)


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

    types = list(SVG_RENDERERS.keys()) if chart_type == "all" else [chart_type]
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

    gist_id = config.github.gist_id
    if gist_id:
        # Update existing gist
        resp = httpx.patch(
            f"https://api.github.com/gists/{gist_id}",
            json=gist_data,
            headers=headers,
            timeout=30,
        )
    else:
        # Create new gist
        resp = httpx.post(
            "https://api.github.com/gists",
            json=gist_data,
            headers=headers,
            timeout=30,
        )

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
