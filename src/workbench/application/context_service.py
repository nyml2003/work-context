from __future__ import annotations

"""上下文构建用例。"""

from pathlib import Path

from ..core import Result
from ..domain.config import WorkbenchConfig
from ..domain.context import ContextPayload, ContextSkillSummary, ContextWorkspaceSummary
from ..domain.errors import AppError
from ..infrastructure.filesystem import write_json
from .skill_service import SkillService
from .workspace_service import WorkspaceService


class ContextService:
    """为 skill 或 workspace 生成可直接消费的上下文载荷。"""

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

    def build_context_payload(
        self,
        skill_name: str,
        workspace_name: str | None = None,
        *,
        block_names: list[str] | None = None,
    ) -> Result[ContextPayload, AppError]:
        """组装上下文 payload。"""

        skill = self.skill_service.find_skill(skill_name)
        if skill.is_err:
            return Result.err(skill.error)
        assembly = self.skill_service.assemble_skill(skill.value, block_names=block_names)
        if assembly.is_err:
            return Result.err(assembly.error)
        payload = ContextPayload(
            selected_skills=[
                ContextSkillSummary(
                    name=skill.value.name,
                    description=skill.value.description,
                    path=str(skill.value.path),
                )
            ],
            loaded_blocks=assembly.value.loaded_blocks,
            references=assembly.value.references,
            script_entries=assembly.value.script_entries,
            bundle_markdown=assembly.value.bundle_markdown,
        )
        if workspace_name:
            workspace = self.workspace_service.get_workspace(workspace_name)
            if workspace.is_err:
                return Result.err(workspace.error)
            payload = ContextPayload(
                selected_skills=payload.selected_skills,
                loaded_blocks=payload.loaded_blocks,
                references=payload.references,
                script_entries=payload.script_entries,
                bundle_markdown=payload.bundle_markdown,
                workspace=ContextWorkspaceSummary(
                    name=workspace.value.name,
                    path=str(workspace.value.resolved_path(self.config.root)),
                    default_branch=workspace.value.default_branch,
                    check_commands=list(workspace.value.check_commands),
                    remote_name=workspace.value.remote_name,
                    repo_slug=workspace.value.repo_slug,
                    expected_remote_url=workspace.value.expected_remote_url(self.config.github_remote_prefix).unwrap_or(None),
                ),
            )
        return Result.ok(payload)

    def build_context_file(
        self,
        skill_name: str,
        *,
        workspace_name: str | None = None,
        output_path: Path | None = None,
        format_name: str = "md",
        block_names: list[str] | None = None,
    ) -> Result[Path, AppError]:
        """把上下文 payload 序列化到文件。"""

        payload = self.build_context_payload(skill_name, workspace_name, block_names=block_names)
        if payload.is_err:
            return Result.err(payload.error)
        if output_path is None:
            suffix = ".json" if format_name == "json" else ".md"
            output_path = self.config.reports_dir / f"context-{skill_name}{suffix}"
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            if format_name == "json":
                write_json(output_path, payload.value)
                return Result.ok(output_path)
            text = payload.value.bundle_markdown
            if payload.value.workspace is not None:
                workspace = payload.value.workspace
                text += "\n## Workspace\n\n"
                text += f"- name: {workspace.name}\n"
                text += f"- path: {workspace.path}\n"
                text += f"- default_branch: {workspace.default_branch}\n"
                text += f"- check_commands: {', '.join(workspace.check_commands)}\n"
                text += f"- remote_name: {workspace.remote_name}\n"
                text += f"- repo_slug: {workspace.repo_slug}\n"
                if workspace.expected_remote_url:
                    text += f"- expected_remote_url: {workspace.expected_remote_url}\n"
            output_path.write_text(text, encoding="utf-8")
        except OSError as exc:
            from ..domain.errors import AppErrorCode, app_error

            return Result.err(app_error(AppErrorCode.INTERNAL_ERROR, str(exc), path=str(output_path)))
        return Result.ok(output_path)
