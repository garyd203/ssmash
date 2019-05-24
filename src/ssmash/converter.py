"""Tools for converting configuration into SSM Parameters."""
import logging
import re
from typing import Any

import inflection
from flyingcircus.core import Stack
from flyingcircus.service.ssm import SSMParameter
from flyingcircus.service.ssm import SSMParameterProperties

LOGGER = logging.getLogger(__file__)

#: RegEx to match `invalid characters
#: <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/resources-section-structure.html#resources-section-structure-logicalid>`_
#: in a CloudFormation logical name
INVALID_LOGICAL_NAME_RE = re.compile(r"[^a-zA-Z0-9]+")

#: RegEx to match `invalid characters
#: <https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-parameter-name-constraints.html>`_
#: in one component of the path (aka name) for a SSM parameter.
#:
#: Note that a full path may contain a slash, but a single component may not.
INVALID_SSM_PARAMETER_COMPONENT_RE = re.compile(r"[^a-zA-Z0-9_.-]")


def convert_hierarchy_to_ssm(appconfig: dict, stack: Stack) -> None:
    """Convert a hierarchical nested dictionary into SSM Parameters."""
    create_params_from_dict(stack, appconfig)


def create_params_from_dict(
    stack: Stack, appconfig: dict, path_prefix: str = "/"
) -> None:
    for key, value in appconfig.items():
        key = _clean_path_component(key)
        item_path = path_prefix + key

        # Nested dictionaries form a parameter hierarchy
        if isinstance(value, dict):
            create_params_from_dict(stack, value, item_path + "/")
            continue

        # Plain values should be stored as a string parameter
        logical_name = "SSM" + _clean_logical_name(item_path)
        stack.Resources[logical_name] = SSMParameter(
            Properties=SSMParameterProperties(
                Name=item_path, Type="String", Value=_get_parameter_value(value)
            )
        )


def _clean_path_component(component: str) -> str:
    """Remove unsupported characters from a component of SSM parameter path."""
    result = INVALID_SSM_PARAMETER_COMPONENT_RE.sub("_", component)
    if not result.strip("_.-"):
        # Parameter name contains no sensible characters. Substitute in a placeholder name
        result = "_symbols_only_"
        LOGGER.warning("Parameter name contains no valid characters: '%s'", component)
    return result


def _clean_logical_name(name: str) -> str:
    """Remove unsupported characters from a Cloud Formation logical name,
    and make it human-readable.
    """
    # We break the name into valid underscore-separated components, and then camelize it

    # Separate existing camelized words with underscore
    result = inflection.underscore(name)

    # Replace invalid characters with underscore
    result = INVALID_LOGICAL_NAME_RE.sub("_", result).strip("_")

    # Turn into a CamelCase version using the underscores as word separators
    result = inflection.camelize(result)

    return result


def _get_parameter_value(value: Any) -> str:
    """All single-value parameters should be stored as a string.

    We normalise the outputs for some situations.
    """
    if isinstance(value, bool):
        return str(value).lower()
    if value is None:
        raise ValueError("Cannot store null values in SSM Parameter Store")
    return str(value)
