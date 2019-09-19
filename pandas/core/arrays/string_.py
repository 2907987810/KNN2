import operator
from typing import Type

import numpy as np

from pandas._libs import lib

from pandas.core.dtypes.base import ExtensionDtype
from pandas.core.dtypes.common import pandas_dtype
from pandas.core.dtypes.dtypes import register_extension_dtype
from pandas.core.dtypes.generic import ABCDataFrame, ABCIndexClass, ABCSeries
from pandas.core.dtypes.inference import is_array_like

from pandas.core import ops
from pandas.core.arrays import PandasArray
from pandas.core.construction import extract_array


@register_extension_dtype
class StringDtype(ExtensionDtype):
    """
    Extension dtype for text data.

    .. versionadded:: 1.0.0

    Attributes
    ----------
    None

    Methods
    -------
    None

    Examples
    --------
    >>> pd.StringDtype()
    StringDtype
    """

    @property
    def na_value(self):
        """
        StringDtype uses :attr:`numpy.nan` as the missing NA value.
        """
        return np.nan

    @property
    def type(self) -> Type:
        return str

    @property
    def name(self) -> str:
        """
        The alias for StringDtype is ``'string'``.
        """
        return "string"

    @classmethod
    def construct_from_string(cls, string: str) -> ExtensionDtype:
        if string == "string":
            return cls()
        return super().construct_from_string(string)

    @classmethod
    def construct_array_type(cls) -> "Type[StringArray]":
        return StringArray

    def __repr__(self) -> str:
        return "StringDtype"


class StringArray(PandasArray):
    """
    Extension array for text data.

    .. versionadded:: 1.0.0

    .. warning::

       StringArray is considered experimental. The implementation and
       parts of the API may change without warning.

    Parameters
    ----------
    values : array-like
        The array of data.

        .. warning::

           Currently, this expects an object-dtype ndarray
           where the elements are Python strings. This may
           change without warning in the future.
    copy : bool, default False
        Whether to copy the array of data.

    Attributes
    ----------
    None

    Methods
    -------
    None

    See Also
    --------
    Series.str
        The string methods are available on Series backed by
        a StringArray.

    Examples
    --------
    >>> pd.array(['This is', 'some text', None, 'data.'], dtype="string")
    <StringArray>
    ['This is', 'some text', nan, 'data.']
    Length: 4, dtype: string

    Unlike ``object`` dtype arrays, ``StringArray`` doesn't allow non-string
    values.

    >>> pd.array(['1', 1], dtype="string")
    Traceback (most recent call last):
    ...
    ValueError: Must provide strings
    """

    # undo the PandasArray hack
    _typ = "extension"

    def __init__(self, values, copy=False):
        super().__init__(values, copy=copy)
        self._dtype = StringDtype()
        self._validate()

    def _validate(self):
        """Validate that we only store NA or strings."""
        if len(self._ndarray) and not lib.is_string_array(self._ndarray, skipna=True):
            raise ValueError("StringArray requires an object-dtype ndarray of strings.")
        if self._ndarray.dtype != "object":
            raise ValueError(
                "StringArray requires an object-dtype ndarray. Got "
                "'{}' instead.".format(self._ndarray.dtype)
            )

    @classmethod
    def _from_sequence(cls, scalars, dtype=None, copy=False):
        if dtype:
            assert dtype == "string"
        result = super()._from_sequence(scalars, dtype=object, copy=copy)
        # convert None to np.nan
        # TODO: it would be nice to do this in _validate / lib.is_string_array
        # We are already doing a scan over the values there.
        result[result.isna()] = np.nan
        return result

    @classmethod
    def _from_sequence_of_strings(cls, strings, dtype=None, copy=False):
        return cls._from_sequence(strings, dtype=dtype, copy=copy)

    def __setitem__(self, key, value):
        value = extract_array(value, extract_numpy=True)
        if isinstance(value, type(self)):
            # extract_array doesn't extract PandasArray subclasses
            value = value._ndarray

        scalar_key = lib.is_scalar(key)
        scalar_value = lib.is_scalar(value)
        if scalar_key and not scalar_value:
            raise ValueError("setting an array element with a sequence.")

        # validate new items
        if scalar_value:
            if scalar_value is None:
                value = np.nan
            elif not (isinstance(value, str) or np.isnan(value)):
                raise ValueError(
                    "Cannot set value '{}' into a StringArray.".format(value)
                )
        else:
            if not is_array_like(value):
                value = np.asarray(value, dtype=object)
            if len(value) and not lib.is_string_array(value, skipna=True):
                raise ValueError("Must provide strings.")

        super().__setitem__(key, value)

    def fillna(self, value=None, method=None, limit=None):
        # TODO: validate dtype
        return super().fillna(value, method, limit)

    def astype(self, dtype, copy=True):
        dtype = pandas_dtype(dtype)
        if isinstance(dtype, StringDtype):
            if copy:
                return self.copy()
            return self
        return super().astype(dtype, copy)

    def __add__(self, other):
        return _add(self, other, operator.add)

    def __radd__(self, other):
        return _add(self, other, ops.radd)

    def _reduce(self, name, skipna=True, **kwargs):
        raise TypeError("Cannot perform reduction '{}' with string dtype".format(name))

    def value_counts(self, dropna=False):
        from pandas import value_counts

        return value_counts(self._ndarray, dropna=dropna)


def _add(array, other, op):
    if isinstance(other, (ABCIndexClass, ABCSeries, ABCDataFrame)):
        return NotImplemented

    mask = array.isna()
    if isinstance(other, type(array)):
        mask |= other.isna()
        other = other._ndarray[~mask]

    valid = ~mask

    out = np.empty_like(array._ndarray, dtype="object")
    out[mask] = np.nan
    out[valid] = op(array._ndarray[valid], other)

    return type(array)(out)
