import pytest
import numpy as np

import pandas as pd

from .base import BaseExtensionTests


class BaseMethodsTests(BaseExtensionTests):
    """Various Series and DataFrame methods."""

    @pytest.mark.parametrize('dropna', [True, False])
    def test_value_counts(self, all_data, dropna):
        all_data = all_data[:10]
        if dropna:
            other = np.array(all_data[~all_data.isna()])
        else:
            other = all_data

        result = pd.Series(all_data).value_counts(dropna=dropna).sort_index()
        expected = pd.Series(other).value_counts(dropna=dropna).sort_index()

        self.assert_series_equal(result, expected)

    def test_count(self, data_missing):
        df = pd.DataFrame({"A": data_missing})
        result = df.count(axis='columns')
        expected = pd.Series([0, 1])
        self.assert_series_equal(result, expected)

    def test_apply_simple_series(self, data):
        result = pd.Series(data).apply(id)
        assert isinstance(result, pd.Series)

    def test_argsort(self, data_for_sorting):
        result = pd.Series(data_for_sorting).argsort()
        expected = pd.Series(np.array([2, 0, 1], dtype=np.int64))
        self.assert_series_equal(result, expected)

    def test_argsort_missing(self, data_missing_for_sorting):
        result = pd.Series(data_missing_for_sorting).argsort()
        expected = pd.Series(np.array([1, -1, 0], dtype=np.int64))
        self.assert_series_equal(result, expected)

    @pytest.mark.parametrize('ascending', [True, False])
    def test_sort_values(self, data_for_sorting, ascending):
        ser = pd.Series(data_for_sorting)
        result = ser.sort_values(ascending=ascending)
        expected = ser.iloc[[2, 0, 1]]
        if not ascending:
            expected = expected[::-1]

        self.assert_series_equal(result, expected)

    @pytest.mark.parametrize('ascending', [True, False])
    def test_sort_values_missing(self, data_missing_for_sorting, ascending):
        ser = pd.Series(data_missing_for_sorting)
        result = ser.sort_values(ascending=ascending)
        if ascending:
            expected = ser.iloc[[2, 0, 1]]
        else:
            expected = ser.iloc[[0, 2, 1]]
        self.assert_series_equal(result, expected)

    @pytest.mark.parametrize('ascending', [True, False])
    def test_sort_values_frame(self, data_for_sorting, ascending):
        df = pd.DataFrame({"A": [1, 2, 1],
                           "B": data_for_sorting})
        result = df.sort_values(['A', 'B'])
        expected = pd.DataFrame({"A": [1, 1, 2],
                                 'B': data_for_sorting.take([2, 0, 1])},
                                index=[2, 0, 1])
        self.assert_frame_equal(result, expected)
