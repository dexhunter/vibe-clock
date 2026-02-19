# vibe-clock

[简体中文](README.zh-CN.md) | [日本語](README.ja.md) | [Español](README.es.md)

**WakaTime for AI coding agents.** Track usage across Claude Code, Codex, and OpenCode — then show it off on your GitHub profile.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![GitHub stars](https://img.shields.io/github/stars/dexhunter/vibe-clock?style=social)](https://github.com/dexhunter/vibe-clock)

<p align="center">
  <img src="https://raw.githubusercontent.com/dexhunter/dexhunter/master/images/vibe-clock-card.svg" alt="Vibe Clock Stats" />
</p>
<p align="center">
  <img src="https://raw.githubusercontent.com/dexhunter/dexhunter/master/images/vibe-clock-donut.svg" alt="Model Usage" width="400" />
  <img src="https://raw.githubusercontent.com/dexhunter/dexhunter/master/images/vibe-clock-token-bars.svg" alt="Token Usage by Model" width="400" />
</p>
<p align="center">
  <img src="https://raw.githubusercontent.com/dexhunter/dexhunter/master/images/vibe-clock-hourly.svg" alt="Activity by Hour" width="400" />
  <img src="https://raw.githubusercontent.com/dexhunter/dexhunter/master/images/vibe-clock-weekly.svg" alt="Activity by Day of Week" width="400" />
</p>

---

## Quick Start

```bash
pip install vibe-clock
vibe-clock init          # auto-detects agents, sets up config
vibe-clock summary       # see your stats in the terminal
```

## Privacy & Security

**Your code never leaves your machine.** vibe-clock reads only session metadata (timestamps, token counts, model names) from local JSONL logs. Before anything is pushed:

1. **Sanitizer strips all PII** — file paths, project names, usernames, and code are removed ([`sanitizer.py`](vibe_clock/sanitizer.py))
2. **Projects are anonymized** — real names become "Project A", "Project B"
3. **`--dry-run` lets you inspect** exactly what will be pushed before it goes anywhere

**What is pushed** (to your own public gist):
- Session counts, message counts, durations
- Token usage totals per model
- Model and agent names
- Daily activity aggregates

**What is NEVER pushed**: file paths, project names, message content, code snippets, git info, or any PII.

## Configurable Charts

Generate only the charts you want with `--type`:

```bash
vibe-clock render --type card,donut           # just these two
vibe-clock render --type all                  # all 7 charts (default)
```

| Chart | File | Description |
|-------|------|-------------|
| `card` | `vibe-clock-card.svg` | Summary stats card |
| `heatmap` | `vibe-clock-heatmap.svg` | Daily activity heatmap |
| `donut` | `vibe-clock-donut.svg` | Model usage breakdown |
| `bars` | `vibe-clock-bars.svg` | Project session bars |
| `token_bars` | `vibe-clock-token-bars.svg` | Token usage by model |
| `hourly` | `vibe-clock-hourly.svg` | Activity by hour of day |
| `weekly` | `vibe-clock-weekly.svg` | Activity by day of week |

## GitHub Actions Setup

Add to your `<username>/<username>` profile repo to auto-update SVGs daily.

### 1. Push your stats

```bash
vibe-clock push          # creates a public gist with sanitized data
# Note the gist ID printed
```

### 2. Add the secret

In your profile repo: **Settings → Secrets → Actions** → add:
- `VIBE_CLOCK_GIST_ID` — the gist ID from step 1

### 3. Create the workflow

`.github/workflows/vibe-clock.yml`:

```yaml
name: Update Vibe Clock Stats

on:
  schedule:
    - cron: '0 0 * * *'
  workflow_dispatch:

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: dexhunter/vibe-clock@v1.1.0
        with:
          gist_id: ${{ secrets.VIBE_CLOCK_GIST_ID }}
```

### 4. Add SVGs to your README

```html
<img src="images/vibe-clock-card.svg" alt="Vibe Clock Stats" />
<img src="images/vibe-clock-heatmap.svg" alt="Activity Heatmap" />
<img src="images/vibe-clock-donut.svg" alt="Model Usage" />
<img src="images/vibe-clock-bars.svg" alt="Projects" />
```

### 5. Run it

Go to **Actions** tab → "Update Vibe Clock Stats" → **Run workflow**

### Action Inputs

| Input | Default | Description |
|-------|---------|-------------|
| `gist_id` | *required* | Gist ID containing `vibe-clock-data.json` |
| `theme` | `dark` | `dark` or `light` |
| `output_dir` | `./images` | Where to write SVG files |
| `chart_types` | `all` | Comma-separated: `card,heatmap,donut,bars,token_bars,hourly,weekly` or `all` |
| `commit` | `true` | Auto-commit generated SVGs |
| `commit_message` | `chore: update vibe-clock stats` | Commit message |

### How it works

```
You (local)                    GitHub
─────────                      ──────
vibe-clock push  ──▶  Gist (sanitized JSON)
                              │
                      Actions (daily cron)
                              │
                       fetch gist JSON
                       generate SVGs
                       commit to profile repo
```

## Supported Agents

| Agent | Log Location | Status |
|-------|-------------|--------|
| **Claude Code** | `~/.claude/` | Supported |
| **Codex** | `~/.codex/` | Supported |
| **OpenCode** | `~/.local/share/opencode/` | Supported |

## Commands

| Command | Description |
|---------|-------------|
| `vibe-clock init` | Interactive setup — detects agents, asks for GitHub token |
| `vibe-clock summary` | Rich terminal summary of usage stats |
| `vibe-clock status` | Show current configuration and connection status |
| `vibe-clock render` | Generate SVG visualizations locally |
| `vibe-clock export` | Export raw stats as JSON |
| `vibe-clock push` | Push sanitized stats to a GitHub gist |
| `vibe-clock push --dry-run` | Preview what would be pushed |

## Configuration

Config file: `~/.config/vibe-clock/config.toml`

Environment variable overrides:
- `GITHUB_TOKEN` — GitHub PAT with `gist` scope
- `VIBE_CLOCK_GIST_ID` — Gist ID for push/pull
- `VIBE_CLOCK_DAYS` — Number of days to aggregate

## License

MIT
