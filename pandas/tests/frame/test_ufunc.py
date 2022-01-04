from functools import partial

import numpy as np
import pytest

from pandas.compat.numpy import np_version_is1p22
import pandas.util._test_decorators as td

import pandas as pd
import pandas._testing as tm
from pandas.api.types import is_extension_array_dtype

dtypes = [
    "int64",
    "Int64",
    {"A": "int64", "B": "Int64"},
]


@pytest.mark.parametrize("dtype", dtypes)
def test_unary_unary(dtype):
    # unary input, unary output
    values = np.array([[-1, -1], [1, 1]], dtype="int64")
    df = pd.DataFrame(values, columns=["A", "B"], index=["a", "b"]).astype(dtype=dtype)
    result = np.positive(df)
    expected = pd.DataFrame(
        np.positive(values), index=df.index, columns=df.columns
    ).astype(dtype)
    tm.assert_frame_equal(result, expected)


@pytest.mark.parametrize("dtype", dtypes)
def test_unary_binary(request, dtype):
    # unary input, binary output
    if is_extension_array_dtype(dtype) or isinstance(dtype, dict):
        request.node.add_marker(
            pytest.mark.xfail(
                reason="Extension / mixed with multiple outputs not implemented."
            )
        )

    values = np.array([[-1, -1], [1, 1]], dtype="int64")
    df = pd.DataFrame(values, columns=["A", "B"], index=["a", "b"]).astype(dtype=dtype)
    result_pandas = np.modf(df)
    assert isinstance(result_pandas, tuple)
    assert len(result_pandas) == 2
    expected_numpy = np.modf(values)

    for result, b in zip(result_pandas, expected_numpy):
        expected = pd.DataFrame(b, index=df.index, columns=df.columns)
        tm.assert_frame_equal(result, expected)


@pytest.mark.parametrize("dtype", dtypes)
def test_binary_input_dispatch_binop(dtype):
    # binop ufuncs are dispatched to our dunder methods.
    values = np.array([[-1, -1], [1, 1]], dtype="int64")
    df = pd.DataFrame(values, columns=["A", "B"], index=["a", "b"]).astype(dtype=dtype)
    result = np.add(df, df)
    expected = pd.DataFrame(
        np.add(values, values), index=df.index, columns=df.columns
    ).astype(dtype)
    tm.assert_frame_equal(result, expected)


@pytest.mark.parametrize(
    "func,arg,expected",
    [
        (np.add, 1, [2, 3, 4, 5]),
        (
            partial(np.add, where=[[False, True], [True, False]]),
            np.array([[1, 1], [1, 1]]),
            [0, 3, 4, 0],
        ),
        (np.power, np.array([[1, 1], [2, 2]]), [1, 2, 9, 16]),
        (np.subtract, 2, [-1, 0, 1, 2]),
        (
            partial(np.negative, where=np.array([[False, True], [True, False]])),
            None,
            [0, -2, -3, 0],
        ),
    ],
)
def test_ufunc_passes_args(func, arg, expected, request):
    # GH#40662
    arr = np.array([[1, 2], [3, 4]])
    df = pd.DataFrame(arr)
    result_inplace = np.zeros_like(arr)
    # 1-argument ufunc
    if arg is None:
        result = func(df, out=result_inplace)
    else:
        result = func(df, arg, out=result_inplace)

    expected = np.array(expected).reshape(2, 2)
    tm.assert_numpy_array_equal(result_inplace, expected)

    expected = pd.DataFrame(expected)
    tm.assert_frame_equal(result, expected)


@pytest.mark.parametrize("dtype_a", dtypes)
@pytest.mark.parametrize("dtype_b", dtypes)
def test_binary_input_aligns_columns(request, dtype_a, dtype_b):
    if (
        is_extension_array_dtype(dtype_a)
        or isinstance(dtype_a, dict)
        or is_extension_array_dtype(dtype_b)
        or isinstance(dtype_b, dict)
    ):
        request.node.add_marker(
            pytest.mark.xfail(
                reason="Extension / mixed with multiple inputs not implemented."
            )
        )

    df1 = pd.DataFrame({"A": [1, 2], "B": [3, 4]}).astype(dtype_a)

    if isinstance(dtype_a, dict) and isinstance(dtype_b, dict):
        dtype_b["C"] = dtype_b.pop("B")

    df2 = pd.DataFrame({"A": [1, 2], "C": [3, 4]}).astype(dtype_b)
    with tm.assert_produces_warning(FutureWarning):
        result = np.heaviside(df1, df2)
    # Expected future behaviour:
    # expected = np.heaviside(
    #     np.array([[1, 3, np.nan], [2, 4, np.nan]]),
    #     np.array([[1, np.nan, 3], [2, np.nan, 4]]),
    # )
    # expected = pd.DataFrame(expected, index=[0, 1], columns=["A", "B", "C"])
    expected = pd.DataFrame([[1.0, 1.0], [1.0, 1.0]], columns=["A", "B"])
    tm.assert_frame_equal(result, expected)

    # ensure the expected is the same when applying with numpy array
    result = np.heaviside(df1, df2.values)
    tm.assert_frame_equal(result, expected)


@pytest.mark.parametrize("dtype", dtypes)
def test_binary_input_aligns_index(request, dtype):
    if is_extension_array_dtype(dtype) or isinstance(dtype, dict):
        request.node.add_marker(
            pytest.mark.xfail(
                reason="Extension / mixed with multiple inputs not implemented."
            )
        )
    df1 = pd.DataFrame({"A": [1, 2], "B": [3, 4]}, index=["a", "b"]).astype(dtype)
    df2 = pd.DataFrame({"A": [1, 2], "B": [3, 4]}, index=["a", "c"]).astype(dtype)
    with tm.assert_produces_warning(FutureWarning):
        result = np.heaviside(df1, df2)
    # Expected future behaviour:
    # expected = np.heaviside(
    #     np.array([[1, 3], [3, 4], [np.nan, np.nan]]),
    #     np.array([[1, 3], [np.nan, np.nan], [3, 4]]),
    # )
    # # TODO(FloatArray): this will be Float64Dtype.
    # expected = pd.DataFrame(expected, index=["a", "b", "c"], columns=["A", "B"])
    expected = pd.DataFrame(
        [[1.0, 1.0], [1.0, 1.0]], columns=["A", "B"], index=["a", "b"]
    )
    tm.assert_frame_equal(result, expected)

    # ensure the expected is the same when applying with numpy array
    result = np.heaviside(df1, df2.values)
    tm.assert_frame_equal(result, expected)


@pytest.mark.filterwarnings("ignore:Calling a ufunc on non-aligned:FutureWarning")
def test_binary_frame_series_raises():
    # We don't currently implement
    df = pd.DataFrame({"A": [1, 2]})
    # with pytest.raises(NotImplementedError, match="logaddexp"):
    with pytest.raises(ValueError, match=""):
        np.logaddexp(df, df["A"])

    # with pytest.raises(NotImplementedError, match="logaddexp"):
    with pytest.raises(ValueError, match=""):
        np.logaddexp(df["A"], df)


def test_unary_accumulate_axis():
    # https://github.com/pandas-dev/pandas/issues/39259
    df = pd.DataFrame({"a": [1, 3, 2, 4]})
    result = np.maximum.accumulate(df)
    expected = pd.DataFrame({"a": [1, 3, 3, 4]})
    tm.assert_frame_equal(result, expected)

    df = pd.DataFrame({"a": [1, 3, 2, 4], "b": [0.1, 4.0, 3.0, 2.0]})
    result = np.maximum.accumulate(df)
    # in theory could preserve int dtype for default axis=0
    expected = pd.DataFrame({"a": [1.0, 3.0, 3.0, 4.0], "b": [0.1, 4.0, 4.0, 4.0]})
    tm.assert_frame_equal(result, expected)

    result = np.maximum.accumulate(df, axis=0)
    tm.assert_frame_equal(result, expected)

    result = np.maximum.accumulate(df, axis=1)
    expected = pd.DataFrame({"a": [1.0, 3.0, 2.0, 4.0], "b": [1.0, 4.0, 3.0, 4.0]})
    tm.assert_frame_equal(result, expected)


def test_frame_outer_deprecated():
    df = pd.DataFrame({"A": [1, 2]})
    with tm.assert_produces_warning(FutureWarning):
        np.subtract.outer(df, df)


def test_alignment_deprecation():
    # https://github.com/pandas-dev/pandas/issues/39184
    df1 = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
    df2 = pd.DataFrame({"b": [1, 2, 3], "c": [4, 5, 6]})
    s1 = pd.Series([1, 2], index=["a", "b"])
    s2 = pd.Series([1, 2], index=["b", "c"])

    # binary dataframe / dataframe
    expected = pd.DataFrame({"a": [2, 4, 6], "b": [8, 10, 12]})

    with tm.assert_produces_warning(None):
        # aligned -> no warning!
        result = np.add(df1, df1)
    tm.assert_frame_equal(result, expected)

    with tm.assert_produces_warning(FutureWarning):
        # non-aligned -> warns
        result = np.add(df1, df2)
    tm.assert_frame_equal(result, expected)

    result = np.add(df1, df2.values)
    tm.assert_frame_equal(result, expected)

    result = np.add(df1.values, df2)
    expected = pd.DataFrame({"b": [2, 4, 6], "c": [8, 10, 12]})
    tm.assert_frame_equal(result, expected)

    # binary dataframe / series
    expected = pd.DataFrame({"a": [2, 3, 4], "b": [6, 7, 8]})

    with tm.assert_produces_warning(None):
        # aligned -> no warning!
        result = np.add(df1, s1)
    tm.assert_frame_equal(result, expected)

    with tm.assert_produces_warning(FutureWarning):
        result = np.add(df1, s2)
    tm.assert_frame_equal(result, expected)

    with tm.assert_produces_warning(FutureWarning):
        result = np.add(s2, df1)
    tm.assert_frame_equal(result, expected)

    result = np.add(df1, s2.values)
    tm.assert_frame_equal(result, expected)


@td.skip_if_no("numba")
def test_alignment_deprecation_many_inputs(request):
    # https://github.com/pandas-dev/pandas/issues/39184
    # test that the deprecation also works with > 2 inputs -> using a numba
    # written ufunc for this because numpy itself doesn't have such ufuncs
    from numba import (
        float64,
        vectorize,
    )

    if np_version_is1p22:
        mark = pytest.mark.xfail(
            reason="ufunc 'my_ufunc' did not contain a loop with signature matching "
            "types",
        )
        request.node.add_marker(mark)

    @vectorize([float64(float64, float64, float64)])
    def my_ufunc(x, y, z):
        return x + y + z

    df1 = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
    df2 = pd.DataFrame({"b": [1, 2, 3], "c": [4, 5, 6]})
    df3 = pd.DataFrame({"a": [1, 2, 3], "c": [4, 5, 6]})

    with tm.assert_produces_warning(FutureWarning):
        result = my_ufunc(df1, df2, df3)
    expected = pd.DataFrame([[3.0, 12.0], [6.0, 15.0], [9.0, 18.0]], columns=["a", "b"])
    tm.assert_frame_equal(result, expected)

    # all aligned -> no warning
    with tm.assert_produces_warning(None):
        result = my_ufunc(df1, df1, df1)
    tm.assert_frame_equal(result, expected)

    # mixed frame / arrays
    with tm.assert_produces_warning(FutureWarning):
        result = my_ufunc(df1, df2, df3.values)
    tm.assert_frame_equal(result, expected)

    # single frame -> no warning
    with tm.assert_produces_warning(None):
        result = my_ufunc(df1, df2.values, df3.values)
    tm.assert_frame_equal(result, expected)

    # takes indices of first frame
    with tm.assert_produces_warning(FutureWarning):
        result = my_ufunc(df1.values, df2, df3)
    expected = expected.set_axis(["b", "c"], axis=1)
    tm.assert_frame_equal(result, expected)
