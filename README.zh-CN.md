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
  <img src="https://raw.githubusercontent.com/dexhunter/dexhunter/master/images/vibe-clock-token-bars.svg" alt="各模型 Token 用量" width="400" />
</p>
<p align="center">
  <img src="https://raw.githubusercontent.com/dexhunter/dexhunter/master/images/vibe-clock-hourly.svg" alt="每小时活动" width="400" />
  <img src="https://raw.githubusercontent.com/dexhunter/dexhunter/master/images/vibe-clock-weekly.svg" alt="每周活动" width="400" />
</p>

---

## 快速开始

```bash
pip install vibe-clock
vibe-clock init          # 自动检测代理，设置配置
vibe-clock summary       # 在终端查看你的统计数据
```

## 隐私与安全

**你的代码永远不会离开你的设备。** vibe-clock 仅从本地 JSONL 日志中读取会话元数据（时间戳、Token 计数、模型名称）。在任何数据被推送之前：

1. **清洗器会剥离所有个人身份信息** — 文件路径、项目名称、用户名和代码都会被移除（[`sanitizer.py`](vibe_clock/sanitizer.py)）
2. **项目名称被匿名化** — 真实名称变为"Project A"、"Project B"
3. **`--dry-run` 让你预先检查** 将要推送的确切内容

**会被推送的内容**（到你自己的公开 gist）：
- 会话次数、消息数量、持续时间
- 每个模型的 Token 使用总量
- 模型和代理名称
- 每日活动汇总

**永远不会被推送的内容**：文件路径、项目名称、消息内容、代码片段、git 信息或任何个人身份信息。

## 可配置图表

使用 `--type` 仅生成你需要的图表：

```bash
vibe-clock render --type card,donut           # 仅生成这两个
vibe-clock render --type all                  # 全部 7 个图表（默认）
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

### 1. 推送你的统计数据

```bash
vibe-clock push          # 创建一个包含清洗后数据的公开 gist
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

      - uses: dexhunter/vibe-clock@v1.3.0
        with:
          gist_id: ${{ secrets.VIBE_CLOCK_GIST_ID }}
```

### 4. 将 SVG 添加到你的 README

```html
<img src="images/vibe-clock-card.svg" alt="Vibe Clock Stats" />
<img src="images/vibe-clock-heatmap.svg" alt="Activity Heatmap" />
<img src="images/vibe-clock-donut.svg" alt="Model Usage" />
<img src="images/vibe-clock-bars.svg" alt="Projects" />
```

### 5. 运行

前往 **Actions** 标签页 → "Update Vibe Clock Stats" → **Run workflow**

### Action 输入参数

| 输入 | 默认值 | 描述 |
|------|--------|------|
| `gist_id` | *必填* | 包含 `vibe-clock-data.json` 的 Gist ID |
| `theme` | `dark` | `dark` 或 `light` |
| `output_dir` | `./images` | SVG 文件输出目录 |
| `chart_types` | `all` | 逗号分隔：`card,heatmap,donut,bars,token_bars,hourly,weekly` 或 `all` |
| `commit` | `true` | 自动提交生成的 SVG |
| `commit_message` | `chore: update vibe-clock stats` | 提交信息 |

### 工作原理

```
你的设备（本地）                GitHub
─────────                      ──────
vibe-clock push  ──▶  Gist（清洗后的 JSON）
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
| **OpenCode** | `~/.local/share/opencode/` | 已支持 |

## 命令

| 命令 | 描述 |
|------|------|
| `vibe-clock init` | 交互式设置 — 检测代理，询问 GitHub Token |
| `vibe-clock summary` | 在终端展示丰富的使用统计摘要 |
| `vibe-clock status` | 显示当前配置和连接状态 |
| `vibe-clock render` | 在本地生成 SVG 可视化图表 |
| `vibe-clock export` | 导出原始统计数据为 JSON |
| `vibe-clock push` | 推送清洗后的统计数据到 GitHub gist 并触发个人主页仓库渲染 |
| `vibe-clock push --dry-run` | 预览将要推送的内容 |
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
