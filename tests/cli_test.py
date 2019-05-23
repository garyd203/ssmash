"""Tests for command line interface."""

from click.testing import CliRunner

from ssmash import cli


def test_should_exit_cleanly():
    runner = CliRunner()
    result = runner.invoke(cli.main)
    assert result.exit_code == 0
    assert "ssmash.cli.main" in result.output


def test_should_display_help():
    runner = CliRunner()
    help_result = runner.invoke(cli.main, ["--help"])
    assert help_result.exit_code == 0
    assert "--help  Show this message and exit." in help_result.output
