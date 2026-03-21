from __future__ import annotations

"""报告输出相关模型。"""

from dataclasses import dataclass

from .skill import SkillLintPayload


@dataclass(frozen=True, slots=True)
class WorkspaceReportSummary:
    """报告里的 workspace 摘要。"""

    workspaces: list[str]


@dataclass(frozen=True, slots=True)
class RepositoryReportSummary:
    """报告正文里的结构化摘要。"""

    skills: SkillLintPayload
    workspace_summary: WorkspaceReportSummary


@dataclass(frozen=True, slots=True)
class RepositoryReportPayload:
    """`report generate` 命令返回体。"""

    report: str
    summary: RepositoryReportSummary


__all__ = ["RepositoryReportPayload", "RepositoryReportSummary", "WorkspaceReportSummary"]
