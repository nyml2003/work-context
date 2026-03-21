from __future__ import annotations

"""轻量 YAML 解析与序列化。

这层只处理当前仓库需要的受限 YAML 子集，不承担通用 YAML 兼容承诺。
"""

import ast
import json
import re
from typing import Any

from .result import Result
from ..domain.errors import AppError, AppErrorCode, app_error


class YamlError(ValueError):
    """内部 YAML 解析错误。"""


def clean_lines(content: str) -> list[str]:
    """清理空行和注释，并阻止 tab 缩进。"""

    lines: list[str] = []
    for raw_line in content.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue
        if line.lstrip().startswith("#"):
            continue
        if "\t" in line[: len(line) - len(line.lstrip(" "))]:
            raise YamlError("Tabs are not allowed for indentation")
        lines.append(line)
    return lines


def indent_of(line: str) -> int:
    """返回当前行的空格缩进。"""

    return len(line) - len(line.lstrip(" "))


def parse_yaml_scalar(text: str) -> Any:
    """解析 YAML 标量。"""

    value = text.strip()
    if value in {"true", "false"}:
        return value == "true"
    if value in {"null", "~"}:
        return None
    if re.fullmatch(r"[+-]?\d+", value):
        return int(value)
    if re.fullmatch(r"[+-]?\d+\.\d+", value):
        return float(value)
    if value.startswith(("'", '"', "[", "{")):
        normalized = re.sub(r"\btrue\b", "True", value)
        normalized = re.sub(r"\bfalse\b", "False", normalized)
        normalized = re.sub(r"\bnull\b", "None", normalized)
        try:
            return ast.literal_eval(normalized)
        except (SyntaxError, ValueError) as exc:
            raise YamlError(f"Unsupported scalar: {value}") from exc
    return value


def parse_block(lines: list[str], index: int, indent: int) -> tuple[Any, int]:
    """根据当前缩进决定进入 mapping 还是 sequence。"""

    if index >= len(lines):
        return {}, index
    current = lines[index]
    if indent_of(current) < indent:
        return {}, index
    if current[indent:].startswith("- "):
        return parse_sequence(lines, index, indent)
    return parse_mapping(lines, index, indent)


def parse_mapping(lines: list[str], index: int, indent: int) -> tuple[dict[str, Any], int]:
    """解析 YAML mapping。"""

    mapping: dict[str, Any] = {}
    while index < len(lines):
        line = lines[index]
        current_indent = indent_of(line)
        if current_indent < indent:
            break
        if current_indent != indent:
            raise YamlError(f"Unexpected indentation at line: {line}")
        stripped = line[indent:]
        if stripped.startswith("- "):
            break
        key, separator, remainder = stripped.partition(":")
        if separator != ":" or not key.strip():
            raise YamlError(f"Invalid mapping entry: {line}")
        key = key.strip()
        remainder = remainder.lstrip()
        index += 1
        if remainder:
            mapping[key] = parse_yaml_scalar(remainder)
            continue
        if index < len(lines) and indent_of(lines[index]) > indent:
            child_indent = indent_of(lines[index])
            if child_indent != indent + 2:
                raise YamlError(f"Expected 2-space indentation under '{key}'")
            mapping[key], index = parse_block(lines, index, indent + 2)
            continue
        mapping[key] = {}
    return mapping, index


def parse_sequence(lines: list[str], index: int, indent: int) -> tuple[list[Any], int]:
    """解析 YAML sequence。"""

    items: list[Any] = []
    while index < len(lines):
        line = lines[index]
        current_indent = indent_of(line)
        if current_indent < indent:
            break
        if current_indent != indent:
            raise YamlError(f"Unexpected indentation at line: {line}")
        stripped = line[indent:]
        if not stripped.startswith("- "):
            break
        remainder = stripped[2:].strip()
        index += 1
        if not remainder:
            if index < len(lines) and indent_of(lines[index]) > indent:
                child_indent = indent_of(lines[index])
                if child_indent != indent + 2:
                    raise YamlError("Sequence children must use 2-space indentation")
                value, index = parse_block(lines, index, indent + 2)
                items.append(value)
            else:
                items.append(None)
            continue
        if re.match(r"^[A-Za-z0-9_-]+:\s*.*$", remainder) and not remainder.startswith(("'", '"')):
            key, _, value_text = remainder.partition(":")
            item: dict[str, Any] = {key.strip(): parse_yaml_scalar(value_text.strip()) if value_text.strip() else {}}
            if index < len(lines) and indent_of(lines[index]) > indent:
                child_indent = indent_of(lines[index])
                if child_indent != indent + 2:
                    raise YamlError("Sequence mapping entries must use 2-space indentation")
                extra, index = parse_mapping(lines, index, indent + 2)
                item.update(extra)
            items.append(item)
            continue
        items.append(parse_yaml_scalar(remainder))
    return items, index


def loads(content: str) -> Result[Any, AppError]:
    """把 YAML 文本解析为 Python 值。"""

    try:
        lines = clean_lines(content)
        if not lines:
            return Result.ok({})
        parsed, index = parse_block(lines, 0, 0)
        if index != len(lines):
            raise YamlError("Trailing YAML content could not be parsed")
    except YamlError as exc:
        return Result.err(app_error(AppErrorCode.PARSE_ERROR, str(exc)))
    return Result.ok(parsed)


def format_yaml_scalar(value: Any, *, quote_strings: bool) -> str:
    """把 Python 标量格式化为 YAML 字面量。"""

    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False) if quote_strings else value
    raise YamlError(f"Unsupported YAML scalar type: {type(value)!r}")


def dump_yaml_value(value: Any, indent: int, lines: list[str], *, quote_strings: bool) -> None:
    """递归展开 YAML 值。"""

    prefix = " " * indent
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(item, (dict, list)):
                if not item:
                    empty = "{}" if isinstance(item, dict) else "[]"
                    lines.append(f"{prefix}{key}: {empty}")
                else:
                    lines.append(f"{prefix}{key}:")
                    dump_yaml_value(item, indent + 2, lines, quote_strings=quote_strings)
            else:
                lines.append(f"{prefix}{key}: {format_yaml_scalar(item, quote_strings=quote_strings)}")
        return
    if isinstance(value, list):
        for item in value:
            if isinstance(item, (dict, list)):
                lines.append(f"{prefix}-")
                dump_yaml_value(item, indent + 2, lines, quote_strings=quote_strings)
            else:
                lines.append(f"{prefix}- {format_yaml_scalar(item, quote_strings=quote_strings)}")
        return
    lines.append(f"{prefix}{format_yaml_scalar(value, quote_strings=quote_strings)}")


def dumps(value: Any, *, quote_strings: bool = True) -> Result[str, AppError]:
    """把 Python 值序列化为 YAML 文本。"""

    try:
        lines: list[str] = []
        dump_yaml_value(value, 0, lines, quote_strings=quote_strings)
    except YamlError as exc:
        return Result.err(app_error(AppErrorCode.PARSE_ERROR, str(exc)))
    return Result.ok("\n".join(lines) + "\n")


__all__ = ["YamlError", "dumps", "loads"]
