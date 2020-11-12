"""Tests for the command line interface."""

import re
from contextlib import contextmanager
from datetime import datetime
from datetime import timezone
from textwrap import dedent
from unittest.mock import ANY
from unittest.mock import patch

import pytest
import semver
import yaml
from click.testing import CliRunner
from flyingcircus.intrinsic_function import ImportValue
from flyingcircus.service.ssm import SSMParameter
from freezegun import freeze_time

from ssmash import cli
from ssmash.invalidation import create_ecs_service_invalidation_stack
from ssmash.invalidation import create_lambda_invalidation_stack

SIMPLE_INPUT = """foo: bar"""
SIMPLE_OUTPUT_LINE = "Name: /foo"


class Patchers:
    """Collection of helpers to patch ssmash internal functions.

    Note that we usually have to patch the object imported into the `cli`
    module, not the original function definition in the `invalidation` module
    """

    @staticmethod
    @contextmanager
    def create_lambda_invalidation_stack():
        with patch(
            "ssmash.cli.create_lambda_invalidation_stack",
            wraps=create_lambda_invalidation_stack,
        ) as mocked:
            yield mocked

    @staticmethod
    @contextmanager
    def create_ecs_service_invalidation_stack():
        # Note that we patch the object imported into the `loader` module, not
        # the original function definition in the `invalidation` module
        with patch(
            "ssmash.loader.create_ecs_service_invalidation_stack",
            wraps=create_ecs_service_invalidation_stack,
        ) as mocked:
            yield mocked

    @staticmethod
    @contextmanager
    def write_cfn_template():
        with patch(
            "ssmash.cli._write_cfn_template", wraps=cli._write_cfn_template
        ) as mocked:
            yield mocked


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

    @pytest.mark.parametrize(
        ("command", "description"),
        [("invalidate-ecs", r"Invalidate.*cache.*ECS\s+Service")],
    )
    def test_sub_commands_should_display_help(self, command, description):
        runner = CliRunner()
        help_result = runner.invoke(cli.run_ssmash, [command, "--help"])

        assert help_result.exit_code == 0
        assert re.search(r"--help +Show this message and exit", help_result.output)
        assert re.search(description, help_result.output, re.DOTALL | re.I)

    def test_should_exit_cleanly_with_empty_input(self):
        runner = CliRunner()
        result = runner.invoke(cli.run_ssmash)
        assert result.exit_code == 0
        assert not result.stderr_bytes

    def test_should_convert_simple_input(self):
        # Exercise
        runner = CliRunner()
        with Patchers.write_cfn_template() as write_mock:
            result = runner.invoke(cli.run_ssmash, input=SIMPLE_INPUT)

        # Verify
        assert result.exit_code == 0
        assert not result.stderr_bytes

        write_mock.assert_called_once()
        actual_stack = write_mock.call_args[0][2]

        assert sorted(actual_stack.Resources.keys()) == ["SSMParamFoo"]
        assert actual_stack.Resources["SSMParamFoo"].Properties.Name == "/foo"
        assert actual_stack.Resources["SSMParamFoo"].Properties.Value == "bar"


class TestCloudFormationMetadata:
    def test_stack_should_have_description(self):
        # Setup
        description = "Some lengthy text"

        # Exercise
        runner = CliRunner()
        result = runner.invoke(cli.run_ssmash, args=["--description", description])

        # Verify
        cfn = yaml.safe_load(result.stdout)
        assert cfn["Description"] == description

    def test_output_should_contain_version(self):
        from ssmash import __version__ as package_version

        # Exercise
        runner = CliRunner()
        result = runner.invoke(cli.run_ssmash)

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
            result = runner.invoke(cli.run_ssmash)

        # Verify
        cfn = yaml.safe_load(result.stdout)
        timestamp = cfn["Metadata"]["ssmash"]["generated_timestamp"]
        assert timestamp == "2019-05-22T01:02:03+00:00"


class TestCloudFormationIsProduced:
    def test_should_convert_simple_input_with_default_pipes(self):
        # Exercise
        runner = CliRunner()
        result = runner.invoke(cli.run_ssmash, input=SIMPLE_INPUT)

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
                cli.run_ssmash, args=["-i", input_filename, "-o", output_filename]
            )

            # Verify
            assert result.exit_code == 0
            assert not result.stdout
            assert not result.stderr_bytes

            with open(output_filename, "r") as f:
                actual_output = f.read()
            assert SIMPLE_OUTPUT_LINE in actual_output


class TestEcsServiceInvalidation:
    def run_script_with_invalidation_params(
        self, cluster=None, service=None, role=None, extra_args=None
    ):
        """Execute script with simple input, and ECS service invalidation."""
        args = ["invalidate-ecs"]

        if cluster:
            args.append("--cluster-name")
            args.append(cluster)
        if service:
            args.append("--service-name")
            args.append(service)
        if role:
            args.append("--role-name")
            args.append(role)

        if extra_args:
            args.extend(extra_args)

        runner = CliRunner()
        result = runner.invoke(
            cli.run_ssmash, input=SIMPLE_INPUT, args=args, catch_exceptions=False
        )
        return result

    def test_should_call_invalidation_helper_and_have_parameters_in_output(self):
        # Setup
        cluster = "arn:cluster"
        service = "arn:service"
        role = "arn:role"

        # Exercise
        with Patchers.create_ecs_service_invalidation_stack() as invalidation_mock:
            result = self.run_script_with_invalidation_params(cluster, service, role)

        # Verify
        assert result.exit_code == 0

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

        # Exercise
        with Patchers.create_ecs_service_invalidation_stack() as invalidation_mock:
            result = self.run_script_with_invalidation_params(
                extra_args=[
                    "--cluster-import",
                    cluster_export,
                    "--service-import",
                    service_export,
                    "--role-import",
                    role_export,
                ]
            )

        # Verify
        assert result.exit_code == 0

        invalidation_mock.assert_called_with(
            cluster=ImportValue(cluster_export),
            service=ImportValue(service_export),
            dependencies=ANY,
            restart_role=ImportValue(role_export),
        )

    @pytest.mark.parametrize(
        ("cluster", "service", "role"),
        [
            (None, "arn:service", "arn:role"),
            (None, None, "arn:role"),
            (None, "arn:service", None),
            ("arn:cluster", None, "arn:role"),
            ("arn:cluster", None, None),
            ("arn:cluster", "arn:service", None),
        ],
    )
    def test_should_error_if_not_all_parameters_specified(self, cluster, service, role):
        # Exercise
        with Patchers.create_ecs_service_invalidation_stack() as invalidation_mock:
            result = self.run_script_with_invalidation_params(cluster, service, role)

        # Verify
        assert result.exit_code != 0
        invalidation_mock.assert_not_called()

    @pytest.mark.parametrize("param_name", ["cluster", "service", "role"])
    def test_should_error_if_both_name_and_import_specified(self, param_name):
        # Setup
        cluster = "arn:cluster"
        service = "arn:service"
        role = "arn:role"

        # Exercise
        with Patchers.create_ecs_service_invalidation_stack() as invalidation_mock:
            result = self.run_script_with_invalidation_params(
                cluster,
                service,
                role,
                extra_args=[f"--{param_name}-import", "some-import-name"],
            )

        # Verify
        assert result.exit_code != 0
        invalidation_mock.assert_not_called()


class TestLambdaInvalidation:
    def run_script_with_invalidation_params(
        self, function=None, role=None, extra_args=None
    ):
        """Execute script with simple input, and Lambda invalidation."""
        args = ["invalidate-lambda"]

        if function:
            args.append("--function-name")
            args.append(function)
        if role:
            args.append("--role-name")
            args.append(role)

        if extra_args:
            args.extend(extra_args)

        runner = CliRunner()
        result = runner.invoke(
            cli.run_ssmash, input=SIMPLE_INPUT, args=args, catch_exceptions=False
        )
        return result

    def test_should_call_invalidation_helper_and_have_parameters_in_output(self):
        # Setup
        function = "function-name"
        role = "arn:role"

        # Exercise
        with Patchers.create_lambda_invalidation_stack() as invalidation_mock:
            result = self.run_script_with_invalidation_params(function, role)

        # Verify
        assert result.exit_code == 0

        invalidation_mock.assert_called_with(
            function=function, role=role, dependencies=ANY
        )

        assert function in result.stdout
        assert role in result.stdout

    def test_should_dereference_cloudformation_imports(self):
        # Setup
        function_export = "some-function-export"
        role_export = "some-role-export"

        # Exercise
        with Patchers.create_lambda_invalidation_stack() as invalidation_mock:
            result = self.run_script_with_invalidation_params(
                extra_args=[
                    "--function-import",
                    function_export,
                    "--role-import",
                    role_export,
                ]
            )

        # Verify
        assert result.exit_code == 0

        invalidation_mock.assert_called_with(
            function=ImportValue(function_export),
            dependencies=ANY,
            role=ImportValue(role_export),
        )

    @pytest.mark.parametrize(
        ("function", "role"), [(None, "arn:role"), ("function-name", None)]
    )
    def test_should_error_if_not_all_parameters_specified(self, function, role):
        # Exercise
        with Patchers.create_lambda_invalidation_stack() as invalidation_mock:
            result = self.run_script_with_invalidation_params(function, role)

        # Verify
        assert result.exit_code != 0
        invalidation_mock.assert_not_called()

    @pytest.mark.parametrize("param_name", ["function", "role"])
    def test_should_error_if_both_name_and_import_specified(self, param_name):
        # Setup
        function = "function-name"
        role = "arn:role"

        # Exercise
        with Patchers.create_lambda_invalidation_stack() as invalidation_mock:
            result = self.run_script_with_invalidation_params(
                function,
                role,
                extra_args=[f"--{param_name}-import", "some-import-name"],
            )

        # Verify
        assert result.exit_code != 0
        invalidation_mock.assert_not_called()


class TestEmbeddedInvalidation:
    def run_script_with_embedded_invalidation(
        self,
        cluster="fake-cluster-name",
        service="fake-service-name",
        role="fake-role-name",
    ):
        """Execute script with simple input, and ECS service invalidation."""
        param_input = dedent(
            f"""---
            top:
                first:
                    a: 1
                    b: 2
                ? !item {{invalidates: [servicea], key: second}}
                :
                    a: 1
                    b: 2
                third:
                    a: 1
                    ? !item {{invalidates: [servicea], key: b}}
                    : 2
            .ssmash-config:
                invalidations:
                    servicea: !ecs-invalidation
                        cluster_name: {cluster}
                        service_name: {service}
                        role_name: {role}
        """
        )

        runner = CliRunner()
        result = runner.invoke(
            cli.run_ssmash, input=param_input, catch_exceptions=False
        )
        return result

    def test_should_create_resources(self):
        # Exercise
        with Patchers.write_cfn_template() as write_mock:
            result = self.run_script_with_embedded_invalidation()

        # Verify
        assert result.exit_code == 0
        assert not result.stderr_bytes

        write_mock.assert_called_once()
        actual_stack = write_mock.call_args[0][2]

        actual_parameter_names = [
            k for k, v in actual_stack.Resources.items() if isinstance(v, SSMParameter)
        ]
        assert sorted(actual_parameter_names) == [
            "SSMParamTopFirstA",
            "SSMParamTopFirstB",
            "SSMParamTopSecondA",
            "SSMParamTopSecondB",
            "SSMParamTopThirdA",
            "SSMParamTopThirdB",
        ]

        assert (
            actual_stack.Resources["SSMParamTopSecondA"].Properties.Name
            == "/top/second/a"
        ), "Should use plain key when node is invalidated"
        assert (
            actual_stack.Resources["SSMParamTopSecondA"].Properties.Value == "1"
        ), "Should use plain value when node is invalidated"

        assert (
            actual_stack.Resources["SSMParamTopThirdB"].Properties.Name
            == "/top/third/b"
        ), "Should use plain key when leaf value is invalidated"
        assert (
            actual_stack.Resources["SSMParamTopThirdB"].Properties.Value == "2"
        ), "Should use plain value when leaf value is invalidated"

    def test_should_call_invalidation_helper_with_dependent_parameters(self):
        # Setup
        cluster = "arn:cluster"
        service = "arn:service"
        role = "arn:role"

        # Exercise
        with Patchers.create_ecs_service_invalidation_stack() as invalidation_mock:
            result = self.run_script_with_embedded_invalidation(cluster, service, role)

        # Verify
        assert result.exit_code == 0
        assert not result.stderr_bytes

        invalidation_mock.assert_called_once_with(
            cluster=cluster, service=service, dependencies=ANY, restart_role=role
        )

        dependency_names = sorted(
            param.Properties.Name
            for param in (invalidation_mock.call_args[1]["dependencies"])
        )
        assert dependency_names == ["/top/second/a", "/top/second/b", "/top/third/b"]

        assert cluster in result.stdout
        assert service in result.stdout
        assert role in result.stdout
