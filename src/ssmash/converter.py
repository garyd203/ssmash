"""Tools for converting configuration into SSM Parameters."""
from typing import Any

from flyingcircus.core import Stack
from flyingcircus.service.ssm import SSMParameter
from flyingcircus.service.ssm import SSMParameterProperties


def convert_hierarchy_to_ssm(appconfig: dict, stack: Stack) -> None:
    """Convert a hierarchical nested dictionary into SSM Parameters."""
    _create_params_from_dict(appconfig, stack)


def _create_params_from_dict(
    appconfig: dict, stack: Stack, path_prefix: str = "/"
) -> None:
    for key, value in appconfig.items():
        item_path = path_prefix + key
        logical_name = "SSM" + key
        stack.Resources[logical_name] = SSMParameter(
            Properties=SSMParameterProperties(
                Name=item_path, Type="String", Value=_get_parameter_value(value)
            )
        )


def _get_parameter_value(value: Any) -> str:
    """All single-value parameters should be stored as a string.

    We normalise the outputs for some situations.
    """
    if isinstance(value, bool):
        return str(value).lower()
    return str(value)
