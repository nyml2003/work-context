from __future__ import annotations

"""上下文构建相关的强类型模型。"""

from dataclasses import dataclass

from .skill import SkillBundleReference, SkillLoadedBlock, SkillScriptEntry


@dataclass(frozen=True, slots=True)
class ContextSkillSummary:
    """上下文里的 skill 摘要。"""

    name: str
    description: str
    path: str


@dataclass(frozen=True, slots=True)
class ContextWorkspaceSummary:
    """上下文里的 workspace 摘要。"""

    name: str
    path: str
    default_branch: str
    check_commands: list[str]
    remote_name: str
    repo_slug: str
    expected_remote_url: str | None


@dataclass(frozen=True, slots=True)
class ContextPayload:
    """完整上下文载荷。"""

    selected_skills: list[ContextSkillSummary]
    loaded_blocks: list[SkillLoadedBlock]
    references: list[SkillBundleReference]
    script_entries: list[SkillScriptEntry]
    bundle_markdown: str
    workspace: ContextWorkspaceSummary | None = None


@dataclass(frozen=True, slots=True)
class ContextBuildResult:
    """`context build` 命令返回体。"""

    context: str
    format: str


__all__ = [
    "ContextBuildResult",
    "ContextPayload",
    "ContextSkillSummary",
    "ContextWorkspaceSummary",
]
