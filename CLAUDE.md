# vibe-clock

A CLI tool that tracks AI coding agent usage across Claude Code, Codex, and OpenCode.

## Project Structure

- `vibe_clock/` — main package
  - `cli.py` — Click CLI entry point (init, summary, render, export, push)
  - `config.py` — TOML + env var config loading (`~/.config/vibe-clock/config.toml`)
  - `models.py` — Pydantic v2 models (Session, TokenUsage, AgentStats, etc.)
  - `aggregator.py` — Pure function merging sessions into AgentStats
  - `sanitizer.py` — Strips PII/paths/project names before any remote push
  - `collectors/` — Agent-specific parsers (claude_code, codex, opencode)
  - `svg/` — Pure Python SVG renderers (card, heatmap, donut, bars, token_bars, hourly, weekly)
- `action.yml` — GitHub composite action for profile repo integration
- `tests/` — pytest tests for collectors, aggregator, SVG output

## Key Commands

```bash
vibe-clock init          # Interactive setup
vibe-clock summary       # Terminal stats
vibe-clock render        # Generate SVG files
vibe-clock push          # Push sanitized stats to GitHub Gist
vibe-clock push --dry-run  # Preview what would be pushed
```

## Development

```bash
pip install -e ".[dev]"
pytest tests/
```

## Privacy Rules

- NEVER push file paths, project names, message content, or PII
- `sanitizer.py` must always run before any network I/O
- Use `--dry-run` to inspect output before pushing
- The `_validate_no_pii` function checks for username leaks using word-boundary regex

## Style

- Python 3.10+, Pydantic v2, Click for CLI, Rich for terminal output
- SVGs use `Arial, Helvetica, sans-serif` (GitHub-compatible)
- `httpx` with `trust_env=False` for GitHub API calls (bypasses SOCKS proxy)
