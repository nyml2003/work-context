from __future__ import annotations

"""命令层通用返回模型。"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class InitializationPayload:
    """`init` 命令返回体。"""

    created: list[str]
    root: str


@dataclass(frozen=True, slots=True)
class CreatedPathPayload:
    """通用创建结果。"""

    created: str


@dataclass(frozen=True, slots=True)
class ArchivePathPayload:
    """归档输出结果。"""

    archive: str


__all__ = ["ArchivePathPayload", "CreatedPathPayload", "InitializationPayload"]
