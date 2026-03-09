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

    def _cutoff_timestamp(self, days: int) -> float:
        """Return a Unix timestamp for `days` days ago."""
        return (datetime.now(timezone.utc) - timedelta(days=days)).timestamp()

    @abstractmethod
    def collect(self, days: int | None = None) -> list[Session]:
        """Collect sessions from this agent's data directory.

        Args:
            days: Optional lookback window in days. Collectors that do not
                support date filtering may ignore this argument.
        """
        ...
