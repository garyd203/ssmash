"""Tools for loading the configuration data."""

from typing import Optional
from typing import Union

from flyingcircus.intrinsic_function import ImportValue


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
