from collections import abc

import numpy as np
import pytest

from pandas import CategoricalDtype, DataFrame, MultiIndex, Series, date_range
import pandas._testing as tm


class TestDataFrameToRecords:
    def test_to_records_dt64(self):
        df = DataFrame(
            [["one", "two", "three"], ["four", "five", "six"]],
            index=date_range("2012-01-01", "2012-01-02"),
        )

        expected = df.index.values[0]
        result = df.to_records()["index"][0]
        assert expected == result

    def test_to_records_with_multindex(self):
        # GH#3189
        index = [
            ["bar", "bar", "baz", "baz", "foo", "foo", "qux", "qux"],
            ["one", "two", "one", "two", "one", "two", "one", "two"],
        ]
        data = np.zeros((8, 4))
        df = DataFrame(data, index=index)
        r = df.to_records(index=True)["level_0"]
        assert "bar" in r
        assert "one" not in r

    def test_to_records_with_Mapping_type(self):
        import email
        from email.parser import Parser

        abc.Mapping.register(email.message.Message)

        headers = Parser().parsestr(
            "From: <user@example.com>\n"
            "To: <someone_else@example.com>\n"
            "Subject: Test message\n"
            "\n"
            "Body would go here\n"
        )

        frame = DataFrame.from_records([headers])
        all(x in frame for x in ["Type", "Subject", "From"])

    def test_to_records_floats(self):
        df = DataFrame(np.random.rand(10, 10))
        df.to_records()

    def test_to_records_index_name(self):
        df = DataFrame(np.random.randn(3, 3))
        df.index.name = "X"
        rs = df.to_records()
        assert "X" in rs.dtype.fields

        df = DataFrame(np.random.randn(3, 3))
        rs = df.to_records()
        assert "index" in rs.dtype.fields

        df.index = MultiIndex.from_tuples([("a", "x"), ("a", "y"), ("b", "z")])
        df.index.names = ["A", None]
        rs = df.to_records()
        assert "level_0" in rs.dtype.fields

    def test_to_records_with_unicode_index(self):
        # GH#13172
        # unicode_literals conflict with to_records
        result = DataFrame([{"a": "x", "b": "y"}]).set_index("a").to_records()
        expected = np.rec.array([("x", "y")], dtype=[("a", "O"), ("b", "O")])
        tm.assert_almost_equal(result, expected)

    def test_to_records_with_unicode_column_names(self):
        # xref issue: https://github.com/numpy/numpy/issues/2407
        # Issue GH#11879. to_records used to raise an exception when used
        # with column names containing non-ascii characters in Python 2
        result = DataFrame(data={"accented_name_é": [1.0]}).to_records()

        # Note that numpy allows for unicode field names but dtypes need
        # to be specified using dictionary instead of list of tuples.
        expected = np.rec.array(
            [(0, 1.0)],
            dtype={"names": ["index", "accented_name_é"], "formats": ["=i8", "=f8"]},
        )
        tm.assert_almost_equal(result, expected)

    def test_to_records_with_categorical(self):
        # GH#8626

        # dict creation
        df = DataFrame({"A": list("abc")}, dtype="category")
        expected = Series(list("abc"), dtype="category", name="A")
        tm.assert_series_equal(df["A"], expected)

        # list-like creation
        df = DataFrame(list("abc"), dtype="category")
        expected = Series(list("abc"), dtype="category", name=0)
        tm.assert_series_equal(df[0], expected)

        # to record array
        # this coerces
        result = df.to_records()
        expected = np.rec.array(
            [(0, "a"), (1, "b"), (2, "c")], dtype=[("index", "=i8"), ("0", "O")]
        )
        tm.assert_almost_equal(result, expected)

    @pytest.mark.parametrize(
        "kwargs,expected",
        [
            # No dtypes --> default to array dtypes.
            (
                dict(),
                np.rec.array(
                    [(0, 1, 0.2, "a"), (1, 2, 1.5, "bc")],
                    dtype=[("index", "<i8"), ("A", "<i8"), ("B", "<f8"), ("C", "O")],
                ),
            ),
            # Should have no effect in this case.
            (
                dict(index=True),
                np.rec.array(
                    [(0, 1, 0.2, "a"), (1, 2, 1.5, "bc")],
                    dtype=[("index", "<i8"), ("A", "<i8"), ("B", "<f8"), ("C", "O")],
                ),
            ),
            # Column dtype applied across the board. Index unaffected.
            (
                dict(column_dtypes="<U4"),
                np.rec.array(
                    [("0", "1", "0.2", "a"), ("1", "2", "1.5", "bc")],
                    dtype=[("index", "<i8"), ("A", "<U4"), ("B", "<U4"), ("C", "<U4")],
                ),
            ),
            # Index dtype applied across the board. Columns unaffected.
            (
                dict(index_dtypes="<U1"),
                np.rec.array(
                    [("0", 1, 0.2, "a"), ("1", 2, 1.5, "bc")],
                    dtype=[("index", "<U1"), ("A", "<i8"), ("B", "<f8"), ("C", "O")],
                ),
            ),
            # Pass in a type instance.
            (
                dict(column_dtypes=np.unicode),
                np.rec.array(
                    [("0", "1", "0.2", "a"), ("1", "2", "1.5", "bc")],
                    dtype=[("index", "<i8"), ("A", "<U"), ("B", "<U"), ("C", "<U")],
                ),
            ),
            # Pass in a dtype instance.
            (
                dict(column_dtypes=np.dtype("unicode")),
                np.rec.array(
                    [("0", "1", "0.2", "a"), ("1", "2", "1.5", "bc")],
                    dtype=[("index", "<i8"), ("A", "<U"), ("B", "<U"), ("C", "<U")],
                ),
            ),
            # Pass in a dictionary (name-only).
            (
                dict(column_dtypes={"A": np.int8, "B": np.float32, "C": "<U2"}),
                np.rec.array(
                    [("0", "1", "0.2", "a"), ("1", "2", "1.5", "bc")],
                    dtype=[("index", "<i8"), ("A", "i1"), ("B", "<f4"), ("C", "<U2")],
                ),
            ),
            # Pass in a dictionary (indices-only).
            (
                dict(index_dtypes={0: "int16"}),
                np.rec.array(
                    [(0, 1, 0.2, "a"), (1, 2, 1.5, "bc")],
                    dtype=[("index", "i2"), ("A", "<i8"), ("B", "<f8"), ("C", "O")],
                ),
            ),
            # Ignore index mappings if index is not True.
            (
                dict(index=False, index_dtypes="<U2"),
                np.rec.array(
                    [(1, 0.2, "a"), (2, 1.5, "bc")],
                    dtype=[("A", "<i8"), ("B", "<f8"), ("C", "O")],
                ),
            ),
            # Non-existent names / indices in mapping should not error.
            (
                dict(index_dtypes={0: "int16", "not-there": "float32"}),
                np.rec.array(
                    [(0, 1, 0.2, "a"), (1, 2, 1.5, "bc")],
                    dtype=[("index", "i2"), ("A", "<i8"), ("B", "<f8"), ("C", "O")],
                ),
            ),
            # Names / indices not in mapping default to array dtype.
            (
                dict(column_dtypes={"A": np.int8, "B": np.float32}),
                np.rec.array(
                    [("0", "1", "0.2", "a"), ("1", "2", "1.5", "bc")],
                    dtype=[("index", "<i8"), ("A", "i1"), ("B", "<f4"), ("C", "O")],
                ),
            ),
            # Names / indices not in dtype mapping default to array dtype.
            (
                dict(column_dtypes={"A": np.dtype("int8"), "B": np.dtype("float32")}),
                np.rec.array(
                    [("0", "1", "0.2", "a"), ("1", "2", "1.5", "bc")],
                    dtype=[("index", "<i8"), ("A", "i1"), ("B", "<f4"), ("C", "O")],
                ),
            ),
            # Mixture of everything.
            (
                dict(column_dtypes={"A": np.int8, "B": np.float32}, index_dtypes="<U2"),
                np.rec.array(
                    [("0", "1", "0.2", "a"), ("1", "2", "1.5", "bc")],
                    dtype=[("index", "<U2"), ("A", "i1"), ("B", "<f4"), ("C", "O")],
                ),
            ),
            # Invalid dype values.
            (
                dict(index=False, column_dtypes=list()),
                (ValueError, "Invalid dtype \\[\\] specified for column A"),
            ),
            (
                dict(index=False, column_dtypes={"A": "int32", "B": 5}),
                (ValueError, "Invalid dtype 5 specified for column B"),
            ),
            # Numpy can't handle EA types, so check error is raised
            (
                dict(
                    index=False,
                    column_dtypes={"A": "int32", "B": CategoricalDtype(["a", "b"])},
                ),
                (ValueError, "Invalid dtype category specified for column B"),
            ),
            # Check that bad types raise
            (
                dict(index=False, column_dtypes={"A": "int32", "B": "foo"}),
                (TypeError, 'data type "foo" not understood'),
            ),
        ],
    )
    def test_to_records_dtype(self, kwargs, expected):
        # see GH#18146
        df = DataFrame({"A": [1, 2], "B": [0.2, 1.5], "C": ["a", "bc"]})

        if not isinstance(expected, np.recarray):
            with pytest.raises(expected[0], match=expected[1]):
                df.to_records(**kwargs)
        else:
            result = df.to_records(**kwargs)
            tm.assert_almost_equal(result, expected)

    @pytest.mark.parametrize(
        "df,kwargs,expected",
        [
            # MultiIndex in the index.
            (
                DataFrame(
                    [[1, 2, 3], [4, 5, 6], [7, 8, 9]], columns=list("abc")
                ).set_index(["a", "b"]),
                dict(column_dtypes="float64", index_dtypes={0: "int32", 1: "int8"}),
                np.rec.array(
                    [(1, 2, 3.0), (4, 5, 6.0), (7, 8, 9.0)],
                    dtype=[("a", "<i4"), ("b", "i1"), ("c", "<f8")],
                ),
            ),
            # MultiIndex in the columns.
            (
                DataFrame(
                    [[1, 2, 3], [4, 5, 6], [7, 8, 9]],
                    columns=MultiIndex.from_tuples(
                        [("a", "d"), ("b", "e"), ("c", "f")]
                    ),
                ),
                dict(column_dtypes={0: "<U1", 2: "float32"}, index_dtypes="float32"),
                np.rec.array(
                    [(0.0, "1", 2, 3.0), (1.0, "4", 5, 6.0), (2.0, "7", 8, 9.0)],
                    dtype=[
                        ("index", "<f4"),
                        ("('a', 'd')", "<U1"),
                        ("('b', 'e')", "<i8"),
                        ("('c', 'f')", "<f4"),
                    ],
                ),
            ),
            # MultiIndex in both the columns and index.
            (
                DataFrame(
                    [[1, 2, 3], [4, 5, 6], [7, 8, 9]],
                    columns=MultiIndex.from_tuples(
                        [("a", "d"), ("b", "e"), ("c", "f")], names=list("ab")
                    ),
                    index=MultiIndex.from_tuples(
                        [("d", -4), ("d", -5), ("f", -6)], names=list("cd")
                    ),
                ),
                dict(column_dtypes="float64", index_dtypes={0: "<U2", 1: "int8"}),
                np.rec.array(
                    [
                        ("d", -4, 1.0, 2.0, 3.0),
                        ("d", -5, 4.0, 5.0, 6.0),
                        ("f", -6, 7, 8, 9.0),
                    ],
                    dtype=[
                        ("c", "<U2"),
                        ("d", "i1"),
                        ("('a', 'd')", "<f8"),
                        ("('b', 'e')", "<f8"),
                        ("('c', 'f')", "<f8"),
                    ],
                ),
            ),
        ],
    )
    def test_to_records_dtype_mi(self, df, kwargs, expected):
        # see GH#18146
        result = df.to_records(**kwargs)
        tm.assert_almost_equal(result, expected)

    def test_to_records_dict_like(self):
        # see GH#18146
        class DictLike:
            def __init__(self, **kwargs):
                self.d = kwargs.copy()

            def __getitem__(self, key):
                return self.d.__getitem__(key)

            def __contains__(self, key):
                return key in self.d

            def keys(self):
                return self.d.keys()

        df = DataFrame({"A": [1, 2], "B": [0.2, 1.5], "C": ["a", "bc"]})

        dtype_mappings = dict(
            column_dtypes=DictLike(**{"A": np.int8, "B": np.float32}),
            index_dtypes="<U2",
        )

        result = df.to_records(**dtype_mappings)
        expected = np.rec.array(
            [("0", "1", "0.2", "a"), ("1", "2", "1.5", "bc")],
            dtype=[("index", "<U2"), ("A", "i1"), ("B", "<f4"), ("C", "O")],
        )
        tm.assert_almost_equal(result, expected)

    @pytest.mark.parametrize("tz", ["UTC", "GMT", "US/Eastern"])
    def test_to_records_datetimeindex_with_tz(self, tz):
        # GH#13937
        dr = date_range("2016-01-01", periods=10, freq="S", tz=tz)

        df = DataFrame({"datetime": dr}, index=dr)

        expected = df.to_records()
        result = df.tz_convert("UTC").to_records()

        # both converted to UTC, so they are equal
        tm.assert_numpy_array_equal(result, expected)
