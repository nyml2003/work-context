from __future__ import annotations

"""配置文件加载与仓库基础布局管理。"""

import json
import tomllib
from collections.abc import Mapping
from pathlib import Path

from .. import __version__
from ..core import Result
from ..domain.config import (
    WorkbenchCodexSettings,
    WorkbenchConfig,
    WorkbenchConfigDocument,
    WorkbenchFileSettings,
    WorkbenchPathSettings,
    WorkbenchToolSettings,
    WorkbenchWorkspaceSettings,
)
from ..domain.errors import AppError, AppErrorCode, app_error
from .filesystem import ensure_dir

ROOT_KEYS = {"paths", "files", "workspace", "codex", "tool"}
PATH_KEYS = {"skills", "templates", "reports", "workspace_config"}
FILE_KEYS = {"workspace_registry"}
WORKSPACE_KEYS = {"managed_subdir", "default_remote_name", "github_remote_prefix"}
CODEX_KEYS = {"install_root", "scripts_root"}
TOOL_KEYS = {"name", "version"}


DEFAULT_CONFIG = WorkbenchConfigDocument(
    tool=WorkbenchToolSettings(name="workbench", version=__version__),
)


def build_workbench_config(root: Path, document: WorkbenchConfigDocument) -> WorkbenchConfig:
    """把配置文档投影为运行时配置对象。"""

    return WorkbenchConfig(
        root=root,
        document=document,
        skills_dir=root / document.paths.skills,
        templates_dir=root / document.paths.templates,
        reports_dir=root / document.paths.reports,
        workspace_config_dir=root / document.paths.workspace_config,
        workspace_registry=root / document.files.workspace_registry,
        managed_subdir=document.workspace.managed_subdir,
        managed_repos_dir=root / document.workspace.managed_subdir,
        default_remote_name=document.workspace.default_remote_name,
        github_remote_prefix=document.workspace.github_remote_prefix,
        codex_install_root=Path(document.codex.install_root).expanduser(),
        work_context_scripts_root=Path(document.codex.scripts_root).expanduser(),
    )


def ensure_mapping(value: object, *, label: str) -> Result[Mapping[str, object], AppError]:
    """要求当前值必须是 TOML table。"""

    if not isinstance(value, Mapping):
        return Result.err(app_error(AppErrorCode.CONFIG_ERROR, f"{label} must be a TOML table"))
    return Result.ok(value)


def reject_unknown_keys(section: Mapping[str, object], *, label: str, allowed: set[str]) -> Result[None, AppError]:
    """显式 schema：拒绝所有未知配置项。"""

    unknown = sorted(key for key in section if key not in allowed)
    if unknown:
        return Result.err(app_error(AppErrorCode.CONFIG_ERROR, f"{label} contains unknown keys: {', '.join(unknown)}"))
    return Result.ok(None)


def read_optional_string(
    section: Mapping[str, object],
    *,
    key: str,
    default: str,
    label: str,
) -> Result[str, AppError]:
    """读取可选字符串，不存在时回落到默认值。"""

    if key not in section:
        return Result.ok(default)
    value = section[key]
    if not isinstance(value, str):
        return Result.err(app_error(AppErrorCode.CONFIG_ERROR, f"{label}.{key} must be a string"))
    return Result.ok(value)


def parse_paths_section(document: Mapping[str, object], defaults: WorkbenchPathSettings) -> Result[WorkbenchPathSettings, AppError]:
    raw = document.get("paths", {})
    table = ensure_mapping(raw, label="paths")
    if table.is_err:
        return Result.err(table.error)
    unknown = reject_unknown_keys(table.value, label="paths", allowed=PATH_KEYS)
    if unknown.is_err:
        return Result.err(unknown.error)
    skills = read_optional_string(table.value, key="skills", default=defaults.skills, label="paths")
    if skills.is_err:
        return Result.err(skills.error)
    templates = read_optional_string(table.value, key="templates", default=defaults.templates, label="paths")
    if templates.is_err:
        return Result.err(templates.error)
    reports = read_optional_string(table.value, key="reports", default=defaults.reports, label="paths")
    if reports.is_err:
        return Result.err(reports.error)
    workspace_config = read_optional_string(
        table.value,
        key="workspace_config",
        default=defaults.workspace_config,
        label="paths",
    )
    if workspace_config.is_err:
        return Result.err(workspace_config.error)
    return Result.ok(
        WorkbenchPathSettings(
            skills=skills.value,
            templates=templates.value,
            reports=reports.value,
            workspace_config=workspace_config.value,
        )
    )


def parse_files_section(document: Mapping[str, object], defaults: WorkbenchFileSettings) -> Result[WorkbenchFileSettings, AppError]:
    raw = document.get("files", {})
    table = ensure_mapping(raw, label="files")
    if table.is_err:
        return Result.err(table.error)
    unknown = reject_unknown_keys(table.value, label="files", allowed=FILE_KEYS)
    if unknown.is_err:
        return Result.err(unknown.error)
    registry = read_optional_string(
        table.value,
        key="workspace_registry",
        default=defaults.workspace_registry,
        label="files",
    )
    if registry.is_err:
        return Result.err(registry.error)
    return Result.ok(WorkbenchFileSettings(workspace_registry=registry.value))


def parse_workspace_section(
    document: Mapping[str, object],
    defaults: WorkbenchWorkspaceSettings,
) -> Result[WorkbenchWorkspaceSettings, AppError]:
    raw = document.get("workspace", {})
    table = ensure_mapping(raw, label="workspace")
    if table.is_err:
        return Result.err(table.error)
    unknown = reject_unknown_keys(table.value, label="workspace", allowed=WORKSPACE_KEYS)
    if unknown.is_err:
        return Result.err(unknown.error)
    managed_subdir = read_optional_string(
        table.value,
        key="managed_subdir",
        default=defaults.managed_subdir,
        label="workspace",
    )
    if managed_subdir.is_err:
        return Result.err(managed_subdir.error)
    default_remote_name = read_optional_string(
        table.value,
        key="default_remote_name",
        default=defaults.default_remote_name,
        label="workspace",
    )
    if default_remote_name.is_err:
        return Result.err(default_remote_name.error)
    github_remote_prefix = read_optional_string(
        table.value,
        key="github_remote_prefix",
        default=defaults.github_remote_prefix,
        label="workspace",
    )
    if github_remote_prefix.is_err:
        return Result.err(github_remote_prefix.error)
    return Result.ok(
        WorkbenchWorkspaceSettings(
            managed_subdir=managed_subdir.value,
            default_remote_name=default_remote_name.value,
            github_remote_prefix=github_remote_prefix.value,
        )
    )


def parse_codex_section(document: Mapping[str, object], defaults: WorkbenchCodexSettings) -> Result[WorkbenchCodexSettings, AppError]:
    raw = document.get("codex", {})
    table = ensure_mapping(raw, label="codex")
    if table.is_err:
        return Result.err(table.error)
    unknown = reject_unknown_keys(table.value, label="codex", allowed=CODEX_KEYS)
    if unknown.is_err:
        return Result.err(unknown.error)
    install_root = read_optional_string(
        table.value,
        key="install_root",
        default=defaults.install_root,
        label="codex",
    )
    if install_root.is_err:
        return Result.err(install_root.error)
    scripts_root = read_optional_string(
        table.value,
        key="scripts_root",
        default=defaults.scripts_root,
        label="codex",
    )
    if scripts_root.is_err:
        return Result.err(scripts_root.error)
    return Result.ok(WorkbenchCodexSettings(install_root=install_root.value, scripts_root=scripts_root.value))


def parse_tool_section(
    document: Mapping[str, object],
    defaults: WorkbenchToolSettings | None,
) -> Result[WorkbenchToolSettings | None, AppError]:
    if defaults is None and "tool" not in document:
        return Result.ok(None)
    raw = document.get("tool", {})
    table = ensure_mapping(raw, label="tool")
    if table.is_err:
        return Result.err(table.error)
    unknown = reject_unknown_keys(table.value, label="tool", allowed=TOOL_KEYS)
    if unknown.is_err:
        return Result.err(unknown.error)
    fallback = defaults or WorkbenchToolSettings(name="workbench", version=__version__)
    name = read_optional_string(table.value, key="name", default=fallback.name, label="tool")
    if name.is_err:
        return Result.err(name.error)
    version = read_optional_string(table.value, key="version", default=fallback.version, label="tool")
    if version.is_err:
        return Result.err(version.error)
    return Result.ok(WorkbenchToolSettings(name=name.value, version=version.value))


def parse_config_document(raw: str, *, path: Path) -> Result[WorkbenchConfigDocument, AppError]:
    """把 TOML 文本解析为配置文档，并拒绝未知字段。"""

    try:
        document = tomllib.loads(raw)
    except tomllib.TOMLDecodeError as exc:
        return Result.err(app_error(AppErrorCode.PARSE_ERROR, str(exc), path=str(path)))
    unknown = reject_unknown_keys(document, label="workbench.toml", allowed=ROOT_KEYS)
    if unknown.is_err:
        return Result.err(unknown.error.with_context(path=str(path)))
    paths = parse_paths_section(document, DEFAULT_CONFIG.paths)
    if paths.is_err:
        return Result.err(paths.error.with_context(path=str(path)))
    files = parse_files_section(document, DEFAULT_CONFIG.files)
    if files.is_err:
        return Result.err(files.error.with_context(path=str(path)))
    workspace = parse_workspace_section(document, DEFAULT_CONFIG.workspace)
    if workspace.is_err:
        return Result.err(workspace.error.with_context(path=str(path)))
    codex = parse_codex_section(document, DEFAULT_CONFIG.codex)
    if codex.is_err:
        return Result.err(codex.error.with_context(path=str(path)))
    tool = parse_tool_section(document, DEFAULT_CONFIG.tool)
    if tool.is_err:
        return Result.err(tool.error.with_context(path=str(path)))
    return Result.ok(
        WorkbenchConfigDocument(
            paths=paths.value,
            files=files.value,
            workspace=workspace.value,
            codex=codex.value,
            tool=tool.value,
        )
    )


def quote_toml_string(value: str) -> str:
    """用 JSON 字符串规则输出 TOML 字符串字面量。"""

    return json.dumps(value, ensure_ascii=False)


def dump_config_document(document: WorkbenchConfigDocument) -> str:
    """以稳定顺序写出最小 TOML。"""

    lines = [
        "[paths]",
        f"skills = {quote_toml_string(document.paths.skills)}",
        f"templates = {quote_toml_string(document.paths.templates)}",
        f"reports = {quote_toml_string(document.paths.reports)}",
        f"workspace_config = {quote_toml_string(document.paths.workspace_config)}",
        "",
        "[files]",
        f"workspace_registry = {quote_toml_string(document.files.workspace_registry)}",
        "",
        "[workspace]",
        f"managed_subdir = {quote_toml_string(document.workspace.managed_subdir)}",
        f"default_remote_name = {quote_toml_string(document.workspace.default_remote_name)}",
        f"github_remote_prefix = {quote_toml_string(document.workspace.github_remote_prefix)}",
        "",
        "[codex]",
        f"install_root = {quote_toml_string(document.codex.install_root)}",
        f"scripts_root = {quote_toml_string(document.codex.scripts_root)}",
    ]
    if document.tool is not None:
        lines.extend(
            [
                "",
                "[tool]",
                f"name = {quote_toml_string(document.tool.name)}",
                f"version = {quote_toml_string(document.tool.version)}",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def load_config(root: Path) -> Result[WorkbenchConfig, AppError]:
    """读取 `workbench.toml` 并返回运行时配置对象。"""

    config_path = root / "workbench.toml"
    document = DEFAULT_CONFIG
    if config_path.exists():
        try:
            raw = config_path.read_text(encoding="utf-8")
        except OSError as exc:
            return Result.err(app_error(AppErrorCode.CONFIG_ERROR, str(exc), path=str(config_path)))
        loaded = parse_config_document(raw, path=config_path)
        if loaded.is_err:
            return Result.err(loaded.error)
        document = loaded.value
    return Result.ok(build_workbench_config(root, document))


def ensure_base_layout(config: WorkbenchConfig) -> Result[None, AppError]:
    """确保配置所声明的基础目录存在。"""

    try:
        for path in [
            config.skills_dir,
            config.templates_dir,
            config.reports_dir,
            config.workspace_config_dir,
            config.managed_repos_dir,
        ]:
            ensure_dir(path)
    except OSError as exc:
        return Result.err(app_error(AppErrorCode.CONFIG_ERROR, str(exc), root=str(config.root)))
    return Result.ok(None)


def write_default_config(root: Path, *, overwrite: bool = False) -> Result[bool, AppError]:
    """在目标目录写入默认 `workbench.toml`。"""

    path = root / "workbench.toml"
    if path.exists() and not overwrite:
        return Result.ok(False)
    try:
        ensure_dir(path.parent)
        path.write_text(dump_config_document(DEFAULT_CONFIG), encoding="utf-8")
    except OSError as exc:
        return Result.err(app_error(AppErrorCode.CONFIG_ERROR, str(exc), path=str(path), root=str(root)))
    return Result.ok(True)


__all__ = [
    "DEFAULT_CONFIG",
    "build_workbench_config",
    "dump_config_document",
    "ensure_base_layout",
    "load_config",
    "parse_config_document",
    "write_default_config",
]
