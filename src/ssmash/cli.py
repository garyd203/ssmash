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

#: Prefix for specifying a CloudFormation import as a CLI parameter
CFN_IMPORT_PREFIX = "!ImportValue:"


@click.command(help=__doc__)
@click.argument("input", type=click.File("r"), default="-")
@click.argument("output", type=click.File("w"), default="-")
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
    # Load source config
    #
    # Note that PyYAML returns None for an empty file, rather than an empty
    # dictionary
    appconfig = yaml.safe_load(input)
    if appconfig is None:
        appconfig = {}

    # Create stack
    stack = Stack(Description=description)

    from ssmash import __version__

    stack.Metadata["ssmash"] = {
        "generated_timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "version": __version__,
    }

    # Create a parameter for each element in the config hierarchy.
    ssm_stack = convert_hierarchy_to_ssm(appconfig)
    stack.merge_stack(ssm_stack.with_prefixed_names("SSMParam"))

    # Re-deploy the specified ECS service
    if invalidate_ecs_service:
        ecs_cluster, ecs_service = invalidate_ecs_service
        ecs_cluster = dereference_cfn_import_maybe(ecs_cluster)
        ecs_service = dereference_cfn_import_maybe(ecs_service)

        if not invalidation_role:
            raise click.UsageError(
                "An invalidation-role needs to be supplied that will be used to restart the ECS service."
            )

        stack.merge_stack(
            create_ecs_service_invalidation_stack(
                cluster=ecs_cluster,
                service=ecs_service,
                dependencies=[
                    r
                    for r in ssm_stack.Resources.values()
                    if isinstance(r, SSMParameter)
                ],
                restart_role=dereference_cfn_import_maybe(invalidation_role),
            ).with_prefixed_names("InvalidateEcs")
        )

    # Write YAML to the specified file
    output.write(stack.export("yaml"))


def dereference_cfn_import_maybe(
    ref: Optional[str]
) -> Optional[Union[str, ImportValue]]:
    """Convert a command line parameter into a CloudFormation import, if necessary."""
    # TODO move to another module
    # TODO tests
    if not ref:
        return None
    if ref.startswith(CFN_IMPORT_PREFIX):
        export_name = ref[len(CFN_IMPORT_PREFIX) :]
        return ImportValue(export_name)
    return ref


if __name__ == "__main__":
    sys.exit(create_stack())
