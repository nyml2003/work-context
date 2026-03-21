from __future__ import annotations

"""配置领域模型。"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class WorkbenchPathSettings:
    """目录类配置。"""

    skills: str = "skills"
    templates: str = "templates"
    reports: str = "reports"
    workspace_config: str = "workspace-config"


@dataclass(frozen=True, slots=True)
class WorkbenchFileSettings:
    """文件类配置。"""

    workspace_registry: str = "workspace-config/workspaces.toml"


@dataclass(frozen=True, slots=True)
class WorkbenchWorkspaceSettings:
    """workspace 相关配置。"""

    managed_subdir: str = "repos"
    default_remote_name: str = "origin"
    github_remote_prefix: str = ""


@dataclass(frozen=True, slots=True)
class WorkbenchCodexSettings:
    """Codex 相关路径配置。"""

    install_root: str = "~/.codex/skills"


@dataclass(frozen=True, slots=True)
class WorkbenchToolSettings:
    """工具自身元信息。"""

    name: str
    version: str


@dataclass(frozen=True, slots=True)
class WorkbenchConfigDocument:
    """`workbench.toml` 的强类型文档模型。"""

    paths: WorkbenchPathSettings = field(default_factory=WorkbenchPathSettings)
    files: WorkbenchFileSettings = field(default_factory=WorkbenchFileSettings)
    workspace: WorkbenchWorkspaceSettings = field(default_factory=WorkbenchWorkspaceSettings)
    codex: WorkbenchCodexSettings = field(default_factory=WorkbenchCodexSettings)
    tool: WorkbenchToolSettings | None = None


@dataclass(frozen=True, slots=True)
class WorkbenchConfig:
    """运行时可消费的配置快照。"""

    root: Path
    document: WorkbenchConfigDocument
    skills_dir: Path
    templates_dir: Path
    reports_dir: Path
    workspace_config_dir: Path
    workspace_registry: Path
    managed_subdir: str
    managed_repos_dir: Path
    default_remote_name: str
    github_remote_prefix: str
    codex_install_root: Path


__all__ = [
    "WorkbenchCodexSettings",
    "WorkbenchConfig",
    "WorkbenchConfigDocument",
    "WorkbenchFileSettings",
    "WorkbenchPathSettings",
    "WorkbenchToolSettings",
    "WorkbenchWorkspaceSettings",
]
