"""Regression tests for the composite GitHub Action."""

from pathlib import Path


ACTION_YAML = Path(__file__).parents[1] / "action.yml"


def test_action_installs_from_checked_out_source() -> None:
    action = ACTION_YAML.read_text()

    assert "github.action_ref" not in action
    assert "VIBE_CLOCK_ACTION_PATH: ${{ github.action_path }}" in action
    assert 'python -m pip install "$VIBE_CLOCK_ACTION_PATH"' in action
