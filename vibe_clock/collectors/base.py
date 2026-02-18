"""Base collector abstract class."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from ..models import Session


class BaseCollector(ABC):
    agent_name: str = "unknown"

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir

    def is_available(self) -> bool:
        return self.data_dir.exists()

    @abstractmethod
    def collect(self) -> list[Session]:
        """Collect sessions from this agent's data directory."""
        ...
