import warnings

import pytest

import pandas as pd
import pandas._testing as tm
from pandas.api.types import is_numeric_dtype
from pandas.tests.extension.base.base import BaseExtensionTests


class BaseReduceTests(BaseExtensionTests):
    """
    Reduction specific tests. Generally these only
    make sense for numeric/boolean operations.
    """

    def _supports_reduction(self, obj, op_name: str) -> bool:
        # Specify if we expect this reduction to succeed.
        return False

    def check_reduce(self, s, op_name, skipna):
        res_op = getattr(s, op_name)
        exp_op = getattr(s.astype("float64"), op_name)
        if op_name == "count":
            result = res_op()
            expected = exp_op()
        else:
            result = res_op(skipna=skipna)
            expected = exp_op(skipna=skipna)
        tm.assert_almost_equal(result, expected)

    @pytest.mark.parametrize("skipna", [True, False])
    def test_reduce_series_boolean(self, data, all_boolean_reductions, skipna):
        op_name = all_boolean_reductions
        s = pd.Series(data)

        if not self._supports_reduction(s, op_name):
            msg = (
                "[Cc]annot perform|Categorical is not ordered for operation|"
                "does not support reduction|"
            )

            with pytest.raises(TypeError, match=msg):
                getattr(s, op_name)(skipna=skipna)

        else:
            self.check_reduce(s, op_name, skipna)

    @pytest.mark.parametrize("skipna", [True, False])
    def test_reduce_series_numeric(self, data, all_numeric_reductions, skipna):
        op_name = all_numeric_reductions
        s = pd.Series(data)

        if not self._supports_reduction(s, op_name):
            msg = (
                "[Cc]annot perform|Categorical is not ordered for operation|"
                "does not support reduction|"
            )

            with pytest.raises(TypeError, match=msg):
                getattr(s, op_name)(skipna=skipna)

        else:
            # min/max with empty produce numpy warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                self.check_reduce(s, op_name, skipna)

    @pytest.mark.parametrize("skipna", [True, False])
    def test_reduce_frame(self, data, all_numeric_reductions, skipna):
        op_name = all_numeric_reductions
        s = pd.Series(data)
        if not is_numeric_dtype(s):
            pytest.skip("not numeric dtype")

        if not self._supports_reduction(s, op_name):
            pytest.skip(f"Reduction {op_name} not supported for this dtype")

        self.check_reduce_frame(s, op_name, skipna)


# TODO: deprecate BaseNoReduceTests, BaseNumericReduceTests, BaseBooleanReduceTests
class BaseNoReduceTests(BaseReduceTests):
    """we don't define any reductions"""


class BaseNumericReduceTests(BaseReduceTests):
    # For backward compatibility only, this only runs the numeric reductions
    def _supports_reduction(self, obj, op_name: str) -> bool:
        if op_name in ["any", "all"]:
            pytest.skip("These are tested in BaseBooleanReduceTests")
        return True


class BaseBooleanReduceTests(BaseReduceTests):
    # For backward compatibility only, this only runs the numeric reductions
    def _supports_reduction(self, obj, op_name: str) -> bool:
        if op_name not in ["any", "all"]:
            pytest.skip("These are tested in BaseNumericReduceTests")
        return True
