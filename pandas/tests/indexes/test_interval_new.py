from __future__ import division

import pytest
import numpy as np

from datetime import timedelta
from pandas import (Interval, IntervalIndex, Index, Int64Index, isna,
                    interval_range, Timestamp, Timedelta,
                    compat, date_range, timedelta_range, DateOffset)
from pandas.tseries.offsets import Day
from pandas._libs.interval import IntervalTree
from pandas.tests.indexes.common import Base
import pandas.util.testing as tm
import pandas as pd


class TestIntervalIndex_new(Base):

    def _compare_tuple_of_numpy_array(self, result, expected):
        lidx, ridx = result
        lidx_expected, ridx_expected = expected

        tm.assert_numpy_array_equal(lidx, lidx_expected)
        tm.assert_numpy_array_equal(ridx, ridx_expected)



    @pytest.mark.xfail(reason="new indexing tests for issue 16316")
    @pytest.mark.parametrize("idx_side", ['right', 'left', 'both', 'neither'])
    def test_get_loc_interval_updated_behavior(self, idx_side):

        idx = IntervalIndex.from_tuples([(0, 1), (2, 3)], closed=idx_side)

        for bound in [[0, 1], [1, 2], [2, 3], [3, 4],
                      [0, 2], [2.5, 3], [-1, 4]]:
            for side in ['right', 'left', 'both', 'neither']:
                # if get_loc is supplied an interval, it should only search
                # for exact matches, not overlaps or covers, else KeyError.
                if idx_side == side:
                    if bound == [0, 1]:
                        assert idx.get_loc(Interval(0, 1, closed=side)) == 0
                    elif bound == [2, 3]:
                        assert idx.get_loc(Interval(2, 3, closed=side)) == 1
                    else:
                        pytest.raises(KeyError, idx.get_loc,
                                      Interval(*bound, closed=side))
                else:
                    pytest.raises(KeyError, idx.get_loc,
                                  Interval(*bound, closed=side))

    @pytest.mark.xfail(reason="new indexing tests for issue 16316")
    @pytest.mark.parametrize("idx_side", ['right', 'left', 'both', 'neither'])
    def test_get_loc_scalar_updated_behavior(self, idx_side):

        scalars = [-0.5, 0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5]
        correct = {'right': {0.5: 0, 1: 0, 2.5: 1, 3: 1},
                   'left': {0: 0, 0.5: 0, 2: 1, 2.5: 1},
                   'both': {0: 0, 0.5: 0, 1: 0, 2: 1, 2.5: 1, 3: 1},
                   'neither': {0.5: 0, 2.5: 1}}

        idx = IntervalIndex.from_tuples([(0, 1), (2, 3)], closed=idx_side)

        for scalar in scalars:
            # if get_loc is supplied a scalar, it should return the index of
            # the interval which contains the scalar, or KeyError.
            if scalar in correct[idx_side].keys():
                assert idx.get_loc(scalar) == correct[idx_side][scalar]
            else:
                pytest.raises(KeyError, idx.get_loc, scalar)

    @pytest.mark.xfail(reason="new indexing tests for issue 16316")
    def test_slice_locs_with_interval_updated_behavior(self):

        # increasing monotonically
        index = IntervalIndex.from_tuples([(0, 2), (1, 3), (2, 4)])

        assert index.slice_locs(
            start=Interval(0, 2), end=Interval(2, 4)) == (0, 3)
        assert index.slice_locs(start=Interval(0, 2)) == (0, 3)
        assert index.slice_locs(end=Interval(2, 4)) == (0, 3)
        assert index.slice_locs(end=Interval(0, 2)) == (0, 1)
        assert index.slice_locs(
            start=Interval(2, 4), end=Interval(0, 2)) == (2, 1)

        # decreasing monotonically
        index = IntervalIndex.from_tuples([(2, 4), (1, 3), (0, 2)])

        assert index.slice_locs(
            start=Interval(0, 2), end=Interval(2, 4)) == (2, 1)
        assert index.slice_locs(start=Interval(0, 2)) == (2, 3)
        assert index.slice_locs(end=Interval(2, 4)) == (0, 1)
        assert index.slice_locs(end=Interval(0, 2)) == (0, 3)
        assert index.slice_locs(
            start=Interval(2, 4), end=Interval(0, 2)) == (0, 3)

        # sorted duplicates
        index = IntervalIndex.from_tuples([(0, 2), (0, 2), (2, 4)])

        assert index.slice_locs(
            start=Interval(0, 2), end=Interval(2, 4)) == (0, 3)
        assert index.slice_locs(start=Interval(0, 2)) == (0, 3)
        assert index.slice_locs(end=Interval(2, 4)) == (0, 3)
        assert index.slice_locs(end=Interval(0, 2)) == (0, 2)
        assert index.slice_locs(
            start=Interval(2, 4), end=Interval(0, 2)) == (2, 2)

        # unsorted duplicates
        index = IntervalIndex.from_tuples([(0, 2), (2, 4), (0, 2)])

        pytest.raises(KeyError, index.slice_locs(
            start=Interval(0, 2), end=Interval(2, 4)))
        pytest.raises(KeyError, index.slice_locs(start=Interval(0, 2)))
        assert index.slice_locs(end=Interval(2, 4)) == (0, 2)
        pytest.raises(KeyError, index.slice_locs(end=Interval(0, 2)))
        pytest.raises(KeyError, index.slice_locs(
            start=Interval(2, 4), end=Interval(0, 2)))

        # another unsorted duplicates
        index = IntervalIndex.from_tuples([(0, 2), (0, 2), (2, 4), (1, 3)])

        assert index.slice_locs(
            start=Interval(0, 2), end=Interval(2, 4)) == (0, 3)
        assert index.slice_locs(start=Interval(0, 2)) == (0, 4)
        assert index.slice_locs(end=Interval(2, 4)) == (0, 3)
        assert index.slice_locs(end=Interval(0, 2)) == (0, 2)
        assert index.slice_locs(
            start=Interval(2, 4), end=Interval(0, 2)) == (2, 2)

    @pytest.mark.xfail(reason="new indexing tests for issue 16316")
    def test_slice_locs_with_ints_and_floats_updated_behavior(self):

        queries = [[0, 1], [0, 2], [0, 3], [3, 1], [3, 4], [0, 4]]

        # increasing non-overlapping
        index = IntervalIndex.from_tuples([(0, 1), (1, 2), (3, 4)])

        assert index.slice_locs(0, 1) == (0, 1)
        assert index.slice_locs(0, 2) == (0, 2)
        assert index.slice_locs(0, 3) == (0, 2)
        assert index.slice_locs(3, 1) == (2, 1)
        assert index.slice_locs(3, 4) == (2, 3)
        assert index.slice_locs(0, 4) == (0, 3)

        # decreasing non-overlapping
        index = IntervalIndex.from_tuples([(3, 4), (1, 2), (0, 1)])
        assert index.slice_locs(0, 1) == (3, 2)
        assert index.slice_locs(0, 2) == (3, 1)
        assert index.slice_locs(0, 3) == (3, 1)
        assert index.slice_locs(3, 1) == (1, 2)
        assert index.slice_locs(3, 4) == (1, 0)
        assert index.slice_locs(0, 4) == (3, 0)

        # increasing overlapping
        index = IntervalIndex.from_tuples([(0, 2), (1, 3), (2, 4)])
        for query in queries:
            pytest.raises(KeyError, index.slice_locs, query)

        # decreasing overlapping
        index = IntervalIndex.from_tuples([(2, 4), (1, 3), (0, 2)])
        for query in queries:
            pytest.raises(KeyError, index.slice_locs, query)

        # sorted duplicates
        index = IntervalIndex.from_tuples([(0, 2), (0, 2), (2, 4)])
        for query in queries:
            pytest.raises(KeyError, index.slice_locs, query)

        # unsorted duplicates
        index = IntervalIndex.from_tuples([(0, 2), (2, 4), (0, 2)])
        for query in queries:
            pytest.raises(KeyError, index.slice_locs, query)

        # another unsorted duplicates
        index = IntervalIndex.from_tuples([(0, 2), (0, 2), (2, 4), (1, 3)])
        for query in queries:
            pytest.raises(KeyError, index.slice_locs, query)

    @pytest.mark.xfail(reason="new indexing tests for issue 16316")
    def test_get_indexer_for_interval_updated_behavior(self):

        index = IntervalIndex.from_tuples(
            [(0, 2.5), (1, 3), (2, 4)], closed='right')

        # single queries
        queries = [Interval(1, 3, closed='right'),
                   Interval(1, 3, closed='left'),
                   Interval(1, 3, closed='both'),
                   Interval(1, 3, closed='neither'),
                   Interval(1, 4, closed='right'),
                   Interval(0, 4, closed='right'),
                   Interval(1, 2, closed='right')]
        expected = [1, -1, -1, -1, -1, -1, -1]

        for query, expected_result in zip(queries, expected):
            result = index.get_indexer([query])
            expect = np.array([expected_result], dtype='intp')
            tm.assert_numpy_array_equal(result, expect)

        # multiple queries
        queries = [
            [Interval(2, 4, closed='right'), Interval(1, 3, closed='right')],
            [Interval(1, 3, closed='right'), Interval(0, 2, closed='right')],
            [Interval(1, 3, closed='right'), Interval(1, 3, closed='left')],
            index]
        expected = [[2, 1], [1, -1], [1, -1], [0, 1, 2]]

        for query, expected_result in zip(queries, expected):
            result = index.get_indexer(query)
            expect = np.array(expected_result, dtype='intp')
            tm.assert_numpy_array_equal(result, expect)

    @pytest.mark.xfail(reason="new indexing tests for issue 16316")
    def test_get_indexer_for_ints_and_floats_updated_behavior(self):

        index = IntervalIndex.from_tuples(
            [(0, 1), (1, 2), (3, 4)], closed='right')

        # single queries
        queries = [-0.5, 0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5]
        expected = [-1, -1, 0, 0, 1, 1, -1, -1, 2, 2, -1]

        for query, expected_result in zip(queries, expected):
            result = index.get_indexer([query])
            expect = np.array([expected_result], dtype='intp')
            tm.assert_numpy_array_equal(result, expect)

        # multiple queries
        queries = [[1, 2], [1, 2, 3], [1, 2, 3, 4], [1, 2, 3, 4, 2]]
        expected = [[0, 1], [0, 1, -1], [0, 1, -1, 2], [0, 1, -1, 2, 1]]

        for query, expected_result in zip(queries, expected):
            result = index.get_indexer(query)
            expect = np.array(expected_result, dtype='intp')
            tm.assert_numpy_array_equal(result, expect)

        index = IntervalIndex.from_tuples([(0, 2), (1, 3), (2, 4)])
        # TODO: @shoyer believes this should raise, master branch doesn't

    @pytest.mark.xfail(reason="new indexing tests for issue 16316")
    def test_get_indexer_non_unique_for_ints_and_floats_updated_behavior(self):

        index = IntervalIndex.from_tuples(
            [(0, 2.5), (1, 3), (2, 4)], closed='left')

        # single queries
        queries = [-0.5, 0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5]
        expected = [(Int64Index([], dtype='int64'), np.array([0]))
                    (Int64Index([0], dtype='int64'), np.array([]))
                    (Int64Index([0], dtype='int64'), np.array([]))
                    (Int64Index([0, 1], dtype='int64'), np.array([]))
                    (Int64Index([0, 1], dtype='int64'), np.array([]))
                    (Int64Index([0, 1, 2], dtype='int64'), np.array([]))
                    (Int64Index([1, 2], dtype='int64'), np.array([]))
                    (Int64Index([2], dtype='int64'), np.array([]))
                    (Int64Index([2], dtype='int64'), np.array([]))
                    (Int64Index([], dtype='int64'), np.array([0]))
                    (Int64Index([], dtype='int64'), np.array([0]))]

        for query, expected_result in zip(queries, expected):
            result = index.get_indexer_non_unique([query])
            tm.assert_numpy_array_equal(result, expected_result)

        # multiple queries
        queries = [[1, 2], [1, 2, 3], [1, 2, 3, 4], [1, 2, 3, 4, 2]]
        expected = [(Int64Index([0, 1, 0, 1, 2], dtype='int64'), np.array([]))
                    (Int64Index([0, 1, 0, 1, 2, 2],
                                dtype='int64'), np.array([]))
                    (Int64Index([0, 1, 0, 1, 2, 2, -1],
                                dtype='int64'), np.array([3]))
                    (Int64Index([0, 1, 0, 1, 2, 2, -1, 0, 1, 2],
                                dtype='int64'), np.array([3]))]

        for query, expected_result in zip(queries, expected):
            result = index.get_indexer_non_unique(query)
            tm.assert_numpy_array_equal(result, expected_result)

        # TODO we may also want to test get_indexer for the case when
        # the intervals are duplicated, decreasing, non-monotonic, etc..

    @pytest.mark.xfail(reason="new indexing tests for issue 16316")
    def test_contains_updated_behavior(self):

        index = IntervalIndex.from_arrays([0, 1], [1, 2], closed='right')

        # __contains__ requires perfect matches to intervals.
        assert 0 not in index
        assert 1 not in index
        assert 2 not in index

        assert Interval(0, 1, closed='right') in index
        assert Interval(0, 2, closed='right') not in index
        assert Interval(0, 0.5, closed='right') not in index
        assert Interval(3, 5, closed='right') not in index
        assert Interval(-1, 0, closed='left') not in index
        assert Interval(0, 1, closed='left') not in index
        assert Interval(0, 1, closed='both') not in index

    @pytest.mark.xfail(reason="new indexing tests for issue 16316")
    def test_contains_method_updated_behavior(self):

        index = IntervalIndex.from_arrays([0, 1], [1, 2], closed='right')

        assert not index.contains(0)
        assert index.contains(0.1)
        assert index.contains(0.5)
        assert index.contains(1)

        assert index.contains(Interval(0, 1), closed='right')
        assert not index.contains(Interval(0, 1), closed='left')
        assert not index.contains(Interval(0, 1), closed='both')
        assert not index.contains(Interval(0, 2), closed='right')

        assert not index.contains(Interval(0, 3), closed='right')
        assert not index.contains(Interval(1, 3), closed='right')

        assert not index.contains(20)
        assert not index.contains(-20)

    ###########################################################################
    # Keep this stuff around otherwise we'll forget about it....
    # I can remove it from this PR, just wanted to make sure it didn't get lost
    ###########################################################################

    @pytest.mark.xfail(reason="new indexing tests for issue 16316")
    def test_interval_covers_interval_updated_behavior(self):

        # class Interval:
        #     def covers(self, other: Interval) -> bool

        assert Interval(1, 3).covers(Interval(1.5, 2.5))
        assert Interval(1, 3).covers(Interval(1, 2))
        assert Interval(1, 3).covers(Interval(2, 3))
        assert not Interval(1, 3).covers(Interval(0.5, 2.5))
        assert not Interval(1, 3).covers(Interval(1.5, 3.5))

        assert Interval(1, 3, closed='right').covers(Interval(1, 3, closed='right'))
        assert not Interval(1, 3, closed='right').covers(Interval(1, 3, closed='left'))
        assert not Interval(1, 3, closed='right').covers(Interval(1, 3, closed='both'))

        assert not Interval(1, 3, closed='left').covers(Interval(1, 3, closed='right'))
        assert Interval(1, 3, closed='left').covers(Interval(1, 3, closed='left'))
        assert not Interval(1, 3, closed='left').covers(Interval(1, 3, closed='both'))

        assert Interval(1, 3, closed='both').covers(Interval(1, 3, closed='right'))
        assert Interval(1, 3, closed='both').covers(Interval(1, 3, closed='left'))
        assert Interval(1, 3, closed='both').covers(Interval(1, 3, closed='both'))

    @pytest.mark.xfail(reason="new indexing tests for issue 16316")
    def test_interval_covers_intervalIndex_updated_behavior(self):

        # class Interval:
        #     def covers(self, other: IntervalIndex) -> IntegerArray1D

        idx = IntervalIndex.from_tuples([(0, 1), (2, 3), (1, 3)], closed='right')

        tm.assert_numpy_array_equal(Interval(1, 3, closed='right').covers(idx), np.array([1, 2]))
        tm.assert_numpy_array_equal(Interval(0, 3, closed='right').covers(idx), np.array([0, 1, 2]))
        tm.assert_numpy_array_equal(Interval(0, 2, closed='right').covers(idx), np.array([0]))
        tm.assert_numpy_array_equal(Interval(2, 4, closed='right').covers(idx), np.array([1]))

        tm.assert_numpy_array_equal(Interval(1, 3, closed='left').covers(idx), np.array([]))
        tm.assert_numpy_array_equal(Interval(0, 3, closed='left').covers(idx), np.array([0]))
        tm.assert_numpy_array_equal(Interval(0, 2, closed='left').covers(idx), np.array([0]))
        tm.assert_numpy_array_equal(Interval(2, 4, closed='left').covers(idx), np.array([1]))

        tm.assert_numpy_array_equal(Interval(1, 3, closed='both').covers(idx), np.array([1, 2]))
        tm.assert_numpy_array_equal(Interval(0, 5, closed='both').covers(idx), np.array([0, 1, 2]))
        tm.assert_numpy_array_equal(Interval(0, 2, closed='both').covers(idx), np.array([0]))
        tm.assert_numpy_array_equal(Interval(2, 4, closed='both').covers(idx), np.array([1]))

    @pytest.mark.xfail(reason="new indexing tests for issue 16316")
    def test_interval_overlaps_interval_updated_behavior(self):

        # class Interval:
        #     def overlaps(self, other: Interval) -> bool

        assert Interval(1, 3).overlaps(Interval(1.5, 2.5))
        assert Interval(1, 3).overlaps(Interval(1, 2))
        assert Interval(1, 3).overlaps(Interval(2, 3))
        assert Interval(1, 3).overlaps(Interval(0.5, 2.5))
        assert Interval(1, 3).overlaps(Interval(1.5, 3.5))

        assert not Interval(1, 3).overlaps(Interval(-1, 1))
        assert not Interval(1, 3).overlaps(Interval(3, 5))

        # right
        assert Interval(1, 3, closed='right').overlaps(Interval(1, 3, closed='right'))
        assert Interval(1, 3, closed='right').overlaps(Interval(1, 3, closed='left'))
        assert Interval(1, 3, closed='right').overlaps(Interval(1, 3, closed='both'))

        assert not Interval(1, 3, closed='right').overlaps(Interval(-1, 1, closed='right'))
        assert not Interval(1, 3, closed='right').overlaps(Interval(-1, 1, closed='left'))
        assert not Interval(1, 3, closed='right').overlaps(Interval(-1, 1, closed='both'))

        assert not Interval(1, 3, closed='right').overlaps(Interval(3, 5, closed='right'))
        assert Interval(1, 3, closed='right').overlaps(Interval(3, 5, closed='left'))
        assert Interval(1, 3, closed='right').overlaps(Interval(3, 5, closed='both'))

        # left
        assert Interval(1, 3, closed='left').overlaps(Interval(1, 3, closed='right'))
        assert Interval(1, 3, closed='left').overlaps(Interval(1, 3, closed='left'))
        assert Interval(1, 3, closed='left').overlaps(Interval(1, 3, closed='both'))

        assert not Interval(1, 3, closed='left').overlaps(Interval(-1, 1, closed='right'))
        assert not Interval(1, 3, closed='left').overlaps(Interval(-1, 1, closed='left'))
        assert not Interval(1, 3, closed='left').overlaps(Interval(-1, 1, closed='both'))

        assert not Interval(1, 3, closed='left').overlaps(Interval(3, 5, closed='right'))
        assert Interval(1, 3, closed='left').overlaps(Interval(3, 5, closed='left'))
        assert Interval(1, 3, closed='left').overlaps(Interval(3, 5, closed='both'))

        # both
        assert Interval(1, 3, closed='both').overlaps(Interval(1, 3, closed='right'))
        assert Interval(1, 3, closed='both').overlaps(Interval(1, 3, closed='left'))
        assert Interval(1, 3, closed='both').overlaps(Interval(1, 3, closed='both'))

        assert Interval(1, 3, closed='both').overlaps(Interval(-1, 1, closed='right'))
        assert not Interval(1, 3, closed='both').overlaps(Interval(-1, 1, closed='left'))
        assert Interval(1, 3, closed='both').overlaps(Interval(-1, 1, closed='both'))

        assert not Interval(1, 3, closed='both').overlaps(Interval(3, 5, closed='right'))
        assert Interval(1, 3, closed='both').overlaps(Interval(3, 5, closed='left'))
        assert Interval(1, 3, closed='both').overlaps(Interval(3, 5, closed='both'))

    @pytest.mark.xfail(reason="new indexing tests for issue 16316")
    def test_interval_overlaps_intervalIndex_updated_behavior(self):

        # class Interval:
        #     def overlaps(self, other: IntervalIndex) -> IntegerArray1D

        idx = IntervalIndex.from_tuples([(0, 1), (2, 3), (1, 3)], closed='right')

        tm.assert_numpy_array_equal(Interval(1, 3, closed='right').overlaps(idx), np.array([1, 2]))
        tm.assert_numpy_array_equal(Interval(1, 2, closed='right').overlaps(idx), np.array([2]))
        tm.assert_numpy_array_equal(Interval(0, 2, closed='right').overlaps(idx), np.array([0, 2]))
        tm.assert_numpy_array_equal(Interval(3, 4, closed='right').overlaps(idx), np.array([]))

        tm.assert_numpy_array_equal(Interval(1, 3, closed='left').overlaps(idx), np.array([0, 1, 2]))
        tm.assert_numpy_array_equal(Interval(1, 2, closed='left').overlaps(idx), np.array([0, 2]))
        tm.assert_numpy_array_equal(Interval(0, 2, closed='left').overlaps(idx), np.array([0, 2]))
        tm.assert_numpy_array_equal(Interval(3, 4, closed='left').overlaps(idx), np.array([3]))

        tm.assert_numpy_array_equal(Interval(1, 3, closed='both').overlaps(idx), np.array([0, 1, 2]))
        tm.assert_numpy_array_equal(Interval(1, 2, closed='both').overlaps(idx), np.array([0, 2]))
        tm.assert_numpy_array_equal(Interval(0, 2, closed='both').overlaps(idx), np.array([0, 2]))
        tm.assert_numpy_array_equal(Interval(3, 4, closed='both').overlaps(idx), np.array([3]))

    @pytest.mark.xfail(reason="new indexing tests for issue 16316")
    def test_intervalIndex_covers_interval_updated_behavior(self):

        # class IntervalIndex:
        #     def covers(self, other: Interval) -> IntegerArray1D

        idx = IntervalIndex.from_tuples([(0, 1), (2, 3), (1, 3)], closed='right')

        tm.assert_numpy_array_equal(idx.covers(Interval(1, 3, closed='right')), np.array([1, 2]))
        tm.assert_numpy_array_equal(idx.covers(Interval(0, 3, closed='right')), np.array([0, 1, 2]))
        tm.assert_numpy_array_equal(idx.covers(Interval(0, 2, closed='right')), np.array([0]))
        tm.assert_numpy_array_equal(idx.covers(Interval(2, 4, closed='right')), np.array([1]))

        tm.assert_numpy_array_equal(idx.covers(Interval(1, 3, closed='left')), np.array([]))
        tm.assert_numpy_array_equal(idx.covers(Interval(0, 3, closed='left')), np.array([0]))
        tm.assert_numpy_array_equal(idx.covers(Interval(0, 2, closed='left')), np.array([0]))
        tm.assert_numpy_array_equal(idx.covers(Interval(2, 4, closed='left')), np.array([1]))

        tm.assert_numpy_array_equal(idx.covers(Interval(1, 3, closed='both')), np.array([1, 2]))
        tm.assert_numpy_array_equal(idx.covers(Interval(0, 5, closed='both')), np.array([0, 1, 2]))
        tm.assert_numpy_array_equal(idx.covers(Interval(0, 2, closed='both')), np.array([0]))
        tm.assert_numpy_array_equal(idx.covers(Interval(2, 4, closed='both')), np.array([1]))

    @pytest.mark.xfail(reason="new indexing tests for issue 16316")
    def test_intervalIndex_covers_intervalIndex(self):

        # class IntervalIndex:
        #     def covers(self, other: IntervalIndex) -> Tuple[IntegerArray1D, IntegerArray1D]

        idx1 = IntervalIndex.from_tuples([(0, 1), (2, 3), (1, 3)], closed='right')
        idx2 = IntervalIndex.from_tuples([(0, 1), (2, 3), (1, 3)], closed='left')
        idx3 = IntervalIndex.from_tuples([(0, 1), (2, 3), (1, 3)], closed='both')

        self._compare_tuple_of_numpy_array(idx.covers(idx1), (np.array([0,1,2,2]), np.array([0,1,1,2])))
        self._compare_tuple_of_numpy_array(idx.covers(idx2), (np.array([2]), np.array([1])))
        self._compare_tuple_of_numpy_array(idx.covers(idx3), (np.array([0,1,2,2]), np.array([0,1,1,2])))

    @pytest.mark.xfail(reason="new indexing tests for issue 16316")
    def test_intervalIndex_overlaps_interval_updated_behavior(self):

        # class IntervalIndex:
        #     def overlaps(self, other: Interval) -> IntegerArray1D

        idx = IntervalIndex.from_tuples([(0, 1), (2, 3), (1, 3)], closed='right')

        tm.assert_numpy_array_equal(idx.overlaps(Interval(1, 3, closed='right')), np.array([1, 2]))
        tm.assert_numpy_array_equal(idx.overlaps(Interval(1, 2, closed='right')), np.array([2]))
        tm.assert_numpy_array_equal(idx.overlaps(Interval(0, 2, closed='right')), np.array([0, 2]))
        tm.assert_numpy_array_equal(idx.overlaps(Interval(3, 4, closed='right')), np.array([]))

        tm.assert_numpy_array_equal(idx.overlaps(Interval(1, 3, closed='left')), np.array([0, 1, 2]))
        tm.assert_numpy_array_equal(idx.overlaps(Interval(1, 2, closed='left')), np.array([0, 2]))
        tm.assert_numpy_array_equal(idx.overlaps(Interval(0, 2, closed='left')), np.array([0, 2]))
        tm.assert_numpy_array_equal(idx.overlaps(Interval(3, 4, closed='left')), np.array([3]))

        tm.assert_numpy_array_equal(idx.overlaps(Interval(1, 3, closed='both')), np.array([0, 1, 2]))
        tm.assert_numpy_array_equal(idx.overlaps(Interval(1, 2, closed='both')), np.array([0, 2]))
        tm.assert_numpy_array_equal(idx.overlaps(Interval(0, 2, closed='both')), np.array([0, 2]))
        tm.assert_numpy_array_equal(idx.overlaps(Interval(3, 4, closed='both')), np.array([3]))

    @pytest.mark.xfail(reason="new indexing tests for issue 16316")
    def test_intervalIndex_overlaps_intervalIndex_updated_behavior(self):

        # class IntervalIndex:
        #     def overlaps(self, other: IntervalIndex) -> Tuple[IntegerArray1D, IntegerArray1D]

        idx1 = IntervalIndex.from_tuples([(0, 1), (2, 3), (1, 3)], closed='right')
        idx2 = IntervalIndex.from_tuples([(0, 1), (2, 3), (1, 3)], closed='left')
        idx3 = IntervalIndex.from_tuples([(0, 1), (2, 3), (1, 3)], closed='both')

        self._compare_tuple_of_numpy_array(idx.overlaps(idx1), (np.array([0,1,2,2]), np.array([0,1,1,2])))
        self._compare_tuple_of_numpy_array(idx.overlaps(idx2), (np.array([0,0,1,1,2,2]), np.array([0,2,1,2,1,2])))
        self._compare_tuple_of_numpy_array(idx.overlaps(idx3), (np.array([0,0,1,1,2,2]), np.array([0,2,1,2,1,2])))



