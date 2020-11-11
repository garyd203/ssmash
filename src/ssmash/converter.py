"""Tools for converting configuration into SSM Parameters."""

import re
from typing import Any
from typing import List

import inflection
from flyingcircus.core import Stack
from flyingcircus.service.ssm import SSMParameter
from flyingcircus.service.ssm import SSMParameterProperties

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


def convert_hierarchy_to_ssm(appconfig: dict) -> Stack:
    """Convert a hierarchical nested dictionary into SSM Parameters."""
    stack = Stack(Description="SSM Parameters")
    create_params_from_dict(stack, appconfig)
    return stack


def create_params_from_dict(
    stack: Stack, appconfig: dict, path_components: List[str] = None
) -> None:
    if path_components is None:
        path_components = []

    for key, value in appconfig.items():
        _check_path_component_is_valid(key)
        item_path_components = path_components + [key]
        item_path = "/" + "/".join(item_path_components)

        # Nested dictionaries form a parameter hierarchy
        if isinstance(value, dict):
            create_params_from_dict(stack, value, item_path_components)
            continue

        # Store this value as a parameter
        logical_name = _clean_logical_name(item_path)
        logical_name = _dedupe_logical_name(stack, logical_name)

        if isinstance(value, list):
            # Store lists of plain values as a StringList
            stack.Resources[logical_name] = SSMParameter(
                Properties=SSMParameterProperties(
                    Name=item_path,
                    Type="StringList",
                    Value=_get_list_parameter_value(value),
                )
            )
        else:
            # Plain values should be stored as a string parameter
            stack.Resources[logical_name] = SSMParameter(
                Properties=SSMParameterProperties(
                    Name=item_path,
                    Type="String",
                    Value=_get_plain_parameter_value(value),
                )
            )


def _check_path_component_is_valid(component: str):
    """Check that this configuration key is valid to use as a component of a SSM Parameter Path.

    We don't want to alter provided configuration names, so we raise an error
    if they can't be used as-is.
    """
    if INVALID_SSM_PARAMETER_COMPONENT_RE.search(component):
        raise ValueError(f"Configuration has invalid key: {component}")


def _clean_logical_name(name: str) -> str:
    """Remove unsupported characters from a Cloud Formation logical name,
    and make it human-readable.
    """
    # We break the name into valid underscore-separated components, and then camelize it

    # Separate existing camelized words with underscore
    result = inflection.underscore(name)

    # Replace invalid characters with no more than 1 underscore
    result = INVALID_LOGICAL_NAME_RE.sub("_", result).strip("_")
    if not result:
        # There are no valid characters in the name, so we substitute in
        # some placeholder text that is valid
        result = "SymbolsOnly"

    # Turn into a CamelCase version using the underscores as word separators
    result = inflection.camelize(result)

    return result


def _dedupe_logical_name(stack: Stack, logical_name: str) -> str:
    """Create a unique logical name."""
    # We simply add a suffix to the existing name, if there is a conflict
    result = logical_name
    while result in stack.Resources:
        result += "Dupe"
    return result


def _get_list_parameter_value(value: list) -> str:
    """Lists of parameters should be stored as a comma-separated string."""
    if not value:
        raise ValueError("Cannot store an empty list in SSM Parameter Store")

    result = []
    for v in value:
        if isinstance(v, (set, list, dict)):
            raise ValueError(
                "Cannot store complex values inside a list in SSM Parameter Store"
            )

        cleaned = _get_plain_parameter_value(v)

        if not cleaned:
            raise ValueError(
                "Cannot store empty values inside a list in SSM Parameter Store"
            )
        if "," in cleaned:
            raise ValueError(
                "Cannot store values with a comma inside a list in SSM Parameter Store"
            )

        result.append(cleaned)

    return ",".join(result)


def _get_plain_parameter_value(value: Any) -> str:
    """All single-value parameters should be stored as a string.

    We normalise the outputs for some situations.
    """
    if isinstance(value, bool):
        return str(value).lower()
    if value is None:
        raise ValueError("Cannot store null values in SSM Parameter Store")
    return str(value)
