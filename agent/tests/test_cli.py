"""
Unit tests for Typer CLI commands.
"""

from typer.testing import CliRunner
from oasis_agent.cli import app

runner = CliRunner()


def test_cli_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "oasis-agent version" in result.stdout


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Autonomous CLI Agent" in result.stdout
    assert "configure" in result.stdout
    assert "status" in result.stdout
    assert "run" in result.stdout
    assert "review" in result.stdout
    assert "history" in result.stdout


def test_cli_status():
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "Free-Tier LLM Providers Status" in result.stdout
    assert "GitHub API Authentication" in result.stdout


def test_cli_history_empty(tmp_path, monkeypatch):
    # Route history DB to a clean temp directory
    cfg_file = tmp_path / "oasis-agent.config.yaml"
    cfg_file.write_text(f"""
version: "1.0"
reporting:
  database_path: "{str(tmp_path / 'history.db').replace('\\', '/')}"
""", encoding="utf-8")

    result = runner.invoke(app, ["history", "--config", str(cfg_file)])
    assert result.exit_code == 0
    assert "No historical runs found" in result.stdout
