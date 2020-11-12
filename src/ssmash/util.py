import re

import inflection

#: RegEx to match `invalid characters
#: <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/resources-section-structure.html#resources-section-structure-logicalid>`_
#: in a CloudFormation logical name
INVALID_LOGICAL_NAME_RE = re.compile(r"[^a-zA-Z0-9]+")


def clean_logical_name(name: str) -> str:
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
