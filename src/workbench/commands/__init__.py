from __future__ import annotations

"""命令组装载入口。

命令模块只需要导出 `COMMAND_GROUP`，这里会负责收集并排序。
"""

from importlib import import_module
from pkgutil import iter_modules
from types import ModuleType

from ..core import Result
from ..domain.errors import AppError, AppErrorCode, app_error
from .base import CommandGroup


def command_modules() -> list[ModuleType]:
    """导入命令包下的命令模块。

    当前采用约定式发现：模块位于 `commands/` 且导出 `COMMAND_GROUP` 即可接入。
    """

    modules: list[ModuleType] = []
    for module_info in iter_modules(__path__):
        if module_info.name == "base":
            continue
        modules.append(import_module(f"{__name__}.{module_info.name}"))
    return modules


def load_command_groups() -> Result[tuple[CommandGroup, ...], AppError]:
    """收集并按稳定顺序返回命令组。"""

    groups: list[CommandGroup] = []
    try:
        modules = command_modules()
    except Exception as exc:
        return Result.err(app_error(AppErrorCode.INTERNAL_ERROR, str(exc), phase="command-import"))
    for module in modules:
        group = getattr(module, "COMMAND_GROUP", None)
        if group is not None:
            groups.append(group)
    return Result.ok(tuple(sorted(groups, key=lambda item: (item.order, item.name))))
