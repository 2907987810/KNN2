import numpy as np
import pytest

from pandas import (
    DatetimeIndex,
    IntervalIndex,
    NaT,
    Period,
    Series,
    Timestamp,
)
import pandas._testing as tm


class TestDropna:
    def test_dropna_empty(self):
        ser = Series([], dtype=object)

        assert len(ser.dropna()) == 0
        return_value = ser.dropna(inplace=True)
        assert return_value is None
        assert len(ser) == 0

        # invalid axis
        msg = "No axis named 1 for object type Series"
        with pytest.raises(ValueError, match=msg):
            ser.dropna(axis=1)

    def test_dropna_preserve_name(self, datetime_series):
        datetime_series[:5] = np.nan
        result = datetime_series.dropna()
        assert result.name == datetime_series.name
        name = datetime_series.name
        ts = datetime_series.copy()
        return_value = ts.dropna(inplace=True)
        assert return_value is None
        assert ts.name == name

    def test_dropna_no_nan(self):
        for ser in [
            Series([1, 2, 3], name="x"),
            Series([False, True, False], name="x"),
        ]:

            result = ser.dropna()
            tm.assert_series_equal(result, ser)
            assert result is not ser

            s2 = ser.copy()
            return_value = s2.dropna(inplace=True)
            assert return_value is None
            tm.assert_series_equal(s2, ser)

    def test_dropna_intervals(self):
        ser = Series(
            [np.nan, 1, 2, 3],
            IntervalIndex.from_arrays([np.nan, 0, 1, 2], [np.nan, 1, 2, 3]),
        )

        result = ser.dropna()
        expected = ser.iloc[1:]
        tm.assert_series_equal(result, expected)

    def test_dropna_period_dtype(self):
        # GH#13737
        ser = Series([Period("2011-01", freq="M"), Period("NaT", freq="M")])
        result = ser.dropna()
        expected = Series([Period("2011-01", freq="M")])

        tm.assert_series_equal(result, expected)

    def test_datetime64_tz_dropna(self):
        # DatetimeLikeBlock
        ser = Series(
            [
                Timestamp("2011-01-01 10:00"),
                NaT,
                Timestamp("2011-01-03 10:00"),
                NaT,
            ]
        )
        result = ser.dropna()
        expected = Series(
            [Timestamp("2011-01-01 10:00"), Timestamp("2011-01-03 10:00")], index=[0, 2]
        )
        tm.assert_series_equal(result, expected)

        # DatetimeTZBlock
        idx = DatetimeIndex(
            ["2011-01-01 10:00", NaT, "2011-01-03 10:00", NaT], tz="Asia/Tokyo"
        )
        ser = Series(idx)
        assert ser.dtype == "datetime64[ns, Asia/Tokyo]"
        result = ser.dropna()
        expected = Series(
            [
                Timestamp("2011-01-01 10:00", tz="Asia/Tokyo"),
                Timestamp("2011-01-03 10:00", tz="Asia/Tokyo"),
            ],
            index=[0, 2],
        )
        assert result.dtype == "datetime64[ns, Asia/Tokyo]"
        tm.assert_series_equal(result, expected)

    def test_dropna_pos_args_deprecation(self):
        # https://github.com/pandas-dev/pandas/issues/41485
        ser = Series([1, 2, 3])
        msg = (
            r"In a future version of pandas all arguments of Series\.dropna "
            r"will be keyword-only"
        )
        with tm.assert_produces_warning(FutureWarning, match=msg):
            result = ser.dropna(0)
        expected = Series([1, 2, 3])
        tm.assert_series_equal(result, expected)
