"""Tests for the command line interface."""
import re
from contextlib import contextmanager
from datetime import datetime
from datetime import timezone
from unittest.mock import ANY
from unittest.mock import patch

import pytest
import semver
import yaml
from click.testing import CliRunner
from flyingcircus.intrinsic_function import ImportValue
from freezegun import freeze_time

from ssmash import cli
from ssmash.invalidation import create_ecs_service_invalidation_stack

SIMPLE_INPUT = """foo: bar"""
SIMPLE_OUTPUT_LINE = "Name: /foo"


class TestBasicCLI:
    def test_should_display_help(self):
        runner = CliRunner()
        help_result = runner.invoke(cli.run_ssmash, ["--help"])

        assert help_result.exit_code == 0
        assert re.search(r"--help +Show this message and exit", help_result.output)
        assert re.search(
            r"Convert.*YAML.*application\s+configuration.*CloudFormation.*SSM\s+parameter",
            help_result.output,
            re.DOTALL | re.I,
        )

    def test_should_exit_cleanly_with_empty_input(self):
        runner = CliRunner()
        result = runner.invoke(cli.run_ssmash, args=["-"])
        assert result.exit_code == 0
        assert not result.stderr_bytes


class TestCloudFormationMetadata:
    def test_stack_should_have_description(self):
        # Setup
        description = "Some lengthy text"

        # Exercise
        runner = CliRunner()
        result = runner.invoke(
            cli.run_ssmash, args=["--description", description, "-"]
        )

        # Verify
        cfn = yaml.safe_load(result.stdout)
        assert cfn["Description"] == description

    def test_output_should_contain_version(self):
        from ssmash import __version__ as package_version

        # Exercise
        runner = CliRunner()
        result = runner.invoke(cli.run_ssmash, args=["-"])

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
            result = runner.invoke(cli.run_ssmash, args=["-"])

        # Verify
        cfn = yaml.safe_load(result.stdout)
        timestamp = cfn["Metadata"]["ssmash"]["generated_timestamp"]
        assert timestamp == "2019-05-22T01:02:03+00:00"


class TestCloudFormationIsProduced:
    def test_should_error_if_input_file_is_not_specified(self):
        # Exercise
        runner = CliRunner()
        result = runner.invoke(cli.run_ssmash, input=SIMPLE_INPUT)

        # Verify
        assert result.exit_code != 0

    def test_should_convert_simple_input_with_default_pipes(self):
        # Exercise
        runner = CliRunner()
        result = runner.invoke(cli.run_ssmash, input=SIMPLE_INPUT, args=["-"])

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
                cli.run_ssmash, args=["-o", output_filename, input_filename]
            )

            # Verify
            assert result.exit_code == 0
            assert not result.stdout
            assert not result.stderr_bytes

            with open(output_filename, "r") as f:
                actual_output = f.read()
            assert SIMPLE_OUTPUT_LINE in actual_output


class TestEcsServiceInvalidation:
    @staticmethod
    @contextmanager
    def patch_create_invalidation_stack():
        # Note that we patch the object imported into the `cli` module, not
        # the original function definition in the `invalidation` module
        with patch(
            "ssmash.cli.create_ecs_service_invalidation_stack",
            wraps=create_ecs_service_invalidation_stack,
        ) as mocked:
            yield mocked

    def run_script_with_invalidation_params(self, cluster, service, role):
        """Execute script with simple input, and ECS service invalidation."""
        args = ["-"]
        if cluster or service:
            args.append("--invalidate-ecs-service")
            if cluster:
                args.append(cluster)
            if service:
                args.append(service)
        if role:
            args.append("--invalidation-role")
            args.append(role)

        runner = CliRunner()
        result = runner.invoke(
            cli.create_stack, input=SIMPLE_INPUT, args=args, catch_exceptions=False
        )
        return result

    def test_should_call_invalidation_helper_and_have_parameters_in_output(self):
        # Setup
        cluster = "arn:cluster"
        service = "arn:service"
        role = "arn:role"

        # Exercise
        with self.patch_create_invalidation_stack() as invalidation_mock:
            result = self.run_script_with_invalidation_params(cluster, service, role)

        # Verify
        invalidation_mock.assert_called_with(
            cluster=cluster, service=service, dependencies=ANY, restart_role=role
        )

        assert cluster in result.stdout
        assert service in result.stdout
        assert role in result.stdout

    def test_should_dereference_cloudformation_imports(self):
        # Setup
        cluster_export = "some-cluster-export"
        service_export = "some-service-export"
        role_export = "some-role-export"

        cluster_cli_param = "!ImportValue:" + cluster_export
        service_cli_param = "!ImportValue:" + service_export
        role_cli_param = "!ImportValue:" + role_export

        # Exercise
        with self.patch_create_invalidation_stack() as invalidation_mock:
            self.run_script_with_invalidation_params(
                cluster_cli_param, service_cli_param, role_cli_param
            )

        # Verify
        invalidation_mock.assert_called_with(
            cluster=ImportValue(cluster_export),
            service=ImportValue(service_export),
            dependencies=ANY,
            restart_role=ImportValue(role_export),
        )

    def test_should_ignore_role_if_service_not_specified(self):
        # Exercise
        with self.patch_create_invalidation_stack() as invalidation_mock:
            self.run_script_with_invalidation_params(None, None, "arn:role")

        # Verify
        invalidation_mock.assert_not_called()

    def test_should_error_if_role_not_specified(self):
        # Exercise
        with self.patch_create_invalidation_stack() as invalidation_mock:
            result = self.run_script_with_invalidation_params(
                "arn:cluster", "arn:service", None
            )

        # Verify
        assert result.exit_code != 0
        invalidation_mock.assert_not_called()

    @pytest.mark.parametrize(
        ("cluster", "service"), [(None, "arn:service"), ("arn:cluster", None)]
    )
    def test_should_error_if_cluster_and_service_not_specified(self, cluster, service):
        # Exercise
        with self.patch_create_invalidation_stack() as invalidation_mock:
            result = self.run_script_with_invalidation_params(
                cluster, service, "arn:role"
            )

        # Verify
        assert result.exit_code != 0
        invalidation_mock.assert_not_called()
