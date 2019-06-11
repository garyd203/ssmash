# -*- coding: utf-8 -*-

"""Convert a plain YAML file with application configuration into a CloudFormation template with SSM parameters."""

import sys
from datetime import datetime
from datetime import timezone
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
    sys.exit(create_stack())
