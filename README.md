# vibe-clock

Track AI coding agent usage across Claude Code, Codex, and OpenCode.

WakaTime tracks editor time but misses AI agent work. **vibe-clock** fills the gap: it collects session data from multiple AI coding agents, pushes aggregated stats to a GitHub gist, and a GitHub Actions workflow generates SVG visualizations for your profile.

## Quick Start

```bash
pip install vibe-clock
vibe-clock init
vibe-clock summary
```

## Commands

| Command | Description |
|---------|-------------|
| `vibe-clock init` | Interactive setup — detects agents, asks for GitHub token |
| `vibe-clock summary` | Rich terminal summary of usage stats |
| `vibe-clock render` | Generate SVG visualizations locally |
| `vibe-clock export` | Export raw stats as JSON |
| `vibe-clock push` | Push sanitized stats to a GitHub gist |
| `vibe-clock push --dry-run` | Preview what would be pushed |

## Privacy

Only aggregated, anonymized numbers ever leave your machine:
- Session counts, message counts, durations
- Token usage totals per model
- Model and agent names
- Anonymized project labels ("Project A", "Project B")

**Never pushed**: file paths, project names, message content, code, git info, or any PII.

## Supported Agents

- **Claude Code** (`~/.claude/`)
- **Codex** (`~/.codex/`)
- **OpenCode** (`~/.local/share/opencode/`)

## GitHub Actions Integration

Add to your `<username>/<username>` profile repo to auto-update SVGs daily.

### Setup

1. Run `vibe-clock push` locally to create the gist (note the gist ID printed)
2. In your profile repo, go to **Settings → Secrets → Actions** and add:
   - `VIBE_CLOCK_GIST_ID` — the gist ID from step 1
3. Create `.github/workflows/vibe-clock.yml` in your profile repo:

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

4. Add the SVGs to your profile README.md:

```html
<img src="images/vibe-clock-card.svg" alt="Vibe Clock Stats" />
<img src="images/vibe-clock-heatmap.svg" alt="Activity Heatmap" />
<img src="images/vibe-clock-donut.svg" alt="Model Usage" />
<img src="images/vibe-clock-bars.svg" alt="Projects" />
```

5. Go to **Actions** tab → "Update Vibe Clock Stats" → **Run workflow** to test

### Action Inputs

| Input | Default | Description |
|-------|---------|-------------|
| `gist_id` | *required* | GitHub Gist ID containing vibe-clock-data.json |
| `theme` | `dark` | `dark` or `light` |
| `output_dir` | `./images` | Where to write SVG files |
| `chart_types` | `all` | `card`, `heatmap`, `donut`, `bars`, or `all` |
| `commit` | `true` | Auto-commit generated SVGs |
| `commit_message` | `chore: update vibe-clock stats` | Commit message |

### How it works

```
You (local)                    GitHub
─────────                      ──────
vibe-clock push  ──▶  Gist (safe JSON)
                              │
                      Actions (daily cron)
                              │
                       fetch gist JSON
                       generate 4 SVGs
                       commit to profile repo
```

You run `vibe-clock push` locally whenever you want to update your stats.
GitHub Actions fetches the safe JSON and regenerates the SVGs automatically.

## SVG Examples

```html
<img src="images/vibe-clock-card.svg" alt="Vibe Clock Stats" />
<img src="images/vibe-clock-heatmap.svg" alt="Activity Heatmap" />
<img src="images/vibe-clock-donut.svg" alt="Model Usage" />
<img src="images/vibe-clock-bars.svg" alt="Projects" />
```

## Configuration

Config file: `~/.config/vibe-clock/config.toml`

Environment variable overrides: `GITHUB_TOKEN`, `VIBE_CLOCK_GIST_ID`, `VIBE_CLOCK_DAYS`

## License

MIT
