# vibe-clock

[English](README.md) | 简体中文 | [日本語](README.ja.md) | [Español](README.es.md)

**AI 编程代理的 WakaTime。** 追踪 Claude Code、Codex 和 OpenCode 的使用情况——并在你的 GitHub 个人主页上展示。

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![GitHub stars](https://img.shields.io/github/stars/dexhunter/vibe-clock?style=social)](https://github.com/dexhunter/vibe-clock)

<p align="center">
  <img src="https://raw.githubusercontent.com/dexhunter/dexhunter/master/images/vibe-clock-card.svg" alt="Vibe Clock 统计" />
</p>
<p align="center">
  <img src="https://raw.githubusercontent.com/dexhunter/dexhunter/master/images/vibe-clock-donut.svg" alt="模型使用情况" width="400" />
</p>

---

## 快速开始

```bash
# macOS (Homebrew)
brew install dexhunter/tap/vibe-clock

# 或通过 pip
pip install vibe-clock
```

```bash
vibe-clock init          # 自动检测代理，设置配置
vibe-clock summary       # 在终端查看你的统计数据
```

## 隐私与安全

**只有在你明确运行 `vibe-clock share` 后，数据才会离开本机。** 默认公开资料只包含最近 7 个完整 UTC 日的：

- 会话数和活跃天数
- 已知代理名称
- OpenAI、Claude、Gemini 等标准化模型系列

公开数据由固定白名单生成。精确日期、消息数、Token 数、时间分布和匿名项目别名都必须单独选择。

**永远不会公开**：路径、真实项目名称、提示词、回复、代码、git 信息、会话 ID、主机信息、持续时间、原始时间戳和精确模型 ID。`vibe-clock unshare` 会删除公开 Gist 并停止后续更新。

## 可配置图表

使用 `--type` 仅生成你需要的图表：

```bash
vibe-clock render --type card,donut           # 仅生成这两个
vibe-clock render --type all                  # 全部 7 个图表
```

| 图表 | 文件 | 描述 |
|------|------|------|
| `card` | `vibe-clock-card.svg` | 统计摘要卡片 |
| `heatmap` | `vibe-clock-heatmap.svg` | 每日活动热力图 |
| `donut` | `vibe-clock-donut.svg` | 模型使用分布 |
| `bars` | `vibe-clock-bars.svg` | 项目会话条形图 |
| `token_bars` | `vibe-clock-token-bars.svg` | 各模型 Token 用量 |
| `hourly` | `vibe-clock-hourly.svg` | 每小时活动分布 |
| `weekly` | `vibe-clock-weekly.svg` | 每周活动分布 |

## GitHub Actions 设置

添加到你的 `<username>/<username>` 个人主页仓库，即可每日自动更新 SVG 图表。

### 1. 预览并明确选择公开

```bash
vibe-clock push --dry-run
vibe-clock share         # 确认后创建公开 gist
# 记下输出的 gist ID
```

### 2. 添加密钥

在你的个人主页仓库中：**Settings → Secrets → Actions** → 添加：
- `VIBE_CLOCK_GIST_ID` — 步骤 1 中获取的 gist ID

### 3. 创建工作流

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

### 4. 将 SVG 添加到你的 README

```html
<img src="images/vibe-clock-card.svg" alt="Vibe Clock Stats" />
<img src="images/vibe-clock-donut.svg" alt="Model Usage" />
```

### 5. 运行

前往 **Actions** 标签页 → "Update Vibe Clock Stats" → **Run workflow**

### Action 输入参数

| 输入 | 默认值 | 描述 |
|------|--------|------|
| `gist_id` | *必填* | 包含 `vibe-clock-data.json` 的 Gist ID |
| `theme` | `dark` | `dark` 或 `light` |
| `output_dir` | `./images` | SVG 文件输出目录 |
| `chart_types` | `card,donut` | 逗号分隔：`card,heatmap,donut,bars,token_bars,hourly,weekly` 或 `all` |
| `commit` | `true` | 自动提交生成的 SVG |
| `commit_message` | `chore: update vibe-clock stats` | 提交信息 |

### 工作原理

```
你的设备（本地）                GitHub
─────────                      ──────
vibe-clock share ──▶  Gist（白名单 JSON）
                     │
                     └──▶  workflow_dispatch
                              │
                       获取 gist JSON
                       生成 SVG 图表
                       提交到个人主页仓库
```

## 支持的代理

| 代理 | 日志位置 | 状态 |
|------|----------|------|
| **Claude Code** | `~/.claude/` | 已支持 |
| **Codex** | `~/.codex/` | 已支持 |
| **Gemini CLI** | `~/.gemini/` | 已支持 |
| **OpenCode** | `~/.local/share/opencode/` | 已支持 |

## 命令

| 命令 | 描述 |
|------|------|
| `vibe-clock init` | 交互式设置 — 检测代理，询问 GitHub Token |
| `vibe-clock summary` | 在终端展示丰富的使用统计摘要 |
| `vibe-clock status` | 显示当前配置和连接状态 |
| `vibe-clock render` | 在本地生成 SVG 可视化图表 |
| `vibe-clock export` | 导出原始统计数据为 JSON |
| `vibe-clock share` | 预览、确认并启用公开 GitHub Gist |
| `vibe-clock push` | 更新已明确启用的公开分享 |
| `vibe-clock push --dry-run` | 预览精确的公开白名单 |
| `vibe-clock unshare` | 删除公开 Gist 并停止后续更新 |
| `vibe-clock schedule` | 自动定时推送（launchd / systemd / cron） |
| `vibe-clock unschedule` | 移除定时推送任务 |

## 配置

配置文件：`~/.config/vibe-clock/config.toml`

环境变量覆盖：
- `GITHUB_TOKEN` — 具有 `gist` 权限的 GitHub PAT
- `VIBE_CLOCK_GIST_ID` — 用于推送/拉取的 Gist ID
- `VIBE_CLOCK_DAYS` — 统计聚合的天数

## 许可证

MIT
