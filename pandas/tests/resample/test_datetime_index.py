from datetime import datetime
from functools import partial
from io import StringIO
from typing import List

import numpy as np
import pytest
import pytz

from pandas._libs import lib
from pandas._typing import DatetimeNaTType

import pandas as pd
from pandas import (
    DataFrame,
    Series,
    Timedelta,
    Timestamp,
    isna,
    notna,
)
import pandas._testing as tm
from pandas.core.groupby.grouper import Grouper
from pandas.core.indexes.datetimes import date_range
from pandas.core.indexes.period import (
    Period,
    period_range,
)
from pandas.core.resample import (
    DatetimeIndex,
    _get_timestamp_range_edges,
)

from pandas.tseries import offsets
from pandas.tseries.offsets import Minute


@pytest.fixture()
def _index_factory():
    return date_range


@pytest.fixture
def _index_freq():
    return "Min"


@pytest.fixture
def _static_values(index):
    return np.random.rand(len(index))


@pytest.fixture(params=["s", "ms", "us", "ns"])
def unit(request):
    return request.param


def test_custom_grouper(index, unit):
    dti = index.as_unit(unit)
    s = Series(np.array([1] * len(dti)), index=dti, dtype="int64")

    b = Grouper(freq=Minute(5))
    g = s.groupby(b)

    # check all cython functions work
    g.ohlc()  # doesn't use _cython_agg_general
    funcs = ["sum", "mean", "prod", "min", "max", "var"]
    for f in funcs:
        g._cython_agg_general(f, alt=None, numeric_only=True)

    b = Grouper(freq=Minute(5), closed="right", label="right")
    g = s.groupby(b)
    # check all cython functions work
    g.ohlc()  # doesn't use _cython_agg_general
    funcs = ["sum", "mean", "prod", "min", "max", "var"]
    for f in funcs:
        g._cython_agg_general(f, alt=None, numeric_only=True)

    assert g.ngroups == 2593
    assert notna(g.mean()).all()

    # construct expected val
    arr = [1] + [5] * 2592
    idx = dti[0:-1:5]
    idx = idx.append(dti[-1:])
    idx = DatetimeIndex(idx, freq="5T").as_unit(unit)
    expect = Series(arr, index=idx)

    # GH2763 - return input dtype if we can
    result = g.agg(np.sum)
    tm.assert_series_equal(result, expect)


def test_custom_grouper_df(index, unit):
    b = Grouper(freq=Minute(5), closed="right", label="right")
    dti = index.as_unit(unit)
    df = DataFrame(np.random.rand(len(dti), 10), index=dti, dtype="float64")
    r = df.groupby(b).agg(np.sum)

    assert len(r.columns) == 10
    assert len(r.index) == 2593


@pytest.mark.parametrize(
    "_index_start,_index_end,_index_name",
    [("1/1/2000 00:00:00", "1/1/2000 00:13:00", "index")],
)
@pytest.mark.parametrize(
    "closed, expected",
    [
        (
            "right",
            lambda s: Series(
                [s[0], s[1:6].mean(), s[6:11].mean(), s[11:].mean()],
                index=date_range("1/1/2000", periods=4, freq="5min", name="index"),
            ),
        ),
        (
            "left",
            lambda s: Series(
                [s[:5].mean(), s[5:10].mean(), s[10:].mean()],
                index=date_range(
                    "1/1/2000 00:05", periods=3, freq="5min", name="index"
                ),
            ),
        ),
    ],
)
def test_resample_basic(series, closed, expected, unit):
    s = series
    s.index = s.index.as_unit(unit)
    expected = expected(s)
    expected.index = expected.index.as_unit(unit)
    result = s.resample("5min", closed=closed, label="right").mean()
    tm.assert_series_equal(result, expected)


def test_resample_integerarray(unit):
    # GH 25580, resample on IntegerArray
    ts = Series(
        range(9),
        index=date_range("1/1/2000", periods=9, freq="T").as_unit(unit),
        dtype="Int64",
    )
    result = ts.resample("3T").sum()
    expected = Series(
        [3, 12, 21],
        index=date_range("1/1/2000", periods=3, freq="3T").as_unit(unit),
        dtype="Int64",
    )
    tm.assert_series_equal(result, expected)

    result = ts.resample("3T").mean()
    expected = Series(
        [1, 4, 7],
        index=date_range("1/1/2000", periods=3, freq="3T").as_unit(unit),
        dtype="Float64",
    )
    tm.assert_series_equal(result, expected)


def test_resample_basic_grouper(series, unit):
    s = series
    s.index = s.index.as_unit(unit)
    result = s.resample("5Min").last()
    grouper = Grouper(freq=Minute(5), closed="left", label="left")
    expected = s.groupby(grouper).agg(lambda x: x[-1])
    tm.assert_series_equal(result, expected)


@pytest.mark.parametrize(
    "_index_start,_index_end,_index_name",
    [("1/1/2000 00:00:00", "1/1/2000 00:13:00", "index")],
)
@pytest.mark.parametrize(
    "keyword,value",
    [("label", "righttt"), ("closed", "righttt"), ("convention", "starttt")],
)
def test_resample_string_kwargs(series, keyword, value, unit):
    # see gh-19303
    # Check that wrong keyword argument strings raise an error
    series.index = series.index.as_unit(unit)
    msg = f"Unsupported value {value} for `{keyword}`"
    with pytest.raises(ValueError, match=msg):
        series.resample("5min", **({keyword: value}))


@pytest.mark.parametrize(
    "_index_start,_index_end,_index_name",
    [("1/1/2000 00:00:00", "1/1/2000 00:13:00", "index")],
)
def test_resample_how(series, downsample_method, unit):
    if downsample_method == "ohlc":
        pytest.skip("covered by test_resample_how_ohlc")

    s = series
    s.index = s.index.as_unit(unit)
    grouplist = np.ones_like(s)
    grouplist[0] = 0
    grouplist[1:6] = 1
    grouplist[6:11] = 2
    grouplist[11:] = 3
    expected = s.groupby(grouplist).agg(downsample_method)
    expected.index = date_range(
        "1/1/2000", periods=4, freq="5min", name="index"
    ).as_unit(unit)

    result = getattr(
        s.resample("5min", closed="right", label="right"), downsample_method
    )()
    tm.assert_series_equal(result, expected)


@pytest.mark.parametrize(
    "_index_start,_index_end,_index_name",
    [("1/1/2000 00:00:00", "1/1/2000 00:13:00", "index")],
)
def test_resample_how_ohlc(series, unit):
    s = series
    s.index = s.index.as_unit(unit)
    grouplist = np.ones_like(s)
    grouplist[0] = 0
    grouplist[1:6] = 1
    grouplist[6:11] = 2
    grouplist[11:] = 3

    def _ohlc(group):
        if isna(group).all():
            return np.repeat(np.nan, 4)
        return [group[0], group.max(), group.min(), group[-1]]

    expected = DataFrame(
        s.groupby(grouplist).agg(_ohlc).values.tolist(),
        index=date_range("1/1/2000", periods=4, freq="5min", name="index").as_unit(
            unit
        ),
        columns=["open", "high", "low", "close"],
    )

    result = s.resample("5min", closed="right", label="right").ohlc()
    tm.assert_frame_equal(result, expected)


def test_resample_how_callables(unit):
    # GH#7929
    data = np.arange(5, dtype=np.int64)
    ind = date_range(start="2014-01-01", periods=len(data), freq="d").as_unit(unit)
    df = DataFrame({"A": data, "B": data}, index=ind)

    def fn(x, a=1):
        return str(type(x))

    class FnClass:
        def __call__(self, x):
            return str(type(x))

    df_standard = df.resample("M").apply(fn)
    df_lambda = df.resample("M").apply(lambda x: str(type(x)))
    df_partial = df.resample("M").apply(partial(fn))
    df_partial2 = df.resample("M").apply(partial(fn, a=2))
    df_class = df.resample("M").apply(FnClass())

    tm.assert_frame_equal(df_standard, df_lambda)
    tm.assert_frame_equal(df_standard, df_partial)
    tm.assert_frame_equal(df_standard, df_partial2)
    tm.assert_frame_equal(df_standard, df_class)


def test_resample_rounding(unit):
    # GH 8371
    # odd results when rounding is needed

    data = """date,time,value
11-08-2014,00:00:01.093,1
11-08-2014,00:00:02.159,1
11-08-2014,00:00:02.667,1
11-08-2014,00:00:03.175,1
11-08-2014,00:00:07.058,1
11-08-2014,00:00:07.362,1
11-08-2014,00:00:08.324,1
11-08-2014,00:00:08.830,1
11-08-2014,00:00:08.982,1
11-08-2014,00:00:09.815,1
11-08-2014,00:00:10.540,1
11-08-2014,00:00:11.061,1
11-08-2014,00:00:11.617,1
11-08-2014,00:00:13.607,1
11-08-2014,00:00:14.535,1
11-08-2014,00:00:15.525,1
11-08-2014,00:00:17.960,1
11-08-2014,00:00:20.674,1
11-08-2014,00:00:21.191,1"""

    df = pd.read_csv(
        StringIO(data),
        parse_dates={"timestamp": ["date", "time"]},
        index_col="timestamp",
    )
    df.index = df.index.as_unit(unit)
    df.index.name = None
    result = df.resample("6s").sum()
    expected = DataFrame(
        {"value": [4, 9, 4, 2]},
        index=date_range("2014-11-08", freq="6s", periods=4).as_unit(unit),
    )
    tm.assert_frame_equal(result, expected)

    result = df.resample("7s").sum()
    expected = DataFrame(
        {"value": [4, 10, 4, 1]},
        index=date_range("2014-11-08", freq="7s", periods=4).as_unit(unit),
    )
    tm.assert_frame_equal(result, expected)

    result = df.resample("11s").sum()
    expected = DataFrame(
        {"value": [11, 8]},
        index=date_range("2014-11-08", freq="11s", periods=2).as_unit(unit),
    )
    tm.assert_frame_equal(result, expected)

    result = df.resample("13s").sum()
    expected = DataFrame(
        {"value": [13, 6]},
        index=date_range("2014-11-08", freq="13s", periods=2).as_unit(unit),
    )
    tm.assert_frame_equal(result, expected)

    result = df.resample("17s").sum()
    expected = DataFrame(
        {"value": [16, 3]},
        index=date_range("2014-11-08", freq="17s", periods=2).as_unit(unit),
    )
    tm.assert_frame_equal(result, expected)


def test_resample_basic_from_daily(unit):
    # from daily
    dti = date_range(
        start=datetime(2005, 1, 1), end=datetime(2005, 1, 10), freq="D", name="index"
    ).as_unit(unit)

    s = Series(np.random.rand(len(dti)), dti)

    # to weekly
    result = s.resample("w-sun").last()

    assert len(result) == 3
    assert (result.index.dayofweek == [6, 6, 6]).all()
    assert result.iloc[0] == s["1/2/2005"]
    assert result.iloc[1] == s["1/9/2005"]
    assert result.iloc[2] == s.iloc[-1]

    result = s.resample("W-MON").last()
    assert len(result) == 2
    assert (result.index.dayofweek == [0, 0]).all()
    assert result.iloc[0] == s["1/3/2005"]
    assert result.iloc[1] == s["1/10/2005"]

    result = s.resample("W-TUE").last()
    assert len(result) == 2
    assert (result.index.dayofweek == [1, 1]).all()
    assert result.iloc[0] == s["1/4/2005"]
    assert result.iloc[1] == s["1/10/2005"]

    result = s.resample("W-WED").last()
    assert len(result) == 2
    assert (result.index.dayofweek == [2, 2]).all()
    assert result.iloc[0] == s["1/5/2005"]
    assert result.iloc[1] == s["1/10/2005"]

    result = s.resample("W-THU").last()
    assert len(result) == 2
    assert (result.index.dayofweek == [3, 3]).all()
    assert result.iloc[0] == s["1/6/2005"]
    assert result.iloc[1] == s["1/10/2005"]

    result = s.resample("W-FRI").last()
    assert len(result) == 2
    assert (result.index.dayofweek == [4, 4]).all()
    assert result.iloc[0] == s["1/7/2005"]
    assert result.iloc[1] == s["1/10/2005"]

    # to biz day
    result = s.resample("B").last()
    assert len(result) == 7
    assert (result.index.dayofweek == [4, 0, 1, 2, 3, 4, 0]).all()

    assert result.iloc[0] == s["1/2/2005"]
    assert result.iloc[1] == s["1/3/2005"]
    assert result.iloc[5] == s["1/9/2005"]
    assert result.index.name == "index"


def test_resample_upsampling_picked_but_not_correct(unit):
    # Test for issue #3020
    dates = date_range("01-Jan-2014", "05-Jan-2014", freq="D").as_unit(unit)
    series = Series(1, index=dates)

    result = series.resample("D").mean()
    assert result.index[0] == dates[0]

    # GH 5955
    # incorrect deciding to upsample when the axis frequency matches the
    # resample frequency

    s = Series(
        np.arange(1.0, 6), index=[datetime(1975, 1, i, 12, 0) for i in range(1, 6)]
    )
    s.index = s.index.as_unit(unit)
    expected = Series(
        np.arange(1.0, 6),
        index=date_range("19750101", periods=5, freq="D").as_unit(unit),
    )

    result = s.resample("D").count()
    tm.assert_series_equal(result, Series(1, index=expected.index))

    result1 = s.resample("D").sum()
    result2 = s.resample("D").mean()
    tm.assert_series_equal(result1, expected)
    tm.assert_series_equal(result2, expected)


@pytest.mark.parametrize("f", ["sum", "mean", "prod", "min", "max", "var"])
def test_resample_frame_basic_cy_funcs(f, unit):
    df = tm.makeTimeDataFrame()
    df.index = df.index.as_unit(unit)

    b = Grouper(freq="M")
    g = df.groupby(b)

    # check all cython functions work
    g._cython_agg_general(f, alt=None, numeric_only=True)


@pytest.mark.parametrize("freq", ["A", "M"])
def test_resample_frame_basic_M_A(freq, unit):
    df = tm.makeTimeDataFrame()
    df.index = df.index.as_unit(unit)
    result = df.resample(freq).mean()
    tm.assert_series_equal(result["A"], df["A"].resample(freq).mean())


@pytest.mark.parametrize("freq", ["W-WED", "M"])
def test_resample_frame_basic_kind(freq, unit):
    df = tm.makeTimeDataFrame()
    df.index = df.index.as_unit(unit)
    df.resample(freq, kind="period").mean()


def test_resample_upsample(unit):
    # from daily
    dti = date_range(
        start=datetime(2005, 1, 1), end=datetime(2005, 1, 10), freq="D", name="index"
    ).as_unit(unit)

    s = Series(np.random.rand(len(dti)), dti)

    # to minutely, by padding
    result = s.resample("Min").ffill()
    assert len(result) == 12961
    assert result[0] == s[0]
    assert result[-1] == s[-1]

    assert result.index.name == "index"


def test_resample_how_method(unit):
    # GH9915
    s = Series(
        [11, 22],
        index=[
            Timestamp("2015-03-31 21:48:52.672000"),
            Timestamp("2015-03-31 21:49:52.739000"),
        ],
    )
    s.index = s.index.as_unit(unit)
    expected = Series(
        [11, np.NaN, np.NaN, np.NaN, np.NaN, np.NaN, 22],
        index=DatetimeIndex(
            [
                Timestamp("2015-03-31 21:48:50"),
                Timestamp("2015-03-31 21:49:00"),
                Timestamp("2015-03-31 21:49:10"),
                Timestamp("2015-03-31 21:49:20"),
                Timestamp("2015-03-31 21:49:30"),
                Timestamp("2015-03-31 21:49:40"),
                Timestamp("2015-03-31 21:49:50"),
            ],
            freq="10s",
        ),
    )
    expected.index = expected.index.as_unit(unit)
    tm.assert_series_equal(s.resample("10S").mean(), expected)


def test_resample_extra_index_point(unit):
    # GH#9756
    index = date_range(start="20150101", end="20150331", freq="BM").as_unit(unit)
    expected = DataFrame({"A": Series([21, 41, 63], index=index)})

    index = date_range(start="20150101", end="20150331", freq="B").as_unit(unit)
    df = DataFrame({"A": Series(range(len(index)), index=index)}, dtype="int64")
    result = df.resample("BM").last()
    tm.assert_frame_equal(result, expected)


def test_upsample_with_limit(unit):
    rng = date_range("1/1/2000", periods=3, freq="5t").as_unit(unit)
    ts = Series(np.random.randn(len(rng)), rng)

    result = ts.resample("t").ffill(limit=2)
    expected = ts.reindex(result.index, method="ffill", limit=2)
    tm.assert_series_equal(result, expected)


@pytest.mark.parametrize("freq", ["5D", "10H", "5Min", "10S"])
@pytest.mark.parametrize("rule", ["Y", "3M", "15D", "30H", "15Min", "30S"])
def test_nearest_upsample_with_limit(tz_aware_fixture, freq, rule, unit):
    # GH 33939
    rng = date_range("1/1/2000", periods=3, freq=freq, tz=tz_aware_fixture).as_unit(
        unit
    )
    ts = Series(np.random.randn(len(rng)), rng)

    result = ts.resample(rule).nearest(limit=2)
    expected = ts.reindex(result.index, method="nearest", limit=2)
    tm.assert_series_equal(result, expected)


def test_resample_ohlc(series, unit):
    s = series
    s.index = s.index.as_unit(unit)

    grouper = Grouper(freq=Minute(5))
    expect = s.groupby(grouper).agg(lambda x: x[-1])
    result = s.resample("5Min").ohlc()

    assert len(result) == len(expect)
    assert len(result.columns) == 4

    xs = result.iloc[-2]
    assert xs["open"] == s[-6]
    assert xs["high"] == s[-6:-1].max()
    assert xs["low"] == s[-6:-1].min()
    assert xs["close"] == s[-2]

    xs = result.iloc[0]
    assert xs["open"] == s[0]
    assert xs["high"] == s[:5].max()
    assert xs["low"] == s[:5].min()
    assert xs["close"] == s[4]


def test_resample_ohlc_result(unit):
    # GH 12332
    index = date_range("1-1-2000", "2-15-2000", freq="h").as_unit(unit)
    index = index.union(date_range("4-15-2000", "5-15-2000", freq="h").as_unit(unit))
    s = Series(range(len(index)), index=index)

    a = s.loc[:"4-15-2000"].resample("30T").ohlc()
    assert isinstance(a, DataFrame)

    b = s.loc[:"4-14-2000"].resample("30T").ohlc()
    assert isinstance(b, DataFrame)


def test_resample_ohlc_result_odd_period(unit):
    # GH12348
    # raising on odd period
    rng = date_range("2013-12-30", "2014-01-07").as_unit(unit)
    index = rng.drop(
        [
            Timestamp("2014-01-01"),
            Timestamp("2013-12-31"),
            Timestamp("2014-01-04"),
            Timestamp("2014-01-05"),
        ]
    )
    df = DataFrame(data=np.arange(len(index)), index=index)
    result = df.resample("B").mean()
    expected = df.reindex(index=date_range(rng[0], rng[-1], freq="B").as_unit(unit))
    tm.assert_frame_equal(result, expected)


def test_resample_ohlc_dataframe(unit):
    df = (
        DataFrame(
            {
                "PRICE": {
                    Timestamp("2011-01-06 10:59:05", tz=None): 24990,
                    Timestamp("2011-01-06 12:43:33", tz=None): 25499,
                    Timestamp("2011-01-06 12:54:09", tz=None): 25499,
                },
                "VOLUME": {
                    Timestamp("2011-01-06 10:59:05", tz=None): 1500000000,
                    Timestamp("2011-01-06 12:43:33", tz=None): 5000000000,
                    Timestamp("2011-01-06 12:54:09", tz=None): 100000000,
                },
            }
        )
    ).reindex(["VOLUME", "PRICE"], axis=1)
    df.index = df.index.as_unit(unit)
    df.columns.name = "Cols"
    res = df.resample("H").ohlc()
    exp = pd.concat(
        [df["VOLUME"].resample("H").ohlc(), df["PRICE"].resample("H").ohlc()],
        axis=1,
        keys=df.columns,
    )
    assert exp.columns.names[0] == "Cols"
    tm.assert_frame_equal(exp, res)

    df.columns = [["a", "b"], ["c", "d"]]
    res = df.resample("H").ohlc()
    exp.columns = pd.MultiIndex.from_tuples(
        [
            ("a", "c", "open"),
            ("a", "c", "high"),
            ("a", "c", "low"),
            ("a", "c", "close"),
            ("b", "d", "open"),
            ("b", "d", "high"),
            ("b", "d", "low"),
            ("b", "d", "close"),
        ]
    )
    tm.assert_frame_equal(exp, res)

    # dupe columns fail atm
    # df.columns = ['PRICE', 'PRICE']


def test_resample_dup_index():
    # GH 4812
    # dup columns with resample raising
    df = DataFrame(
        np.random.randn(4, 12),
        index=[2000, 2000, 2000, 2000],
        columns=[Period(year=2000, month=i + 1, freq="M") for i in range(12)],
    )
    df.iloc[3, :] = np.nan
    result = df.resample("Q", axis=1).mean()
    msg = "DataFrame.groupby with axis=1 is deprecated"
    with tm.assert_produces_warning(FutureWarning, match=msg):
        expected = df.groupby(lambda x: int((x.month - 1) / 3), axis=1).mean()
    expected.columns = [Period(year=2000, quarter=i + 1, freq="Q") for i in range(4)]
    tm.assert_frame_equal(result, expected)


def test_resample_reresample(unit):
    dti = date_range(
        start=datetime(2005, 1, 1), end=datetime(2005, 1, 10), freq="D"
    ).as_unit(unit)
    s = Series(np.random.rand(len(dti)), dti)
    bs = s.resample("B", closed="right", label="right").mean()
    result = bs.resample("8H").mean()
    assert len(result) == 22
    assert isinstance(result.index.freq, offsets.DateOffset)
    assert result.index.freq == offsets.Hour(8)


@pytest.mark.parametrize(
    "freq, expected_kwargs",
    [
        ["A-DEC", {"start": "1990", "end": "2000", "freq": "a-dec"}],
        ["A-JUN", {"start": "1990", "end": "2000", "freq": "a-jun"}],
        ["M", {"start": "1990-01", "end": "2000-01", "freq": "M"}],
    ],
)
def test_resample_timestamp_to_period(
    simple_date_range_series, freq, expected_kwargs, unit
):
    ts = simple_date_range_series("1/1/1990", "1/1/2000")
    ts.index = ts.index.as_unit(unit)

    result = ts.resample(freq, kind="period").mean()
    expected = ts.resample(freq).mean()
    expected.index = period_range(**expected_kwargs)
    tm.assert_series_equal(result, expected)


def test_ohlc_5min(unit):
    def _ohlc(group):
        if isna(group).all():
            return np.repeat(np.nan, 4)
        return [group[0], group.max(), group.min(), group[-1]]

    rng = date_range("1/1/2000 00:00:00", "1/1/2000 5:59:50", freq="10s").as_unit(unit)
    ts = Series(np.random.randn(len(rng)), index=rng)

    resampled = ts.resample("5min", closed="right", label="right").ohlc()

    assert (resampled.loc["1/1/2000 00:00"] == ts[0]).all()

    exp = _ohlc(ts[1:31])
    assert (resampled.loc["1/1/2000 00:05"] == exp).all()

    exp = _ohlc(ts["1/1/2000 5:55:01":])
    assert (resampled.loc["1/1/2000 6:00:00"] == exp).all()


def test_downsample_non_unique(unit):
    rng = date_range("1/1/2000", "2/29/2000").as_unit(unit)
    rng2 = rng.repeat(5).values
    ts = Series(np.random.randn(len(rng2)), index=rng2)

    result = ts.resample("M").mean()

    expected = ts.groupby(lambda x: x.month).mean()
    assert len(result) == 2
    tm.assert_almost_equal(result[0], expected[1])
    tm.assert_almost_equal(result[1], expected[2])


def test_asfreq_non_unique(unit):
    # GH #1077
    rng = date_range("1/1/2000", "2/29/2000").as_unit(unit)
    rng2 = rng.repeat(2).values
    ts = Series(np.random.randn(len(rng2)), index=rng2)

    msg = "cannot reindex on an axis with duplicate labels"
    with pytest.raises(ValueError, match=msg):
        ts.asfreq("B")


def test_resample_axis1(unit):
    rng = date_range("1/1/2000", "2/29/2000").as_unit(unit)
    df = DataFrame(np.random.randn(3, len(rng)), columns=rng, index=["a", "b", "c"])

    result = df.resample("M", axis=1).mean()
    expected = df.T.resample("M").mean().T
    tm.assert_frame_equal(result, expected)


@pytest.mark.parametrize("freq", ["t", "5t", "15t", "30t", "4h", "12h"])
def test_resample_anchored_ticks(freq, unit):
    # If a fixed delta (5 minute, 4 hour) evenly divides a day, we should
    # "anchor" the origin at midnight so we get regular intervals rather
    # than starting from the first timestamp which might start in the
    # middle of a desired interval

    rng = date_range("1/1/2000 04:00:00", periods=86400, freq="s").as_unit(unit)
    ts = Series(np.random.randn(len(rng)), index=rng)
    ts[:2] = np.nan  # so results are the same
    result = ts[2:].resample(freq, closed="left", label="left").mean()
    expected = ts.resample(freq, closed="left", label="left").mean()
    tm.assert_series_equal(result, expected)


@pytest.mark.parametrize("end", [1, 2])
def test_resample_single_group(end, unit):
    mysum = lambda x: x.sum()

    rng = date_range("2000-1-1", f"2000-{end}-10", freq="D").as_unit(unit)
    ts = Series(np.random.randn(len(rng)), index=rng)
    tm.assert_series_equal(ts.resample("M").sum(), ts.resample("M").apply(mysum))


def test_resample_single_group_std(unit):
    # GH 3849
    s = Series(
        [30.1, 31.6],
        index=[Timestamp("20070915 15:30:00"), Timestamp("20070915 15:40:00")],
    )
    s.index = s.index.as_unit(unit)
    expected = Series(
        [0.75], index=DatetimeIndex([Timestamp("20070915")], freq="D").as_unit(unit)
    )
    result = s.resample("D").apply(lambda x: np.std(x))
    tm.assert_series_equal(result, expected)


def test_resample_offset(unit):
    # GH 31809

    rng = date_range("1/1/2000 00:00:00", "1/1/2000 02:00", freq="s").as_unit(unit)
    ts = Series(np.random.randn(len(rng)), index=rng)

    resampled = ts.resample("5min", offset="2min").mean()
    exp_rng = date_range("12/31/1999 23:57:00", "1/1/2000 01:57", freq="5min").as_unit(
        unit
    )
    tm.assert_index_equal(resampled.index, exp_rng)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"origin": "1999-12-31 23:57:00"},
        {"origin": Timestamp("1970-01-01 00:02:00")},
        {"origin": "epoch", "offset": "2m"},
        # origin of '1999-31-12 12:02:00' should be equivalent for this case
        {"origin": "1999-12-31 12:02:00"},
        {"offset": "-3m"},
    ],
)
def test_resample_origin(kwargs, unit):
    # GH 31809
    rng = date_range("2000-01-01 00:00:00", "2000-01-01 02:00", freq="s").as_unit(unit)
    ts = Series(np.random.randn(len(rng)), index=rng)

    exp_rng = date_range(
        "1999-12-31 23:57:00", "2000-01-01 01:57", freq="5min"
    ).as_unit(unit)

    resampled = ts.resample("5min", **kwargs).mean()
    tm.assert_index_equal(resampled.index, exp_rng)


@pytest.mark.parametrize(
    "origin", ["invalid_value", "epch", "startday", "startt", "2000-30-30", object()]
)
def test_resample_bad_origin(origin, unit):
    rng = date_range("2000-01-01 00:00:00", "2000-01-01 02:00", freq="s").as_unit(unit)
    ts = Series(np.random.randn(len(rng)), index=rng)
    msg = (
        "'origin' should be equal to 'epoch', 'start', 'start_day', "
        "'end', 'end_day' or should be a Timestamp convertible type. Got "
        f"'{origin}' instead."
    )
    with pytest.raises(ValueError, match=msg):
        ts.resample("5min", origin=origin)


@pytest.mark.parametrize("offset", ["invalid_value", "12dayys", "2000-30-30", object()])
def test_resample_bad_offset(offset, unit):
    rng = date_range("2000-01-01 00:00:00", "2000-01-01 02:00", freq="s").as_unit(unit)
    ts = Series(np.random.randn(len(rng)), index=rng)
    msg = f"'offset' should be a Timedelta convertible type. Got '{offset}' instead."
    with pytest.raises(ValueError, match=msg):
        ts.resample("5min", offset=offset)


def test_resample_origin_prime_freq(unit):
    # GH 31809
    start, end = "2000-10-01 23:30:00", "2000-10-02 00:30:00"
    rng = date_range(start, end, freq="7min").as_unit(unit)
    ts = Series(np.random.randn(len(rng)), index=rng)

    exp_rng = date_range(
        "2000-10-01 23:14:00", "2000-10-02 00:22:00", freq="17min"
    ).as_unit(unit)
    resampled = ts.resample("17min").mean()
    tm.assert_index_equal(resampled.index, exp_rng)
    resampled = ts.resample("17min", origin="start_day").mean()
    tm.assert_index_equal(resampled.index, exp_rng)

    exp_rng = date_range(
        "2000-10-01 23:30:00", "2000-10-02 00:21:00", freq="17min"
    ).as_unit(unit)
    resampled = ts.resample("17min", origin="start").mean()
    tm.assert_index_equal(resampled.index, exp_rng)
    resampled = ts.resample("17min", offset="23h30min").mean()
    tm.assert_index_equal(resampled.index, exp_rng)
    resampled = ts.resample("17min", origin="start_day", offset="23h30min").mean()
    tm.assert_index_equal(resampled.index, exp_rng)

    exp_rng = date_range(
        "2000-10-01 23:18:00", "2000-10-02 00:26:00", freq="17min"
    ).as_unit(unit)
    resampled = ts.resample("17min", origin="epoch").mean()
    tm.assert_index_equal(resampled.index, exp_rng)

    exp_rng = date_range(
        "2000-10-01 23:24:00", "2000-10-02 00:15:00", freq="17min"
    ).as_unit(unit)
    resampled = ts.resample("17min", origin="2000-01-01").mean()
    tm.assert_index_equal(resampled.index, exp_rng)


def test_resample_origin_with_tz(unit):
    # GH 31809
    msg = "The origin must have the same timezone as the index."

    tz = "Europe/Paris"
    rng = date_range(
        "2000-01-01 00:00:00", "2000-01-01 02:00", freq="s", tz=tz
    ).as_unit(unit)
    ts = Series(np.random.randn(len(rng)), index=rng)

    exp_rng = date_range(
        "1999-12-31 23:57:00", "2000-01-01 01:57", freq="5min", tz=tz
    ).as_unit(unit)
    resampled = ts.resample("5min", origin="1999-12-31 23:57:00+00:00").mean()
    tm.assert_index_equal(resampled.index, exp_rng)

    # origin of '1999-31-12 12:02:00+03:00' should be equivalent for this case
    resampled = ts.resample("5min", origin="1999-12-31 12:02:00+03:00").mean()
    tm.assert_index_equal(resampled.index, exp_rng)

    resampled = ts.resample("5min", origin="epoch", offset="2m").mean()
    tm.assert_index_equal(resampled.index, exp_rng)

    with pytest.raises(ValueError, match=msg):
        ts.resample("5min", origin="12/31/1999 23:57:00").mean()

    # if the series is not tz aware, origin should not be tz aware
    rng = date_range("2000-01-01 00:00:00", "2000-01-01 02:00", freq="s").as_unit(unit)
    ts = Series(np.random.randn(len(rng)), index=rng)
    with pytest.raises(ValueError, match=msg):
        ts.resample("5min", origin="12/31/1999 23:57:00+03:00").mean()


def test_resample_origin_epoch_with_tz_day_vs_24h(unit):
    # GH 34474
    start, end = "2000-10-01 23:30:00+0500", "2000-12-02 00:30:00+0500"
    rng = date_range(start, end, freq="7min").as_unit(unit)
    random_values = np.random.randn(len(rng))
    ts_1 = Series(random_values, index=rng)

    result_1 = ts_1.resample("D", origin="epoch").mean()
    result_2 = ts_1.resample("24H", origin="epoch").mean()
    tm.assert_series_equal(result_1, result_2)

    # check that we have the same behavior with epoch even if we are not timezone aware
    ts_no_tz = ts_1.tz_localize(None)
    result_3 = ts_no_tz.resample("D", origin="epoch").mean()
    result_4 = ts_no_tz.resample("24H", origin="epoch").mean()
    tm.assert_series_equal(result_1, result_3.tz_localize(rng.tz), check_freq=False)
    tm.assert_series_equal(result_1, result_4.tz_localize(rng.tz), check_freq=False)

    # check that we have the similar results with two different timezones (+2H and +5H)
    start, end = "2000-10-01 23:30:00+0200", "2000-12-02 00:30:00+0200"
    rng = date_range(start, end, freq="7min").as_unit(unit)
    ts_2 = Series(random_values, index=rng)
    result_5 = ts_2.resample("D", origin="epoch").mean()
    result_6 = ts_2.resample("24H", origin="epoch").mean()
    tm.assert_series_equal(result_1.tz_localize(None), result_5.tz_localize(None))
    tm.assert_series_equal(result_1.tz_localize(None), result_6.tz_localize(None))


def test_resample_origin_with_day_freq_on_dst(unit):
    # GH 31809
    tz = "America/Chicago"

    def _create_series(values, timestamps, freq="D"):
        return Series(
            values,
            index=DatetimeIndex(
                [Timestamp(t, tz=tz) for t in timestamps], freq=freq, ambiguous=True
            ).as_unit(unit),
        )

    # test classical behavior of origin in a DST context
    start = Timestamp("2013-11-02", tz=tz)
    end = Timestamp("2013-11-03 23:59", tz=tz)
    rng = date_range(start, end, freq="1h").as_unit(unit)
    ts = Series(np.ones(len(rng)), index=rng)

    expected = _create_series([24.0, 25.0], ["2013-11-02", "2013-11-03"])
    for origin in ["epoch", "start", "start_day", start, None]:
        result = ts.resample("D", origin=origin).sum()
        tm.assert_series_equal(result, expected)

    # test complex behavior of origin/offset in a DST context
    start = Timestamp("2013-11-03", tz=tz)
    end = Timestamp("2013-11-03 23:59", tz=tz)
    rng = date_range(start, end, freq="1h").as_unit(unit)
    ts = Series(np.ones(len(rng)), index=rng)

    expected_ts = ["2013-11-02 22:00-05:00", "2013-11-03 22:00-06:00"]
    expected = _create_series([23.0, 2.0], expected_ts)
    result = ts.resample("D", origin="start", offset="-2H").sum()
    tm.assert_series_equal(result, expected)

    expected_ts = ["2013-11-02 22:00-05:00", "2013-11-03 21:00-06:00"]
    expected = _create_series([22.0, 3.0], expected_ts, freq="24H")
    result = ts.resample("24H", origin="start", offset="-2H").sum()
    tm.assert_series_equal(result, expected)

    expected_ts = ["2013-11-02 02:00-05:00", "2013-11-03 02:00-06:00"]
    expected = _create_series([3.0, 22.0], expected_ts)
    result = ts.resample("D", origin="start", offset="2H").sum()
    tm.assert_series_equal(result, expected)

    expected_ts = ["2013-11-02 23:00-05:00", "2013-11-03 23:00-06:00"]
    expected = _create_series([24.0, 1.0], expected_ts)
    result = ts.resample("D", origin="start", offset="-1H").sum()
    tm.assert_series_equal(result, expected)

    expected_ts = ["2013-11-02 01:00-05:00", "2013-11-03 01:00:00-0500"]
    expected = _create_series([1.0, 24.0], expected_ts)
    result = ts.resample("D", origin="start", offset="1H").sum()
    tm.assert_series_equal(result, expected)


def test_resample_daily_anchored(unit):
    rng = date_range("1/1/2000 0:00:00", periods=10000, freq="T").as_unit(unit)
    ts = Series(np.random.randn(len(rng)), index=rng)
    ts[:2] = np.nan  # so results are the same

    result = ts[2:].resample("D", closed="left", label="left").mean()
    expected = ts.resample("D", closed="left", label="left").mean()
    tm.assert_series_equal(result, expected)


def test_resample_to_period_monthly_buglet(unit):
    # GH #1259

    rng = date_range("1/1/2000", "12/31/2000").as_unit(unit)
    ts = Series(np.random.randn(len(rng)), index=rng)

    result = ts.resample("M", kind="period").mean()
    exp_index = period_range("Jan-2000", "Dec-2000", freq="M")
    tm.assert_index_equal(result.index, exp_index)


def test_period_with_agg():
    # aggregate a period resampler with a lambda
    s2 = Series(
        np.random.randint(0, 5, 50),
        index=period_range("2012-01-01", freq="H", periods=50),
        dtype="float64",
    )

    expected = s2.to_timestamp().resample("D").mean().to_period()
    result = s2.resample("D").agg(lambda x: x.mean())
    tm.assert_series_equal(result, expected)


def test_resample_segfault(unit):
    # GH 8573
    # segfaulting in older versions
    all_wins_and_wagers = [
        (1, datetime(2013, 10, 1, 16, 20), 1, 0),
        (2, datetime(2013, 10, 1, 16, 10), 1, 0),
        (2, datetime(2013, 10, 1, 18, 15), 1, 0),
        (2, datetime(2013, 10, 1, 16, 10, 31), 1, 0),
    ]

    df = DataFrame.from_records(
        all_wins_and_wagers, columns=("ID", "timestamp", "A", "B")
    ).set_index("timestamp")
    df.index = df.index.as_unit(unit)
    result = df.groupby("ID").resample("5min").sum()
    expected = df.groupby("ID").apply(lambda x: x.resample("5min").sum())
    tm.assert_frame_equal(result, expected)


def test_resample_dtype_preservation(unit):
    # GH 12202
    # validation tests for dtype preservation

    df = DataFrame(
        {
            "date": date_range(start="2016-01-01", periods=4, freq="W").as_unit(unit),
            "group": [1, 1, 2, 2],
            "val": Series([5, 6, 7, 8], dtype="int32"),
        }
    ).set_index("date")

    result = df.resample("1D").ffill()
    assert result.val.dtype == np.int32

    result = df.groupby("group").resample("1D").ffill()
    assert result.val.dtype == np.int32


def test_resample_dtype_coercion(unit):
    pytest.importorskip("scipy.interpolate")

    # GH 16361
    df = {"a": [1, 3, 1, 4]}
    df = DataFrame(df, index=date_range("2017-01-01", "2017-01-04").as_unit(unit))

    expected = df.astype("float64").resample("H").mean()["a"].interpolate("cubic")

    result = df.resample("H")["a"].mean().interpolate("cubic")
    tm.assert_series_equal(result, expected)

    result = df.resample("H").mean()["a"].interpolate("cubic")
    tm.assert_series_equal(result, expected)


def test_weekly_resample_buglet(unit):
    # #1327
    rng = date_range("1/1/2000", freq="B", periods=20).as_unit(unit)
    ts = Series(np.random.randn(len(rng)), index=rng)

    resampled = ts.resample("W").mean()
    expected = ts.resample("W-SUN").mean()
    tm.assert_series_equal(resampled, expected)


def test_monthly_resample_error(unit):
    # #1451
    dates = date_range("4/16/2012 20:00", periods=5000, freq="h").as_unit(unit)
    ts = Series(np.random.randn(len(dates)), index=dates)
    # it works!
    ts.resample("M")


def test_nanosecond_resample_error():
    # GH 12307 - Values falls after last bin when
    # Resampling using pd.tseries.offsets.Nano as period
    start = 1443707890427
    exp_start = 1443707890400
    indx = date_range(start=pd.to_datetime(start), periods=10, freq="100n")
    ts = Series(range(len(indx)), index=indx)
    r = ts.resample(pd.tseries.offsets.Nano(100))
    result = r.agg("mean")

    exp_indx = date_range(start=pd.to_datetime(exp_start), periods=10, freq="100n")
    exp = Series(range(len(exp_indx)), index=exp_indx, dtype=float)

    tm.assert_series_equal(result, exp)


def test_resample_anchored_intraday(simple_date_range_series, unit):
    # #1471, #1458

    rng = date_range("1/1/2012", "4/1/2012", freq="100min").as_unit(unit)
    df = DataFrame(rng.month, index=rng)

    result = df.resample("M").mean()
    expected = df.resample("M", kind="period").mean().to_timestamp(how="end")
    expected.index += Timedelta(1, "ns") - Timedelta(1, "D")
    expected.index = expected.index.as_unit(unit)._with_freq("infer")
    assert expected.index.freq == "M"
    tm.assert_frame_equal(result, expected)

    result = df.resample("M", closed="left").mean()
    exp = df.shift(1, freq="D").resample("M", kind="period").mean()
    exp = exp.to_timestamp(how="end")

    exp.index = exp.index + Timedelta(1, "ns") - Timedelta(1, "D")
    exp.index = exp.index.as_unit(unit)._with_freq("infer")
    assert exp.index.freq == "M"
    tm.assert_frame_equal(result, exp)

    rng = date_range("1/1/2012", "4/1/2012", freq="100min").as_unit(unit)
    df = DataFrame(rng.month, index=rng)

    result = df.resample("Q").mean()
    expected = df.resample("Q", kind="period").mean().to_timestamp(how="end")
    expected.index += Timedelta(1, "ns") - Timedelta(1, "D")
    expected.index._data.freq = "Q"
    expected.index._freq = lib.no_default
    expected.index = expected.index.as_unit(unit)
    tm.assert_frame_equal(result, expected)

    result = df.resample("Q", closed="left").mean()
    expected = df.shift(1, freq="D").resample("Q", kind="period", closed="left").mean()
    expected = expected.to_timestamp(how="end")
    expected.index += Timedelta(1, "ns") - Timedelta(1, "D")
    expected.index._data.freq = "Q"
    expected.index._freq = lib.no_default
    expected.index = expected.index.as_unit(unit)
    tm.assert_frame_equal(result, expected)

    ts = simple_date_range_series("2012-04-29 23:00", "2012-04-30 5:00", freq="h")
    ts.index = ts.index.as_unit(unit)
    resampled = ts.resample("M").mean()
    assert len(resampled) == 1


@pytest.mark.parametrize("freq", ["MS", "BMS", "QS-MAR", "AS-DEC", "AS-JUN"])
def test_resample_anchored_monthstart(simple_date_range_series, freq, unit):
    ts = simple_date_range_series("1/1/2000", "12/31/2002")
    ts.index = ts.index.as_unit(unit)
    ts.resample(freq).mean()


@pytest.mark.parametrize("label, sec", [[None, 2.0], ["right", "4.2"]])
def test_resample_anchored_multiday(label, sec):
    # When resampling a range spanning multiple days, ensure that the
    # start date gets used to determine the offset.  Fixes issue where
    # a one day period is not a multiple of the frequency.
    #
    # See: https://github.com/pandas-dev/pandas/issues/8683

    index1 = date_range("2014-10-14 23:06:23.206", periods=3, freq="400L")
    index2 = date_range("2014-10-15 23:00:00", periods=2, freq="2200L")
    index = index1.union(index2)

    s = Series(np.random.randn(5), index=index)

    # Ensure left closing works
    result = s.resample("2200L", label=label).mean()
    assert result.index[-1] == Timestamp(f"2014-10-15 23:00:{sec}00")


def test_corner_cases(unit):
    # miscellaneous test coverage

    rng = date_range("1/1/2000", periods=12, freq="t").as_unit(unit)
    ts = Series(np.random.randn(len(rng)), index=rng)

    result = ts.resample("5t", closed="right", label="left").mean()
    ex_index = date_range("1999-12-31 23:55", periods=4, freq="5t").as_unit(unit)
    tm.assert_index_equal(result.index, ex_index)


def test_corner_cases_period(simple_period_range_series):
    # miscellaneous test coverage
    len0pts = simple_period_range_series("2007-01", "2010-05", freq="M")[:0]
    # it works
    result = len0pts.resample("A-DEC").mean()
    assert len(result) == 0


def test_corner_cases_date(simple_date_range_series, unit):
    # resample to periods
    ts = simple_date_range_series("2000-04-28", "2000-04-30 11:00", freq="h")
    ts.index = ts.index.as_unit(unit)
    result = ts.resample("M", kind="period").mean()
    assert len(result) == 1
    assert result.index[0] == Period("2000-04", freq="M")


def test_anchored_lowercase_buglet(unit):
    dates = date_range("4/16/2012 20:00", periods=50000, freq="s").as_unit(unit)
    ts = Series(np.random.randn(len(dates)), index=dates)
    # it works!
    ts.resample("d").mean()


def test_upsample_apply_functions(unit):
    # #1596
    rng = date_range("2012-06-12", periods=4, freq="h").as_unit(unit)

    ts = Series(np.random.randn(len(rng)), index=rng)

    result = ts.resample("20min").aggregate(["mean", "sum"])
    assert isinstance(result, DataFrame)


def test_resample_not_monotonic(unit):
    rng = date_range("2012-06-12", periods=200, freq="h").as_unit(unit)
    ts = Series(np.random.randn(len(rng)), index=rng)

    ts = ts.take(np.random.permutation(len(ts)))

    result = ts.resample("D").sum()
    exp = ts.sort_index().resample("D").sum()
    tm.assert_series_equal(result, exp)


@pytest.mark.parametrize(
    "dtype",
    [
        "int64",
        "int32",
        "float64",
        pytest.param(
            "float32",
            marks=pytest.mark.xfail(
                reason="Empty groups cause x.mean() to return float64"
            ),
        ),
    ],
)
def test_resample_median_bug_1688(dtype):
    df = DataFrame(
        [1, 2],
        index=[datetime(2012, 1, 1, 0, 0, 0), datetime(2012, 1, 1, 0, 5, 0)],
        dtype=dtype,
    )

    result = df.resample("T").apply(lambda x: x.mean())
    exp = df.asfreq("T")
    tm.assert_frame_equal(result, exp)

    result = df.resample("T").median()
    exp = df.asfreq("T")
    tm.assert_frame_equal(result, exp)


def test_how_lambda_functions(simple_date_range_series, unit):
    ts = simple_date_range_series("1/1/2000", "4/1/2000")
    ts.index = ts.index.as_unit(unit)

    result = ts.resample("M").apply(lambda x: x.mean())
    exp = ts.resample("M").mean()
    tm.assert_series_equal(result, exp)

    foo_exp = ts.resample("M").mean()
    foo_exp.name = "foo"
    bar_exp = ts.resample("M").std()
    bar_exp.name = "bar"

    result = ts.resample("M").apply([lambda x: x.mean(), lambda x: x.std(ddof=1)])
    result.columns = ["foo", "bar"]
    tm.assert_series_equal(result["foo"], foo_exp)
    tm.assert_series_equal(result["bar"], bar_exp)

    # this is a MI Series, so comparing the names of the results
    # doesn't make sense
    result = ts.resample("M").aggregate(
        {"foo": lambda x: x.mean(), "bar": lambda x: x.std(ddof=1)}
    )
    tm.assert_series_equal(result["foo"], foo_exp, check_names=False)
    tm.assert_series_equal(result["bar"], bar_exp, check_names=False)


def test_resample_unequal_times(unit):
    # #1772
    start = datetime(1999, 3, 1, 5)
    # end hour is less than start
    end = datetime(2012, 7, 31, 4)
    bad_ind = date_range(start, end, freq="30min").as_unit(unit)
    df = DataFrame({"close": 1}, index=bad_ind)

    # it works!
    df.resample("AS").sum()


def test_resample_consistency(unit):
    # GH 6418
    # resample with bfill / limit / reindex consistency

    i30 = date_range("2002-02-02", periods=4, freq="30T").as_unit(unit)
    s = Series(np.arange(4.0), index=i30)
    s[2] = np.NaN

    # Upsample by factor 3 with reindex() and resample() methods:
    i10 = date_range(i30[0], i30[-1], freq="10T").as_unit(unit)

    s10 = s.reindex(index=i10, method="bfill")
    s10_2 = s.reindex(index=i10, method="bfill", limit=2)
    rl = s.reindex_like(s10, method="bfill", limit=2)
    r10_2 = s.resample("10Min").bfill(limit=2)
    r10 = s.resample("10Min").bfill()

    # s10_2, r10, r10_2, rl should all be equal
    tm.assert_series_equal(s10_2, r10)
    tm.assert_series_equal(s10_2, r10_2)
    tm.assert_series_equal(s10_2, rl)


dates1: List[DatetimeNaTType] = [
    datetime(2014, 10, 1),
    datetime(2014, 9, 3),
    datetime(2014, 11, 5),
    datetime(2014, 9, 5),
    datetime(2014, 10, 8),
    datetime(2014, 7, 15),
]

dates2: List[DatetimeNaTType] = (
    dates1[:2] + [pd.NaT] + dates1[2:4] + [pd.NaT] + dates1[4:]
)
dates3 = [pd.NaT] + dates1 + [pd.NaT]


@pytest.mark.parametrize("dates", [dates1, dates2, dates3])
def test_resample_timegrouper(dates):
    # GH 7227
    df = DataFrame({"A": dates, "B": np.arange(len(dates))})
    result = df.set_index("A").resample("M").count()
    exp_idx = DatetimeIndex(
        ["2014-07-31", "2014-08-31", "2014-09-30", "2014-10-31", "2014-11-30"],
        freq="M",
        name="A",
    )
    expected = DataFrame({"B": [1, 0, 2, 2, 1]}, index=exp_idx)
    if df["A"].isna().any():
        expected.index = expected.index._with_freq(None)
    tm.assert_frame_equal(result, expected)

    result = df.groupby(Grouper(freq="M", key="A")).count()
    tm.assert_frame_equal(result, expected)

    df = DataFrame({"A": dates, "B": np.arange(len(dates)), "C": np.arange(len(dates))})
    result = df.set_index("A").resample("M").count()
    expected = DataFrame(
        {"B": [1, 0, 2, 2, 1], "C": [1, 0, 2, 2, 1]},
        index=exp_idx,
        columns=["B", "C"],
    )
    if df["A"].isna().any():
        expected.index = expected.index._with_freq(None)
    tm.assert_frame_equal(result, expected)

    result = df.groupby(Grouper(freq="M", key="A")).count()
    tm.assert_frame_equal(result, expected)


def test_resample_nunique(unit):
    # GH 12352
    df = DataFrame(
        {
            "ID": {
                Timestamp("2015-06-05 00:00:00"): "0010100903",
                Timestamp("2015-06-08 00:00:00"): "0010150847",
            },
            "DATE": {
                Timestamp("2015-06-05 00:00:00"): "2015-06-05",
                Timestamp("2015-06-08 00:00:00"): "2015-06-08",
            },
        }
    )
    df.index = df.index.as_unit(unit)
    r = df.resample("D")
    g = df.groupby(Grouper(freq="D"))
    expected = df.groupby(Grouper(freq="D")).ID.apply(lambda x: x.nunique())
    assert expected.name == "ID"

    for t in [r, g]:
        result = t.ID.nunique()
        tm.assert_series_equal(result, expected)

    result = df.ID.resample("D").nunique()
    tm.assert_series_equal(result, expected)

    result = df.ID.groupby(Grouper(freq="D")).nunique()
    tm.assert_series_equal(result, expected)


def test_resample_nunique_preserves_column_level_names(unit):
    # see gh-23222
    df = tm.makeTimeDataFrame(freq="1D").abs()
    df.index = df.index.as_unit(unit)
    df.columns = pd.MultiIndex.from_arrays(
        [df.columns.tolist()] * 2, names=["lev0", "lev1"]
    )
    result = df.resample("1h").nunique()
    tm.assert_index_equal(df.columns, result.columns)


@pytest.mark.parametrize(
    "func",
    [
        lambda x: x.nunique(),
        lambda x: x.agg(Series.nunique),
        lambda x: x.agg("nunique"),
    ],
    ids=["nunique", "series_nunique", "nunique_str"],
)
def test_resample_nunique_with_date_gap(func, unit):
    # GH 13453
    # Since all elements are unique, these should all be the same
    index = date_range("1-1-2000", "2-15-2000", freq="h").as_unit(unit)
    index2 = date_range("4-15-2000", "5-15-2000", freq="h").as_unit(unit)
    index3 = index.append(index2)
    s = Series(range(len(index3)), index=index3, dtype="int64")
    r = s.resample("M")
    result = r.count()
    expected = func(r)
    tm.assert_series_equal(result, expected)


@pytest.mark.parametrize("n", [10000, 100000])
@pytest.mark.parametrize("k", [10, 100, 1000])
def test_resample_group_info(n, k, unit):
    # GH10914

    # use a fixed seed to always have the same uniques
    prng = np.random.RandomState(1234)

    dr = date_range(start="2015-08-27", periods=n // 10, freq="T").as_unit(unit)
    ts = Series(prng.randint(0, n // k, n).astype("int64"), index=prng.choice(dr, n))

    left = ts.resample("30T").nunique()
    ix = date_range(start=ts.index.min(), end=ts.index.max(), freq="30T").as_unit(unit)

    vals = ts.values
    bins = np.searchsorted(ix.values, ts.index, side="right")

    sorter = np.lexsort((vals, bins))
    vals, bins = vals[sorter], bins[sorter]

    mask = np.r_[True, vals[1:] != vals[:-1]]
    mask |= np.r_[True, bins[1:] != bins[:-1]]

    arr = np.bincount(bins[mask] - 1, minlength=len(ix)).astype("int64", copy=False)
    right = Series(arr, index=ix)

    tm.assert_series_equal(left, right)


def test_resample_size(unit):
    n = 10000
    dr = date_range("2015-09-19", periods=n, freq="T").as_unit(unit)
    ts = Series(np.random.randn(n), index=np.random.choice(dr, n))

    left = ts.resample("7T").size()
    ix = date_range(start=left.index.min(), end=ts.index.max(), freq="7T").as_unit(unit)

    bins = np.searchsorted(ix.values, ts.index.values, side="right")
    val = np.bincount(bins, minlength=len(ix) + 1)[1:].astype("int64", copy=False)

    right = Series(val, index=ix)
    tm.assert_series_equal(left, right)


def test_resample_across_dst():
    # The test resamples a DatetimeIndex with values before and after a
    # DST change
    # Issue: 14682

    # The DatetimeIndex we will start with
    # (note that DST happens at 03:00+02:00 -> 02:00+01:00)
    # 2016-10-30 02:23:00+02:00, 2016-10-30 02:23:00+01:00
    df1 = DataFrame([1477786980, 1477790580], columns=["ts"])
    dti1 = DatetimeIndex(
        pd.to_datetime(df1.ts, unit="s")
        .dt.tz_localize("UTC")
        .dt.tz_convert("Europe/Madrid")
    )

    # The expected DatetimeIndex after resampling.
    # 2016-10-30 02:00:00+02:00, 2016-10-30 02:00:00+01:00
    df2 = DataFrame([1477785600, 1477789200], columns=["ts"])
    dti2 = DatetimeIndex(
        pd.to_datetime(df2.ts, unit="s")
        .dt.tz_localize("UTC")
        .dt.tz_convert("Europe/Madrid"),
        freq="H",
    )
    df = DataFrame([5, 5], index=dti1)

    result = df.resample(rule="H").sum()
    expected = DataFrame([5, 5], index=dti2)

    tm.assert_frame_equal(result, expected)


def test_groupby_with_dst_time_change(unit):
    # GH 24972
    index = (
        DatetimeIndex([1478064900001000000, 1480037118776792000], tz="UTC")
        .tz_convert("America/Chicago")
        .as_unit(unit)
    )

    df = DataFrame([1, 2], index=index)
    result = df.groupby(Grouper(freq="1d")).last()
    expected_index_values = date_range(
        "2016-11-02", "2016-11-24", freq="d", tz="America/Chicago"
    ).as_unit(unit)

    index = DatetimeIndex(expected_index_values)
    expected = DataFrame([1.0] + ([np.nan] * 21) + [2.0], index=index)
    tm.assert_frame_equal(result, expected)


def test_resample_dst_anchor(unit):
    # 5172
    dti = DatetimeIndex([datetime(2012, 11, 4, 23)], tz="US/Eastern").as_unit(unit)
    df = DataFrame([5], index=dti)

    dti = DatetimeIndex(df.index.normalize(), freq="D").as_unit(unit)
    expected = DataFrame([5], index=dti)
    tm.assert_frame_equal(df.resample(rule="D").sum(), expected)
    df.resample(rule="MS").sum()
    tm.assert_frame_equal(
        df.resample(rule="MS").sum(),
        DataFrame(
            [5],
            index=DatetimeIndex(
                [datetime(2012, 11, 1)], tz="US/Eastern", freq="MS"
            ).as_unit(unit),
        ),
    )

    dti = date_range(
        "2013-09-30", "2013-11-02", freq="30Min", tz="Europe/Paris"
    ).as_unit(unit)
    values = range(dti.size)
    df = DataFrame({"a": values, "b": values, "c": values}, index=dti, dtype="int64")
    how = {"a": "min", "b": "max", "c": "count"}

    tm.assert_frame_equal(
        df.resample("W-MON").agg(how)[["a", "b", "c"]],
        DataFrame(
            {
                "a": [0, 48, 384, 720, 1056, 1394],
                "b": [47, 383, 719, 1055, 1393, 1586],
                "c": [48, 336, 336, 336, 338, 193],
            },
            index=date_range(
                "9/30/2013", "11/4/2013", freq="W-MON", tz="Europe/Paris"
            ).as_unit(unit),
        ),
        "W-MON Frequency",
    )

    tm.assert_frame_equal(
        df.resample("2W-MON").agg(how)[["a", "b", "c"]],
        DataFrame(
            {
                "a": [0, 48, 720, 1394],
                "b": [47, 719, 1393, 1586],
                "c": [48, 672, 674, 193],
            },
            index=date_range(
                "9/30/2013", "11/11/2013", freq="2W-MON", tz="Europe/Paris"
            ).as_unit(unit),
        ),
        "2W-MON Frequency",
    )

    tm.assert_frame_equal(
        df.resample("MS").agg(how)[["a", "b", "c"]],
        DataFrame(
            {"a": [0, 48, 1538], "b": [47, 1537, 1586], "c": [48, 1490, 49]},
            index=date_range(
                "9/1/2013", "11/1/2013", freq="MS", tz="Europe/Paris"
            ).as_unit(unit),
        ),
        "MS Frequency",
    )

    tm.assert_frame_equal(
        df.resample("2MS").agg(how)[["a", "b", "c"]],
        DataFrame(
            {"a": [0, 1538], "b": [1537, 1586], "c": [1538, 49]},
            index=date_range(
                "9/1/2013", "11/1/2013", freq="2MS", tz="Europe/Paris"
            ).as_unit(unit),
        ),
        "2MS Frequency",
    )

    df_daily = df["10/26/2013":"10/29/2013"]
    tm.assert_frame_equal(
        df_daily.resample("D").agg({"a": "min", "b": "max", "c": "count"})[
            ["a", "b", "c"]
        ],
        DataFrame(
            {
                "a": [1248, 1296, 1346, 1394],
                "b": [1295, 1345, 1393, 1441],
                "c": [48, 50, 48, 48],
            },
            index=date_range(
                "10/26/2013", "10/29/2013", freq="D", tz="Europe/Paris"
            ).as_unit(unit),
        ),
        "D Frequency",
    )


def test_downsample_across_dst(unit):
    # GH 8531
    tz = pytz.timezone("Europe/Berlin")
    dt = datetime(2014, 10, 26)
    dates = date_range(tz.localize(dt), periods=4, freq="2H").as_unit(unit)
    result = Series(5, index=dates).resample("H").mean()
    expected = Series(
        [5.0, np.nan] * 3 + [5.0],
        index=date_range(tz.localize(dt), periods=7, freq="H").as_unit(unit),
    )
    tm.assert_series_equal(result, expected)


def test_downsample_across_dst_weekly(unit):
    # GH 9119, GH 21459
    df = DataFrame(
        index=DatetimeIndex(
            ["2017-03-25", "2017-03-26", "2017-03-27", "2017-03-28", "2017-03-29"],
            tz="Europe/Amsterdam",
        ).as_unit(unit),
        data=[11, 12, 13, 14, 15],
    )
    result = df.resample("1W").sum()
    expected = DataFrame(
        [23, 42],
        index=DatetimeIndex(
            ["2017-03-26", "2017-04-02"], tz="Europe/Amsterdam", freq="W"
        ).as_unit(unit),
    )
    tm.assert_frame_equal(result, expected)


def test_downsample_across_dst_weekly_2(unit):
    # GH 9119, GH 21459
    idx = date_range("2013-04-01", "2013-05-01", tz="Europe/London", freq="H").as_unit(
        unit
    )
    s = Series(index=idx, dtype=np.float64)
    result = s.resample("W").mean()
    expected = Series(
        index=date_range("2013-04-07", freq="W", periods=5, tz="Europe/London").as_unit(
            unit
        ),
        dtype=np.float64,
    )
    tm.assert_series_equal(result, expected)


def test_downsample_dst_at_midnight(unit):
    # GH 25758
    start = datetime(2018, 11, 3, 12)
    end = datetime(2018, 11, 5, 12)
    index = date_range(start, end, freq="1H").as_unit(unit)
    index = index.tz_localize("UTC").tz_convert("America/Havana")
    data = list(range(len(index)))
    dataframe = DataFrame(data, index=index)
    result = dataframe.groupby(Grouper(freq="1D")).mean()

    dti = date_range("2018-11-03", periods=3).tz_localize(
        "America/Havana", ambiguous=True
    )
    dti = DatetimeIndex(dti, freq="D").as_unit(unit)
    expected = DataFrame([7.5, 28.0, 44.5], index=dti)
    tm.assert_frame_equal(result, expected)


def test_resample_with_nat(unit):
    # GH 13020
    index = DatetimeIndex(
        [
            pd.NaT,
            "1970-01-01 00:00:00",
            pd.NaT,
            "1970-01-01 00:00:01",
            "1970-01-01 00:00:02",
        ]
    )
    frame = DataFrame([2, 3, 5, 7, 11], index=index)
    frame.index = frame.index.as_unit(unit)

    index_1s = DatetimeIndex(
        ["1970-01-01 00:00:00", "1970-01-01 00:00:01", "1970-01-01 00:00:02"]
    ).as_unit(unit)
    frame_1s = DataFrame([3.0, 7.0, 11.0], index=index_1s)
    tm.assert_frame_equal(frame.resample("1s").mean(), frame_1s)

    index_2s = DatetimeIndex(["1970-01-01 00:00:00", "1970-01-01 00:00:02"]).as_unit(
        unit
    )
    frame_2s = DataFrame([5.0, 11.0], index=index_2s)
    tm.assert_frame_equal(frame.resample("2s").mean(), frame_2s)

    index_3s = DatetimeIndex(["1970-01-01 00:00:00"]).as_unit(unit)
    frame_3s = DataFrame([7.0], index=index_3s)
    tm.assert_frame_equal(frame.resample("3s").mean(), frame_3s)

    tm.assert_frame_equal(frame.resample("60s").mean(), frame_3s)


def test_resample_datetime_values(unit):
    # GH 13119
    # check that datetime dtype is preserved when NaT values are
    # introduced by the resampling

    dates = [datetime(2016, 1, 15), datetime(2016, 1, 19)]
    df = DataFrame({"timestamp": dates}, index=dates)
    df.index = df.index.as_unit(unit)

    exp = Series(
        [datetime(2016, 1, 15), pd.NaT, datetime(2016, 1, 19)],
        index=date_range("2016-01-15", periods=3, freq="2D").as_unit(unit),
        name="timestamp",
    )

    res = df.resample("2D").first()["timestamp"]
    tm.assert_series_equal(res, exp)
    res = df["timestamp"].resample("2D").first()
    tm.assert_series_equal(res, exp)


def test_resample_apply_with_additional_args(series, unit):
    # GH 14615
    def f(data, add_arg):
        return np.mean(data) * add_arg

    series.index = series.index.as_unit(unit)

    multiplier = 10
    result = series.resample("D").apply(f, multiplier)
    expected = series.resample("D").mean().multiply(multiplier)
    tm.assert_series_equal(result, expected)

    # Testing as kwarg
    result = series.resample("D").apply(f, add_arg=multiplier)
    expected = series.resample("D").mean().multiply(multiplier)
    tm.assert_series_equal(result, expected)

    # Testing dataframe
    df = DataFrame({"A": 1, "B": 2}, index=date_range("2017", periods=10))
    result = df.groupby("A").resample("D").agg(f, multiplier).astype(float)
    expected = df.groupby("A").resample("D").mean().multiply(multiplier)
    tm.assert_frame_equal(result, expected)


@pytest.mark.parametrize("k", [1, 2, 3])
@pytest.mark.parametrize(
    "n1, freq1, n2, freq2",
    [
        (30, "S", 0.5, "Min"),
        (60, "S", 1, "Min"),
        (3600, "S", 1, "H"),
        (60, "Min", 1, "H"),
        (21600, "S", 0.25, "D"),
        (86400, "S", 1, "D"),
        (43200, "S", 0.5, "D"),
        (1440, "Min", 1, "D"),
        (12, "H", 0.5, "D"),
        (24, "H", 1, "D"),
    ],
)
def test_resample_equivalent_offsets(n1, freq1, n2, freq2, k, unit):
    # GH 24127
    n1_ = n1 * k
    n2_ = n2 * k
    s = Series(
        0,
        index=date_range("19910905 13:00", "19911005 07:00", freq=freq1).as_unit(unit),
    )
    s = s + range(len(s))

    result1 = s.resample(str(n1_) + freq1).mean()
    result2 = s.resample(str(n2_) + freq2).mean()
    tm.assert_series_equal(result1, result2)


@pytest.mark.parametrize(
    "first,last,freq,exp_first,exp_last",
    [
        ("19910905", "19920406", "D", "19910905", "19920407"),
        ("19910905 00:00", "19920406 06:00", "D", "19910905", "19920407"),
        ("19910905 06:00", "19920406 06:00", "H", "19910905 06:00", "19920406 07:00"),
        ("19910906", "19920406", "M", "19910831", "19920430"),
        ("19910831", "19920430", "M", "19910831", "19920531"),
        ("1991-08", "1992-04", "M", "19910831", "19920531"),
    ],
)
def test_get_timestamp_range_edges(first, last, freq, exp_first, exp_last, unit):
    first = Period(first)
    first = first.to_timestamp(first.freq).as_unit(unit)
    last = Period(last)
    last = last.to_timestamp(last.freq).as_unit(unit)

    exp_first = Timestamp(exp_first)
    exp_last = Timestamp(exp_last)

    freq = pd.tseries.frequencies.to_offset(freq)
    result = _get_timestamp_range_edges(first, last, freq, unit="ns")
    expected = (exp_first, exp_last)
    assert result == expected


@pytest.mark.parametrize("duplicates", [True, False])
def test_resample_apply_product(duplicates, unit):
    # GH 5586
    index = date_range(start="2012-01-31", freq="M", periods=12).as_unit(unit)

    ts = Series(range(12), index=index)
    df = DataFrame({"A": ts, "B": ts + 2})
    if duplicates:
        df.columns = ["A", "A"]

    result = df.resample("Q").apply(np.product)
    expected = DataFrame(
        np.array([[0, 24], [60, 210], [336, 720], [990, 1716]], dtype=np.int64),
        index=DatetimeIndex(
            ["2012-03-31", "2012-06-30", "2012-09-30", "2012-12-31"], freq="Q-DEC"
        ).as_unit(unit),
        columns=df.columns,
    )
    tm.assert_frame_equal(result, expected)


@pytest.mark.parametrize(
    "first,last,freq_in,freq_out,exp_last",
    [
        (
            "2020-03-28",
            "2020-03-31",
            "D",
            "24H",
            "2020-03-30 01:00",
        ),  # includes transition into DST
        (
            "2020-03-28",
            "2020-10-27",
            "D",
            "24H",
            "2020-10-27 00:00",
        ),  # includes transition into and out of DST
        (
            "2020-10-25",
            "2020-10-27",
            "D",
            "24H",
            "2020-10-26 23:00",
        ),  # includes transition out of DST
        (
            "2020-03-28",
            "2020-03-31",
            "24H",
            "D",
            "2020-03-30 00:00",
        ),  # same as above, but from 24H to D
        ("2020-03-28", "2020-10-27", "24H", "D", "2020-10-27 00:00"),
        ("2020-10-25", "2020-10-27", "24H", "D", "2020-10-26 00:00"),
    ],
)
def test_resample_calendar_day_with_dst(
    first: str, last: str, freq_in: str, freq_out: str, exp_last: str, unit
):
    # GH 35219
    ts = Series(
        1.0, date_range(first, last, freq=freq_in, tz="Europe/Amsterdam").as_unit(unit)
    )
    result = ts.resample(freq_out).ffill()
    expected = Series(
        1.0,
        date_range(first, exp_last, freq=freq_out, tz="Europe/Amsterdam").as_unit(unit),
    )
    tm.assert_series_equal(result, expected)


@pytest.mark.parametrize("func", ["min", "max", "first", "last"])
def test_resample_aggregate_functions_min_count(func, unit):
    # GH#37768
    index = date_range(start="2020", freq="M", periods=3).as_unit(unit)
    ser = Series([1, np.nan, np.nan], index)
    result = getattr(ser.resample("Q"), func)(min_count=2)
    expected = Series(
        [np.nan],
        index=DatetimeIndex(["2020-03-31"], freq="Q-DEC").as_unit(unit),
    )
    tm.assert_series_equal(result, expected)


def test_resample_unsigned_int(any_unsigned_int_numpy_dtype, unit):
    # gh-43329
    df = DataFrame(
        index=date_range(start="2000-01-01", end="2000-01-03 23", freq="12H").as_unit(
            unit
        ),
        columns=["x"],
        data=[0, 1, 0] * 2,
        dtype=any_unsigned_int_numpy_dtype,
    )
    df = df.loc[(df.index < "2000-01-02") | (df.index > "2000-01-03"), :]

    result = df.resample("D").max()

    expected = DataFrame(
        [1, np.nan, 0],
        columns=["x"],
        index=date_range(start="2000-01-01", end="2000-01-03 23", freq="D").as_unit(
            unit
        ),
    )
    tm.assert_frame_equal(result, expected)


def test_long_rule_non_nano():
    # https://github.com/pandas-dev/pandas/issues/51024
    idx = date_range("0300-01-01", "2000-01-01", unit="s", freq="100Y")
    ser = Series([1, 4, 2, 8, 5, 7, 1, 4, 2, 8, 5, 7, 1, 4, 2, 8, 5], index=idx)
    result = ser.resample("200Y").mean()
    expected_idx = DatetimeIndex(
        np.array(
            [
                "0300-12-31",
                "0500-12-31",
                "0700-12-31",
                "0900-12-31",
                "1100-12-31",
                "1300-12-31",
                "1500-12-31",
                "1700-12-31",
                "1900-12-31",
            ]
        ).astype("datetime64[s]"),
        freq="200A-DEC",
    )
    expected = Series([1.0, 3.0, 6.5, 4.0, 3.0, 6.5, 4.0, 3.0, 6.5], index=expected_idx)
    tm.assert_series_equal(result, expected)
