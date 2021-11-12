from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from pandas._typing import ArrayLike

from pandas.core.dtypes.common import is_sparse
from pandas.core.dtypes.missing import (
    isna,
    na_value_for_dtype,
)

from pandas.core.nanops import nanpercentile

if TYPE_CHECKING:
    from pandas.core.arrays import ExtensionArray


def quantile_compat(values: ArrayLike, qs: np.ndarray, interpolation: str) -> ArrayLike:
    """
    Compute the quantiles of the given values for each quantile in `qs`.

    Parameters
    ----------
    values : np.ndarray or ExtensionArray
    qs : np.ndarray[float64]
    interpolation : str

    Returns
    -------
    np.ndarray or ExtensionArray
    """
    if isinstance(values, np.ndarray):
        fill_value = na_value_for_dtype(values.dtype, compat=False)
        mask = isna(values)
        return quantile_with_mask(values, mask, fill_value, qs, interpolation)
    else:
        # In general we don't want to import from arrays here;
        #  this is temporary pending discussion in GH#41428
        from pandas.core.arrays import BaseMaskedArray

        if isinstance(values, BaseMaskedArray):
            # e.g. IntegerArray, does not implement _from_factorized
            return values._quantile(qs, interpolation)

        else:
            out = _quantile_ea_compat(values, qs, interpolation)

        return out


def quantile_with_mask(
    values: np.ndarray,
    mask: np.ndarray,
    fill_value,
    qs: np.ndarray,
    interpolation: str,
) -> np.ndarray:
    """
    Compute the quantiles of the given values for each quantile in `qs`.

    Parameters
    ----------
    values : np.ndarray
        For ExtensionArray, this is _values_for_factorize()[0]
    mask : np.ndarray[bool]
        mask = isna(values)
        For ExtensionArray, this is computed before calling _value_for_factorize
    fill_value : Scalar
        The value to interpret fill NA entries with
        For ExtensionArray, this is _values_for_factorize()[1]
    qs : np.ndarray[float64]
    interpolation : str
        Type of interpolation

    Returns
    -------
    np.ndarray

    Notes
    -----
    Assumes values is already 2D.  For ExtensionArray this means np.atleast_2d
    has been called on _values_for_factorize()[0]

    Quantile is computed along axis=1.
    """
    assert values.ndim == 2

    is_empty = values.shape[1] == 0

    if is_empty:
        # create the array of na_values
        # 2d len(values) * len(qs)
        flat = np.array([fill_value] * len(qs))
        result = np.repeat(flat, len(values)).reshape(len(values), len(qs))
    else:
        # asarray needed for Sparse, see GH#24600
        result = nanpercentile(
            values,
            np.array(qs) * 100,
            na_value=fill_value,
            mask=mask,
            interpolation=interpolation,
        )

        result = np.array(result, copy=False)
        result = result.T

    return result


def _quantile_ea_compat(
    values: ExtensionArray, qs: np.ndarray, interpolation: str
) -> ExtensionArray:
    """
    ExtensionArray compatibility layer for quantile_with_mask.

    We pretend that an ExtensionArray with shape (N,) is actually (1, N,)
    for compatibility with non-EA code.

    Parameters
    ----------
    values : ExtensionArray
    qs : np.ndarray[float64]
    interpolation: str

    Returns
    -------
    ExtensionArray
    """
    # TODO(EA2D): make-believe not needed with 2D EAs
    orig = values

    # asarray needed for Sparse, see GH#24600
    mask = np.asarray(values.isna())
    mask = np.atleast_2d(mask)

    arr, fill_value = values._values_for_factorize()
    arr = np.atleast_2d(arr)

    result = quantile_with_mask(arr, mask, fill_value, qs, interpolation)

    if not is_sparse(orig.dtype):
        # shape[0] should be 1 as long as EAs are 1D

        if orig.ndim == 2:
            # i.e. DatetimeArray
            result = type(orig)._from_factorized(result, orig)

        else:
            assert result.shape == (1, len(qs)), result.shape
            result = type(orig)._from_factorized(result[0], orig)

    # error: Incompatible return value type (got "ndarray", expected "ExtensionArray")
    return result  # type: ignore[return-value]
