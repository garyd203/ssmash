"""Tools for loading the YAML configuration file."""

import yaml

from ssmash.config import InvalidatingConfigKey
from ssmash.loader import EcsServiceInvalidator


def _config_item_constructor(loader, node) -> InvalidatingConfigKey:
    """Construct a InvalidatingConfigKey from a custom YAML node"""
    data = loader.construct_mapping(node, deep=True)

    unknown_parameters = set(data.keys()).difference({"key", "invalidates"})
    if unknown_parameters:
        raise ValueError(
            "Unsupported parameters in YAML tag: {}".format(sorted(unknown_parameters))
        )

    return InvalidatingConfigKey.construct(**data)


def _ecs_service_constructor(loader, node) -> EcsServiceInvalidator:
    """Construct a EcsServiceInvalidator from a custom YAML node"""
    data = loader.construct_mapping(node, deep=True)

    unknown_parameters = set(data.keys()).difference(
        {
            "cluster_name",
            "cluster_import",
            "service_name",
            "service_import",
            "role_name",
            "role_import",
        }
    )
    if unknown_parameters:
        raise ValueError(
            "Unsupported parameters in YAML tag: {}".format(sorted(unknown_parameters))
        )

    return EcsServiceInvalidator(**data)


class SsmashYamlLoader(yaml.SafeLoader):
    """YAML Loader with support for customised YAML tags used by our configuration file."""

    @classmethod
    def register_extra_constructors(cls):
        cls.add_constructor("!ecs-invalidation", _ecs_service_constructor)
        cls.add_constructor("!item", _config_item_constructor)


SsmashYamlLoader.register_extra_constructors()
