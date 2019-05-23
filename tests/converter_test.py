import hypothesis.strategies as st
from flyingcircus.core import Stack
from hypothesis import given

from ssmash.converter import convert_hierarchy_to_ssm
from .strategies import aws_logical_name_strategy


class TestConvertHierarchyToSsm:
    """Tests for convert_hierarchy_to_ssm."""

    # TODO tests
    #   single top-level int/decimal
    #   nested hierarchy with values at several levels
    #   output is sorted at each level
    #   clean key names
    #   handle logical name overrides

    @given(aws_logical_name_strategy(), st.text(min_size=1))
    def test_should_create_parameter_resource_for_single_top_level_item(
        self, key, value
    ):
        stack = Stack()

        # Exercise
        convert_hierarchy_to_ssm({key: value}, stack)

        # Verify
        param = stack.Resources[key]
        assert param.RESOURCE_TYPE == "AWS::SSM::Parameter"
        assert param.Properties.Name == key
        assert param.Properties.Type == "String"
        assert param.Properties.Value == value
