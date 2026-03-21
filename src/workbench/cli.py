from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .commands import load_command_groups
from .commands.base import CommandGroup, ParserFactory
from .composition import RuntimeContext
from .domain.errors import AppError, AppErrorCode, app_error
from .report import to_json_text


def repo_root() -> Path:
    return Path.cwd()


def print_payload(payload: Any) -> None:
    print(to_json_text(payload))


def print_error(error: AppError) -> int:
    print_payload({"ok": False, "err": error.to_dict()})
    return 1


def print_success(payload: Any) -> None:
    print_payload({"ok": True, "value": payload})


def dispatch(group: CommandGroup, args: argparse.Namespace, runtime: RuntimeContext) -> int:
    result = group.run(args, runtime)
    if result.is_err:
        return print_error(result.error)
    print_success(result.value.payload)
    return result.value.exit_code


def main(argv: list[str] | None = None) -> int:
    command_groups = load_command_groups()
    if command_groups.is_err:
        return print_error(command_groups.error)
    parser = ParserFactory().build(
        prog="workbench",
        description="Codex skills repository workbench",
        groups=command_groups.value,
    )
    if parser.is_err:
        return print_error(parser.error)
    args = parser.value.parse_args(argv)
    runtime = RuntimeContext(repo_root())
    command_map = {group.name: group for group in command_groups.value}
    group = command_map.get(args.command)
    if group is None:  # pragma: no cover
        return print_error(app_error(AppErrorCode.UNSUPPORTED_COMMAND, f"Unsupported command: {args.command}"))
    return dispatch(group, args, runtime)
