from typing import List

import pandas as pd
from pandas import api, compat
import pandas.util.testing as tm


class Base:
    def check(self, namespace, expected, ignored=None):
        # see which names are in the namespace, minus optional
        # ignored ones
        # compare vs the expected

        result = sorted(f for f in dir(namespace) if not f.startswith("__"))
        if ignored is not None:
            result = sorted(set(result) - set(ignored))

        expected = sorted(expected)
        tm.assert_almost_equal(result, expected)


class TestPDApi(Base):

    # these are optionally imported based on testing
    # & need to be ignored
    ignored = ["tests", "locale", "conftest"]

    # top-level sub-packages
    lib = [
        "api",
        "arrays",
        "compat",
        "core",
        "errors",
        "pandas",
        "plotting",
        "test",
        "testing",
        "tseries",
        "util",
        "options",
        "io",
    ]

    # these are already deprecated; awaiting removal
    deprecated_modules: List[str] = []

    # misc
    misc = ["IndexSlice", "NaT", "NA"]

    # top-level classes
    classes = [
        "Categorical",
        "CategoricalIndex",
        "DataFrame",
        "DateOffset",
        "DatetimeIndex",
        "ExcelFile",
        "ExcelWriter",
        "Float64Index",
        "Grouper",
        "HDFStore",
        "Index",
        "Int64Index",
        "MultiIndex",
        "Period",
        "PeriodIndex",
        "RangeIndex",
        "UInt64Index",
        "Series",
        "SparseArray",
        "SparseDtype",
        "StringDtype",
        "Timedelta",
        "TimedeltaIndex",
        "Timestamp",
        "Interval",
        "IntervalIndex",
        "CategoricalDtype",
        "PeriodDtype",
        "IntervalDtype",
        "DatetimeTZDtype",
        "BooleanDtype",
        "Int8Dtype",
        "Int16Dtype",
        "Int32Dtype",
        "Int64Dtype",
        "UInt8Dtype",
        "UInt16Dtype",
        "UInt32Dtype",
        "UInt64Dtype",
        "NamedAgg",
    ]
    if not compat.PY37:
        classes.extend(["Panel", "SparseSeries", "SparseDataFrame"])
        deprecated_modules.extend("datetime")

    # these are already deprecated; awaiting removal
    deprecated_classes: List[str] = []

    # these should be deprecated in the future
    deprecated_classes_in_future: List[str] = []

    # external modules exposed in pandas namespace
    modules = ["np"]

    # top-level functions
    funcs = [
        "array",
        "bdate_range",
        "concat",
        "crosstab",
        "cut",
        "date_range",
        "interval_range",
        "eval",
        "factorize",
        "get_dummies",
        "infer_freq",
        "isna",
        "isnull",
        "lreshape",
        "melt",
        "notna",
        "notnull",
        "offsets",
        "merge",
        "merge_ordered",
        "merge_asof",
        "period_range",
        "pivot",
        "pivot_table",
        "qcut",
        "show_versions",
        "timedelta_range",
        "unique",
        "value_counts",
        "wide_to_long",
    ]

    # top-level option funcs
    funcs_option = [
        "reset_option",
        "describe_option",
        "get_option",
        "option_context",
        "set_option",
        "set_eng_float_format",
    ]

    # top-level read_* funcs
    funcs_read = [
        "read_clipboard",
        "read_csv",
        "read_excel",
        "read_fwf",
        "read_gbq",
        "read_hdf",
        "read_html",
        "read_json",
        "read_pickle",
        "read_sas",
        "read_sql",
        "read_sql_query",
        "read_sql_table",
        "read_stata",
        "read_table",
        "read_feather",
        "read_parquet",
        "read_orc",
        "read_spss",
    ]

    # top-level json funcs
    funcs_json = ["json_normalize"]

    # top-level to_* funcs
    funcs_to = ["to_datetime", "to_numeric", "to_pickle", "to_timedelta"]

    # top-level to deprecate in the future
    deprecated_funcs_in_future: List[str] = []

    # these are already deprecated; awaiting removal
    deprecated_funcs: List[str] = []

    # private modules in pandas namespace
    private_modules = [
        "_config",
        "_hashtable",
        "_lib",
        "_libs",
        "_np_version_under1p14",
        "_np_version_under1p15",
        "_np_version_under1p16",
        "_np_version_under1p17",
        "_np_version_under1p18",
        "_tslib",
        "_typing",
        "_version",
    ]

    def test_api(self):

        self.check(
            pd,
            self.lib
            + self.misc
            + self.modules
            + self.deprecated_modules
            + self.classes
            + self.deprecated_classes
            + self.deprecated_classes_in_future
            + self.funcs
            + self.funcs_option
            + self.funcs_read
            + self.funcs_json
            + self.funcs_to
            + self.deprecated_funcs_in_future
            + self.deprecated_funcs
            + self.private_modules,
            self.ignored,
        )


def test_datetime():
    from datetime import datetime
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)
        assert datetime.date(2015, 7, 10) == pd.datetime.date(2015, 7, 10)


class TestApi(Base):

    allowed = ["types", "extensions", "indexers"]

    def test_api(self):

        self.check(api, self.allowed)


class TestTesting(Base):

    funcs = ["assert_frame_equal", "assert_series_equal", "assert_index_equal"]

    def test_testing(self):

        from pandas import testing

        self.check(testing, self.funcs)
