"""Tools for loading the configuration data."""

from typing import List
from typing import Optional
from typing import Union

from flyingcircus.core import Stack
from flyingcircus.intrinsic_function import ImportValue
from flyingcircus.service.ssm import SSMParameter

from ssmash.invalidation import create_ecs_service_invalidation_stack


class EcsServiceInvalidator:
    """Invalidates an ECS Service"""

    def __init__(
        self,
        cluster_name: Optional[str] = None,
        cluster_import: Optional[str] = None,
        service_name: Optional[str] = None,
        service_import: Optional[str] = None,
        role_name: Optional[str] = None,
        role_import: Optional[str] = None,
    ):
        self.cluster = get_cfn_resource_from_options(
            "cluster", cluster_name, cluster_import
        )
        self.service = get_cfn_resource_from_options(
            "service", service_name, service_import
        )
        self.role = get_cfn_resource_from_options("role", role_name, role_import)

    def create_resources(self, dependencies: List[SSMParameter]) -> Stack:
        """Create CloudFormation resources to invalidate this ECS service,
        contingent on any change in the specified dependencies.
        """
        return create_ecs_service_invalidation_stack(
            cluster=self.cluster,
            service=self.service,
            dependencies=dependencies,
            restart_role=self.role,
        )


def get_cfn_resource_from_options(
    option_name: str, arn: Optional[str], export_name: Optional[str]
) -> Union[str, ImportValue]:
    """Get a CloudFormation resource from one of several ways to specify it.

    Parameters:
        arn: The physical name or ARN of the underlying resources
        export_name: The name of a CloudFormation Export that can be
            dereferenced to access the resource.
        option_name: The name of the option, used in CLI error messages.

    Raises:
        ValueError: If the supplied data is inconsistent.
    """
    if arn and export_name:
        raise ValueError(
            f"The {option_name} may not be specified using both a name/ARN and a CloudFormation Export."
        )

    if export_name:
        result = ImportValue(export_name)
    else:
        result = arn

    if not result:
        raise ValueError(
            f"The {option_name} must be specified using either a name/ARN, or a CloudFormation Export."
        )
    return result
