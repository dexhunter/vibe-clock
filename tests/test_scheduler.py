"""Tests for the scheduler module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from vibe_clock.scheduler import (
    CRONTAB_MARKER,
    CrontabScheduler,
    LaunchdScheduler,
    SystemdScheduler,
    get_scheduler,
    resolve_binary,
)


# --- resolve_binary ---


def test_resolve_binary_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("shutil.which", lambda _name: "/usr/local/bin/vibe-clock")
    assert resolve_binary() == "/usr/local/bin/vibe-clock"


def test_resolve_binary_fallback(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("shutil.which", lambda _name: None)
    fake_bin = tmp_path / "vibe-clock"
    fake_bin.touch()
    fake_python = tmp_path / "python"
    monkeypatch.setattr("sys.executable", str(fake_python))
    assert resolve_binary() == str(fake_bin)


def test_resolve_binary_not_found(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("shutil.which", lambda _name: None)
    monkeypatch.setattr("sys.executable", str(tmp_path / "python"))
    with pytest.raises(FileNotFoundError, match="Cannot find vibe-clock"):
        resolve_binary()


# --- LaunchdScheduler ---


def test_launchd_is_available(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.platform", "darwin")
    assert LaunchdScheduler().is_available()


def test_launchd_not_available_on_linux(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.platform", "linux")
    assert not LaunchdScheduler().is_available()


def test_launchd_is_scheduled(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    plist_path = tmp_path / "com.vibe-clock.push.plist"
    monkeypatch.setattr("vibe_clock.scheduler.PLIST_PATH", plist_path)
    assert not LaunchdScheduler().is_scheduled()
    plist_path.touch()
    assert LaunchdScheduler().is_scheduled()


def test_launchd_schedule(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    plist_path = tmp_path / "LaunchAgents" / "com.vibe-clock.push.plist"
    log_dir = tmp_path / "logs"
    monkeypatch.setattr("vibe_clock.scheduler.PLIST_PATH", plist_path)
    monkeypatch.setattr("vibe_clock.scheduler.LOG_DIR", log_dir)

    mock_run = MagicMock()
    monkeypatch.setattr("subprocess.run", mock_run)

    scheduler = LaunchdScheduler()
    verify = scheduler.schedule("/usr/local/bin/vibe-clock", "daily", "08:30")

    assert plist_path.exists()
    assert "launchctl list" in verify
    mock_run.assert_called_once()

    # Verify plist content
    import plistlib

    with open(plist_path, "rb") as f:
        plist = plistlib.load(f)
    assert plist["Label"] == "com.vibe-clock.push"
    assert plist["ProgramArguments"] == ["/usr/local/bin/vibe-clock", "push"]
    assert plist["StartCalendarInterval"] == {"Hour": 8, "Minute": 30}
    assert plist["RunAtLoad"] is True


def test_launchd_schedule_hourly(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    plist_path = tmp_path / "LaunchAgents" / "com.vibe-clock.push.plist"
    log_dir = tmp_path / "logs"
    monkeypatch.setattr("vibe_clock.scheduler.PLIST_PATH", plist_path)
    monkeypatch.setattr("vibe_clock.scheduler.LOG_DIR", log_dir)
    monkeypatch.setattr("subprocess.run", MagicMock())

    LaunchdScheduler().schedule("/usr/local/bin/vibe-clock", "hourly", "00:15")

    import plistlib

    with open(plist_path, "rb") as f:
        plist = plistlib.load(f)
    assert plist["StartCalendarInterval"] == {"Minute": 15}


def test_launchd_schedule_weekly(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    plist_path = tmp_path / "LaunchAgents" / "com.vibe-clock.push.plist"
    log_dir = tmp_path / "logs"
    monkeypatch.setattr("vibe_clock.scheduler.PLIST_PATH", plist_path)
    monkeypatch.setattr("vibe_clock.scheduler.LOG_DIR", log_dir)
    monkeypatch.setattr("subprocess.run", MagicMock())

    LaunchdScheduler().schedule("/usr/local/bin/vibe-clock", "weekly", "09:00")

    import plistlib

    with open(plist_path, "rb") as f:
        plist = plistlib.load(f)
    assert plist["StartCalendarInterval"] == {"Weekday": 1, "Hour": 9, "Minute": 0}


def test_launchd_unschedule(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    plist_path = tmp_path / "com.vibe-clock.push.plist"
    plist_path.touch()
    monkeypatch.setattr("vibe_clock.scheduler.PLIST_PATH", plist_path)

    mock_run = MagicMock()
    monkeypatch.setattr("subprocess.run", mock_run)

    scheduler = LaunchdScheduler()
    scheduler.unschedule()

    assert not plist_path.exists()
    mock_run.assert_called_once()


def test_launchd_unschedule_noop(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    plist_path = tmp_path / "com.vibe-clock.push.plist"
    monkeypatch.setattr("vibe_clock.scheduler.PLIST_PATH", plist_path)

    mock_run = MagicMock()
    monkeypatch.setattr("subprocess.run", mock_run)

    LaunchdScheduler().unschedule()
    mock_run.assert_not_called()


# --- SystemdScheduler ---


def test_systemd_is_available(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.platform", "linux")
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/systemctl" if name == "systemctl" else None)
    assert SystemdScheduler().is_available()


def test_systemd_not_available_on_macos(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.platform", "darwin")
    assert not SystemdScheduler().is_available()


def test_systemd_is_scheduled(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("vibe_clock.scheduler.SYSTEMD_DIR", tmp_path)
    assert not SystemdScheduler().is_scheduled()
    (tmp_path / "vibe-clock-push.timer").touch()
    assert SystemdScheduler().is_scheduled()


def test_systemd_schedule(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("vibe_clock.scheduler.SYSTEMD_DIR", tmp_path)

    mock_run = MagicMock()
    monkeypatch.setattr("subprocess.run", mock_run)

    scheduler = SystemdScheduler()
    verify = scheduler.schedule("/usr/local/bin/vibe-clock", "daily", "14:30")

    assert (tmp_path / "vibe-clock-push.service").exists()
    assert (tmp_path / "vibe-clock-push.timer").exists()
    assert "systemctl" in verify

    service_text = (tmp_path / "vibe-clock-push.service").read_text()
    assert "ExecStart=/usr/local/bin/vibe-clock push" in service_text

    timer_text = (tmp_path / "vibe-clock-push.timer").read_text()
    assert "OnCalendar=*-*-* 14:30:00" in timer_text
    assert "Persistent=true" in timer_text

    assert mock_run.call_count == 2  # daemon-reload + enable


def test_systemd_schedule_hourly(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("vibe_clock.scheduler.SYSTEMD_DIR", tmp_path)
    monkeypatch.setattr("subprocess.run", MagicMock())

    SystemdScheduler().schedule("/usr/local/bin/vibe-clock", "hourly", "00:45")

    timer_text = (tmp_path / "vibe-clock-push.timer").read_text()
    assert "OnCalendar=*-*-* *:45:00" in timer_text


def test_systemd_unschedule(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("vibe_clock.scheduler.SYSTEMD_DIR", tmp_path)
    (tmp_path / "vibe-clock-push.service").touch()
    (tmp_path / "vibe-clock-push.timer").touch()

    mock_run = MagicMock()
    monkeypatch.setattr("subprocess.run", mock_run)

    SystemdScheduler().unschedule()

    assert not (tmp_path / "vibe-clock-push.service").exists()
    assert not (tmp_path / "vibe-clock-push.timer").exists()
    assert mock_run.call_count == 2  # disable + daemon-reload


# --- CrontabScheduler ---


def test_crontab_is_available(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/crontab" if name == "crontab" else None)
    assert CrontabScheduler().is_available()


def test_crontab_not_available(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("shutil.which", lambda _name: None)
    assert not CrontabScheduler().is_available()


def test_crontab_is_scheduled(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_result = MagicMock()
    mock_result.stdout = f"0 0 * * * /usr/bin/vibe-clock push {CRONTAB_MARKER}\n"
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: mock_result)
    assert CrontabScheduler().is_scheduled()


def test_crontab_not_scheduled(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_result = MagicMock()
    mock_result.stdout = "0 0 * * * /usr/bin/other-task\n"
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: mock_result)
    assert not CrontabScheduler().is_scheduled()


def test_crontab_schedule_preserves_existing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    log_dir = tmp_path / "logs"
    monkeypatch.setattr("vibe_clock.scheduler.LOG_DIR", log_dir)

    existing_crontab = "0 5 * * * /usr/bin/backup\n"
    calls: list[tuple] = []

    def mock_run(*args, **kwargs):
        result = MagicMock()
        cmd = args[0]
        if cmd == ["crontab", "-l"]:
            result.returncode = 0
            result.stdout = existing_crontab
        elif cmd == ["crontab", "-"]:
            calls.append(("install", kwargs.get("input", "")))
        return result

    monkeypatch.setattr("subprocess.run", mock_run)

    scheduler = CrontabScheduler()
    scheduler.schedule("/usr/local/bin/vibe-clock", "daily", "08:00")

    assert len(calls) == 1
    installed = calls[0][1]
    # Existing entry preserved
    assert "/usr/bin/backup" in installed
    # New entry added
    assert CRONTAB_MARKER in installed
    assert "0 8 * * *" in installed


def test_crontab_schedule_no_existing_crontab(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    log_dir = tmp_path / "logs"
    monkeypatch.setattr("vibe_clock.scheduler.LOG_DIR", log_dir)

    calls: list[tuple] = []

    def mock_run(*args, **kwargs):
        result = MagicMock()
        cmd = args[0]
        if cmd == ["crontab", "-l"]:
            result.returncode = 1
            result.stdout = ""
        elif cmd == ["crontab", "-"]:
            calls.append(("install", kwargs.get("input", "")))
        return result

    monkeypatch.setattr("subprocess.run", mock_run)

    scheduler = CrontabScheduler()
    scheduler.schedule("/usr/local/bin/vibe-clock", "weekly", "23:00")

    assert len(calls) == 1
    installed = calls[0][1]
    assert "0 23 * * 1" in installed
    assert CRONTAB_MARKER in installed


def test_crontab_unschedule(monkeypatch: pytest.MonkeyPatch) -> None:
    existing = f"0 5 * * * /usr/bin/backup\n0 0 * * * /usr/bin/vibe-clock push {CRONTAB_MARKER}\n"
    calls: list[tuple] = []

    def mock_run(*args, **kwargs):
        result = MagicMock()
        cmd = args[0]
        if cmd == ["crontab", "-l"]:
            result.returncode = 0
            result.stdout = existing
        elif cmd == ["crontab", "-"]:
            calls.append(("install", kwargs.get("input", "")))
        return result

    monkeypatch.setattr("subprocess.run", mock_run)

    CrontabScheduler().unschedule()

    assert len(calls) == 1
    installed = calls[0][1]
    assert "/usr/bin/backup" in installed
    assert CRONTAB_MARKER not in installed


# --- get_scheduler factory ---


def test_get_scheduler_darwin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.platform", "darwin")
    scheduler = get_scheduler()
    assert isinstance(scheduler, LaunchdScheduler)


def test_get_scheduler_linux_systemd(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.platform", "linux")
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/systemctl" if name == "systemctl" else None)
    scheduler = get_scheduler()
    assert isinstance(scheduler, SystemdScheduler)


def test_get_scheduler_linux_crontab(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.platform", "linux")

    def which(name: str) -> str | None:
        if name == "crontab":
            return "/usr/bin/crontab"
        return None

    monkeypatch.setattr("shutil.which", which)
    scheduler = get_scheduler()
    assert isinstance(scheduler, CrontabScheduler)


def test_get_scheduler_unsupported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.platform", "win32")
    monkeypatch.setattr("shutil.which", lambda _name: None)
    with pytest.raises(RuntimeError, match="No supported scheduler"):
        get_scheduler()
