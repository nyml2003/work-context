from __future__ import annotations

"""轻量 TOML 解析与序列化。

这层只处理字符串级别的格式协议，不负责具体文件路径的读取与写回。
"""

import ast
import re
from typing import Any

from .result import Result
from ..domain.errors import AppError, AppErrorCode, app_error


class TomlError(ValueError):
    """内部 TOML 解析错误。"""


def strip_comment(line: str) -> str:
    """移除 TOML 行内注释，同时保留字符串字面量里的 `#`。"""

    result: list[str] = []
    quote: str | None = None
    escaped = False
    for char in line:
        if quote is not None:
            result.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in ('"', "'"):
            quote = char
            result.append(char)
        elif char == "#":
            break
        else:
            result.append(char)
    return "".join(result).strip()


def ensure_table(root: dict[str, Any], dotted_path: list[str]) -> dict[str, Any]:
    """确保多级 table 路径存在，必要时逐层创建。"""

    current = root
    for part in dotted_path:
        next_value = current.setdefault(part, {})
        if not isinstance(next_value, dict):
            raise TomlError(f"Cannot redefine scalar as table: {'.'.join(dotted_path)}")
        current = next_value
    return current


def parse_toml_value(raw: str) -> Any:
    """解析一个简单 TOML 标量或字面量集合。"""

    text = raw.strip()
    if not text:
        raise TomlError("Empty TOML value")
    if text in {"true", "false"}:
        return text == "true"
    if re.fullmatch(r"[+-]?\d+", text):
        return int(text)
    if re.fullmatch(r"[+-]?\d+\.\d+", text):
        return float(text)
    if text.startswith(("\"", "'", "[", "{")):
        normalized = re.sub(r"\btrue\b", "True", text)
        normalized = re.sub(r"\bfalse\b", "False", normalized)
        try:
            return ast.literal_eval(normalized)
        except (SyntaxError, ValueError) as exc:
            raise TomlError(f"Unsupported TOML value: {text}") from exc
    raise TomlError(f"Unsupported TOML value: {text}")


def loads(content: str) -> Result[dict[str, Any], AppError]:
    """把 TOML 文本解析为 Python 字典。"""

    try:
        data: dict[str, Any] = {}
        current = data
        for index, raw_line in enumerate(content.splitlines(), start=1):
            line = strip_comment(raw_line)
            if not line:
                continue
            if line.startswith("[") and line.endswith("]"):
                path = [part.strip() for part in line[1:-1].split(".") if part.strip()]
                if not path:
                    raise TomlError(f"Empty table declaration at line {index}")
                current = ensure_table(data, path)
                continue
            if "=" not in line:
                raise TomlError(f"Invalid TOML statement at line {index}: {raw_line}")
            key, raw_value = line.split("=", 1)
            current[key.strip()] = parse_toml_value(raw_value)
    except TomlError as exc:
        return Result.err(app_error(AppErrorCode.PARSE_ERROR, str(exc)))
    return Result.ok(data)


def format_toml_value(value: Any) -> str:
    """把 Python 值格式化为 TOML 字面量。"""

    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return repr(value).replace("'", '"')
    if isinstance(value, list):
        return "[" + ", ".join(format_toml_value(item) for item in value) + "]"
    raise TomlError(f"Unsupported value type: {type(value)!r}")


def dump_table(lines: list[str], path: list[str], payload: dict[str, Any]) -> None:
    """递归展开 TOML table。"""

    scalars = [(key, value) for key, value in payload.items() if not isinstance(value, dict)]
    tables = [(key, value) for key, value in payload.items() if isinstance(value, dict)]
    if path:
        lines.append(f"[{'.'.join(path)}]")
    for key, value in scalars:
        lines.append(f"{key} = {format_toml_value(value)}")
    if scalars or path:
        lines.append("")
    for key, value in tables:
        dump_table(lines, path + [key], value)


def dumps(payload: dict[str, Any]) -> Result[str, AppError]:
    """把 Python 字典序列化为 TOML 文本。"""

    try:
        lines: list[str] = []
        dump_table(lines, [], payload)
        while lines and not lines[-1].strip():
            lines.pop()
    except TomlError as exc:
        return Result.err(app_error(AppErrorCode.PARSE_ERROR, str(exc)))
    return Result.ok("\n".join(lines) + "\n")


__all__ = ["TomlError", "dumps", "loads"]
