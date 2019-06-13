# -*- coding: utf-8 -*-

"""Convert a plain YAML file with application configuration into a CloudFormation template with SSM parameters."""

import sys
from datetime import datetime
from datetime import timezone
from functools import partial
from functools import wraps
from typing import Callable
from typing import Optional
from typing import Tuple
from typing import Union

import click
import yaml
from flyingcircus.core import Stack
from flyingcircus.intrinsic_function import ImportValue
from flyingcircus.service.ssm import SSMParameter

from ssmash.converter import convert_hierarchy_to_ssm
from ssmash.invalidation import create_ecs_service_invalidation_stack

# TODO move helper functions to another module
# TODO tests for helper functions


#: Prefix for specifying a CloudFormation import as a CLI parameter
CFN_IMPORT_PREFIX = "!ImportValue:"


@click.group("ssmash", chain=True, invoke_without_command=True, help=__doc__)
@click.option(
    "-i",
    "--input",
    "--input-file",
    "input_file",
    type=click.File("r"),
    default="-",
    help="Where to read the application configuration YAML file",
)
@click.option(
    "-o",
    "--output",
    "--output-file",
    "output_file",
    type=click.File("w"),
    default="-",
    help="Where to write the CloudFormation template file",
)
@click.option(
    "--description",
    type=str,
    default="Application configuration",
    help="The description for the CloudFormation stack.",
)
def run_ssmash(input_file, output_file, description: str):
    pass


@run_ssmash.resultcallback()
def process_pipeline(processors, input_file, output_file, description: str):
    # Create basic processor inputs
    appconfig = _load_appconfig_from_yaml(input_file)
    stack = _initialise_stack(description)

    # Augment processing functions with default loader and writer
    processors = (
        [_create_ssm_parameters]
        + processors
        + [partial(_write_cfn_template, output_file)]
    )

    # Apply all chained commands
    for processor in processors:
        processor(appconfig, stack)


def appconfig_processor(func: Callable) -> Callable:
    """Decorator to convert a Click command into a custom processor for application configuration."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        def processor(appconfig: dict, stack: Stack):
            return func(appconfig, stack, *args, **kwargs)

        return processor

    return wrapper


@run_ssmash.command("invalidate-ecs")
@click.option(
    "-c",
    "--cluster-name",
    type=str,
    default=None,
    help="The cluster that contains the ECS Service to invalidate (as a name or ARN).",
    metavar="ARN",
)
@click.option(
    "--cluster-import",
    type=str,
    default=None,
    help=(
        "Alternative way to specify the cluster that contains the ECS "
        "Service to invalidate, by referencing a CloudFormation export."
    ),
    metavar="EXPORT_NAME",
)
@click.option(
    "-s",
    "--service-name",
    type=str,
    default=None,
    help="The ECS Service that depends on this configuration (as a name or ARN).",
    metavar="ARN",
)
@click.option(
    "--service-import",
    type=str,
    default=None,
    help=(
        "Alternative way to specify the ECS Service to invalidate, "
        "by referencing a CloudFormation export."
    ),
    metavar="EXPORT_NAME",
)
@click.option(
    "-r",
    "--role-name",
    type=str,
    default=None,
    help="The IAM role to use for invalidating this service.",
    metavar="ARN",
)
@click.option(
    "--role-import",
    type=str,
    default=None,
    help=(
        "Alternative way to specify the IAM role to use for invalidating "
        "this service, by referencing a CloudFormation export."
    ),
    metavar="EXPORT_NAME",
)
@appconfig_processor
def invalidate_ecs_service(
    appconfig,
    stack,
    cluster_name,
    cluster_import,
    service_name,
    service_import,
    role_name,
    role_import,
):
    """Invalidate the cache in an ECS Service that uses these parameters,
    by restarting the service.
    """
    # Unpack the resource references
    cluster = _get_cfn_resource_from_options("cluster", cluster_name, cluster_import)
    service = _get_cfn_resource_from_options("service", service_name, service_import)
    role = _get_cfn_resource_from_options("role", role_name, role_import)

    # Use a custom Lambda to restart the service iff it's dependent resources
    # have changed
    stack.merge_stack(
        create_ecs_service_invalidation_stack(
            cluster=cluster,
            service=service,
            dependencies=[
                r for r in stack.Resources.values() if isinstance(r, SSMParameter)
            ],
            restart_role=role,
        ).with_prefixed_names("InvalidateEcs")
    )


@click.command(help=__doc__)
@click.argument("input", type=click.File("r"))
@click.option(
    "-o",
    "--output",
    type=click.File("w"),
    default="-",
    help="Where to write the CloudFormation template file",
)
@click.option(
    "--description",
    type=str,
    default="Application configuration",
    help="The description for the CloudFormation stack.",
)
@click.option(
    "--invalidate-ecs-service",
    nargs=2,
    type=str,
    help=(
        "Whether to invalidate (restart) an ECS Service that depends on this "
        + "configuration. The cluster and service may be referenced by their "
        + "name or ARN. "
        + "You can also reference a CloudFormation export if you prefix it "
        + f"with '{CFN_IMPORT_PREFIX}' (eg. '{CFN_IMPORT_PREFIX}some-export-name'."
    ),
    metavar="ClusterArn ServiceArn",
)
@click.option(
    "--invalidation-role",
    type=str,
    default=None,
    help=(
        "The ARN of the IAM role to use for invalidating services. "
        + "You can also reference a CloudFormation export if you prefix it "
        + f"with '{CFN_IMPORT_PREFIX}' (eg. '{CFN_IMPORT_PREFIX}some-export-name'."
    ),
    metavar="ARN",
)
def create_stack(
    input,
    output,
    description: str,
    invalidate_ecs_service: Tuple[str, str],
    invalidation_role: str,
):
    appconfig = _load_appconfig_from_yaml(input)
    stack = _initialise_stack(description)

    _create_ssm_parameters(appconfig, stack)

    # Re-deploy the specified ECS service
    if invalidate_ecs_service:
        ecs_cluster, ecs_service = invalidate_ecs_service
        ecs_cluster = _dereference_cfn_import_maybe(ecs_cluster)
        ecs_service = _dereference_cfn_import_maybe(ecs_service)

        if not invalidation_role:
            raise click.UsageError(
                "An invalidation-role needs to be supplied that will be used to restart the ECS service."
            )

        stack.merge_stack(
            create_ecs_service_invalidation_stack(
                cluster=ecs_cluster,
                service=ecs_service,
                dependencies=[
                    r for r in stack.Resources.values() if isinstance(r, SSMParameter)
                ],
                restart_role=_dereference_cfn_import_maybe(invalidation_role),
            ).with_prefixed_names("InvalidateEcs")
        )

    # Write YAML to the specified file
    _write_cfn_template(output, appconfig, stack)


def _create_ssm_parameters(appconfig: dict, stack: Stack):
    """Create SSM parameters for every item in the application configuration"""
    stack.merge_stack(
        convert_hierarchy_to_ssm(appconfig).with_prefixed_names("SSMParam")
    )


def _dereference_cfn_import_maybe(
    ref: Optional[str]
) -> Optional[Union[str, ImportValue]]:
    """Convert a command line parameter into a CloudFormation import, if necessary."""
    if not ref:
        return None
    if ref.startswith(CFN_IMPORT_PREFIX):
        export_name = ref[len(CFN_IMPORT_PREFIX) :]
        return ImportValue(export_name)
    return ref


def _get_cfn_resource_from_options(
    option_name: str, arn: Optional[str], export_name: Optional[str]
) -> Union[str, ImportValue]:
    """Get a CloudFormation resource from one of several ways to specify it.

    Parameters:
        arn: The physical name or ARN of the underlying resources
        export_name: The name of a CloudFormation Export that can be
            dereferenced to access the resource.
        option_name: The name of the option, used in CLI error messages.
    """
    if arn and export_name:
        raise click.UsageError(
            f"The {option_name} may not be specified using both a name/ARN and a CloudFormation Export."
        )

    if export_name:
        result = ImportValue(export_name)
    else:
        result = arn

    if not result:
        raise click.UsageError(
            f"The {option_name} must be specified using either a name/ARN, or a CloudFormation Export."
        )
    return result


def _initialise_stack(description: str) -> Stack:
    """Create a basic Flying Circus stack, customised for ssmash"""
    stack = Stack(Description=description)

    from ssmash import __version__

    stack.Metadata["ssmash"] = {
        "generated_timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "version": __version__,
    }
    return stack


def _load_appconfig_from_yaml(input) -> dict:
    """Load a YAML description of the application configuration"""
    appconfig = yaml.safe_load(input)

    # Note that PyYAML returns None for an empty file, rather than an empty
    # dictionary
    if appconfig is None:
        appconfig = {}

    return appconfig


def _write_cfn_template(output, appconfig: dict, stack: Stack):
    """Write the CloudFormation template"""
    output.write(stack.export("yaml"))


if __name__ == "__main__":
    sys.exit(run_ssmash())
