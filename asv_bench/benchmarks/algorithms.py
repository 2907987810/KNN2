from importlib import import_module

import numpy as np
import pandas as pd
from pandas.util import testing as tm
from pandas.core.algorithms import checked_add_with_arr

for imp in ['pandas.util', 'pandas.tools.hashing']:
    try:
        hashing = import_module(imp)
        break
    except:
        pass


class Factorize(object):

    goal_time = 0.2

    def setup(self):
        N = 10**5
        np.random.seed(1234)
        self.int_idx = pd.Int64Index(np.arange(N).repeat(5))
        self.float_idx = pd.Float64Index(np.random.randn(N).repeat(5))
        self.string_idx = tm.makeStringIndex(N)

    def time_factorize_int(self):
        self.int_idx.factorize()

    def time_factorize_float(self):
        self.float_idx.factorize()

    def time_factorize_string(self):
        self.string_idx.factorize()


class Duplicated(object):

    goal_time = 0.2

    def setup(self):
        N = 10**5
        np.random.seed(1234)
        self.int_idx = pd.Int64Index(np.arange(N).repeat(5))
        self.float_idx = pd.Float64Index(np.random.randn(N).repeat(5))

    def time_duplicated_int(self):
        self.int_idx.duplicated()

    def time_duplicated_float(self):
        self.float_idx.duplicated()


class DuplicatedUniqueIndex(object):

    goal_time = 0.2

    def setup(self):
        N = 10**5
        self.idx_int_dup = pd.Int64Index(np.arange(N * 5))
        # cache is_unique
        self.idx_int_dup.is_unique

    def time_duplicated_unique_int(self):
        self.idx_int_dup.duplicated()


class Match(object):

    goal_time = 0.2

    def setup(self):
        np.random.seed(1234)
        self.uniques = tm.makeStringIndex(1000).values
        self.all = self.uniques.repeat(10)

    def time_match_string(self):
        pd.match(self.all, self.uniques)


class AddOverflowScalar(object):

    goal_time = 0.2

    params = [1, -1, 0]

    def setup(self, scalar):
        N = 10**6
        self.arr = np.arange(N)

    def time_add_overflow_scalar(self, scalar):
        checked_add_with_arr(self.arr, scalar)


class AddOverflowArray(object):

    goal_time = 0.2

    def setup(self):
        np.random.seed(1234)
        N = 10**6
        self.arr = np.arange(N)
        self.arr_rev = np.arange(-N, 0)
        self.arr_mixed = np.array([1, -1]).repeat(N / 2)
        self.arr_nan_1 = np.random.choice([True, False], size=N)
        self.arr_nan_2 = np.random.choice([True, False], size=N)

    def time_add_overflow_arr_rev(self):
        checked_add_with_arr(self.arr, self.arr_rev)

    def time_add_overflow_arr_mask_nan(self):
        checked_add_with_arr(self.arr, self.arr_mixed, arr_mask=self.arr_nan_1)

    def time_add_overflow_b_mask_nan(self):
        checked_add_with_arr(self.arr, self.arr_mixed,
                             b_mask=self.arr_nan_1)

    def time_add_overflow_both_arg_nan(self):
        checked_add_with_arr(self.arr, self.arr_mixed, arr_mask=self.arr_nan_1,
                             b_mask=self.arr_nan_2)


class Hashing(object):

    goal_time = 0.2

    def setup_cache(self):
        np.random.seed(1234)
        N = 10**5

        df = pd.DataFrame(
            {'strings': pd.Series(tm.makeStringIndex(10000).take(
                np.random.randint(0, 10000, size=N))),
             'floats': np.random.randn(N),
             'ints': np.arange(N),
             'dates': pd.date_range('20110101', freq='s', periods=N),
             'timedeltas': pd.timedelta_range('1 day', freq='s', periods=N)})
        df['categories'] = df['strings'].astype('category')
        df.iloc[10:20] = np.nan
        return df

    def time_frame(self, df):
        hashing.hash_pandas_object(df)

    def time_series_int(self, df):
        hashing.hash_pandas_object(df['ints'])

    def time_series_string(self, df):
        hashing.hash_pandas_object(df['strings'])

    def time_series_float(self, df):
        hashing.hash_pandas_object(df['floats'])

    def time_series_categorical(self, df):
        hashing.hash_pandas_object(df['categories'])

    def time_series_timedeltas(self, df):
        hashing.hash_pandas_object(df['timedeltas'])

    def time_series_dates(self, df):
        hashing.hash_pandas_object(df['dates'])
