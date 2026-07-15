"""Base collector abstract class."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ..models import Session


class BaseCollector(ABC):
    agent_name: str = "unknown"

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir

    def is_available(self) -> bool:
        return self.data_dir.exists()

    @abstractmethod
    def collect(self, days: int = 365) -> list[Session]:
        """Collect sessions from this agent's data directory."""
        ...

    def _cutoff_timestamp(self, days: int) -> float:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        return cutoff.timestamp()
