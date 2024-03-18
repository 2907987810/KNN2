"""
Just a conftest file for doctest stuff

The main conftest file is in pandas/tests/conftest.py
"""

from datetime import (
    timedelta,
    timezone,
)
import zoneinfo

from dateutil.tz import (
    tzlocal,
    tzutc,
)
import pytest
from pytz import FixedOffset

import pandas.util._test_decorators as td

try:
    zoneinfo.ZoneInfo("UTC")
except zoneinfo.ZoneInfoNotFoundError:
    zoneinfo = None  # type: ignore[assignment]


# https://github.com/pytest-dev/pytest/issues/11873
# Would like to avoid autouse=True, but cannot as of pytest 8.0.0
@pytest.fixture(autouse=True)
def add_doctest_imports(doctest_namespace) -> None:
    """
    Make `np` and `pd` names available for doctests.
    """
    import numpy as np

    import pandas as pd

    doctest_namespace["np"] = np
    doctest_namespace["pd"] = pd


def ignore_doctest_warning(item: pytest.Item, path: str, message: str) -> None:
    """Ignore doctest warning.

    Parameters
    ----------
    item : pytest.Item
        pytest test item.
    path : str
        Module path to Python object, e.g. "pandas.core.frame.DataFrame.append". A
        warning will be filtered when item.name ends with in given path. So it is
        sufficient to specify e.g. "DataFrame.append".
    message : str
        Message to be filtered.
    """
    if item.name.endswith(path):
        item.add_marker(pytest.mark.filterwarnings(f"ignore:{message}"))


def pytest_collection_modifyitems(items, config) -> None:
    is_doctest = config.getoption("--doctest-modules") or config.getoption(
        "--doctest-cython", default=False
    )

    # Warnings from doctests that can be ignored; place reason in comment above.
    # Each entry specifies (path, message) - see the ignore_doctest_warning function
    ignored_doctest_warnings = [
        ("is_int64_dtype", "is_int64_dtype is deprecated"),
        ("is_interval_dtype", "is_interval_dtype is deprecated"),
        ("is_period_dtype", "is_period_dtype is deprecated"),
        ("is_datetime64tz_dtype", "is_datetime64tz_dtype is deprecated"),
        ("is_categorical_dtype", "is_categorical_dtype is deprecated"),
        ("is_sparse", "is_sparse is deprecated"),
        ("DataFrameGroupBy.fillna", "DataFrameGroupBy.fillna is deprecated"),
        ("NDFrame.replace", "The 'method' keyword"),
        ("NDFrame.replace", "Series.replace without 'value'"),
        ("NDFrame.clip", "Downcasting behavior in Series and DataFrame methods"),
        ("Series.idxmin", "The behavior of Series.idxmin"),
        ("Series.idxmax", "The behavior of Series.idxmax"),
        ("SeriesGroupBy.fillna", "SeriesGroupBy.fillna is deprecated"),
        ("SeriesGroupBy.idxmin", "The behavior of Series.idxmin"),
        ("SeriesGroupBy.idxmax", "The behavior of Series.idxmax"),
        # Docstring divides by zero to show behavior difference
        ("missing.mask_zero_div_zero", "divide by zero encountered"),
        (
            "pandas.core.generic.NDFrame.first",
            "first is deprecated and will be removed in a future version. "
            "Please create a mask and filter using `.loc` instead",
        ),
        (
            "Resampler.fillna",
            "DatetimeIndexResampler.fillna is deprecated",
        ),
        (
            "DataFrameGroupBy.fillna",
            "DataFrameGroupBy.fillna with 'method' is deprecated",
        ),
        ("read_parquet", "Passing a BlockManager to DataFrame is deprecated"),
    ]

    if is_doctest:
        for item in items:
            for path, message in ignored_doctest_warnings:
                ignore_doctest_warning(item, path, message)


# ----------------------------------------------------------------
# Time zones
# ----------------------------------------------------------------
TIMEZONES = [
    None,
    "UTC",
    "US/Eastern",
    "Asia/Tokyo",
    "dateutil/US/Pacific",
    "dateutil/Asia/Singapore",
    "+01:15",
    "-02:15",
    "UTC+01:15",
    "UTC-02:15",
    tzutc(),
    tzlocal(),
    FixedOffset(300),
    FixedOffset(0),
    FixedOffset(-300),
    timezone.utc,
    timezone(timedelta(hours=1)),
    timezone(timedelta(hours=-1), name="foo"),
]
if zoneinfo is not None:
    TIMEZONES.extend(
        [
            zoneinfo.ZoneInfo("US/Pacific"),  # type: ignore[list-item]
            zoneinfo.ZoneInfo("UTC"),  # type: ignore[list-item]
        ]
    )
TIMEZONE_IDS = [repr(i) for i in TIMEZONES]


@td.parametrize_fixture_doc(str(TIMEZONE_IDS))
@pytest.fixture(params=TIMEZONES, ids=TIMEZONE_IDS)
def tz_naive_fixture(request):
    """
    Fixture for trying timezones including default (None): {0}
    """
    return request.param


@td.parametrize_fixture_doc(str(TIMEZONE_IDS[1:]))
@pytest.fixture(params=TIMEZONES[1:], ids=TIMEZONE_IDS[1:])
def tz_aware_fixture(request):
    """
    Fixture for trying explicit timezones: {0}
    """
    return request.param


# Generate cartesian product of tz_aware_fixture:
tz_aware_fixture2 = tz_aware_fixture
