from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from ..core.serialization import JsonValue


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


@dataclass(frozen=True, slots=True)
class AppErrorDetail:
    """错误上下文的强类型载体。

    这里保留的是项目当前真实用到的上下文字段，而不是开放式字典。
    """

    path: str | None = None
    root: str | None = None
    workspace: str | None = None
    skill: str | None = None
    command: str | None = None
    token: str | None = None
    resource: str | None = None
    phase: str | None = None
    cwd: str | None = None
    url: str | None = None
    remote_name: str | None = None
    pattern: str | None = None
    args: list[str] | None = None


@dataclass(frozen=True, slots=True)
class AppErrorPayload:
    """CLI 对外暴露的错误 JSON 结构。"""

    code: str
    message: str
    context: dict[str, JsonValue]


@dataclass(frozen=True)
class AppError:
    code: AppErrorCode
    message: str
    detail: AppErrorDetail | None = None

    def with_context(
        self,
        *,
        path: str | None = None,
        root: str | None = None,
        workspace: str | None = None,
        skill: str | None = None,
        command: str | None = None,
        token: str | None = None,
        resource: str | None = None,
        phase: str | None = None,
        cwd: str | None = None,
        url: str | None = None,
        remote_name: str | None = None,
        pattern: str | None = None,
        args: list[str] | None = None,
    ) -> "AppError":
        merged = merge_error_detail(
            self.detail,
            path=path,
            root=root,
            workspace=workspace,
            skill=skill,
            command=command,
            token=token,
            resource=resource,
            phase=phase,
            cwd=cwd,
            url=url,
            remote_name=remote_name,
            pattern=pattern,
            args=args,
        )
        return AppError(self.code, self.message, merged)

    def to_payload(self) -> AppErrorPayload:
        return AppErrorPayload(
            code=self.code.value,
            message=self.message,
            context=error_detail_to_context(self.detail),
        )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "code": self.code.value,
            "message": self.message,
            "context": error_detail_to_context(self.detail),
        }


def build_error_detail(
    *,
    path: str | None = None,
    root: str | None = None,
    workspace: str | None = None,
    skill: str | None = None,
    command: str | None = None,
    token: str | None = None,
    resource: str | None = None,
    phase: str | None = None,
    cwd: str | None = None,
    url: str | None = None,
    remote_name: str | None = None,
    pattern: str | None = None,
    args: list[str] | None = None,
) -> AppErrorDetail | None:
    detail = AppErrorDetail(
        path=path,
        root=root,
        workspace=workspace,
        skill=skill,
        command=command,
        token=token,
        resource=resource,
        phase=phase,
        cwd=cwd,
        url=url,
        remote_name=remote_name,
        pattern=pattern,
        args=list(args) if args is not None else None,
    )
    return detail if detail != AppErrorDetail() else None


def merge_error_detail(
    current: AppErrorDetail | None,
    *,
    path: str | None = None,
    root: str | None = None,
    workspace: str | None = None,
    skill: str | None = None,
    command: str | None = None,
    token: str | None = None,
    resource: str | None = None,
    phase: str | None = None,
    cwd: str | None = None,
    url: str | None = None,
    remote_name: str | None = None,
    pattern: str | None = None,
    args: list[str] | None = None,
) -> AppErrorDetail | None:
    base = current or AppErrorDetail()
    return build_error_detail(
        path=path if path is not None else base.path,
        root=root if root is not None else base.root,
        workspace=workspace if workspace is not None else base.workspace,
        skill=skill if skill is not None else base.skill,
        command=command if command is not None else base.command,
        token=token if token is not None else base.token,
        resource=resource if resource is not None else base.resource,
        phase=phase if phase is not None else base.phase,
        cwd=cwd if cwd is not None else base.cwd,
        url=url if url is not None else base.url,
        remote_name=remote_name if remote_name is not None else base.remote_name,
        pattern=pattern if pattern is not None else base.pattern,
        args=args if args is not None else base.args,
    )


def error_detail_to_context(detail: AppErrorDetail | None) -> dict[str, JsonValue]:
    """把内部 detail 压平成对外 JSON 结构。"""

    if detail is None:
        return {}
    context: dict[str, JsonValue] = {}
    if detail.path is not None:
        context["path"] = detail.path
    if detail.root is not None:
        context["root"] = detail.root
    if detail.workspace is not None:
        context["workspace"] = detail.workspace
    if detail.skill is not None:
        context["skill"] = detail.skill
    if detail.command is not None:
        context["command"] = detail.command
    if detail.token is not None:
        context["token"] = detail.token
    if detail.resource is not None:
        context["resource"] = detail.resource
    if detail.phase is not None:
        context["phase"] = detail.phase
    if detail.cwd is not None:
        context["cwd"] = detail.cwd
    if detail.url is not None:
        context["url"] = detail.url
    if detail.remote_name is not None:
        context["remote_name"] = detail.remote_name
    if detail.pattern is not None:
        context["pattern"] = detail.pattern
    if detail.args is not None:
        context["args"] = list(detail.args)
    return context


def app_error(
    code: AppErrorCode,
    message: str,
    *,
    path: str | None = None,
    root: str | None = None,
    workspace: str | None = None,
    skill: str | None = None,
    command: str | None = None,
    token: str | None = None,
    resource: str | None = None,
    phase: str | None = None,
    cwd: str | None = None,
    url: str | None = None,
    remote_name: str | None = None,
    pattern: str | None = None,
    args: list[str] | None = None,
) -> AppError:
    return AppError(
        code=code,
        message=message,
        detail=build_error_detail(
            path=path,
            root=root,
            workspace=workspace,
            skill=skill,
            command=command,
            token=token,
            resource=resource,
            phase=phase,
            cwd=cwd,
            url=url,
            remote_name=remote_name,
            pattern=pattern,
            args=args,
        ),
    )


def from_exception(
    exc: BaseException,
    *,
    default_code: AppErrorCode = AppErrorCode.INTERNAL_ERROR,
    path: str | None = None,
    root: str | None = None,
    workspace: str | None = None,
    skill: str | None = None,
    command: str | None = None,
    token: str | None = None,
    resource: str | None = None,
    phase: str | None = None,
    cwd: str | None = None,
    url: str | None = None,
    remote_name: str | None = None,
    pattern: str | None = None,
    args: list[str] | None = None,
) -> AppError:
    error_type = exc.__class__.__name__
    message = str(exc) or error_type

    if error_type == "PathBoundaryError":
        return app_error(
            AppErrorCode.PATH_OUT_OF_BOUNDARY,
            message,
            path=path,
            root=root,
            workspace=workspace,
            skill=skill,
            command=command,
            token=token,
            resource=resource,
            phase=phase,
            cwd=cwd,
            url=url,
            remote_name=remote_name,
            pattern=pattern,
            args=args,
        )
    if error_type in {"TomlError", "YamlError"}:
        return app_error(
            AppErrorCode.PARSE_ERROR,
            message,
            path=path,
            root=root,
            workspace=workspace,
            skill=skill,
            command=command,
            token=token,
            resource=resource,
            phase=phase,
            cwd=cwd,
            url=url,
            remote_name=remote_name,
            pattern=pattern,
            args=args,
        )
    if isinstance(exc, FileExistsError):
        return app_error(
            AppErrorCode.ALREADY_EXISTS,
            message,
            path=path,
            root=root,
            workspace=workspace,
            skill=skill,
            command=command,
            token=token,
            resource=resource,
            phase=phase,
            cwd=cwd,
            url=url,
            remote_name=remote_name,
            pattern=pattern,
            args=args,
        )
    if isinstance(exc, FileNotFoundError):
        return app_error(
            AppErrorCode.NOT_FOUND,
            message,
            path=path,
            root=root,
            workspace=workspace,
            skill=skill,
            command=command,
            token=token,
            resource=resource,
            phase=phase,
            cwd=cwd,
            url=url,
            remote_name=remote_name,
            pattern=pattern,
            args=args,
        )
    if isinstance(exc, NotADirectoryError):
        return app_error(
            AppErrorCode.NOT_A_DIRECTORY,
            message,
            path=path,
            root=root,
            workspace=workspace,
            skill=skill,
            command=command,
            token=token,
            resource=resource,
            phase=phase,
            cwd=cwd,
            url=url,
            remote_name=remote_name,
            pattern=pattern,
            args=args,
        )
    if isinstance(exc, IsADirectoryError):
        return app_error(
            AppErrorCode.NOT_A_FILE,
            message,
            path=path,
            root=root,
            workspace=workspace,
            skill=skill,
            command=command,
            token=token,
            resource=resource,
            phase=phase,
            cwd=cwd,
            url=url,
            remote_name=remote_name,
            pattern=pattern,
            args=args,
        )
    if isinstance(exc, ValueError):
        return app_error(
            AppErrorCode.INVALID_ARGUMENT,
            message,
            path=path,
            root=root,
            workspace=workspace,
            skill=skill,
            command=command,
            token=token,
            resource=resource,
            phase=phase,
            cwd=cwd,
            url=url,
            remote_name=remote_name,
            pattern=pattern,
            args=args,
        )
    if isinstance(exc, OSError):
        return app_error(
            default_code,
            message,
            path=path,
            root=root,
            workspace=workspace,
            skill=skill,
            command=command,
            token=token,
            resource=resource,
            phase=phase,
            cwd=cwd,
            url=url,
            remote_name=remote_name,
            pattern=pattern,
            args=args,
        )
    return app_error(
        default_code,
        message,
        path=path,
        root=root,
        workspace=workspace,
        skill=skill,
        command=command,
        token=token,
        resource=resource,
        phase=phase,
        cwd=cwd,
        url=url,
        remote_name=remote_name,
        pattern=pattern,
        args=args,
    )
