"""Tests for the command line interface."""

from datetime import datetime, timezone

import semver
import yaml
from click.testing import CliRunner
from freezegun import freeze_time

from ssmash import cli

SIMPLE_INPUT = """foo: bar"""
SIMPLE_OUTPUT_LINE = "Name: /foo"


class TestBasicCLI:
    def test_should_display_help(self):
        runner = CliRunner()
        help_result = runner.invoke(cli.create_stack, ["--help"])
        assert help_result.exit_code == 0
        assert "--help  Show this message and exit." in help_result.output

    def test_should_exit_cleanly_with_empty_input(self):
        runner = CliRunner()
        result = runner.invoke(cli.create_stack)
        assert result.exit_code == 0
        assert not result.stderr_bytes


class TestCloudFormationMetadata:
    def test_output_should_contain_version(self):
        from ssmash import __version__ as package_version

        # Exercise
        runner = CliRunner()
        result = runner.invoke(cli.create_stack, input=SIMPLE_INPUT)

        # Verify
        cfn = yaml.safe_load(result.stdout)
        ssmash_version = cfn["Metadata"]["ssmash"]["version"]
        assert ssmash_version == package_version
        semver.parse(ssmash_version)

    def test_output_should_contain_timestamp(self):
        expected_time = datetime(2019, 5, 22, 1, 2, 3, tzinfo=timezone.utc)

        # Exercise
        runner = CliRunner()

        with freeze_time(expected_time):
            result = runner.invoke(cli.create_stack, input=SIMPLE_INPUT)

        # Verify
        cfn = yaml.safe_load(result.stdout)
        timestamp = cfn["Metadata"]["ssmash"]["generated_timestamp"]
        assert timestamp == "2019-05-22T01:02:03+00:00"


class TestCloudFormationIsProduced:
    def test_should_convert_simple_input_with_default_pipes(self):
        # Exercise
        runner = CliRunner()
        result = runner.invoke(cli.create_stack, input=SIMPLE_INPUT)

        # Verify
        assert result.exit_code == 0
        assert not result.stderr_bytes

        assert SIMPLE_OUTPUT_LINE in result.stdout

    def test_should_convert_simple_input_with_files(self):
        input_filename = "input.yaml"
        output_filename = "output.yaml"

        runner = CliRunner()
        with runner.isolated_filesystem():
            with open(input_filename, "w") as f:
                f.write(SIMPLE_INPUT)

            # Exercise
            result = runner.invoke(
                cli.create_stack, args=[input_filename, output_filename]
            )

            # Verify
            assert result.exit_code == 0
            assert not result.stdout
            assert not result.stderr_bytes

            with open(output_filename, "r") as f:
                actual_output = f.read()
            assert SIMPLE_OUTPUT_LINE in actual_output
