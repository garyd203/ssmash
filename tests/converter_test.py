from datetime import datetime

import hypothesis.strategies as st
import pytest
from flyingcircus.core import Stack
from hypothesis import given

from ssmash.converter import convert_hierarchy_to_ssm
from .strategies import aws_logical_name_strategy


class TestConvertHierarchyToSsm:
    """Tests for convert_hierarchy_to_ssm."""

    # TODO tests
    #   nested hierarchy with values at several levels
    #   output is sorted at each level
    #   clean key names
    #   handle logical name overrides
    #   cant have null valure

    @given(aws_logical_name_strategy(), st.text(min_size=1))
    def test_should_create_parameter_resource_for_single_top_level_item(
        self, key, value
    ):
        stack = Stack()

        # Exercise
        convert_hierarchy_to_ssm({key: value}, stack)

        # Verify
        logical_name, param = stack.Resources.popitem()

        assert logical_name.startswith("SSM")
        assert logical_name[3:] == key

        assert param.RESOURCE_TYPE == "AWS::SSM::Parameter"
        assert param.Properties.Name == "/" + key
        assert param.Properties.Type == "String"
        assert param.Properties.Value == value

    @pytest.mark.parametrize(
        ("value", "expected"), [(0, "0"), (True, "true"), (False, "false")]
    )
    def test_should_store_any_primitive_as_a_string(self, value, expected):
        stack = Stack()

        # Exercise
        convert_hierarchy_to_ssm({"key": value}, stack)

        # Verify
        _, param = stack.Resources.popitem()
        assert param.Properties.Type == "String"
        assert param.Properties.Value == expected
