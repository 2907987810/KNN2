from datetime import datetime
from decimal import Decimal
from warnings import catch_warnings, filterwarnings

import numpy as np
import pytest

from pandas._config import config as cf

from pandas._libs import missing as libmissing
from pandas._libs.tslibs import iNaT, is_null_datetimelike

from pandas.core.dtypes.common import is_scalar
from pandas.core.dtypes.dtypes import DatetimeTZDtype, IntervalDtype, PeriodDtype
from pandas.core.dtypes.missing import (
    array_equivalent,
    isna,
    isnull,
    na_value_for_dtype,
    notna,
    notnull,
)

import pandas as pd
from pandas import DatetimeIndex, Float64Index, NaT, Series, TimedeltaIndex, date_range
import pandas.util.testing as tm

now = pd.Timestamp.now()
utcnow = pd.Timestamp.now("UTC")


@pytest.mark.parametrize("notna_f", [notna, notnull])
def test_notna_notnull(notna_f):
    assert notna_f(1.0)
    assert not notna_f(None)
    assert not notna_f(np.NaN)

    with cf.option_context("mode.use_inf_as_na", False):
        assert notna_f(np.inf)
        assert notna_f(-np.inf)

        arr = np.array([1.5, np.inf, 3.5, -np.inf])
        result = notna_f(arr)
        assert result.all()

    with cf.option_context("mode.use_inf_as_na", True):
        assert not notna_f(np.inf)
        assert not notna_f(-np.inf)

        arr = np.array([1.5, np.inf, 3.5, -np.inf])
        result = notna_f(arr)
        assert result.sum() == 2

    with cf.option_context("mode.use_inf_as_na", False):
        for s in [
            tm.makeFloatSeries(),
            tm.makeStringSeries(),
            tm.makeObjectSeries(),
            tm.makeTimeSeries(),
            tm.makePeriodSeries(),
        ]:
            assert isinstance(notna_f(s), Series)


class TestIsNA:
    def test_0d_array(self):
        assert isna(np.array(np.nan))
        assert not isna(np.array(0.0))
        assert not isna(np.array(0))
        # test object dtype
        assert isna(np.array(np.nan, dtype=object))
        assert not isna(np.array(0.0, dtype=object))
        assert not isna(np.array(0, dtype=object))

    def test_empty_object(self):

        for shape in [(4, 0), (4,)]:
            arr = np.empty(shape=shape, dtype=object)
            result = isna(arr)
            expected = np.ones(shape=shape, dtype=bool)
            tm.assert_numpy_array_equal(result, expected)

    @pytest.mark.parametrize("isna_f", [isna, isnull])
    def test_isna_isnull(self, isna_f):
        assert not isna_f(1.0)
        assert isna_f(None)
        assert isna_f(np.NaN)
        assert float("nan")
        assert not isna_f(np.inf)
        assert not isna_f(-np.inf)

        # type
        assert not isna_f(type(pd.Series(dtype=object)))
        assert not isna_f(type(pd.Series(dtype=np.float64)))
        assert not isna_f(type(pd.DataFrame()))

        # series
        for s in [
            tm.makeFloatSeries(),
            tm.makeStringSeries(),
            tm.makeObjectSeries(),
            tm.makeTimeSeries(),
            tm.makePeriodSeries(),
        ]:
            assert isinstance(isna_f(s), Series)

        # frame
        for df in [
            tm.makeTimeDataFrame(),
            tm.makePeriodFrame(),
            tm.makeMixedDataFrame(),
        ]:
            result = isna_f(df)
            expected = df.apply(isna_f)
            tm.assert_frame_equal(result, expected)

    def test_isna_lists(self):
        result = isna([[False]])
        exp = np.array([[False]])
        tm.assert_numpy_array_equal(result, exp)

        result = isna([[1], [2]])
        exp = np.array([[False], [False]])
        tm.assert_numpy_array_equal(result, exp)

        # list of strings / unicode
        result = isna(["foo", "bar"])
        exp = np.array([False, False])
        tm.assert_numpy_array_equal(result, exp)

        result = isna(["foo", "bar"])
        exp = np.array([False, False])
        tm.assert_numpy_array_equal(result, exp)

        # GH20675
        result = isna([np.NaN, "world"])
        exp = np.array([True, False])
        tm.assert_numpy_array_equal(result, exp)

    def test_isna_nat(self):
        result = isna([NaT])
        exp = np.array([True])
        tm.assert_numpy_array_equal(result, exp)

        result = isna(np.array([NaT], dtype=object))
        exp = np.array([True])
        tm.assert_numpy_array_equal(result, exp)

    def test_isna_numpy_nat(self):
        arr = np.array(
            [
                NaT,
                np.datetime64("NaT"),
                np.timedelta64("NaT"),
                np.datetime64("NaT", "s"),
            ]
        )
        result = isna(arr)
        expected = np.array([True] * 4)
        tm.assert_numpy_array_equal(result, expected)

    def test_isna_datetime(self):
        assert not isna(datetime.now())
        assert notna(datetime.now())

        idx = date_range("1/1/1990", periods=20)
        exp = np.ones(len(idx), dtype=bool)
        tm.assert_numpy_array_equal(notna(idx), exp)

        idx = np.asarray(idx)
        idx[0] = iNaT
        idx = DatetimeIndex(idx)
        mask = isna(idx)
        assert mask[0]
        exp = np.array([True] + [False] * (len(idx) - 1), dtype=bool)
        tm.assert_numpy_array_equal(mask, exp)

        # GH 9129
        pidx = idx.to_period(freq="M")
        mask = isna(pidx)
        assert mask[0]
        exp = np.array([True] + [False] * (len(idx) - 1), dtype=bool)
        tm.assert_numpy_array_equal(mask, exp)

        mask = isna(pidx[1:])
        exp = np.zeros(len(mask), dtype=bool)
        tm.assert_numpy_array_equal(mask, exp)

    @pytest.mark.parametrize(
        "value, expected",
        [
            (np.complex128(np.nan), True),
            (np.float64(1), False),
            (np.array([1, 1 + 0j, np.nan, 3]), np.array([False, False, True, False])),
            (
                np.array([1, 1 + 0j, np.nan, 3], dtype=object),
                np.array([False, False, True, False]),
            ),
            (
                np.array([1, 1 + 0j, np.nan, 3]).astype(object),
                np.array([False, False, True, False]),
            ),
        ],
    )
    def test_complex(self, value, expected):
        result = isna(value)
        if is_scalar(result):
            assert result is expected
        else:
            tm.assert_numpy_array_equal(result, expected)

    def test_datetime_other_units(self):
        idx = pd.DatetimeIndex(["2011-01-01", "NaT", "2011-01-02"])
        exp = np.array([False, True, False])
        tm.assert_numpy_array_equal(isna(idx), exp)
        tm.assert_numpy_array_equal(notna(idx), ~exp)
        tm.assert_numpy_array_equal(isna(idx.values), exp)
        tm.assert_numpy_array_equal(notna(idx.values), ~exp)

        for dtype in [
            "datetime64[D]",
            "datetime64[h]",
            "datetime64[m]",
            "datetime64[s]",
            "datetime64[ms]",
            "datetime64[us]",
            "datetime64[ns]",
        ]:
            values = idx.values.astype(dtype)

            exp = np.array([False, True, False])
            tm.assert_numpy_array_equal(isna(values), exp)
            tm.assert_numpy_array_equal(notna(values), ~exp)

            exp = pd.Series([False, True, False])
            s = pd.Series(values)
            tm.assert_series_equal(isna(s), exp)
            tm.assert_series_equal(notna(s), ~exp)
            s = pd.Series(values, dtype=object)
            tm.assert_series_equal(isna(s), exp)
            tm.assert_series_equal(notna(s), ~exp)

    def test_timedelta_other_units(self):
        idx = pd.TimedeltaIndex(["1 days", "NaT", "2 days"])
        exp = np.array([False, True, False])
        tm.assert_numpy_array_equal(isna(idx), exp)
        tm.assert_numpy_array_equal(notna(idx), ~exp)
        tm.assert_numpy_array_equal(isna(idx.values), exp)
        tm.assert_numpy_array_equal(notna(idx.values), ~exp)

        for dtype in [
            "timedelta64[D]",
            "timedelta64[h]",
            "timedelta64[m]",
            "timedelta64[s]",
            "timedelta64[ms]",
            "timedelta64[us]",
            "timedelta64[ns]",
        ]:
            values = idx.values.astype(dtype)

            exp = np.array([False, True, False])
            tm.assert_numpy_array_equal(isna(values), exp)
            tm.assert_numpy_array_equal(notna(values), ~exp)

            exp = pd.Series([False, True, False])
            s = pd.Series(values)
            tm.assert_series_equal(isna(s), exp)
            tm.assert_series_equal(notna(s), ~exp)
            s = pd.Series(values, dtype=object)
            tm.assert_series_equal(isna(s), exp)
            tm.assert_series_equal(notna(s), ~exp)

    def test_period(self):
        idx = pd.PeriodIndex(["2011-01", "NaT", "2012-01"], freq="M")
        exp = np.array([False, True, False])
        tm.assert_numpy_array_equal(isna(idx), exp)
        tm.assert_numpy_array_equal(notna(idx), ~exp)

        exp = pd.Series([False, True, False])
        s = pd.Series(idx)
        tm.assert_series_equal(isna(s), exp)
        tm.assert_series_equal(notna(s), ~exp)
        s = pd.Series(idx, dtype=object)
        tm.assert_series_equal(isna(s), exp)
        tm.assert_series_equal(notna(s), ~exp)


def test_array_equivalent():
    assert array_equivalent(np.array([np.nan, np.nan]), np.array([np.nan, np.nan]))
    assert array_equivalent(
        np.array([np.nan, 1, np.nan]), np.array([np.nan, 1, np.nan])
    )
    assert array_equivalent(
        np.array([np.nan, None], dtype="object"),
        np.array([np.nan, None], dtype="object"),
    )
    assert array_equivalent(
        np.array([np.nan, 1 + 1j], dtype="complex"),
        np.array([np.nan, 1 + 1j], dtype="complex"),
    )
    assert not array_equivalent(
        np.array([np.nan, 1 + 1j], dtype="complex"),
        np.array([np.nan, 1 + 2j], dtype="complex"),
    )
    assert not array_equivalent(
        np.array([np.nan, 1, np.nan]), np.array([np.nan, 2, np.nan])
    )
    assert not array_equivalent(np.array(["a", "b", "c", "d"]), np.array(["e", "e"]))
    assert array_equivalent(Float64Index([0, np.nan]), Float64Index([0, np.nan]))
    assert not array_equivalent(Float64Index([0, np.nan]), Float64Index([1, np.nan]))
    assert array_equivalent(DatetimeIndex([0, np.nan]), DatetimeIndex([0, np.nan]))
    assert not array_equivalent(DatetimeIndex([0, np.nan]), DatetimeIndex([1, np.nan]))
    assert array_equivalent(TimedeltaIndex([0, np.nan]), TimedeltaIndex([0, np.nan]))
    assert not array_equivalent(
        TimedeltaIndex([0, np.nan]), TimedeltaIndex([1, np.nan])
    )
    assert array_equivalent(
        DatetimeIndex([0, np.nan], tz="US/Eastern"),
        DatetimeIndex([0, np.nan], tz="US/Eastern"),
    )
    assert not array_equivalent(
        DatetimeIndex([0, np.nan], tz="US/Eastern"),
        DatetimeIndex([1, np.nan], tz="US/Eastern"),
    )
    assert not array_equivalent(
        DatetimeIndex([0, np.nan]), DatetimeIndex([0, np.nan], tz="US/Eastern")
    )
    assert not array_equivalent(
        DatetimeIndex([0, np.nan], tz="CET"),
        DatetimeIndex([0, np.nan], tz="US/Eastern"),
    )

    assert not array_equivalent(DatetimeIndex([0, np.nan]), TimedeltaIndex([0, np.nan]))


@pytest.mark.parametrize(
    "lvalue, rvalue",
    [
        # There are 3 variants for each of lvalue and rvalue. We include all
        #  three for the tz-naive `now` and exclude the datetim64 variant
        #  for utcnow because it drops tzinfo.
        (now, utcnow),
        (now.to_datetime64(), utcnow),
        (now.to_pydatetime(), utcnow),
        (now, utcnow),
        (now.to_datetime64(), utcnow.to_pydatetime()),
        (now.to_pydatetime(), utcnow.to_pydatetime()),
    ],
)
def test_array_equivalent_tzawareness(lvalue, rvalue):
    # we shouldn't raise if comparing tzaware and tznaive datetimes
    left = np.array([lvalue], dtype=object)
    right = np.array([rvalue], dtype=object)

    assert not array_equivalent(left, right, strict_nan=True)
    assert not array_equivalent(left, right, strict_nan=False)


def test_array_equivalent_compat():
    # see gh-13388
    m = np.array([(1, 2), (3, 4)], dtype=[("a", int), ("b", float)])
    n = np.array([(1, 2), (3, 4)], dtype=[("a", int), ("b", float)])
    assert array_equivalent(m, n, strict_nan=True)
    assert array_equivalent(m, n, strict_nan=False)

    m = np.array([(1, 2), (3, 4)], dtype=[("a", int), ("b", float)])
    n = np.array([(1, 2), (4, 3)], dtype=[("a", int), ("b", float)])
    assert not array_equivalent(m, n, strict_nan=True)
    assert not array_equivalent(m, n, strict_nan=False)

    m = np.array([(1, 2), (3, 4)], dtype=[("a", int), ("b", float)])
    n = np.array([(1, 2), (3, 4)], dtype=[("b", int), ("a", float)])
    assert not array_equivalent(m, n, strict_nan=True)
    assert not array_equivalent(m, n, strict_nan=False)


def test_array_equivalent_str():
    for dtype in ["O", "S", "U"]:
        assert array_equivalent(
            np.array(["A", "B"], dtype=dtype), np.array(["A", "B"], dtype=dtype)
        )
        assert not array_equivalent(
            np.array(["A", "B"], dtype=dtype), np.array(["A", "X"], dtype=dtype)
        )


def test_array_equivalent_nested():
    # reached in groupby aggregations, make sure we use np.any when checking
    #  if the comparison is truthy
    left = np.array([np.array([50, 70, 90]), np.array([20, 30, 40])], dtype=object)
    right = np.array([np.array([50, 70, 90]), np.array([20, 30, 40])], dtype=object)

    assert array_equivalent(left, right, strict_nan=True)
    assert not array_equivalent(left, right[::-1], strict_nan=True)

    left = np.array([np.array([50, 50, 50]), np.array([40, 40, 40])], dtype=object)
    right = np.array([50, 40])
    assert not array_equivalent(left, right, strict_nan=True)


@pytest.mark.parametrize(
    "dtype, na_value",
    [
        # Datetime-like
        (np.dtype("M8[ns]"), NaT),
        (np.dtype("m8[ns]"), NaT),
        (DatetimeTZDtype.construct_from_string("datetime64[ns, US/Eastern]"), NaT),
        (PeriodDtype("M"), NaT),
        # Integer
        ("u1", 0),
        ("u2", 0),
        ("u4", 0),
        ("u8", 0),
        ("i1", 0),
        ("i2", 0),
        ("i4", 0),
        ("i8", 0),
        # Bool
        ("bool", False),
        # Float
        ("f2", np.nan),
        ("f4", np.nan),
        ("f8", np.nan),
        # Object
        ("O", np.nan),
        # Interval
        (IntervalDtype(), np.nan),
    ],
)
def test_na_value_for_dtype(dtype, na_value):
    result = na_value_for_dtype(dtype)
    assert result is na_value


class TestNAObj:

    _1d_methods = ["isnaobj", "isnaobj_old"]
    _2d_methods = ["isnaobj2d", "isnaobj2d_old"]

    def _check_behavior(self, arr, expected):
        for method in TestNAObj._1d_methods:
            result = getattr(libmissing, method)(arr)
            tm.assert_numpy_array_equal(result, expected)

        arr = np.atleast_2d(arr)
        expected = np.atleast_2d(expected)

        for method in TestNAObj._2d_methods:
            result = getattr(libmissing, method)(arr)
            tm.assert_numpy_array_equal(result, expected)

    def test_basic(self):
        arr = np.array([1, None, "foo", -5.1, pd.NaT, np.nan])
        expected = np.array([False, True, False, False, True, True])

        self._check_behavior(arr, expected)

    def test_non_obj_dtype(self):
        arr = np.array([1, 3, np.nan, 5], dtype=float)
        expected = np.array([False, False, True, False])

        self._check_behavior(arr, expected)

    def test_empty_arr(self):
        arr = np.array([])
        expected = np.array([], dtype=bool)

        self._check_behavior(arr, expected)

    def test_empty_str_inp(self):
        arr = np.array([""])  # empty but not na
        expected = np.array([False])

        self._check_behavior(arr, expected)

    def test_empty_like(self):
        # see gh-13717: no segfaults!
        arr = np.empty_like([None])
        expected = np.array([True])

        self._check_behavior(arr, expected)


m8_units = ["as", "ps", "ns", "us", "ms", "s", "m", "h", "D", "W", "M", "Y"]

na_vals = (
    [
        None,
        NaT,
        float("NaN"),
        complex("NaN"),
        np.nan,
        np.float64("NaN"),
        np.float32("NaN"),
        np.complex64(np.nan),
        np.complex128(np.nan),
        np.datetime64("NaT"),
        np.timedelta64("NaT"),
    ]
    + [np.datetime64("NaT", unit) for unit in m8_units]
    + [np.timedelta64("NaT", unit) for unit in m8_units]
)

inf_vals = [
    float("inf"),
    float("-inf"),
    complex("inf"),
    complex("-inf"),
    np.inf,
    np.NINF,
]

int_na_vals = [
    # Values that match iNaT, which we treat as null in specific cases
    np.int64(NaT.value),
    int(NaT.value),
]

sometimes_na_vals = [Decimal("NaN")]

never_na_vals = [
    # float/complex values that when viewed as int64 match iNaT
    -0.0,
    np.float64("-0.0"),
    -0j,
    np.complex64(-0j),
]


class TestLibMissing:
    def test_checknull(self):
        for value in na_vals:
            assert libmissing.checknull(value)

        for value in inf_vals:
            assert not libmissing.checknull(value)

        for value in int_na_vals:
            assert not libmissing.checknull(value)

        for value in sometimes_na_vals:
            assert not libmissing.checknull(value)

        for value in never_na_vals:
            assert not libmissing.checknull(value)

    def checknull_old(self):
        for value in na_vals:
            assert libmissing.checknull_old(value)

        for value in inf_vals:
            assert libmissing.checknull_old(value)

        for value in int_na_vals:
            assert not libmissing.checknull_old(value)

        for value in sometimes_na_vals:
            assert not libmissing.checknull_old(value)

        for value in never_na_vals:
            assert not libmissing.checknull_old(value)

    def test_is_null_datetimelike(self):
        for value in na_vals:
            assert is_null_datetimelike(value)
            assert is_null_datetimelike(value, False)

        for value in inf_vals:
            assert not is_null_datetimelike(value)
            assert not is_null_datetimelike(value, False)

        for value in int_na_vals:
            assert is_null_datetimelike(value)
            assert not is_null_datetimelike(value, False)

        for value in sometimes_na_vals:
            assert not is_null_datetimelike(value)
            assert not is_null_datetimelike(value, False)

        for value in never_na_vals:
            assert not is_null_datetimelike(value)
