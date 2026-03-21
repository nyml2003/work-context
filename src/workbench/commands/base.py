from __future__ import annotations

import argparse
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from ..composition import RuntimeContext, ServiceContainer
from ..core import Result
from ..domain.errors import AppError, AppErrorCode, app_error


@dataclass
class CommandResult:
    exit_code: int
    payload: dict[str, Any]


@dataclass(frozen=True)
class ArgumentSpec:
    flags: tuple[str, ...]
    kwargs: dict[str, Any] = field(default_factory=dict)

    @property
    def is_option(self) -> bool:
        return any(flag.startswith("-") for flag in self.flags)

    @property
    def dest(self) -> str:
        if "dest" in self.kwargs:
            return str(self.kwargs["dest"])
        primary = self.flags[-1] if self.is_option else self.flags[0]
        return primary.lstrip("-").replace("-", "_")


@dataclass(frozen=True)
class CommandSpec:
    name: str
    help: str
    arguments: tuple[ArgumentSpec, ...] = ()
    subcommands: tuple["CommandSpec", ...] = ()
    subcommand_dest: str | None = None


class CommandGroup(ABC):
    name: str
    order: int = 100

    @property
    @abstractmethod
    def spec(self) -> CommandSpec:
        raise NotImplementedError

    @abstractmethod
    def run(self, args: Any, runtime: RuntimeContext) -> Result[CommandResult, AppError]:
        raise NotImplementedError

    def subcommand(self, args: Any) -> str | None:
        current = self.spec
        while current.subcommands:
            if current.subcommand_dest is None:
                return None
            value = getattr(args, current.subcommand_dest, None)
            if value is None:
                return None
            child = next((item for item in current.subcommands if item.name == value), None)
            if child is None:
                return value
            current = child
        return None


class ParserFactory:
    def build(self, *, prog: str, description: str, groups: tuple[CommandGroup, ...]) -> Result[argparse.ArgumentParser, AppError]:
        parser = argparse.ArgumentParser(prog=prog, description=description)
        subparsers = parser.add_subparsers(dest="command", required=True)
        validated = self.validate_group_names(groups)
        if validated.is_err:
            return Result.err(validated.error)
        for group in groups:
            registered = self.register_spec(subparsers, group.spec, ancestor_dests={"command"}, path=(group.spec.name,))
            if registered.is_err:
                return Result.err(registered.error)
        return Result.ok(parser)

    def validate_group_names(self, groups: tuple[CommandGroup, ...]) -> Result[None, AppError]:
        seen: set[str] = set()
        for group in groups:
            if group.name != group.spec.name:
                return Result.err(
                    app_error(AppErrorCode.INVALID_ARGUMENT, f"Command group name mismatch: {group.name} != {group.spec.name}")
                )
            if group.name in seen:
                return Result.err(app_error(AppErrorCode.INVALID_ARGUMENT, f"Duplicate command group name: {group.name}"))
            seen.add(group.name)
        return Result.ok(None)

    def register_spec(
        self,
        subparsers: Any,
        spec: CommandSpec,
        *,
        ancestor_dests: set[str],
        path: tuple[str, ...],
    ) -> Result[None, AppError]:
        parser = subparsers.add_parser(spec.name, help=spec.help)
        validated = self.validate_arguments(spec, ancestor_dests, path)
        if validated.is_err:
            return Result.err(validated.error)
        local_dests = validated.value
        for argument in spec.arguments:
            if not argument.flags:
                return Result.err(app_error(AppErrorCode.INVALID_ARGUMENT, f"Argument missing flags in command {' '.join(path)}"))
            parser.add_argument(*argument.flags, **argument.kwargs)
        if spec.subcommands:
            if not spec.subcommand_dest:
                return Result.err(
                    app_error(
                        AppErrorCode.INVALID_ARGUMENT,
                        f"Command {' '.join(path)} declares subcommands without subcommand_dest",
                    )
                )
            if spec.subcommand_dest in ancestor_dests or spec.subcommand_dest in local_dests:
                return Result.err(
                    app_error(
                        AppErrorCode.INVALID_ARGUMENT,
                        f"Duplicate parser dest '{spec.subcommand_dest}' in command {' '.join(path)}",
                    )
                )
            child_validated = self.validate_child_names(spec, path)
            if child_validated.is_err:
                return Result.err(child_validated.error)
            child_subparsers = parser.add_subparsers(dest=spec.subcommand_dest, required=True)
            next_ancestor_dests = set(ancestor_dests)
            next_ancestor_dests.update(local_dests)
            next_ancestor_dests.add(spec.subcommand_dest)
            for child in spec.subcommands:
                child_result = self.register_spec(child_subparsers, child, ancestor_dests=next_ancestor_dests, path=path + (child.name,))
                if child_result.is_err:
                    return Result.err(child_result.error)
        return Result.ok(None)

    def validate_child_names(self, spec: CommandSpec, path: tuple[str, ...]) -> Result[None, AppError]:
        seen: set[str] = set()
        for child in spec.subcommands:
            if child.name in seen:
                return Result.err(
                    app_error(AppErrorCode.INVALID_ARGUMENT, f"Duplicate subcommand '{child.name}' under {' '.join(path)}")
                )
            seen.add(child.name)
        return Result.ok(None)

    def validate_arguments(self, spec: CommandSpec, ancestor_dests: set[str], path: tuple[str, ...]) -> Result[set[str], AppError]:
        option_flags: set[str] = set()
        positional_names: set[str] = set()
        local_dests: set[str] = set()
        for argument in spec.arguments:
            if not argument.flags:
                return Result.err(app_error(AppErrorCode.INVALID_ARGUMENT, f"Argument missing flags in command {' '.join(path)}"))
            dest = argument.dest
            if dest in ancestor_dests or dest in local_dests:
                return Result.err(
                    app_error(AppErrorCode.INVALID_ARGUMENT, f"Duplicate argument dest '{dest}' in command {' '.join(path)}")
                )
            local_dests.add(dest)
            if argument.is_option:
                for flag in argument.flags:
                    if flag in option_flags:
                        return Result.err(
                            app_error(AppErrorCode.INVALID_ARGUMENT, f"Duplicate option flag '{flag}' in command {' '.join(path)}")
                        )
                    option_flags.add(flag)
            else:
                positional = argument.flags[0]
                if positional in positional_names:
                    return Result.err(
                        app_error(
                            AppErrorCode.INVALID_ARGUMENT,
                            f"Duplicate positional argument '{positional}' in command {' '.join(path)}",
                        )
                    )
                positional_names.add(positional)
        return Result.ok(local_dests)
