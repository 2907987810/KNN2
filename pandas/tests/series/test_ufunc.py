import string

import numpy as np
import pytest

import pandas as pd
import pandas.util.testing as tm

UNARY_UFUNCS = [np.positive, np.floor, np.exp]
BINARY_UFUNCS = [
    np.add,  # dunder op
    np.logaddexp,
]
SPARSE = [
    pytest.param(True,
                 marks=pytest.mark.xfail(reason="Series.__array_ufunc__")),
    False,
]
SPARSE_IDS = ['sparse', 'dense']
SHUFFLE = [
    pytest.param(True, marks=pytest.mark.xfail(reason="GH-26945")),
    False
]


@pytest.fixture
def arrays_for_binary_ufunc():
    """
    A pair of random, length-100 integer-dtype arrays, that are mostly 0.
    """
    a1 = np.random.randint(0, 10, 100)
    a2 = np.random.randint(0, 10, 100)
    a1[::3] = 0
    a2[::4] = 0
    return a1, a2


@pytest.mark.parametrize("ufunc", UNARY_UFUNCS)
@pytest.mark.parametrize("sparse", SPARSE, ids=SPARSE_IDS)
def test_unary_ufunc(ufunc, sparse):
    array = np.random.randint(0, 10, 10)
    array[::2] = 0
    if sparse:
        array = pd.SparseArray(array, dtype=pd.SparseDtype('int', 0))

    index = list(string.ascii_letters[:10])
    name = "name"
    series = pd.Series(array, index=index, name=name)

    result = ufunc(series)
    expected = pd.Series(ufunc(array), index=index, name=name)
    tm.assert_series_equal(result, expected)


@pytest.mark.parametrize("ufunc", BINARY_UFUNCS)
@pytest.mark.parametrize("sparse", SPARSE, ids=SPARSE_IDS)
@pytest.mark.parametrize("shuffle", SHUFFLE)
@pytest.mark.parametrize("box_other", [True, False],
                         ids=['other-boxed', 'other-raw'])
@pytest.mark.parametrize("flip", [True, False],
                         ids=['flipped', 'straight'])
def test_binary_ufunc(ufunc, sparse, shuffle, box_other,
                      flip,
                      arrays_for_binary_ufunc):
    # Check the invariant that
    #   ufunc(Series(a), Series(b)) == Series(ufunc(a, b))
    #   with alignment.
    a1, a2 = arrays_for_binary_ufunc
    if sparse:
        a1 = pd.SparseArray(a1, dtype=pd.SparseDtype('int', 0))
        a2 = pd.SparseArray(a2, dtype=pd.SparseDtype('int', 0))

    name = "name"
    # TODO: verify name when the differ? Take the first? Drop?
    s1 = pd.Series(a1, name=name)
    s2 = pd.Series(a2, name=name)

    # handle shufling / alignment
    # If boxing -- ufunc(series, series) -- then we don't need to shuffle
    # the other array for the expected, since we align.
    # If not boxing -- ufunc(series, array) -- then we do need to shuffle
    # the other array, since we *dont'* align
    idx = np.random.permutation(len(s1))
    if box_other and shuffle:
        # ensure we align before applying the ufunc
        s2 = s2.take(idx)
    elif shuffle:
        a2 = a2.take(idx)

    a, b = s1, s2
    c, d = a1, a2

    if flip:
        a, b = b, a
        c, d = d, c

    result = ufunc(a, b)
    expected = pd.Series(ufunc(c, d), name=name)
    tm.assert_series_equal(result, expected)


@pytest.mark.parametrize("ufunc", BINARY_UFUNCS)
@pytest.mark.parametrize("sparse", SPARSE, ids=SPARSE_IDS)
@pytest.mark.parametrize("flip", [True, False])
def test_binary_ufunc_scalar(ufunc, sparse, flip, arrays_for_binary_ufunc):
    array, _ = arrays_for_binary_ufunc
    if sparse:
        array = pd.SparseArray(array)
    other = 2
    series = pd.Series(array, name="name")

    a, b = series, other
    c, d = array, other
    if flip:
        c, d = b, c
        a, b = b, a

    expected = pd.Series(ufunc(a, b), name="name")
    result = pd.Series(ufunc(c, d), name="name")
    tm.assert_series_equal(result, expected)


@pytest.mark.parametrize("ufunc", [np.divmod])  # any others?
@pytest.mark.parametrize("sparse", SPARSE, ids=SPARSE_IDS)
@pytest.mark.parametrize("shuffle", SHUFFLE)
@pytest.mark.filterwarnings("ignore:divide by zero:RuntimeWarning")
def test_multiple_ouput_binary_ufuncs(ufunc, sparse, shuffle,
                                      arrays_for_binary_ufunc):
    a1, a2 = arrays_for_binary_ufunc

    if sparse:
        a1 = pd.SparseArray(a1, dtype=pd.SparseDtype('int', 0))
        a2 = pd.SparseArray(a2, dtype=pd.SparseDtype('int', 0))

    s1 = pd.Series(a1)
    s2 = pd.Series(a2)

    if shuffle:
        # ensure we align before applying the ufunc
        s2 = s2.sample(frac=1)

    expected = ufunc(a1, a2)
    assert isinstance(expected, tuple)

    result = ufunc(s1, s2)
    assert isinstance(result, tuple)
    tm.assert_series_equal(result[0], pd.Series(expected[0]))
    tm.assert_series_equal(result[1], pd.Series(expected[1]))


@pytest.mark.parametrize("sparse", SPARSE, ids=SPARSE_IDS)
def test_multiple_ouput_ufunc(sparse, arrays_for_binary_ufunc):
    array, _ = arrays_for_binary_ufunc

    if sparse:
        array = pd.SparseArray(array)

    series = pd.Series(array, name="name")
    result = np.modf(series)
    expected = np.modf(array)

    assert isinstance(result, tuple)
    assert isinstance(expected, tuple)

    tm.assert_series_equal(result[0], pd.Series(expected[0], name="name"))
    tm.assert_series_equal(result[1], pd.Series(expected[1], name="name"))


@pytest.mark.parametrize("sparse", SPARSE, ids=SPARSE_IDS)
@pytest.mark.parametrize("ufunc", BINARY_UFUNCS)
@pytest.mark.xfail(reason="Series.__array_ufunc__")
def test_binary_ufunc_drops_series_name(ufunc, sparse,
                                        arrays_for_binary_ufunc):
    a1, a2 = arrays_for_binary_ufunc
    s1 = pd.Series(a1, name='a')
    s2 = pd.Series(a2, name='b')

    result = ufunc(s1, s2)
    assert result.name is None
