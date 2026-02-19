---
name: vibe-clock-setup
description: Set up vibe-clock to track AI coding agent usage (Claude Code, Codex, OpenCode) and display SVG stats on a GitHub profile README.
license: MIT
compatibility:
  - claude-code
  - codex-cli
  - opencode
metadata:
  version: "0.1.0"
  author: dexhunter
  repository: https://github.com/dexhunter/vibe-clock
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - WebFetch
---

# vibe-clock Setup

You are setting up **vibe-clock**, a CLI tool that tracks AI coding agent usage across Claude Code, Codex, and OpenCode, then displays SVG visualizations on a GitHub profile README.

## Architecture

```
Local machine                  GitHub
─────────────                  ──────
~/.claude/                     Gist (vibe-clock-data.json)
~/.codex/          ──push──▶        │
~/.local/share/opencode/       Actions (daily cron)
                                    │
                               fetch gist → generate SVGs → commit to profile repo
```

Two-stage pipeline:
1. **Local**: `vibe-clock push` collects sessions from agent data dirs, aggregates, sanitizes (strips all PII/paths/project names), and pushes safe JSON to a GitHub Gist.
2. **Remote**: A GitHub Actions workflow in the user's `<username>/<username>` profile repo fetches the gist, generates SVGs via `vibe-clock render --from-json`, and commits them.

## Prerequisites

- Python 3.10+
- A GitHub Classic Personal Access Token (PAT) with `gist` scope (fine-grained tokens do NOT support gists)
- At least one supported agent installed: Claude Code (`~/.claude/`), Codex (`~/.codex/`), or OpenCode (`~/.local/share/opencode/`)
- A GitHub profile repo (`<username>/<username>`) with a README.md

## Step 1: Install vibe-clock

```bash
pip install git+https://github.com/dexhunter/vibe-clock.git
```

Or with uv:
```bash
uv tool install git+https://github.com/dexhunter/vibe-clock.git
```

Verify the installation:
```bash
vibe-clock --version
```

## Step 2: Initialize configuration

```bash
vibe-clock init
```

This will:
- Auto-detect which agents are available on the machine
- Prompt for a GitHub PAT (Classic token with `gist` scope)
- Write config to `~/.config/vibe-clock/config.toml`

If the user already has a `GITHUB_TOKEN` environment variable, note that the TOML config token takes precedence when set. If the env var token lacks gist scope, make sure to enter the correct token during init.

## Step 3: Verify local data collection

```bash
vibe-clock summary
```

This shows a terminal table with session counts, total time, token usage, favorite model, and peak hour. If no data appears, check that agent data directories exist and contain session files.

## Step 4: Push sanitized stats to GitHub Gist

First do a dry run to preview what will be pushed:
```bash
vibe-clock push --dry-run
```

Verify the output contains ONLY aggregated numbers — no file paths, project names, or personal information. Then push:
```bash
vibe-clock push
```

This creates a **public** gist named `vibe-clock-data.json`. Note the gist ID printed — it is automatically saved to the config file.

To retrieve the gist ID later:
```bash
grep gist_id ~/.config/vibe-clock/config.toml
```

## Step 5: Set up GitHub Actions in the profile repo

The user's profile repo is `<username>/<username>` (e.g., `dexhunter/dexhunter`).

### 5a: Add repository secret

Go to the profile repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**:
- Name: `VIBE_CLOCK_GIST_ID`
- Value: the gist ID from Step 4

### 5b: Create the workflow file

Create `.github/workflows/vibe-clock.yml` in the profile repo:

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

      - uses: dexhunter/vibe-clock@main
        with:
          gist_id: ${{ secrets.VIBE_CLOCK_GIST_ID }}
```

### 5c: Add SVGs to README.md

Add this section to the profile repo's `README.md`:

```html
<h2 align="center"> Vibe Clock </h2>

<p align="center">
  <img src="images/vibe-clock-card.svg" alt="Vibe Clock Stats" />
</p>
<p align="center">
  <img src="images/vibe-clock-donut.svg" alt="Model Usage" />
  <img src="images/vibe-clock-token-bars.svg" alt="Token Usage by Model" />
</p>
<p align="center">
  <img src="images/vibe-clock-hourly.svg" alt="Activity by Hour" />
  <img src="images/vibe-clock-weekly.svg" alt="Activity by Day of Week" />
</p>
```

Available chart types: `card`, `heatmap`, `donut`, `bars`, `token_bars`, `hourly`, `weekly`.

## Step 6: Trigger the workflow

Go to the profile repo → **Actions** tab → "Update Vibe Clock Stats" → **Run workflow**.

Or if the user has a `gh` CLI token with workflow permissions:
```bash
gh workflow run vibe-clock.yml --repo <username>/<username>
```

## Ongoing Usage

- Run `vibe-clock push` locally whenever you want to update stats (e.g., daily via cron or manually)
- The GitHub Actions workflow runs daily at midnight UTC and regenerates SVGs automatically
- To update stats on demand: push locally, then trigger the workflow

## Configuration Reference

Config file: `~/.config/vibe-clock/config.toml`

```toml
[general]
default_days = 30
theme = "dark"

[paths]
claude_code = "~/.claude"
codex = "~/.codex"
opencode = "~/.local/share/opencode"

[github]
token = ""
gist_id = ""

[agents]
enabled = ["claude_code", "codex", "opencode"]

[privacy]
exclude_projects = []
exclude_date_ranges = []
anonymize_projects = true
```

Environment variable overrides (used when TOML value is empty): `GITHUB_TOKEN`, `VIBE_CLOCK_GIST_ID`, `VIBE_CLOCK_DAYS`.

## Privacy

Only aggregated numbers leave the machine. Never pushed: file paths, project names, message content, code, git info, or PII. Use `--dry-run` to verify before any push.

## Troubleshooting

- **`vibe-clock: command not found`**: Ensure pip/uv installed it globally. Try `uv tool install --force git+https://github.com/dexhunter/vibe-clock.git`.
- **Push fails with 401**: Token likely lacks `gist` scope. Must be a Classic PAT, not fine-grained.
- **Push fails with connection error**: If behind a SOCKS proxy (`ALL_PROXY`), vibe-clock already uses `trust_env=False` to bypass it.
- **SVGs don't render in GitHub README**: GitHub caches aggressively. Wait a few minutes or hard-refresh. Ensure SVGs use web-safe fonts (Arial, Helvetica).
- **No sessions found**: Check that agent data directories exist (`~/.claude/projects/`, `~/.codex/sessions/`, `~/.local/share/opencode/storage/`).
