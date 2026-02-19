"""OS-agnostic scheduling for vibe-clock push."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from abc import ABC, abstractmethod
from pathlib import Path

LOG_DIR = Path.home() / ".config" / "vibe-clock" / "logs"
PLIST_LABEL = "com.vibe-clock.push"
PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / f"{PLIST_LABEL}.plist"
SYSTEMD_DIR = Path.home() / ".config" / "systemd" / "user"
CRONTAB_MARKER = "# vibe-clock-push"


def resolve_binary() -> str:
    """Find the vibe-clock binary path."""
    found = shutil.which("vibe-clock")
    if found:
        return found
    # Fallback: look next to the current Python executable
    bin_dir = Path(sys.executable).parent
    candidate = bin_dir / "vibe-clock"
    if candidate.exists():
        return str(candidate)
    raise FileNotFoundError(
        "Cannot find vibe-clock binary. "
        "Ensure it is installed and on your PATH."
    )


class BaseScheduler(ABC):
    """Abstract base class for OS scheduling backends."""

    backend_name: str = "unknown"

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this scheduling backend is available on the current OS."""
        ...

    @abstractmethod
    def is_scheduled(self) -> bool:
        """Check if vibe-clock push is already scheduled."""
        ...

    @abstractmethod
    def schedule(self, binary: str, interval: str, time: str = "00:00") -> str:
        """Create a scheduled task. Returns a verification command.

        Args:
            binary: Path to the vibe-clock binary.
            interval: One of "hourly", "daily", "weekly".
            time: HH:MM time of day to run (ignored for hourly).
        """
        ...

    @abstractmethod
    def unschedule(self) -> None:
        """Remove the scheduled task."""
        ...


class LaunchdScheduler(BaseScheduler):
    """macOS launchd backend."""

    backend_name = "launchd"

    def is_available(self) -> bool:
        return sys.platform == "darwin"

    def is_scheduled(self) -> bool:
        return PLIST_PATH.exists()

    def schedule(self, binary: str, interval: str, time: str = "00:00") -> str:
        import plistlib

        hour, minute = (int(p) for p in time.split(":"))
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        os.chmod(LOG_DIR, 0o700)

        if interval == "hourly":
            calendar = {"Minute": minute}
        elif interval == "weekly":
            calendar = {"Weekday": 1, "Hour": hour, "Minute": minute}
        else:  # daily
            calendar = {"Hour": hour, "Minute": minute}

        plist = {
            "Label": PLIST_LABEL,
            "ProgramArguments": [binary, "push"],
            "StartCalendarInterval": calendar,
            "RunAtLoad": True,
            "StandardOutPath": str(LOG_DIR / "push-stdout.log"),
            "StandardErrorPath": str(LOG_DIR / "push-stderr.log"),
            "EnvironmentVariables": {
                "PATH": os.environ.get("PATH", "/usr/bin:/bin:/usr/local/bin"),
            },
        }

        PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(PLIST_PATH, "wb") as f:
            plistlib.dump(plist, f)

        subprocess.run(
            ["launchctl", "load", str(PLIST_PATH)],
            check=True,
        )

        return f"launchctl list | grep {PLIST_LABEL}"

    def unschedule(self) -> None:
        if PLIST_PATH.exists():
            subprocess.run(
                ["launchctl", "unload", str(PLIST_PATH)],
                check=False,
            )
            PLIST_PATH.unlink()


class SystemdScheduler(BaseScheduler):
    """Linux systemd user timer backend."""

    backend_name = "systemd"

    def is_available(self) -> bool:
        return sys.platform == "linux" and shutil.which("systemctl") is not None

    def is_scheduled(self) -> bool:
        service = SYSTEMD_DIR / "vibe-clock-push.timer"
        return service.exists()

    def schedule(self, binary: str, interval: str, time: str = "00:00") -> str:
        SYSTEMD_DIR.mkdir(parents=True, exist_ok=True)

        hour, minute = time.split(":")
        if interval == "hourly":
            calendar = f"*-*-* *:{minute.zfill(2)}:00"
        elif interval == "weekly":
            calendar = f"Mon *-*-* {hour.zfill(2)}:{minute.zfill(2)}:00"
        else:  # daily
            calendar = f"*-*-* {hour.zfill(2)}:{minute.zfill(2)}:00"

        service_content = (
            "[Unit]\n"
            "Description=vibe-clock push\n"
            "\n"
            "[Service]\n"
            "Type=oneshot\n"
            f"ExecStart={binary} push\n"
        )

        timer_content = (
            "[Unit]\n"
            "Description=vibe-clock push timer\n"
            "\n"
            "[Timer]\n"
            f"OnCalendar={calendar}\n"
            "Persistent=true\n"
            "\n"
            "[Install]\n"
            "WantedBy=timers.target\n"
        )

        service_path = SYSTEMD_DIR / "vibe-clock-push.service"
        timer_path = SYSTEMD_DIR / "vibe-clock-push.timer"
        service_path.write_text(service_content)
        timer_path.write_text(timer_content)

        subprocess.run(
            ["systemctl", "--user", "daemon-reload"],
            check=True,
        )
        subprocess.run(
            ["systemctl", "--user", "enable", "--now", "vibe-clock-push.timer"],
            check=True,
        )

        return "systemctl --user status vibe-clock-push.timer"

    def unschedule(self) -> None:
        subprocess.run(
            ["systemctl", "--user", "disable", "--now", "vibe-clock-push.timer"],
            check=False,
        )
        for name in ("vibe-clock-push.service", "vibe-clock-push.timer"):
            path = SYSTEMD_DIR / name
            if path.exists():
                path.unlink()
        subprocess.run(
            ["systemctl", "--user", "daemon-reload"],
            check=False,
        )


class CrontabScheduler(BaseScheduler):
    """Fallback crontab backend."""

    backend_name = "crontab"

    def is_available(self) -> bool:
        return shutil.which("crontab") is not None

    def is_scheduled(self) -> bool:
        try:
            result = subprocess.run(
                ["crontab", "-l"],
                capture_output=True,
                text=True,
                check=False,
            )
            return CRONTAB_MARKER in result.stdout
        except FileNotFoundError:
            return False

    def schedule(self, binary: str, interval: str, time: str = "00:00") -> str:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        os.chmod(LOG_DIR, 0o700)

        hour, minute = (int(p) for p in time.split(":"))
        if interval == "hourly":
            cron_expr = f"{minute} * * * *"
        elif interval == "weekly":
            cron_expr = f"{minute} {hour} * * 1"
        else:  # daily
            cron_expr = f"{minute} {hour} * * *"
        log_path = LOG_DIR / "push.log"
        cron_line = f"{cron_expr} {binary} push >> {log_path} 2>&1 {CRONTAB_MARKER}"

        # Get existing crontab (may be empty)
        result = subprocess.run(
            ["crontab", "-l"],
            capture_output=True,
            text=True,
            check=False,
        )
        existing = result.stdout if result.returncode == 0 else ""

        # Remove any old vibe-clock entries
        lines = [
            line for line in existing.splitlines()
            if CRONTAB_MARKER not in line
        ]
        lines.append(cron_line)

        new_crontab = "\n".join(lines) + "\n"
        subprocess.run(
            ["crontab", "-"],
            input=new_crontab,
            text=True,
            check=True,
        )

        return "crontab -l | grep vibe-clock"

    def unschedule(self) -> None:
        result = subprocess.run(
            ["crontab", "-l"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return

        lines = [
            line for line in result.stdout.splitlines()
            if CRONTAB_MARKER not in line
        ]
        new_crontab = "\n".join(lines) + "\n" if lines else ""
        subprocess.run(
            ["crontab", "-"],
            input=new_crontab,
            text=True,
            check=True,
        )


_BACKENDS: list[type[BaseScheduler]] = [
    LaunchdScheduler,
    SystemdScheduler,
    CrontabScheduler,
]


def get_scheduler() -> BaseScheduler:
    """Auto-detect and return the appropriate scheduler backend."""
    for cls in _BACKENDS:
        scheduler = cls()
        if scheduler.is_available():
            return scheduler
    raise RuntimeError(
        "No supported scheduler found. "
        "Requires macOS (launchd), Linux (systemd), or crontab."
    )
