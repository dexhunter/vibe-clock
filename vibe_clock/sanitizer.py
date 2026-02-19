"""Sanitize AgentStats before pushing to remote.

Ensures no PII, file paths, or project names leave the machine.
"""

from __future__ import annotations

import getpass
import re
import string
from pathlib import Path

from .config import Config
from .formatting import format_number
from .models import AgentStats, ProjectBreakdown

# Patterns that should never appear in pushed data
_PATH_PATTERN = re.compile(r"(/[a-zA-Z0-9._-]+){2,}")
_HOME_DIR = str(Path.home())
_USERNAME = getpass.getuser()


def sanitize(stats: AgentStats, config: Config) -> AgentStats:
    """Prepare stats for safe remote push.

    - Anonymizes project names to "Project A", "Project B", etc.
    - Strips any path fragments
    - Validates no PII leaks
    """
    data = stats.model_copy(deep=True)

    # Strip project details entirely
    data.projects = []

    # Filter out placeholder models
    data.models = [m for m in data.models if m.model not in ("unknown", "<synthetic>")]

    _validate_no_pii(data)
    return data


def _anonymize_projects(
    projects: list[ProjectBreakdown],
) -> list[ProjectBreakdown]:
    """Replace project names with anonymous labels."""
    label_map: dict[str, str] = {}
    label_idx = 0

    result = []
    for p in projects:
        if p.project not in label_map:
            label = _make_label(label_idx)
            label_map[p.project] = label
            label_idx += 1

        result.append(
            p.model_copy(update={"project": label_map[p.project]})
        )
    return result


def _make_label(idx: int) -> str:
    """Generate 'Project A', 'Project B', ... 'Project AA', etc."""
    letters = string.ascii_uppercase
    if idx < 26:
        return f"Project {letters[idx]}"
    return f"Project {letters[idx // 26 - 1]}{letters[idx % 26]}"


def _validate_no_pii(stats: AgentStats) -> None:
    """Check serialized output for PII leaks. Raises ValueError if found."""
    json_str = stats.model_dump_json()

    # Full paths are always blocked (high confidence)
    path_blocklist = [_HOME_DIR]
    if _HOME_DIR != f"/home/{_USERNAME}":
        path_blocklist.append(f"/home/{_USERNAME}")
    path_blocklist.append(f"/Users/{_USERNAME}")

    for blocked in path_blocklist:
        if blocked in json_str:
            raise ValueError(
                f"PII leak detected: found '{blocked}' in output data. "
                "Check project names and paths."
            )

    # Username check uses word boundaries to avoid false positives
    # (e.g. "dex" inside "codex")
    if len(_USERNAME) >= 3:
        pattern = re.compile(rf"(?<![a-zA-Z]){re.escape(_USERNAME)}(?![a-zA-Z])")
        if pattern.search(json_str):
            raise ValueError(
                f"PII leak detected: found username '{_USERNAME}' in output data. "
                "Check project names and paths."
            )

    # Check for path-like strings in project names
    for p in stats.projects:
        if _PATH_PATTERN.search(p.project):
            raise ValueError(
                f"Path fragment detected in project name: '{p.project}'"
            )


def preview(stats: AgentStats) -> str:
    """Human-readable preview of what will be pushed."""
    lines = [
        "=== Dry Run: Data to be pushed ===",
        "",
        f"Generated at: {stats.generated_at.isoformat()}",
        f"Days covered: {stats.days_covered}",
        f"Total sessions: {stats.total_sessions}",
        f"Total messages: {stats.total_messages}",
        f"Total minutes: {stats.total_minutes:.1f}",
        f"Total tokens: {format_number(stats.total_tokens.total)}",
        f"Active agents: {', '.join(stats.active_agents)}",
        f"Favorite model: {stats.favorite_model}",
        f"Peak hour: {stats.peak_hour}:00",
        f"Longest session: {stats.longest_session_minutes:.1f} min",
        "",
        "--- Daily Activity ---",
    ]
    for d in stats.daily[-7:]:  # Show last 7 days
        lines.append(
            f"  {d.date}: {d.session_count} sessions, "
            f"{d.message_count} msgs, {d.total_minutes:.0f} min"
        )
    if len(stats.daily) > 7:
        lines.append(f"  ... and {len(stats.daily) - 7} more days")

    lines.append("")
    lines.append("--- Models ---")
    for m in stats.models:
        lines.append(
            f"  {m.model}: {m.session_count} sessions, "
            f"{format_number(m.tokens.total)} tokens"
        )

    lines.append("")
    lines.append("--- Projects (anonymized) ---")
    for p in stats.projects:
        lines.append(
            f"  {p.project} ({p.agent}): {p.session_count} sessions, "
            f"{p.total_minutes:.0f} min"
        )

    lines.append("")
    lines.append("=== No file paths, project names, or PII above ===")
    return "\n".join(lines)
