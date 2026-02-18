"""Pydantic models for vibe-clock data."""

from __future__ import annotations

from datetime import UTC, date, datetime

from pydantic import BaseModel, Field


class TokenUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0

    @property
    def total(self) -> int:
        return (
            self.input_tokens
            + self.output_tokens
            + self.cache_read_tokens
            + self.cache_write_tokens
        )


class Session(BaseModel):
    session_id: str
    agent: str  # "claude_code", "codex", "opencode"
    start_time: datetime
    end_time: datetime | None = None
    model: str = "unknown"
    project: str = "unknown"
    message_count: int = 0
    tokens: TokenUsage = Field(default_factory=TokenUsage)

    @property
    def duration_minutes(self) -> float:
        if self.end_time is None:
            return 0.0
        return (self.end_time - self.start_time).total_seconds() / 60.0


class DailyActivity(BaseModel):
    date: date
    session_count: int = 0
    message_count: int = 0
    total_minutes: float = 0.0
    tokens: TokenUsage = Field(default_factory=TokenUsage)


class ModelBreakdown(BaseModel):
    model: str
    session_count: int = 0
    message_count: int = 0
    total_minutes: float = 0.0
    tokens: TokenUsage = Field(default_factory=TokenUsage)


class ProjectBreakdown(BaseModel):
    project: str
    agent: str
    session_count: int = 0
    total_minutes: float = 0.0
    tokens: TokenUsage = Field(default_factory=TokenUsage)


class AgentStats(BaseModel):
    """Top-level aggregated stats — this is what gets pushed to the gist."""

    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    days_covered: int = 30
    total_sessions: int = 0
    total_messages: int = 0
    total_minutes: float = 0.0
    total_tokens: TokenUsage = Field(default_factory=TokenUsage)
    active_agents: list[str] = Field(default_factory=list)
    favorite_model: str = ""
    peak_hour: int = 0  # 0-23
    longest_session_minutes: float = 0.0
    hourly: list[int] = Field(default_factory=lambda: [0] * 24)  # sessions per hour 0-23
    daily: list[DailyActivity] = Field(default_factory=list)
    models: list[ModelBreakdown] = Field(default_factory=list)
    projects: list[ProjectBreakdown] = Field(default_factory=list)
