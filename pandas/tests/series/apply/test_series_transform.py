import numpy as np
import pytest

from pandas import DataFrame, Series, concat
import pandas._testing as tm
from pandas.core.base import SpecificationError
from pandas.core.groupby.base import transformation_kernels


def test_transform(string_series):
    with np.errstate(all="ignore"):
        # transforming functions
        f_sqrt = np.sqrt(string_series)
        f_abs = np.abs(string_series)

        # ufunc
        result = string_series.transform(np.sqrt)
        expected = f_sqrt.copy()
        tm.assert_series_equal(result, expected)

        # list-like
        result = string_series.transform([np.sqrt])
        expected = f_sqrt.to_frame().copy()
        expected.columns = ["sqrt"]
        tm.assert_frame_equal(result, expected)

        result = string_series.transform(["sqrt"])
        tm.assert_frame_equal(result, expected)

        # multiple items in list
        # these are in the order as if we are applying both functions per
        # series and then concatting
        result = string_series.transform(["sqrt", "abs"])
        expected = concat([f_sqrt, f_abs], axis=1)
        expected.columns = ["sqrt", "abs"]
        tm.assert_frame_equal(result, expected)

        # dict, provide renaming
        expected = concat([f_sqrt, f_abs], axis=1)
        expected.columns = ["foo", "bar"]
        result = string_series.transform({"foo": np.sqrt, "bar": np.abs})
        tm.assert_frame_equal(result, expected)


def test_transform_udf(axis, string_series):
    # via apply
    def func(x):
        if isinstance(x, Series):
            raise ValueError
        return x + 1

    result = string_series.transform(func)
    expected = string_series + 1
    tm.assert_series_equal(result, expected)

    # via map Series -> Series
    def func(x):
        if not isinstance(x, Series):
            raise ValueError
        return x + 1

    result = string_series.transform(func)
    expected = string_series + 1
    tm.assert_series_equal(result, expected)


def test_transform_wont_agg(string_series):
    # we are trying to transform with an aggregator
    msg = "Function did not transform"
    with pytest.raises(ValueError, match=msg):
        string_series.transform(["min", "max"])

    msg = "Function did not transform"
    with pytest.raises(ValueError, match=msg):
        with np.errstate(all="ignore"):
            string_series.transform(["sqrt", "max"])


def test_transform_none_to_type():
    # GH34377
    df = DataFrame({"a": [None]})
    msg = "Transform function failed"
    with pytest.raises(ValueError, match=msg):
        df.transform({"a": int})


def test_transform_reducer_raises(all_reductions):
    op = all_reductions
    s = Series([1, 2, 3])
    msg = "Function did not transform"
    with pytest.raises(ValueError, match=msg):
        s.transform(op)
    with pytest.raises(ValueError, match=msg):
        s.transform([op])
    with pytest.raises(ValueError, match=msg):
        s.transform({"A": op})
    with pytest.raises(ValueError, match=msg):
        s.transform({"A": [op]})


# mypy doesn't allow adding lists of different types
# https://github.com/python/mypy/issues/5492
@pytest.mark.parametrize("op", [*transformation_kernels, lambda x: x + 1])
def test_transform_bad_dtype(op):
    s = Series(3 * [object])  # Series that will fail on most transforms
    if op in ("backfill", "shift", "pad", "bfill", "ffill"):
        pytest.xfail("Transform function works on any datatype")
    msg = "Transform function failed"
    with pytest.raises(ValueError, match=msg):
        s.transform(op)
    with pytest.raises(ValueError, match=msg):
        s.transform([op])
    with pytest.raises(ValueError, match=msg):
        s.transform({"A": op})
    with pytest.raises(ValueError, match=msg):
        s.transform({"A": [op]})


@pytest.mark.parametrize("use_apply", [True, False])
def test_transform_passes_args(use_apply):
    # transform uses UDF either via apply or passing the entire Series
    expected_args = [1, 2]
    expected_kwargs = {"c": 3}

    def f(x, a, b, c):
        # transform is using apply iff x is not a Series
        if use_apply == isinstance(x, Series):
            # Force transform to fallback
            raise ValueError
        assert [a, b] == expected_args
        assert c == expected_kwargs["c"]
        return x

    Series([1]).transform(f, 0, *expected_args, **expected_kwargs)


def test_transform_axis_1_raises():
    msg = "No axis named 1 for object type Series"
    with pytest.raises(ValueError, match=msg):
        Series([1]).transform("sum", axis=1)


def test_transform_nested_renamer():
    match = "nested renamer is not supported"
    with pytest.raises(SpecificationError, match=match):
        Series([1]).transform({"A": {"B": ["sum"]}})
