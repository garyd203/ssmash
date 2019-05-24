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


@st.composite
def parameter_name_strategy(draw):
    """A strategy that produces a valid parameter name component."""
    return draw(
        # NB: No "/", but otherwise it's the character set for a SSM Parameter Name
        st.from_regex(r"[a-zA-Z0-9_.-]+", fullmatch=True)
    )
