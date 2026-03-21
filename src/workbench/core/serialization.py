from __future__ import annotations

"""统一的序列化边界。

这里负责把 dataclass、Path、Enum 等运行时对象收敛为 JSON/YAML/TOML 可消费的普通数据。
"""

from dataclasses import fields, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Mapping, TypeAlias


JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]


def to_plain_data(value: object) -> JsonValue:
    """把内部对象转换成稳定的普通数据结构。"""

    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Enum):
        return to_plain_data(value.value)
    if is_dataclass(value) and not isinstance(value, type):
        payload: dict[str, JsonValue] = {}
        for field in fields(value):
            payload[field.name] = to_plain_data(getattr(value, field.name))
        return payload
    if isinstance(value, Mapping):
        payload: dict[str, JsonValue] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"Only string keys can be serialized, got {type(key)!r}")
            payload[key] = to_plain_data(item)
        return payload
    if isinstance(value, (list, tuple)):
        return [to_plain_data(item) for item in value]
    raise TypeError(f"Unsupported serializable type: {type(value)!r}")


__all__ = ["JsonScalar", "JsonValue", "to_plain_data"]
