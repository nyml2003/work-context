from __future__ import annotations

from importlib import import_module
from pkgutil import iter_modules
from types import ModuleType

from ..core import Result
from ..domain.errors import AppError, AppErrorCode, app_error
from .base import CommandGroup


def command_modules() -> list[ModuleType]:
    modules: list[ModuleType] = []
    for module_info in iter_modules(__path__):
        if module_info.name == "base":
            continue
        modules.append(import_module(f"{__name__}.{module_info.name}"))
    return modules


def load_command_groups() -> Result[tuple[CommandGroup, ...], AppError]:
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
