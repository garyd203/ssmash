"""Tools for loading the YAML configuration file."""

import yaml

from ssmash.loader import EcsServiceInvalidator
from ssmash.config import InvalidatingConfigKey


class SsmashYamlLoader(yaml.SafeLoader):
    """YAML Loader with support for customised YAML tags used by our configuration file."""

    @classmethod
    def register_extra_constructors(cls):
        cls.add_constructor("!ecs-invalidation", EcsServiceInvalidator.from_yaml)
        cls.add_constructor("!item", InvalidatingConfigKey.from_yaml)


SsmashYamlLoader.register_extra_constructors()
