from __future__ import annotations

"""CLI 进程入口。

这里只保留启动编排和统一输出协议，不承载业务规则本身。
"""

import argparse
from pathlib import Path
from typing import Any

from .commands import load_command_groups
from .commands.base import CommandGroup, ParserFactory
from .composition import RuntimeContext
from .domain.errors import AppError, AppErrorCode, app_error
from .infrastructure.report_output import to_json_text


def repo_root() -> Path:
    """将当前工作目录视为 CLI 的仓库根。"""

    return Path.cwd()


def print_payload(payload: Any) -> None:
    """统一输出 JSON，保证所有命令的机器可读边界一致。"""

    print(to_json_text(payload))


def print_error(error: AppError) -> int:
    """将领域错误规范化为统一的 CLI 失败载荷。"""

    print_payload({"ok": False, "err": error.to_dict()})
    return 1


def print_success(payload: Any) -> None:
    """将成功结果包装成统一协议。"""

    print_payload({"ok": True, "value": payload})


def dispatch(group: CommandGroup, args: argparse.Namespace, runtime: RuntimeContext) -> int:
    """把解析后的参数交给命令组，并统一处理 Result 输出。"""

    result = group.run(args, runtime)
    if result.is_err:
        return print_error(result.error)
    print_success(result.value.payload)
    return result.value.exit_code


def main(argv: list[str] | None = None) -> int:
    """CLI 主入口。

    启动链路固定为：加载命令组、构建 parser、创建 runtime、分发到命令组。
    """

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
