"""Customised hypothesis stategies for generating test data."""

import hypothesis.strategies as st


@st.composite
def aws_logical_name_strategy(draw):
    """A strategy that produces a valid logical name for an AWS Stack object."""
    return draw(
        st.builds(
            lambda a, b: a + b,
            st.text("ABCDEFGHIJKLMNOPQRSTUVWXYZ", min_size=1, max_size=1),
            st.text("abcdefghijklmnnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"),
        )
    )
