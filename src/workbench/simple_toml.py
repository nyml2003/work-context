from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

from .core import Result
from .domain.errors import AppError, AppErrorCode, app_error


class TomlError(ValueError):
    pass


def _strip_comment(line: str) -> str:
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


def _ensure_table(root: dict[str, Any], dotted_path: list[str]) -> dict[str, Any]:
    current = root
    for part in dotted_path:
        next_value = current.setdefault(part, {})
        if not isinstance(next_value, dict):
            raise TomlError(f"Cannot redefine scalar as table: {'.'.join(dotted_path)}")
        current = next_value
    return current


def _parse_value(raw: str) -> Any:
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
    try:
        data: dict[str, Any] = {}
        current = data
        for index, raw_line in enumerate(content.splitlines(), start=1):
            line = _strip_comment(raw_line)
            if not line:
                continue
            if line.startswith("[") and line.endswith("]"):
                path = [part.strip() for part in line[1:-1].split(".") if part.strip()]
                if not path:
                    raise TomlError(f"Empty table declaration at line {index}")
                current = _ensure_table(data, path)
                continue
            if "=" not in line:
                raise TomlError(f"Invalid TOML statement at line {index}: {raw_line}")
            key, raw_value = line.split("=", 1)
            current[key.strip()] = _parse_value(raw_value)
    except TomlError as exc:
        return Result.err(app_error(AppErrorCode.PARSE_ERROR, str(exc)))
    return Result.ok(data)


def load(path: Path) -> Result[dict[str, Any], AppError]:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        return Result.err(app_error(AppErrorCode.CONFIG_ERROR, str(exc), path=str(path)))
    return loads(content).map_err(lambda error: error.with_context(path=str(path)))


def _format_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return repr(value).replace("'", '"')
    if isinstance(value, list):
        return "[" + ", ".join(_format_value(item) for item in value) + "]"
    raise TomlError(f"Unsupported value type: {type(value)!r}")


def _dump_table(lines: list[str], path: list[str], payload: dict[str, Any]) -> None:
    scalars = [(key, value) for key, value in payload.items() if not isinstance(value, dict)]
    tables = [(key, value) for key, value in payload.items() if isinstance(value, dict)]
    if path:
        lines.append(f"[{'.'.join(path)}]")
    for key, value in scalars:
        lines.append(f"{key} = {_format_value(value)}")
    if scalars or path:
        lines.append("")
    for key, value in tables:
        _dump_table(lines, path + [key], value)


def dumps(payload: dict[str, Any]) -> Result[str, AppError]:
    try:
        lines: list[str] = []
        _dump_table(lines, [], payload)
        while lines and not lines[-1].strip():
            lines.pop()
    except TomlError as exc:
        return Result.err(app_error(AppErrorCode.PARSE_ERROR, str(exc)))
    return Result.ok("\n".join(lines) + "\n")


def dump(path: Path, payload: dict[str, Any]) -> Result[Path, AppError]:
    dumped = dumps(payload)
    if dumped.is_err:
        return Result.err(dumped.error.with_context(path=str(path)))
    try:
        path.write_text(dumped.value, encoding="utf-8")
    except OSError as exc:
        return Result.err(app_error(AppErrorCode.CONFIG_ERROR, str(exc), path=str(path)))
    return Result.ok(path)
