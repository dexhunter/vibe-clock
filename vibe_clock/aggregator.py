"""Aggregate sessions into AgentStats."""

from __future__ import annotations

import fnmatch
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from .config import Config
from .models import (
    AgentStats,
    DailyActivity,
    ModelBreakdown,
    ProjectBreakdown,
    Session,
    TokenUsage,
)


def aggregate(sessions: list[Session], config: Config) -> AgentStats:
    """Aggregate raw sessions into AgentStats, applying privacy filters."""
    days = config.default_days
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Filter by date range
    filtered = [s for s in sessions if s.start_time >= cutoff]

    # Filter excluded date ranges
    for dr in config.privacy.exclude_date_ranges:
        if len(dr) == 2:
            try:
                start = date.fromisoformat(dr[0])
                end = date.fromisoformat(dr[1])
                filtered = [
                    s
                    for s in filtered
                    if not (start <= s.start_time.date() <= end)
                ]
            except ValueError:
                continue

    # Filter excluded projects
    if config.privacy.exclude_projects:
        filtered = [
            s
            for s in filtered
            if not any(
                fnmatch.fnmatch(s.project, pat)
                for pat in config.privacy.exclude_projects
            )
        ]

    if not filtered:
        return AgentStats(days_covered=days)

    # Group by date
    daily_map: dict[date, _DailyAcc] = defaultdict(_DailyAcc)
    model_map: dict[str, _ModelAcc] = defaultdict(_ModelAcc)
    project_map: dict[tuple[str, str], _ProjectAcc] = defaultdict(_ProjectAcc)
    hour_counts: dict[int, int] = defaultdict(int)
    agents_seen: set[str] = set()
    longest_minutes = 0.0

    total_tokens = TokenUsage()
    total_messages = 0

    for s in filtered:
        d = s.start_time.date()
        dur = s.duration_minutes

        # Daily
        acc = daily_map[d]
        acc.session_count += 1
        acc.message_count += s.message_count
        acc.total_minutes += dur
        _add_tokens(acc.tokens, s.tokens)

        # Model
        macc = model_map[s.model]
        macc.session_count += 1
        macc.message_count += s.message_count
        macc.total_minutes += dur
        _add_tokens(macc.tokens, s.tokens)

        # Project
        key = (s.project, s.agent)
        pacc = project_map[key]
        pacc.session_count += 1
        pacc.total_minutes += dur
        _add_tokens(pacc.tokens, s.tokens)

        # Totals
        _add_tokens(total_tokens, s.tokens)
        total_messages += s.message_count
        hour_counts[s.start_time.hour] += 1
        agents_seen.add(s.agent)
        if dur > longest_minutes:
            longest_minutes = dur

    # Find peak hour
    peak_hour = max(hour_counts, key=hour_counts.get) if hour_counts else 0  # type: ignore[arg-type]

    # Find favorite model
    favorite = max(model_map, key=lambda m: model_map[m].session_count) if model_map else ""

    # Build daily list sorted by date
    daily = sorted(
        [
            DailyActivity(
                date=d,
                session_count=a.session_count,
                message_count=a.message_count,
                total_minutes=round(a.total_minutes, 1),
                tokens=a.tokens,
            )
            for d, a in daily_map.items()
        ],
        key=lambda x: x.date,
    )

    models = sorted(
        [
            ModelBreakdown(
                model=m,
                session_count=a.session_count,
                message_count=a.message_count,
                total_minutes=round(a.total_minutes, 1),
                tokens=a.tokens,
            )
            for m, a in model_map.items()
        ],
        key=lambda x: x.session_count,
        reverse=True,
    )

    projects = sorted(
        [
            ProjectBreakdown(
                project=proj,
                agent=agent,
                session_count=a.session_count,
                total_minutes=round(a.total_minutes, 1),
                tokens=a.tokens,
            )
            for (proj, agent), a in project_map.items()
        ],
        key=lambda x: x.total_minutes,
        reverse=True,
    )

    return AgentStats(
        days_covered=days,
        total_sessions=len(filtered),
        total_messages=total_messages,
        total_minutes=round(sum(s.duration_minutes for s in filtered), 1),
        total_tokens=total_tokens,
        active_agents=sorted(agents_seen),
        favorite_model=favorite,
        peak_hour=peak_hour,
        longest_session_minutes=round(longest_minutes, 1),
        daily=daily,
        models=models,
        projects=projects,
    )


def _add_tokens(target: TokenUsage, source: TokenUsage) -> None:
    target.input_tokens += source.input_tokens
    target.output_tokens += source.output_tokens
    target.cache_read_tokens += source.cache_read_tokens
    target.cache_write_tokens += source.cache_write_tokens


class _DailyAcc:
    def __init__(self) -> None:
        self.session_count = 0
        self.message_count = 0
        self.total_minutes = 0.0
        self.tokens = TokenUsage()


class _ModelAcc:
    def __init__(self) -> None:
        self.session_count = 0
        self.message_count = 0
        self.total_minutes = 0.0
        self.tokens = TokenUsage()


class _ProjectAcc:
    def __init__(self) -> None:
        self.session_count = 0
        self.total_minutes = 0.0
        self.tokens = TokenUsage()
