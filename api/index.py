"""FastAPI app for serving dynamic vibe-clock SVGs (optional Vercel deployment)."""

from __future__ import annotations

import httpx
from fastapi import FastAPI, Query, Response
from fastapi.responses import JSONResponse

from vibe_clock.models import AgentStats
from vibe_clock.svg.bars import render_bars
from vibe_clock.svg.card import render_card
from vibe_clock.svg.donut import render_donut
from vibe_clock.svg.heatmap import render_heatmap

app = FastAPI(
    title="vibe-clock API",
    description="Dynamic SVG generation from vibe-clock gist data",
    version="0.1.0",
)

SVG_RENDERERS = {
    "card": render_card,
    "heatmap": render_heatmap,
    "donut": render_donut,
    "bars": render_bars,
}


async def _fetch_stats(gist_id: str) -> AgentStats:
    """Fetch stats JSON from a public GitHub gist."""
    url = f"https://gist.githubusercontent.com/raw/{gist_id}/vibe-clock-data.json"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=15, follow_redirects=True)
        resp.raise_for_status()
    return AgentStats.model_validate_json(resp.text)


@app.get("/api/stats")
async def get_stats(gist_id: str = Query(..., description="GitHub gist ID")) -> JSONResponse:
    """Return raw AgentStats JSON."""
    stats = await _fetch_stats(gist_id)
    return JSONResponse(content=stats.model_dump(mode="json"))


@app.get("/api/svg/{chart_type}")
async def get_svg(
    chart_type: str,
    gist_id: str = Query(..., description="GitHub gist ID"),
    theme: str = Query("dark", description="Theme: dark or light"),
) -> Response:
    """Return an SVG chart image."""
    renderer = SVG_RENDERERS.get(chart_type)
    if renderer is None:
        return JSONResponse(
            status_code=400,
            content={"error": f"Unknown chart type: {chart_type}. Valid: {list(SVG_RENDERERS)}"},
        )

    stats = await _fetch_stats(gist_id)
    svg = renderer(stats, theme=theme)

    return Response(
        content=svg,
        media_type="image/svg+xml",
        headers={"Cache-Control": "public, max-age=3600"},
    )
