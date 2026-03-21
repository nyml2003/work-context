from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class AppErrorCode(StrEnum):
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    INVALID_STATE = "INVALID_STATE"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    PATH_OUT_OF_BOUNDARY = "PATH_OUT_OF_BOUNDARY"
    NOT_A_FILE = "NOT_A_FILE"
    NOT_A_DIRECTORY = "NOT_A_DIRECTORY"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    PARSE_ERROR = "PARSE_ERROR"
    CONFIG_ERROR = "CONFIG_ERROR"
    COMMAND_BLOCKED = "COMMAND_BLOCKED"
    EXTERNAL_TOOL_FAILED = "EXTERNAL_TOOL_FAILED"
    NOT_A_GIT_REPOSITORY = "NOT_A_GIT_REPOSITORY"
    REGISTRY_INVALID = "REGISTRY_INVALID"
    UNSUPPORTED_COMMAND = "UNSUPPORTED_COMMAND"
    INTERNAL_ERROR = "INTERNAL_ERROR"


@dataclass(frozen=True)
class AppError:
    code: AppErrorCode
    message: str
    context: dict[str, Any] = field(default_factory=dict)

    def with_context(self, **context: Any) -> "AppError":
        merged = dict(self.context)
        merged.update(context)
        return AppError(self.code, self.message, merged)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code.value,
            "message": self.message,
            "context": self.context,
        }


def app_error(code: AppErrorCode, message: str, **context: Any) -> AppError:
    return AppError(code=code, message=message, context=context)


def from_exception(
    exc: BaseException,
    *,
    default_code: AppErrorCode = AppErrorCode.INTERNAL_ERROR,
    **context: Any,
) -> AppError:
    error_type = exc.__class__.__name__
    message = str(exc) or error_type

    if error_type == "PathBoundaryError":
        return app_error(AppErrorCode.PATH_OUT_OF_BOUNDARY, message, **context)
    if error_type in {"TomlError", "YamlError"}:
        return app_error(AppErrorCode.PARSE_ERROR, message, **context)
    if isinstance(exc, FileExistsError):
        return app_error(AppErrorCode.ALREADY_EXISTS, message, **context)
    if isinstance(exc, FileNotFoundError):
        return app_error(AppErrorCode.NOT_FOUND, message, **context)
    if isinstance(exc, NotADirectoryError):
        return app_error(AppErrorCode.NOT_A_DIRECTORY, message, **context)
    if isinstance(exc, IsADirectoryError):
        return app_error(AppErrorCode.NOT_A_FILE, message, **context)
    if isinstance(exc, ValueError):
        return app_error(AppErrorCode.INVALID_ARGUMENT, message, **context)
    if isinstance(exc, OSError):
        return app_error(default_code, message, **context)
    return app_error(default_code, message, **context)
