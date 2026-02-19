# vibe-clock

[English](README.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md) | Español

**WakaTime para agentes de programación con IA.** Rastrea el uso de Claude Code, Codex y OpenCode — y muéstralo en tu perfil de GitHub.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![GitHub stars](https://img.shields.io/github/stars/dexhunter/vibe-clock?style=social)](https://github.com/dexhunter/vibe-clock)

<p align="center">
  <img src="https://raw.githubusercontent.com/dexhunter/dexhunter/master/images/vibe-clock-card.svg" alt="Estadísticas de Vibe Clock" />
</p>
<p align="center">
  <img src="https://raw.githubusercontent.com/dexhunter/dexhunter/master/images/vibe-clock-donut.svg" alt="Uso de modelos" width="400" />
  <img src="https://raw.githubusercontent.com/dexhunter/dexhunter/master/images/vibe-clock-token-bars.svg" alt="Uso de tokens por modelo" width="400" />
</p>
<p align="center">
  <img src="https://raw.githubusercontent.com/dexhunter/dexhunter/master/images/vibe-clock-hourly.svg" alt="Actividad por hora" width="400" />
  <img src="https://raw.githubusercontent.com/dexhunter/dexhunter/master/images/vibe-clock-weekly.svg" alt="Actividad por día de la semana" width="400" />
</p>

---

## Inicio rápido

```bash
pip install vibe-clock
vibe-clock init          # detecta agentes automáticamente, configura todo
vibe-clock summary       # ve tus estadísticas en la terminal
```

## Privacidad y seguridad

**Tu código nunca sale de tu máquina.** vibe-clock solo lee metadatos de sesión (marcas de tiempo, conteos de tokens, nombres de modelos) de los logs JSONL locales. Antes de que se envíe cualquier dato:

1. **El sanitizador elimina toda información personal** — rutas de archivos, nombres de proyectos, nombres de usuario y código son removidos ([`sanitizer.py`](vibe_clock/sanitizer.py))
2. **Los proyectos se anonimizan** — los nombres reales se convierten en "Project A", "Project B"
3. **`--dry-run` te permite inspeccionar** exactamente qué se enviará antes de hacerlo

**Lo que se envía** (a tu propio gist público):
- Conteos de sesiones, conteos de mensajes, duraciones
- Totales de uso de tokens por modelo
- Nombres de modelos y agentes
- Agregados de actividad diaria

**Lo que NUNCA se envía**: rutas de archivos, nombres de proyectos, contenido de mensajes, fragmentos de código, información de git o cualquier información personal.

## Gráficos configurables

Genera solo los gráficos que necesites con `--type`:

```bash
vibe-clock render --type card,donut           # solo estos dos
vibe-clock render --type all                  # los 7 gráficos (por defecto)
```

| Gráfico | Archivo | Descripción |
|---------|---------|-------------|
| `card` | `vibe-clock-card.svg` | Tarjeta de resumen de estadísticas |
| `heatmap` | `vibe-clock-heatmap.svg` | Mapa de calor de actividad diaria |
| `donut` | `vibe-clock-donut.svg` | Distribución de uso de modelos |
| `bars` | `vibe-clock-bars.svg` | Barras de sesiones por proyecto |
| `token_bars` | `vibe-clock-token-bars.svg` | Uso de tokens por modelo |
| `hourly` | `vibe-clock-hourly.svg` | Actividad por hora del día |
| `weekly` | `vibe-clock-weekly.svg` | Actividad por día de la semana |

## Configuración de GitHub Actions

Agrega esto a tu repositorio de perfil `<username>/<username>` para actualizar los SVGs automáticamente cada día.

### 1. Envía tus estadísticas

```bash
vibe-clock push          # crea un gist público con datos sanitizados
# Anota el ID del gist que se muestra
```

### 2. Agrega el secreto

En tu repositorio de perfil: **Settings → Secrets → Actions** → agrega:
- `VIBE_CLOCK_GIST_ID` — el ID del gist del paso 1

### 3. Crea el workflow

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

### 4. Agrega los SVGs a tu README

```html
<img src="images/vibe-clock-card.svg" alt="Vibe Clock Stats" />
<img src="images/vibe-clock-heatmap.svg" alt="Activity Heatmap" />
<img src="images/vibe-clock-donut.svg" alt="Model Usage" />
<img src="images/vibe-clock-bars.svg" alt="Projects" />
```

### 5. Ejecútalo

Ve a la pestaña **Actions** → "Update Vibe Clock Stats" → **Run workflow**

### Parámetros del Action

| Parámetro | Predeterminado | Descripción |
|-----------|---------------|-------------|
| `gist_id` | *requerido* | ID del Gist que contiene `vibe-clock-data.json` |
| `theme` | `dark` | `dark` o `light` |
| `output_dir` | `./images` | Directorio de salida para archivos SVG |
| `chart_types` | `all` | Separados por coma: `card,heatmap,donut,bars,token_bars,hourly,weekly` o `all` |
| `commit` | `true` | Auto-commit de los SVGs generados |
| `commit_message` | `chore: update vibe-clock stats` | Mensaje del commit |

### Cómo funciona

```
Tú (local)                     GitHub
─────────                      ──────
vibe-clock push  ──▶  Gist (JSON sanitizado)
                              │
                      Actions (cron diario)
                              │
                       obtener JSON del gist
                       generar SVGs
                       commit al repositorio de perfil
```

## Agentes soportados

| Agente | Ubicación de logs | Estado |
|--------|-------------------|--------|
| **Claude Code** | `~/.claude/` | Soportado |
| **Codex** | `~/.codex/` | Soportado |
| **OpenCode** | `~/.local/share/opencode/` | Soportado |

## Comandos

| Comando | Descripción |
|---------|-------------|
| `vibe-clock init` | Configuración interactiva — detecta agentes, solicita token de GitHub |
| `vibe-clock summary` | Resumen enriquecido de estadísticas de uso en la terminal |
| `vibe-clock status` | Muestra la configuración actual y el estado de conexión |
| `vibe-clock render` | Genera visualizaciones SVG localmente |
| `vibe-clock export` | Exporta estadísticas sin procesar como JSON |
| `vibe-clock push` | Envía estadísticas sanitizadas a un gist de GitHub |
| `vibe-clock push --dry-run` | Previsualiza lo que se enviaría |
| `vibe-clock schedule` | Programar push periódico automático (launchd / systemd / cron) |
| `vibe-clock unschedule` | Eliminar la tarea de push programada |

## Configuración

Archivo de configuración: `~/.config/vibe-clock/config.toml`

Variables de entorno:
- `GITHUB_TOKEN` — PAT de GitHub con permisos de `gist`
- `VIBE_CLOCK_GIST_ID` — ID del Gist para enviar/recibir
- `VIBE_CLOCK_DAYS` — Número de días a agregar

## Licencia

MIT
