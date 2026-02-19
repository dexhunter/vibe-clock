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
  <img src="https://raw.githubusercontent.com/dexhunter/dexhunter/master/images/vibe-clock-token-bars.svg" alt="モデル別トークン使用量" width="400" />
</p>
<p align="center">
  <img src="https://raw.githubusercontent.com/dexhunter/dexhunter/master/images/vibe-clock-hourly.svg" alt="時間帯別アクティビティ" width="400" />
  <img src="https://raw.githubusercontent.com/dexhunter/dexhunter/master/images/vibe-clock-weekly.svg" alt="曜日別アクティビティ" width="400" />
</p>

---

## クイックスタート

```bash
pip install vibe-clock
vibe-clock init          # エージェントを自動検出し、設定を行います
vibe-clock summary       # ターミナルで統計情報を確認
```

## プライバシーとセキュリティ

**あなたのコードがマシンから外に出ることはありません。** vibe-clockはローカルのJSONLログからセッションメタデータ（タイムスタンプ、トークン数、モデル名）のみを読み取ります。データがプッシュされる前に：

1. **サニタイザーがすべての個人情報を除去** — ファイルパス、プロジェクト名、ユーザー名、コードが削除されます（[`sanitizer.py`](vibe_clock/sanitizer.py)）
2. **プロジェクト名は匿名化** — 実名は「Project A」「Project B」に変換されます
3. **`--dry-run` で事前確認可能** — プッシュされる内容を正確に確認できます

**プッシュされるデータ**（あなた自身のパブリックgistへ）：
- セッション数、メッセージ数、持続時間
- モデルごとのトークン使用量合計
- モデル名とエージェント名
- 日次アクティビティの集計

**プッシュされないデータ**：ファイルパス、プロジェクト名、メッセージ内容、コードスニペット、git情報、その他すべての個人情報。

## カスタマイズ可能なチャート

`--type` で必要なチャートのみを生成：

```bash
vibe-clock render --type card,donut           # この2つだけ
vibe-clock render --type all                  # 全7種類のチャート（デフォルト）
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
vibe-clock push          # サニタイズされたデータを含むパブリックgistを作成
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
| `chart_types` | `all` | カンマ区切り：`card,heatmap,donut,bars,token_bars,hourly,weekly` または `all` |
| `commit` | `true` | 生成されたSVGを自動コミット |
| `commit_message` | `chore: update vibe-clock stats` | コミットメッセージ |

### 仕組み

```
あなた（ローカル）              GitHub
─────────                      ──────
vibe-clock push  ──▶  Gist（サニタイズ済みJSON）
                              │
                      Actions（毎日のcronジョブ）
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
| **OpenCode** | `~/.local/share/opencode/` | 対応済み |

## コマンド

| コマンド | 説明 |
|---------|------|
| `vibe-clock init` | インタラクティブセットアップ — エージェントを検出し、GitHub Tokenを確認 |
| `vibe-clock summary` | ターミナルでリッチな使用統計サマリーを表示 |
| `vibe-clock status` | 現在の設定と接続状態を表示 |
| `vibe-clock render` | SVGビジュアライゼーションをローカルで生成 |
| `vibe-clock export` | 生の統計データをJSONでエクスポート |
| `vibe-clock push` | サニタイズされた統計データをGitHub gistにプッシュ |
| `vibe-clock push --dry-run` | プッシュされる内容をプレビュー |
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
