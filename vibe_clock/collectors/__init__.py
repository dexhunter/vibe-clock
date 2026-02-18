"""Agent data collectors."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .claude_code import ClaudeCodeCollector
from .codex import CodexCollector
from .opencode import OpenCodeCollector

if TYPE_CHECKING:
    from ..config import Config
    from .base import BaseCollector

COLLECTOR_MAP: dict[str, type[BaseCollector]] = {
    "claude_code": ClaudeCodeCollector,
    "codex": CodexCollector,
    "opencode": OpenCodeCollector,
}


def get_collectors(config: Config) -> list[BaseCollector]:
    """Return enabled, available collectors based on config."""
    collectors = []
    for name in config.enabled_agents:
        cls = COLLECTOR_MAP.get(name)
        if cls is None:
            continue
        path = getattr(config.paths, name, None)
        if path is None:
            continue
        collector = cls(data_dir=path)
        if collector.is_available():
            collectors.append(collector)
    return collectors
