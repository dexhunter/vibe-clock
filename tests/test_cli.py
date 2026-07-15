"""CLI privacy and public-sharing behavior."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from click.testing import CliRunner

from vibe_clock.cli import push, render, share, unshare
from vibe_clock.config import Config
from vibe_clock.models import AgentStats, Session, TokenUsage


def test_local_render_keeps_full_configured_stats(monkeypatch, tmp_path) -> None:
    config = Config(default_days=30)
    session = Session(
        session_id="local",
        agent="codex",
        start_time=datetime.now(timezone.utc) - timedelta(hours=1),
        end_time=datetime.now(timezone.utc),
        model="gpt-private-model",
        project="private-project",
        message_count=4,
        tokens=TokenUsage(input_tokens=1000, output_tokens=500),
    )

    class Collector:
        def collect(self, days: int = 365) -> list[Session]:
            assert days == 30
            return [session]

    monkeypatch.setattr("vibe_clock.cli.load_config", lambda: config)
    monkeypatch.setattr("vibe_clock.cli.get_collectors", lambda _config: [Collector()])

    result = CliRunner().invoke(
        render,
        ["--type", "token_bars", "--output", str(tmp_path)],
    )

    assert result.exit_code == 0
    svg = (tmp_path / "vibe-clock-token-bars.svg").read_text()
    assert "gpt-private-model" in svg
    assert "No token data" not in svg


def test_push_requires_explicit_public_opt_in(monkeypatch) -> None:
    config = Config()
    monkeypatch.setattr("vibe_clock.cli.load_config", lambda: config)
    monkeypatch.setattr(
        "vibe_clock.cli._collect_public_stats",
        lambda _config: AgentStats(days_covered=7),
    )

    def fail_publish(_config: Config, _stats: AgentStats) -> None:
        raise AssertionError("disabled sharing must not publish")

    monkeypatch.setattr("vibe_clock.cli._publish_public_stats", fail_publish)

    result = CliRunner().invoke(push)

    assert result.exit_code == 0
    assert "Public sharing is disabled" in result.output


def test_share_enables_future_updates_after_confirmation(monkeypatch) -> None:
    config = Config()
    saves = []
    publishes = []
    monkeypatch.setattr("vibe_clock.cli.load_config", lambda: config)
    monkeypatch.setattr(
        "vibe_clock.cli._collect_public_stats",
        lambda _config: AgentStats(days_covered=7),
    )
    monkeypatch.setattr(
        "vibe_clock.cli._publish_public_stats",
        lambda current, _stats: publishes.append(current.privacy.public_sharing_enabled),
    )
    monkeypatch.setattr("vibe_clock.cli.save_config", lambda current: saves.append(current))

    result = CliRunner().invoke(share, ["--yes"])

    assert result.exit_code == 0
    assert publishes == [True]
    assert saves[-1].privacy.public_sharing_enabled is True
    assert saves[-1].privacy.public_days == 7


def test_share_requires_legacy_history_cleanup(monkeypatch) -> None:
    config = Config()
    config.github.gist_id = "legacy-gist"
    monkeypatch.setattr("vibe_clock.cli.load_config", lambda: config)

    result = CliRunner().invoke(share, ["--yes"])

    assert result.exit_code == 0
    assert "legacy public Gist" in result.output
    assert config.privacy.public_sharing_enabled is False


def test_unshare_deletes_gist_and_disables_updates(monkeypatch) -> None:
    config = Config()
    config.github.token = "configured"
    config.github.gist_id = "gist-id"
    config.privacy.public_sharing_enabled = True
    saves = []
    monkeypatch.setattr("vibe_clock.cli.load_config", lambda: config)
    monkeypatch.setattr("vibe_clock.cli.save_config", lambda current: saves.append(current))
    monkeypatch.setattr(
        "httpx.delete",
        lambda *args, **kwargs: SimpleNamespace(status_code=204, text=""),
    )

    result = CliRunner().invoke(unshare, ["--yes"])

    assert result.exit_code == 0
    assert saves[-1].github.gist_id == ""
    assert saves[-1].privacy.public_sharing_enabled is False
