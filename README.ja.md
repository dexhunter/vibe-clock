# vibe-clock

[English](README.md) | [简体中文](README.zh-CN.md) | 日本語 | [Español](README.es.md)

**AIコーディングエージェントのためのWakaTime。** Claude Code、Codex、OpenCodeの使用状況を追跡し、GitHubプロフィールに表示しましょう。

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![GitHub stars](https://img.shields.io/github/stars/dexhunter/vibe-clock?style=social)](https://github.com/dexhunter/vibe-clock)

<p align="center">
  <img src="https://raw.githubusercontent.com/dexhunter/dexhunter/master/images/vibe-clock-card.svg" alt="Vibe Clock 統計" />
</p>
<p align="center">
  <img src="https://raw.githubusercontent.com/dexhunter/dexhunter/master/images/vibe-clock-donut.svg" alt="モデル使用状況" width="400" />
</p>

---

## クイックスタート

```bash
# macOS (Homebrew)
brew install dexhunter/tap/vibe-clock

# または pip で
pip install vibe-clock
```

```bash
vibe-clock init          # エージェントを自動検出し、設定を行います
vibe-clock summary       # ターミナルで統計情報を確認
```

## プライバシーとセキュリティ

**`vibe-clock share` を明示的に実行するまで、データはローカルに留まります。** デフォルトの公開プロフィールは、直近7日間の完了したUTC日について次の情報だけを含みます：

- セッション数とアクティブ日数
- 既知のエージェント名
- OpenAI、Claude、Geminiなどに正規化されたモデルファミリー

公開ペイロードは固定の許可リストから作成されます。正確な日付、メッセージ数、トークン数、時間パターン、匿名プロジェクト別名は個別のオプトインです。

**決して公開されない情報**：パス、実際のプロジェクト名、プロンプト、応答、コード、git情報、セッションID、ホスト情報、持続時間、生のタイムスタンプ、正確なモデルID。`vibe-clock unshare` は公開Gistを削除し、今後の更新を無効にします。

## カスタマイズ可能なチャート

`--type` で必要なチャートのみを生成：

```bash
vibe-clock render --type card,donut           # この2つだけ
vibe-clock render --type all                  # 全7種類のチャート
```

| チャート | ファイル | 説明 |
|----------|----------|------|
| `card` | `vibe-clock-card.svg` | 統計サマリーカード |
| `heatmap` | `vibe-clock-heatmap.svg` | 日次アクティビティヒートマップ |
| `donut` | `vibe-clock-donut.svg` | モデル使用内訳 |
| `bars` | `vibe-clock-bars.svg` | プロジェクトセッション棒グラフ |
| `token_bars` | `vibe-clock-token-bars.svg` | モデル別トークン使用量 |
| `hourly` | `vibe-clock-hourly.svg` | 時間帯別アクティビティ |
| `weekly` | `vibe-clock-weekly.svg` | 曜日別アクティビティ |

## GitHub Actions セットアップ

`<username>/<username>` プロフィールリポジトリに追加して、SVGを毎日自動更新しましょう。

### 1. 統計データをプッシュ

```bash
vibe-clock push --dry-run # 公開データをプレビュー
vibe-clock share         # 確認後にパブリックgistを作成
# 表示されたgist IDをメモしてください
```

### 2. シークレットを追加

プロフィールリポジトリで：**Settings → Secrets → Actions** → 以下を追加：
- `VIBE_CLOCK_GIST_ID` — ステップ1で取得したgist ID

### 3. ワークフローを作成

`.github/workflows/vibe-clock.yml`：

```yaml
name: Update Vibe Clock Stats

on:
  workflow_dispatch:

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: dexhunter/vibe-clock@v1.4.0
        with:
          gist_id: ${{ secrets.VIBE_CLOCK_GIST_ID }}
```

### 4. READMEにSVGを追加

```html
<img src="images/vibe-clock-card.svg" alt="Vibe Clock Stats" />
<img src="images/vibe-clock-heatmap.svg" alt="Activity Heatmap" />
<img src="images/vibe-clock-donut.svg" alt="Model Usage" />
<img src="images/vibe-clock-bars.svg" alt="Projects" />
```

### 5. 実行

**Actions** タブ → "Update Vibe Clock Stats" → **Run workflow**

### Action 入力パラメータ

| 入力 | デフォルト | 説明 |
|------|-----------|------|
| `gist_id` | *必須* | `vibe-clock-data.json` を含むGist ID |
| `theme` | `dark` | `dark` または `light` |
| `output_dir` | `./images` | SVGファイルの出力先ディレクトリ |
| `chart_types` | `card,donut` | カンマ区切り：`card,heatmap,donut,bars,token_bars,hourly,weekly` または `all` |
| `commit` | `true` | 生成されたSVGを自動コミット |
| `commit_message` | `chore: update vibe-clock stats` | コミットメッセージ |

### 仕組み

```
あなた（ローカル）              GitHub
─────────                      ──────
vibe-clock share ──▶  Gist（許可リストJSON）
                     │
                     └──▶  workflow_dispatch
                              │
                       gist JSONを取得
                       SVGを生成
                       プロフィールリポジトリにコミット
```

## 対応エージェント

| エージェント | ログの場所 | ステータス |
|-------------|-----------|-----------|
| **Claude Code** | `~/.claude/` | 対応済み |
| **Codex** | `~/.codex/` | 対応済み |
| **Gemini CLI** | `~/.gemini/` | 対応済み |
| **OpenCode** | `~/.local/share/opencode/` | 対応済み |

## コマンド

| コマンド | 説明 |
|---------|------|
| `vibe-clock init` | インタラクティブセットアップ — エージェントを検出し、GitHub Tokenを確認 |
| `vibe-clock summary` | ターミナルでリッチな使用統計サマリーを表示 |
| `vibe-clock status` | 現在の設定と接続状態を表示 |
| `vibe-clock render` | SVGビジュアライゼーションをローカルで生成 |
| `vibe-clock export` | 生の統計データをJSONでエクスポート |
| `vibe-clock share` | プレビュー、確認して公開GitHub Gistを有効化 |
| `vibe-clock push` | 明示的に有効化された公開共有を更新 |
| `vibe-clock push --dry-run` | 公開許可リストをプレビュー |
| `vibe-clock unshare` | 公開Gistを削除し、今後の更新を無効化 |
| `vibe-clock schedule` | 定期プッシュを自動スケジュール（launchd / systemd / cron） |
| `vibe-clock unschedule` | スケジュールされたプッシュタスクを削除 |

## 設定

設定ファイル：`~/.config/vibe-clock/config.toml`

環境変数によるオーバーライド：
- `GITHUB_TOKEN` — `gist` スコープを持つGitHub PAT
- `VIBE_CLOCK_GIST_ID` — プッシュ/プルに使用するGist ID
- `VIBE_CLOCK_DAYS` — 集計する日数

## ライセンス

MIT
