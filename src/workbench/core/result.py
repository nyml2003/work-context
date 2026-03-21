from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, TypeAlias, TypeVar, cast


T = TypeVar("T")
U = TypeVar("U")
E = TypeVar("E")
F = TypeVar("F")

_MISSING = object()


@dataclass(frozen=True)
class Option(Generic[T]):
    _value: object = _MISSING

    @classmethod
    def some(cls, value: T) -> "Option[T]":
        return cls(value)

    @classmethod
    def none(cls) -> "Option[T]":
        return cls()

    @property
    def is_some(self) -> bool:
        return self._value is not _MISSING

    @property
    def is_none(self) -> bool:
        return self._value is _MISSING

    @property
    def value(self) -> T:
        if self.is_none:
            raise RuntimeError("Option has no value")
        return cast(T, self._value)

    def map(self, mapper: Callable[[T], U]) -> "Option[U]":
        if self.is_none:
            return Option.none()
        return Option.some(mapper(self.value))

    def and_then(self, mapper: Callable[[T], "Option[U]"]) -> "Option[U]":
        if self.is_none:
            return Option.none()
        return mapper(self.value)

    def unwrap_or(self, default: T) -> T:
        if self.is_none:
            return default
        return self.value

    def to_result(self, error: E) -> "Result[T, E]":
        if self.is_none:
            return Result.err(error)
        return Result.ok(self.value)


@dataclass(frozen=True)
class Result(Generic[T, E]):
    _state: str
    _payload: object

    @classmethod
    def ok(cls, value: T) -> "Result[T, E]":
        return cls("ok", value)

    @classmethod
    def err(cls, error: E) -> "Result[T, E]":
        return cls("err", error)

    @property
    def is_ok(self) -> bool:
        return self._state == "ok"

    @property
    def is_err(self) -> bool:
        return self._state == "err"

    @property
    def value(self) -> T:
        if self.is_err:
            raise RuntimeError("Result has no value")
        return cast(T, self._payload)

    @property
    def error(self) -> E:
        if self.is_ok:
            raise RuntimeError("Result has no error")
        return cast(E, self._payload)

    def map(self, mapper: Callable[[T], U]) -> "Result[U, E]":
        if self.is_err:
            return Result.err(self.error)
        return Result.ok(mapper(self.value))

    def map_err(self, mapper: Callable[[E], F]) -> "Result[T, F]":
        if self.is_ok:
            return Result.ok(self.value)
        return Result.err(mapper(self.error))

    def and_then(self, mapper: Callable[[T], "Result[U, E]"]) -> "Result[U, E]":
        if self.is_err:
            return Result.err(self.error)
        return mapper(self.value)

    def unwrap_or(self, default: T) -> T:
        if self.is_err:
            return default
        return self.value


AppResult: TypeAlias = Result[T, "AppError"]


def some(value: T) -> Option[T]:
    return Option.some(value)


def none() -> Option[T]:
    return Option.none()


def ok(value: T) -> Result[T, E]:
    return Result.ok(value)


def err(error: E) -> Result[T, E]:
    return Result.err(error)
