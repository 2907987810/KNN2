from __future__ import annotations

from typing import (
    Any,
    Callable,
    Generic,
    TypeVar,
    overload,
)

F = TypeVar("F")
G = TypeVar("G")

class CachedProperty(Generic[F, G]):
    def __init__(self, func: Callable[[F], G]) -> None: ...
    @overload
    def __get__(self, obj: F, typ) -> G: ...
    @overload
    def __get__(self, obj: None, typ) -> cache_readonly[F, G]: ...
    def __set__(self, obj: F, value: G) -> None: ...

cache_readonly = CachedProperty

AxisProperty: Any
