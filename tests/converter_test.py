import re

import hypothesis.strategies as st
import pytest
from flyingcircus.core import Stack
from flyingcircus.service.ssm import SSMParameter
from hypothesis import given

from ssmash.converter import convert_hierarchy_to_ssm
from .strategies import aws_logical_name_strategy
from .strategies import parameter_name_strategy

LOGICAL_NAME_RE = re.compile(r"[a-z0-9]+", re.I)
PARAMETER_NAME_RE = re.compile(r"[a-z0-9_./-]+", re.I)


class TestConvertHierarchyToSsm:
    """Tests for convert_hierarchy_to_ssm."""

    def _verify_stack_has_parameter(
        self, stack: Stack, path: str, value: str, logical_name: str = None
    ):
        # If we know the logical name, then just get the resource directly
        if logical_name:
            assert logical_name in stack.Resources
            assert stack.Resources[logical_name].Properties.Name == path
            assert stack.Resources[logical_name].Properties.Value == value
            return

        # Otherwise search for the Parameter by path
        params = {
            param.Properties.Name: param.Properties.Value
            for param in stack.Resources.values()
            if isinstance(param, SSMParameter)
        }

        assert path in params
        assert params[path] == value

    @given(aws_logical_name_strategy(), st.text(min_size=1))
    def test_should_create_parameter_resource_for_single_top_level_item(
        self, key, value
    ):
        # Exercise
        stack = convert_hierarchy_to_ssm({key: value})

        # Verify
        logical_name, param = stack.Resources.popitem()

        assert logical_name.lower() == key.lower()

        assert param.RESOURCE_TYPE == "AWS::SSM::Parameter"
        assert param.Properties.Name == "/" + key
        assert param.Properties.Type == "String"
        assert param.Properties.Value == value

    @pytest.mark.parametrize(
        ("value", "expected"), [(0, "0"), (True, "true"), (False, "false")]
    )
    def test_should_store_any_primitive_as_a_string(self, value, expected):
        # Exercise
        stack = convert_hierarchy_to_ssm({"some_key": value})

        # Verify
        _, param = stack.Resources.popitem()
        assert param.Properties.Type == "String"
        assert param.Properties.Value == expected

    def test_should_throw_error_for_none_value(self):
        # Exercise
        with pytest.raises(ValueError, match="(null|None)"):
            convert_hierarchy_to_ssm({"some_key": None})

    @pytest.mark.parametrize("name", ["some?value", "some/value"])
    def test_should_throw_error_for_invalid_parameter_name(self, name):
        # Exercise
        with pytest.raises(
            ValueError, match="invalid.*{}".format(name.replace("?", r"\?"))
        ):
            convert_hierarchy_to_ssm({name: "aaa"})

    @given(parameter_name_strategy())
    def test_should_clean_logical_names(self, key):
        # Exercise
        stack = convert_hierarchy_to_ssm({key: "some_value"})

        # Verify
        logical_name, param = stack.Resources.popitem()

        assert LOGICAL_NAME_RE.fullmatch(
            logical_name
        ), f"A logical name must be alphanumeric: '{logical_name}'"

        assert PARAMETER_NAME_RE.fullmatch(
            param.Properties.Name
        ), f"A parameter name must contain only valid characters: '{param.Properties.Name}'"
        assert (
            "/" not in param.Properties.Name[1:]
        ), "individual path components may not have a slash"

    def test_should_create_parameter_paths_from_nested_dictionaries(self):
        # Setup
        appconfig = {
            "top_value": "aaa",
            "top_dict": {"middle_value": "bbb", "middle_dict": {"bottom_value": "ccc"}},
        }

        # Exercise
        stack = convert_hierarchy_to_ssm(appconfig)

        # Verify
        assert (
            len(stack.Resources) == 3
        ), "3 parameter values should be stored from this input"

        self._verify_stack_has_parameter(stack, "/top_value", "aaa")
        self._verify_stack_has_parameter(stack, "/top_dict/middle_value", "bbb")
        self._verify_stack_has_parameter(
            stack, "/top_dict/middle_dict/bottom_value", "ccc"
        )

    def test_should_deterministically_handle_name_clashes_from_cleaned_logical_names(
        self
    ):
        # Setup
        appconfig = {
            "some": {"value": "eee"},
            "some-Value": "ccc",
            "some.Value": "ddd",
            "some_value": "aaa",
            "some_value_dupe": "fff",
            "someValue": "bbb",
        }

        # Exercise
        stack = convert_hierarchy_to_ssm(appconfig)

        # Verify
        assert (
            len(stack.Resources) == 6
        ), "6 parameter values should be stored from this input"

        self._verify_stack_has_parameter(stack, "/some/value", "eee", "SomeValue")
        self._verify_stack_has_parameter(stack, "/some-Value", "ccc", "SomeValueDupe")
        self._verify_stack_has_parameter(
            stack, "/some.Value", "ddd", "SomeValueDupeDupe"
        )
        self._verify_stack_has_parameter(
            stack, "/some_value", "aaa", "SomeValueDupeDupeDupe"
        )
        self._verify_stack_has_parameter(
            stack, "/some_value_dupe", "fff", "SomeValueDupeDupeDupeDupe"
        )
        self._verify_stack_has_parameter(
            stack, "/someValue", "bbb", "SomeValueDupeDupeDupeDupeDupe"
        )
