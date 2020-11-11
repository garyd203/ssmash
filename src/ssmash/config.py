"""Tools for managing the configuration data."""

from typing import FrozenSet
from typing import Iterable
from typing import List
from typing import Optional

from flyingcircus.core import Resource


class InvalidatingConfigKey(str):
    """Represents a configuration key that invalidates some applications when it (or it's children) changes."""

    @classmethod
    def construct(
        cls, key: str, invalidates: Optional[List[str]] = None
    ) -> "InvalidatingConfigKey":
        """Constructor for this class.

        We can't extend the __init__ method for the `str` builtin, so use this
        factory function instead.
        """
        # Checks
        if not isinstance(key, str):
            raise TypeError(
                "Configuration keys must be a string: %s (%s)", key, type(key)
            )

        invalidates = invalidates if invalidates is not None else []
        for target in invalidates:
            if not isinstance(target, str):
                raise TypeError(
                    "Invalidation service references must be a string: %s (%s)",
                    target,
                    type(target),
                )

        # Create the object
        result = cls(key)
        result.invalidated_applications = invalidates
        return result

    @property
    def invalidated_applications(self) -> FrozenSet[str]:
        """References to applications that need to be invalidated.

        This is a read-only copy of the internal set.
        """
        if not hasattr(self, "_invalidated_services"):
            # noinspection PyAttributeOutsideInit
            self._invalidated_services = set()
        return frozenset(self._invalidated_services)

    @invalidated_applications.setter
    def invalidated_applications(self, value: Iterable[str]):
        # noinspection PyAttributeOutsideInit
        self._invalidated_services = set(value)

    @property
    def dependent_resources(self) -> FrozenSet[Resource]:
        """Resources that are dependent on this key.

        This is a read-only copy of the internal set.
        """
        if not hasattr(self, "_dependent_resources"):
            # noinspection PyAttributeOutsideInit
            self._dependent_resources = list()
        return frozenset(self._dependent_resources)

    def add_child_resource(self, resource: Resource):
        # Touch the property to ensure the internal list exists, before we use it
        _ = self.dependent_resources
        self._dependent_resources.append(resource)
