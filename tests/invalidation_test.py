import re

from flyingcircus.core import AWSObject
from flyingcircus.intrinsic_function import GetAtt
from flyingcircus.intrinsic_function import Ref
from flyingcircus.service.lambda_ import Function
from flyingcircus.service.ssm import SSMParameter
from flyingcircus.service.ssm import SSMParameterProperties

from ssmash.invalidation import create_ecs_service_invalidation_stack
from ssmash.invalidation import create_lambda_invalidation_stack


class TestEcsServiceInvalidation:
    def test_creates_stack_with_supplied_parameters(self):
        # Setup
        ssm_parameter = SSMParameter(
            Properties=SSMParameterProperties(
                Name="test-parameter-name", Type="String", Value="test-param-value"
            )
        )

        cluster_name = "cluster-name"
        service = "service-name"
        dependencies = [ssm_parameter]
        role = "role-arn"

        # Exercise
        stack = create_ecs_service_invalidation_stack(
            cluster=cluster_name,
            service=service,
            dependencies=dependencies,
            restart_role=role,
            timeout=30,
        )

        # Verify Lambda Function
        functions = [r for r in stack.Resources.values() if isinstance(r, Function)]
        assert len(functions) == 1, "There should be a Lambda Function resource"

        func = functions[0]
        assert re.search(
            r"restart.*ecs.*service", func.Properties.Handler, re.I
        ), "Lambda should restart an ECS service"
        assert func.Properties.Role == role

        # Verify Custom Resource
        custom_resources = [
            r for r in stack.Resources.values() if r["Type"].startswith("Custom::")
        ]
        assert (
            len(custom_resources) == 1
        ), "There should be a custom resource to restart the ECS service"

        restarter = custom_resources[0]
        assert restarter["Properties"]["ClusterArn"] == cluster_name
        assert restarter["Properties"]["ServiceArn"] == service

        # Verify dependencies for service restart
        dependent_values = _get_flattened_attributes(restarter)
        assert Ref(ssm_parameter) in dependent_values
        assert GetAtt(ssm_parameter, "Value") in dependent_values


def _get_flattened_attributes(value) -> set:
    """Get all attributes on this resource, flattening the hierarchy"""
    result = set()
    if isinstance(value, (set, list)):
        for v in value:
            result |= _get_flattened_attributes(v)
    elif isinstance(value, dict):
        for v in value.values():
            result |= _get_flattened_attributes(v)
    elif isinstance(value, AWSObject):
        for k in value:
            v = value[k]
            result |= _get_flattened_attributes(v)
    else:
        result.add(value)

    return result


class TestLambdaInvalidation:
    def test_creates_stack_for_single_lambda(self):
        # TODO pull out some common helpers

        # Setup
        ssm_parameter = SSMParameter(
            Properties=SSMParameterProperties(
                Name="test-parameter-name", Type="String", Value="test-param-value"
            )
        )

        function_name = "some-function-name"
        dependencies = [ssm_parameter]
        role = "role-arn"

        # Exercise
        stack = create_lambda_invalidation_stack(
            function=function_name, dependencies=dependencies, role=role
        )

        # Verify Lambda Function
        functions = [r for r in stack.Resources.values() if isinstance(r, Function)]
        assert (
            len(functions) == 1
        ), "There should be a Lambda Function resource to perform the invalidation"

        func = functions[0]
        assert re.search(
            r"replace.*lambda.*context", func.Properties.Handler, re.I
        ), "Lambda should update an existing Lambda"
        assert func.Properties.Role == role

        # Verify Custom Resource
        custom_resources = [
            r for r in stack.Resources.values() if r["Type"].startswith("Custom::")
        ]
        assert (
            len(custom_resources) == 1
        ), "There should be a custom resource to update the target Lambda"

        updater = custom_resources[0]
        assert updater["Properties"]["FunctionName"] == function_name

        # Verify dependencies for Lambda update
        dependent_values = _get_flattened_attributes(updater)
        assert Ref(ssm_parameter) in dependent_values
        assert GetAtt(ssm_parameter, "Value") in dependent_values
