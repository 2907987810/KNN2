from textwrap import dedent

import pytest

from pandas import DataFrame

pytest.importorskip("jinja2")
from pandas.io.formats.style import Styler


@pytest.fixture
def df():
    return DataFrame({"A": [0, 1], "B": [-0.61, -1.22], "C": ["ab", "cd"]})


@pytest.fixture
def styler(df):
    return Styler(df, uuid_len=0, precision=2)


def test_basic_string(styler):
    result = styler.to_string()
    expected = dedent(
        """\
     A B C
    0 0 -0.61 ab
    1 1 -1.22 cd
    """
    )
    assert result == expected


def test_string_delimiter(styler):
    result = styler.to_string(delimiter=";")
    expected = dedent(
        """\
    ;A;B;C
    0;0;-0.61;ab
    1;1;-1.22;cd
    """
    )
    assert result == expected


@pytest.mark.parametrize("delimiter", [" ", ";"])
def test_set_footer(styler, delimiter):
    styler.set_footer(["sum"])
    expected = f"sum{delimiter}1{delimiter}-1.830000{delimiter}abcd"
    result = styler.to_string(delimiter=delimiter)
    assert expected in result
