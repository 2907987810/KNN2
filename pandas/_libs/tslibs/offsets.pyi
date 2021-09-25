from __future__ import annotations
from datetime import datetime
from typing import Any, Tuple, Union
from datetime import timedelta

class BaseOffset:
    def __init__(self, n: int = ..., normalize: bool = ...) -> None: ...
    def __eq__(self, other) -> bool: ...
    def __ne__(self, other) -> bool: ...
    def __hash__(self) -> int: ...
    @property
    def kwds(self) -> dict: ...
    @property
    def base(self) -> BaseOffset: ...
    def __add__(self, other) -> BaseOffset: ...
    def __sub__(self, other) -> BaseOffset: ...
    def __call__(self, other): ...
    def __mul__(self, other): ...
    def __neg__(self) -> BaseOffset: ...
    def copy(self) -> BaseOffset: ...
    def __repr__(self) -> str: ...
    @property
    def name(self) -> str: ...
    @property
    def rule_code(self) -> str: ...
    def freqstr(self) -> str: ...
    # Next one is problematic due to circular imports
    # def apply_index(self, dtindex: DatetimeIndex) -> DatetimeIndex: ...
    def apply_index(self, dtindex): ...
    def _apply_array(self, dtarr) -> None: ...
    def rollback(self, dt: datetime) -> datetime: ...
    def rollforward(self, dt: datetime) -> datetime: ...
    def is_on_offset(self, dt: datetime) -> bool: ...
    def __setstate__(self, state) -> None: ...
    def __getstate__(self): ...
    @property
    def nanos(self) -> int: ...
    def onOffset(self, dt: datetime) -> bool: ...
    def isAnchored(self) -> bool: ...
    def is_anchored(self) -> bool: ...

class SingleConstructorOffset(BaseOffset):
    @classmethod
    def _from_name(cls, suffix=None): ...
    def __reduce__(self): ...

def to_offset(
    freq: Union[str, Tuple, timedelta, BaseOffset, None]
) -> Union[BaseOffset, None]: ...

class Tick(SingleConstructorOffset):
    def __init__(self, n: int = ..., normalize: bool = ...) -> None: ...

class Day(Tick): ...
class Hour(Tick): ...
class Minute(Tick): ...
class Second(Tick): ...
class Milli(Tick): ...
class Micro(Tick): ...
class Nano(Tick): ...

class RelativeDeltaOffset(BaseOffset):
    def __init__(self, n: int = ..., normalize: bool = ..., **kwds: Any) -> None: ...

class BusinessMixin(SingleConstructorOffset): ...
class BusinessDay(BusinessMixin): ...
class BusinessHour(BusinessMixin): ...
class WeekOfMonthMixin(SingleConstructorOffset): ...
class YearOffset(SingleConstructorOffset): ...
class BYearEnd(YearOffset): ...
class BYearBegin(YearOffset): ...
class YearEnd(YearOffset): ...
class YearBegin(YearOffset): ...
class QuarterOffset(SingleConstructorOffset): ...
class BQuarterEnd(QuarterOffset): ...
class BQuarterBegin(QuarterOffset): ...
class QuarterEnd(QuarterOffset): ...
class QuarterBegin(QuarterOffset): ...
class MonthOffset(SingleConstructorOffset): ...
class MonthEnd(MonthOffset): ...
class MonthBegin(MonthOffset): ...
class BusinessMonthEnd(MonthOffset): ...
class BusinessMonthBegin(MonthOffset): ...
class SemiMonthOffset(SingleConstructorOffset): ...
class SemiMonthEnd(SemiMonthOffset): ...
class SemiMonthBegin(SemiMonthOffset): ...
class Week(SingleConstructorOffset): ...
class WeekOfMonth(WeekOfMonthMixin): ...
class LastWeekOfMonth(WeekOfMonthMixin): ...
class FY5253Mixin(SingleConstructorOffset): ...
class FY5253(FY5253Mixin): ...
class FY5253Quarter(FY5253Mixin): ...
class Easter(SingleConstructorOffset): ...
class _CustomBusinessMonth(BusinessMixin): ...
class CustomBusinessDay(BusinessDay): ...
class CustomBusinessHour(BusinessHour): ...
class CustomBusinessMonthEnd(_CustomBusinessMonth): ...
class CustomBusinessMonthBegin(_CustomBusinessMonth): ...
class DateOffset(RelativeDeltaOffset): ...

BDay = BusinessDay
BMonthEnd = BusinessMonthEnd
BMonthBegin = BusinessMonthBegin
CBMonthEnd = CustomBusinessMonthEnd
CBMonthBegin = CustomBusinessMonthBegin
CDay = CustomBusinessDay
