from __future__ import annotations

import ast
import json
import re
from typing import Any

from .core import Result
from .domain.errors import AppError, AppErrorCode, app_error


class YamlError(ValueError):
    pass


def _clean_lines(content: str) -> list[str]:
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


def _indent_of(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _parse_scalar(text: str) -> Any:
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


def _parse_block(lines: list[str], index: int, indent: int) -> tuple[Any, int]:
    if index >= len(lines):
        return {}, index
    current = lines[index]
    if _indent_of(current) < indent:
        return {}, index
    if current[indent:].startswith("- "):
        return _parse_sequence(lines, index, indent)
    return _parse_mapping(lines, index, indent)


def _parse_mapping(lines: list[str], index: int, indent: int) -> tuple[dict[str, Any], int]:
    mapping: dict[str, Any] = {}
    while index < len(lines):
        line = lines[index]
        current_indent = _indent_of(line)
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
            mapping[key] = _parse_scalar(remainder)
            continue
        if index < len(lines) and _indent_of(lines[index]) > indent:
            child_indent = _indent_of(lines[index])
            if child_indent != indent + 2:
                raise YamlError(f"Expected 2-space indentation under '{key}'")
            mapping[key], index = _parse_block(lines, index, indent + 2)
            continue
        mapping[key] = {}
    return mapping, index


def _parse_sequence(lines: list[str], index: int, indent: int) -> tuple[list[Any], int]:
    items: list[Any] = []
    while index < len(lines):
        line = lines[index]
        current_indent = _indent_of(line)
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
            if index < len(lines) and _indent_of(lines[index]) > indent:
                child_indent = _indent_of(lines[index])
                if child_indent != indent + 2:
                    raise YamlError("Sequence children must use 2-space indentation")
                value, index = _parse_block(lines, index, indent + 2)
                items.append(value)
            else:
                items.append(None)
            continue
        if re.match(r"^[A-Za-z0-9_-]+:\s*.*$", remainder) and not remainder.startswith(("'", '"')):
            key, _, value_text = remainder.partition(":")
            item: dict[str, Any] = {key.strip(): _parse_scalar(value_text.strip()) if value_text.strip() else {}}
            if index < len(lines) and _indent_of(lines[index]) > indent:
                child_indent = _indent_of(lines[index])
                if child_indent != indent + 2:
                    raise YamlError("Sequence mapping entries must use 2-space indentation")
                extra, index = _parse_mapping(lines, index, indent + 2)
                item.update(extra)
            items.append(item)
            continue
        items.append(_parse_scalar(remainder))
    return items, index


def loads(content: str) -> Result[Any, AppError]:
    try:
        lines = _clean_lines(content)
        if not lines:
            return Result.ok({})
        parsed, index = _parse_block(lines, 0, 0)
        if index != len(lines):
            raise YamlError("Trailing YAML content could not be parsed")
    except YamlError as exc:
        return Result.err(app_error(AppErrorCode.PARSE_ERROR, str(exc)))
    return Result.ok(parsed)


def _format_scalar(value: Any, *, quote_strings: bool) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False) if quote_strings else value
    raise YamlError(f"Unsupported YAML scalar type: {type(value)!r}")


def _dump_value(value: Any, indent: int, lines: list[str], *, quote_strings: bool) -> None:
    prefix = " " * indent
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(item, (dict, list)):
                if not item:
                    empty = "{}" if isinstance(item, dict) else "[]"
                    lines.append(f"{prefix}{key}: {empty}")
                else:
                    lines.append(f"{prefix}{key}:")
                    _dump_value(item, indent + 2, lines, quote_strings=quote_strings)
            else:
                lines.append(f"{prefix}{key}: {_format_scalar(item, quote_strings=quote_strings)}")
        return
    if isinstance(value, list):
        for item in value:
            if isinstance(item, (dict, list)):
                lines.append(f"{prefix}-")
                _dump_value(item, indent + 2, lines, quote_strings=quote_strings)
            else:
                lines.append(f"{prefix}- {_format_scalar(item, quote_strings=quote_strings)}")
        return
    lines.append(f"{prefix}{_format_scalar(value, quote_strings=quote_strings)}")


def dumps(value: Any, *, quote_strings: bool = True) -> Result[str, AppError]:
    try:
        lines: list[str] = []
        _dump_value(value, 0, lines, quote_strings=quote_strings)
    except YamlError as exc:
        return Result.err(app_error(AppErrorCode.PARSE_ERROR, str(exc)))
    return Result.ok("\n".join(lines) + "\n")
