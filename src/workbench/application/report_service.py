from __future__ import annotations

"""报告生成用例。"""

import json
from pathlib import Path
from typing import Any

from ..config import WorkbenchConfig
from ..core import Result
from ..domain.errors import AppError
from ..infrastructure.report_output import timestamp_slug, write_markdown_report
from .skill_service import SkillService
from .workspace_service import WorkspaceService


class ReportService:
    """汇总多个 application service 的结果，生成状态报告。"""

    def __init__(
        self,
        config: WorkbenchConfig,
        *,
        skill_service: SkillService | None = None,
        workspace_service: WorkspaceService | None = None,
    ) -> None:
        self.config = config
        self.skill_service = skill_service or SkillService(config)
        self.workspace_service = workspace_service or WorkspaceService(config)

    def generate_report(self, *, output: Path | None = None) -> Result[dict[str, Any], AppError]:
        """生成 Markdown 报告，并返回结构化摘要。"""

        lint_payload = self.skill_service.lint_skills()
        if lint_payload.is_err:
            return Result.err(lint_payload.error)
        workspaces = self.workspace_service.load_workspaces()
        if workspaces.is_err:
            return Result.err(workspaces.error)
        workspace_payload = {"workspaces": [entry.name for entry in workspaces.value]}
        report_payload = {
            "skills": lint_payload.value,
            "workspace_summary": workspace_payload,
        }
        target = output or (self.config.reports_dir / f"status-{timestamp_slug()}.md")
        sections = [
            ("Skill Lint", json.dumps(lint_payload.value, indent=2, ensure_ascii=False)),
            ("Workspaces", json.dumps(workspace_payload, indent=2, ensure_ascii=False)),
        ]
        written = write_markdown_report(target, "Codex Skills Repository Report", sections)
        if written.is_err:
            return Result.err(written.error)
        return Result.ok({"report": str(written.value), "summary": report_payload})
