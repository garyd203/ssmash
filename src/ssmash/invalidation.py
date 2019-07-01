"""Tools to invalidate applications that depend on the parameters."""

from typing import List

from flyingcircus.core import Stack
from flyingcircus.intrinsic_function import GetAtt
from flyingcircus.intrinsic_function import Ref
from flyingcircus.service.lambda_ import Function
from flyingcircus.service.ssm import SSMParameter

from ssmash.custom_resources import replace_lambda_context_resource_handler
from ssmash.custom_resources import restart_ecs_service_resource_handler


def create_ecs_service_invalidation_stack(
    cluster,
    service,
    dependencies: List[SSMParameter],
    restart_role,
    timeout: int = 8 * 60,
) -> Stack:
    """Create CloudFormation resources to invalidate a single ECS service.

    This is accomplished by restarting the ECS service, which will force it to
    use the new parameters.

    Parameters:
        cluster: CloudFormation reference (eg. an ARN) to the cluster the service is in
        dependencies: SSM Parameters that this service uses
        service: CloudFormation reference (eg. an ARN) to the ECS service to invalidate
        restart_role: CloudFormation reference (eg. an ARN) to an IAM role
            that will be used to restart the ECS service.
        timeout: Number of seconds to wait for the ECS service to detect the
            new parameters successfully after restart. If we exceed this
            timeout it is presumed that the updated parameters are broken,
            and the changes will be rolled back. The default is 5 minutes,
            which should be enough for most services.
    """
    # TODO make restart_role optional, and create it on-the-fly if not provided
    # TODO find a way to share role and lambda between multiple calls in the same stack? can de-dupe/cache based on identity in the final stack
    # TODO get Lambda handler to have an internal timeout as well?

    stack = Stack(Description="Invalidate ECS service after parameter update")

    # Create an inline Lambda that can restart an ECS service, since this
    # isn't built-in CloudFormation functionality.
    stack.Resources[
        "RestartLambda"
    ] = restart_service_lambda = Function.create_from_python_function(
        handler=restart_ecs_service_resource_handler, Role=restart_role
    )

    # The Lambda timeout should be a bit longer than the restart timeout,
    # to give some leeway.
    restart_service_lambda.Properties.Timeout = timeout + 15

    # Create a custom resource to restart the ECS service.
    #
    # We don't want the service restart to happen until the parameters have
    # all been created, so we need to have the Restarter resource depend on
    # the parameters (either implicitly or via DependsOn). We also want the
    # restart to only happen if the parameters have actually changed - this
    # can be done if we make the SSM Parameters be part of the resource
    # specification (both the key and the value).
    stack.Resources["Restarter"] = dict(
        Type="Custom::RestartEcsService",
        Properties=dict(
            ServiceToken=GetAtt(restart_service_lambda, "Arn"),
            ClusterArn=cluster,
            ServiceArn=service,
            IgnoredParameterNames=[Ref(p) for p in dependencies],
            IgnoredParameterKeys=[GetAtt(p, "Value") for p in dependencies],
        ),
    )

    # TODO consider creating a waiter anyway, so that the timeout is strictly reliable

    return stack


def create_lambda_invalidation_stack(
    function: str, dependencies: List[SSMParameter], role
) -> Stack:
    """Create CloudFormation resources to invalidate a single AWS Lambda Function.

    This is accomplished by adding a meaningless environment variable to the
    Function, which will force it to re-deploy into a new execution context
    (but without altering any behaviour).

    Parameters:
        dependencies: SSM Parameters that this Function uses
        function: CloudFormation reference to the Lambda Function
            (eg. an unversioned ARN, or the name)
        role: CloudFormation reference (eg. an ARN) to an IAM role
            that will be used to modify the Function.
    """
    # TODO make role optional, and create it on-the-fly if not provided
    # TODO find a way to share role and lambda between multiple calls in the same stack? can de-dupe/cache based on identity in the final stack
    # TODO get Lambda handler to have an internal timeout as well?

    stack = Stack(Description="Invalidate Lambda Function after parameter update")

    # Create an inline Lambda that can restart an ECS service, since this
    # isn't built-in CloudFormation functionality.
    stack.Resources[
        "ReplacementLambda"
    ] = replace_lambda_context_lambda = Function.create_from_python_function(
        handler=replace_lambda_context_resource_handler, Role=role
    )

    # Set the Lambda Replacer's timeout to a fixed value. This should be
    # universal, so we don't let callers specify it.
    replace_lambda_context_lambda.Properties.Timeout = 20

    # Create a custom resource to replace the Lambda's execution context.
    #
    # We don't want this to happen until the parameters have
    # all been created, so we need to have the Restarter resource depend on
    # the parameters (either implicitly or via DependsOn). We also want the
    # restart to only happen if the parameters have actually changed - this
    # can be done if we make the SSM Parameters be part of the resource
    # specification (both the key and the value).
    # TODO pull out common code here
    stack.Resources["Replacer"] = dict(
        Type="Custom::ReplaceLambdaContext",
        Properties=dict(
            ServiceToken=GetAtt(replace_lambda_context_lambda, "Arn"),
            FunctionName=function,
            IgnoredParameterNames=[Ref(p) for p in dependencies],
            IgnoredParameterKeys=[GetAtt(p, "Value") for p in dependencies],
        ),
    )

    # TODO consider creating a waiter anyway, so that the timeout is strictly reliable

    return stack
