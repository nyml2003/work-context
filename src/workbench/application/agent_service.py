from __future__ import annotations

"""多 agent 编排用例。"""

from collections.abc import Mapping
from pathlib import Path

from ..core import Result
from ..domain.agent import (
    AgentAssemblyPayload,
    AgentHandoffPayload,
    AgentHandoffValidationPayload,
    AgentPlanPayload,
    AgentResolutionPayload,
    AgentRole,
    AgentSubtask,
    AgentTask,
    SkillSelectionReason,
)
from ..domain.config import WorkbenchConfig
from ..domain.context import ContextSkillSummary
from ..domain.errors import AppError, AppErrorCode, app_error
from ..domain.skill import Skill
from ..infrastructure.agent_trace_store import load_trace_document, trace_path, write_trace_document
from ..infrastructure.filesystem import read_json
from ..infrastructure.template_rendering import slugify
from .skill_service import SkillService

ALLOWED_WORKSTREAMS = {"ui", "logic", "api", "logging"}


class AgentService:
    """编排顶层任务、按角色解析 skill，并生成最小上下文。"""

    def __init__(self, config: WorkbenchConfig, *, skill_service: SkillService | None = None) -> None:
        self.config = config
        self.skill_service = skill_service or SkillService(config)

    def parse_task_payload(self, payload: object, *, path: str | None = None) -> Result[AgentTask, AppError]:
        if not isinstance(payload, Mapping):
            return Result.err(app_error(AppErrorCode.PARSE_ERROR, "Task file must contain a JSON object", path=path))
        domain = payload.get("domain")
        if not isinstance(domain, str) or not domain.strip():
            return Result.err(app_error(AppErrorCode.PARSE_ERROR, "Task must include string field 'domain'", path=path))
        if domain != "frontend":
            return Result.err(app_error(AppErrorCode.INVALID_ARGUMENT, "Only frontend domain is supported in v1", path=path))
        title = payload.get("title")
        if not isinstance(title, str) or not title.strip():
            return Result.err(app_error(AppErrorCode.PARSE_ERROR, "Task must include string field 'title'", path=path))
        objective = payload.get("objective", title)
        if not isinstance(objective, str) or not objective.strip():
            return Result.err(app_error(AppErrorCode.PARSE_ERROR, "Task field 'objective' must be a string", path=path))
        workstreams = payload.get("workstreams")
        if not isinstance(workstreams, list) or not workstreams or any(not isinstance(item, str) for item in workstreams):
            return Result.err(app_error(AppErrorCode.PARSE_ERROR, "Task field 'workstreams' must be a non-empty list of strings", path=path))
        normalized_workstreams = list(dict.fromkeys(item for item in workstreams if item in ALLOWED_WORKSTREAMS))
        if not normalized_workstreams:
            return Result.err(app_error(AppErrorCode.INVALID_ARGUMENT, "Task workstreams must include ui, logic, api or logging", path=path))
        constraints = payload.get("constraints", [])
        if not isinstance(constraints, list) or any(not isinstance(item, str) for item in constraints):
            return Result.err(app_error(AppErrorCode.PARSE_ERROR, "Task field 'constraints' must be a list of strings", path=path))
        acceptance_criteria = payload.get("acceptance_criteria", [])
        if not isinstance(acceptance_criteria, list) or any(not isinstance(item, str) for item in acceptance_criteria):
            return Result.err(app_error(AppErrorCode.PARSE_ERROR, "Task field 'acceptance_criteria' must be a list of strings", path=path))
        notes = payload.get("notes", [])
        if not isinstance(notes, list) or any(not isinstance(item, str) for item in notes):
            return Result.err(app_error(AppErrorCode.PARSE_ERROR, "Task field 'notes' must be a list of strings", path=path))
        task_id = payload.get("id", slugify(title))
        if not isinstance(task_id, str) or not task_id.strip():
            return Result.err(app_error(AppErrorCode.PARSE_ERROR, "Task field 'id' must be a string when provided", path=path))
        return Result.ok(
            AgentTask(
                task_id=task_id,
                domain=domain,
                title=title,
                objective=objective,
                workstreams=normalized_workstreams,
                constraints=list(dict.fromkeys(constraints)),
                acceptance_criteria=list(acceptance_criteria),
                notes=list(notes),
            )
        )

    def load_task_file(self, task_file: Path) -> Result[AgentTask, AppError]:
        try:
            payload = read_json(task_file)
        except Exception as exc:  # pragma: no cover
            return Result.err(app_error(AppErrorCode.PARSE_ERROR, str(exc), path=str(task_file)))
        return self.parse_task_payload(payload, path=str(task_file))

    def build_plan(self, task: AgentTask) -> AgentPlanPayload:
        subtasks: list[AgentSubtask] = [
            AgentSubtask(
                task_id=task.task_id,
                subtask_id="task-analysis",
                title="Analyze frontend task and parallel plan",
                role=AgentRole.DIRECTOR,
                capability_tags=["frontend-directing", "parallel-planning"],
                domain_tags=["frontend"],
                depends_on=[],
                parallelizable=False,
                description="Break down the frontend task, set execution order, and identify parallelizable workstreams.",
            )
        ]
        worker_ids: list[str] = []
        if "ui" in task.workstreams:
            subtasks.extend(
                [
                    AgentSubtask(
                        task_id=task.task_id,
                        subtask_id="ui-policy",
                        title="Collect UI policy constraints",
                        role=AgentRole.POLICY,
                        capability_tags=["tsx-rules", "eslint-rules"]
                        + (["tailwind-rules"] if "tailwind" in task.constraints else []),
                        domain_tags=["frontend", "ui"],
                        depends_on=["task-analysis"],
                        parallelizable=False,
                        description="Summarize TSX, styling, and lint constraints for UI work.",
                    ),
                    AgentSubtask(
                        task_id=task.task_id,
                        subtask_id="ui-implementation",
                        title="Implement UI structure and styling",
                        role=AgentRole.WORKER,
                        capability_tags=["ui-implementation"],
                        domain_tags=["frontend", "ui"],
                        depends_on=["task-analysis", "ui-policy"],
                        parallelizable=True,
                        description="Implement the page shell, layout, and UI interactions for the task.",
                    ),
                ]
            )
            worker_ids.append("ui-implementation")
        if "logic" in task.workstreams:
            subtasks.extend(
                [
                    AgentSubtask(
                        task_id=task.task_id,
                        subtask_id="logic-policy",
                        title="Collect logic and type constraints",
                        role=AgentRole.POLICY,
                        capability_tags=["typescript-rules", "eslint-rules"],
                        domain_tags=["frontend", "logic"],
                        depends_on=["task-analysis"],
                        parallelizable=False,
                        description="Summarize typing and lint constraints for client-side logic.",
                    ),
                    AgentSubtask(
                        task_id=task.task_id,
                        subtask_id="logic-implementation",
                        title="Implement view logic and state flow",
                        role=AgentRole.WORKER,
                        capability_tags=["logic-implementation"],
                        domain_tags=["frontend", "logic"],
                        depends_on=["task-analysis", "logic-policy"],
                        parallelizable=True,
                        description="Implement hooks, view-model logic, and local state transitions.",
                    ),
                ]
            )
            worker_ids.append("logic-implementation")
        if "api" in task.workstreams:
            subtasks.extend(
                [
                    AgentSubtask(
                        task_id=task.task_id,
                        subtask_id="api-policy",
                        title="Collect API and typing constraints",
                        role=AgentRole.POLICY,
                        capability_tags=["typescript-rules", "eslint-rules"],
                        domain_tags=["frontend", "api"],
                        depends_on=["task-analysis"],
                        parallelizable=False,
                        description="Summarize typing and lint constraints that apply to API integration.",
                    ),
                    AgentSubtask(
                        task_id=task.task_id,
                        subtask_id="api-integration",
                        title="Integrate API calls and mapping logic",
                        role=AgentRole.WORKER,
                        capability_tags=["api-integration"],
                        domain_tags=["frontend", "api"],
                        depends_on=["task-analysis", "api-policy"],
                        parallelizable=True,
                        description="Implement API client usage, response mapping, and error states.",
                    ),
                ]
            )
            worker_ids.append("api-integration")
        if "logging" in task.workstreams:
            subtasks.extend(
                [
                    AgentSubtask(
                        task_id=task.task_id,
                        subtask_id="logging-policy",
                        title="Collect logging constraints",
                        role=AgentRole.POLICY,
                        capability_tags=["logging-rules", "typescript-rules"],
                        domain_tags=["frontend", "logging"],
                        depends_on=["task-analysis"],
                        parallelizable=False,
                        description="Summarize logging and typing constraints for diagnostics integration.",
                    ),
                    AgentSubtask(
                        task_id=task.task_id,
                        subtask_id="logging-integration",
                        title="Integrate logging and diagnostics",
                        role=AgentRole.WORKER,
                        capability_tags=["logging-implementation"],
                        domain_tags=["frontend", "logging"],
                        depends_on=["task-analysis", "logging-policy"],
                        parallelizable=True,
                        description="Implement logs, diagnostics, and instrumentation hooks.",
                    ),
                ]
            )
            worker_ids.append("logging-integration")
        subtasks.extend(
            [
                AgentSubtask(
                    task_id=task.task_id,
                    subtask_id="testing-review",
                    title="Review testing and acceptance coverage",
                    role=AgentRole.REVIEW,
                    capability_tags=["testing-review"],
                    domain_tags=["frontend", "review"],
                    depends_on=list(worker_ids),
                    parallelizable=False,
                    description="Check whether implementation work satisfies testing and acceptance requirements.",
                ),
                AgentSubtask(
                    task_id=task.task_id,
                    subtask_id="regression-review",
                    title="Review regression risk and release readiness",
                    role=AgentRole.REVIEW,
                    capability_tags=["regression-review"],
                    domain_tags=["frontend", "review"],
                    depends_on=["testing-review"],
                    parallelizable=False,
                    description="Inspect likely regressions and summarize release risks after implementation.",
                ),
            ]
        )
        return AgentPlanPayload(task=task, subtasks=subtasks, trace_path=str(trace_path(self.config, task.task_id)))

    def plan_from_file(self, task_file: Path) -> Result[AgentPlanPayload, AppError]:
        task = self.load_task_file(task_file)
        if task.is_err:
            return Result.err(task.error)
        payload = self.build_plan(task.value)
        saved = self.persist_plan(payload)
        if saved.is_err:
            return Result.err(saved.error)
        return Result.ok(payload)

    def persist_plan(self, plan: AgentPlanPayload) -> Result[Path, AppError]:
        loaded = load_trace_document(self.config, plan.task.task_id)
        if loaded.is_err:
            return Result.err(loaded.error)
        document = loaded.value
        document["task"] = plan.task
        document["plan"] = plan
        document.setdefault("resolutions", {})
        document.setdefault("assemblies", {})
        return write_trace_document(self.config, plan.task.task_id, document)

    def get_subtask(self, task: AgentTask, subtask_id: str) -> Result[AgentSubtask, AppError]:
        plan = self.build_plan(task)
        subtask = next((item for item in plan.subtasks if item.subtask_id == subtask_id), None)
        if subtask is None:
            return Result.err(app_error(AppErrorCode.NOT_FOUND, f"Subtask not found: {subtask_id}", command=subtask_id))
        return Result.ok(subtask)

    def resolve_subtask(self, task: AgentTask, subtask_id: str) -> Result[AgentResolutionPayload, AppError]:
        subtask = self.get_subtask(task, subtask_id)
        if subtask.is_err:
            return Result.err(subtask.error)
        discovered = self.skill_service.discover_skills()
        if discovered.is_err:
            return Result.err(discovered.error)
        candidates: list[tuple[Skill, list[str], list[str]]] = []
        for skill in discovered.value:
            if subtask.value.role.value not in skill.frontmatter.role_fit:
                continue
            matched_domains = sorted(set(subtask.value.domain_tags).intersection(skill.frontmatter.domain_tags))
            if not matched_domains:
                continue
            matched_capabilities = sorted(set(subtask.value.capability_tags).intersection(skill.frontmatter.capabilities))
            if not matched_capabilities:
                continue
            candidates.append((skill, matched_capabilities, matched_domains))
        if not candidates:
            return Result.err(
                app_error(
                    AppErrorCode.NOT_FOUND,
                    f"No skills matched subtask '{subtask_id}' for role '{subtask.value.role.value}'",
                    command=subtask_id,
                )
            )
        candidates.sort(key=lambda item: (-len(item[1]), -len(item[2]), item[0].name))
        main_skill = candidates[0][0]
        selected: list[Skill] = [main_skill]
        reasons: list[SkillSelectionReason] = [
            SkillSelectionReason(
                skill=main_skill.name,
                matched_capabilities=candidates[0][1],
                matched_domain_tags=candidates[0][2],
                recommended_by=None,
            )
        ]
        uncovered = set(subtask.value.capability_tags).difference(main_skill.frontmatter.capabilities)
        remaining = candidates[1:]
        while uncovered and len(selected) < 3 and remaining:
            next_index = -1
            for index, (candidate, matched_capabilities, matched_domains) in enumerate(remaining):
                if not uncovered.intersection(candidate.frontmatter.capabilities):
                    continue
                recommended_by = next(
                    (selected_skill.name for selected_skill in selected if candidate.name in selected_skill.frontmatter.recommends),
                    None,
                )
                selected.append(candidate)
                reasons.append(
                    SkillSelectionReason(
                        skill=candidate.name,
                        matched_capabilities=matched_capabilities,
                        matched_domain_tags=matched_domains,
                        recommended_by=recommended_by,
                    )
                )
                uncovered.difference_update(candidate.frontmatter.capabilities)
                next_index = index
                break
            if next_index == -1:
                break
            remaining.pop(next_index)
        if uncovered:
            return Result.err(
                app_error(
                    AppErrorCode.INVALID_STATE,
                    f"Resolved skills do not cover required capabilities for subtask '{subtask_id}': {', '.join(sorted(uncovered))}",
                    command=subtask_id,
                )
            )
        payload = AgentResolutionPayload(
            task_id=task.task_id,
            subtask=subtask.value,
            selected_skills=[skill.name for skill in selected],
            reasons=reasons,
            trace_path=str(trace_path(self.config, task.task_id)),
        )
        saved = self.persist_resolution(payload)
        if saved.is_err:
            return Result.err(saved.error)
        return Result.ok(payload)

    def persist_resolution(self, resolution: AgentResolutionPayload) -> Result[Path, AppError]:
        loaded = load_trace_document(self.config, resolution.task_id)
        if loaded.is_err:
            return Result.err(loaded.error)
        document = loaded.value
        resolutions = document.setdefault("resolutions", {})
        if not isinstance(resolutions, dict):
            return Result.err(app_error(AppErrorCode.PARSE_ERROR, "Trace file has invalid resolutions section"))
        resolutions[resolution.subtask.subtask_id] = resolution
        return write_trace_document(self.config, resolution.task_id, document)

    def resolve_from_file(self, task_file: Path, subtask_id: str) -> Result[AgentResolutionPayload, AppError]:
        task = self.load_task_file(task_file)
        if task.is_err:
            return Result.err(task.error)
        planned = self.persist_plan(self.build_plan(task.value))
        if planned.is_err:
            return Result.err(planned.error)
        return self.resolve_subtask(task.value, subtask_id)

    def assemble_subtask(self, task: AgentTask, subtask_id: str) -> Result[AgentAssemblyPayload, AppError]:
        resolved = self.resolve_subtask(task, subtask_id)
        if resolved.is_err:
            return Result.err(resolved.error)
        selected_skills: list[ContextSkillSummary] = []
        loaded_blocks = []
        script_entries = []
        sections: list[str] = []
        for skill_name in resolved.value.selected_skills:
            skill = self.skill_service.find_skill(skill_name)
            if skill.is_err:
                return Result.err(skill.error)
            assembly = self.skill_service.assemble_skill(skill.value)
            if assembly.is_err:
                return Result.err(assembly.error)
            selected_skills.append(
                ContextSkillSummary(name=skill.value.name, description=skill.value.description, path=str(skill.value.path))
            )
            loaded_blocks.extend(assembly.value.loaded_blocks)
            script_entries.extend(assembly.value.script_entries)
            sections.extend([assembly.value.bundle_markdown.strip(), ""])
        payload = AgentAssemblyPayload(
            task_id=task.task_id,
            subtask=resolved.value.subtask,
            selected_skills=selected_skills,
            loaded_blocks=loaded_blocks,
            script_entries=script_entries,
            bundle_markdown="\n".join(section for section in sections if section).rstrip() + "\n",
            trace_path=str(trace_path(self.config, task.task_id)),
        )
        saved = self.persist_assembly(payload)
        if saved.is_err:
            return Result.err(saved.error)
        return Result.ok(payload)

    def assemble_from_file(self, task_file: Path, subtask_id: str) -> Result[AgentAssemblyPayload, AppError]:
        task = self.load_task_file(task_file)
        if task.is_err:
            return Result.err(task.error)
        planned = self.persist_plan(self.build_plan(task.value))
        if planned.is_err:
            return Result.err(planned.error)
        return self.assemble_subtask(task.value, subtask_id)

    def persist_assembly(self, payload: AgentAssemblyPayload) -> Result[Path, AppError]:
        loaded = load_trace_document(self.config, payload.task_id)
        if loaded.is_err:
            return Result.err(loaded.error)
        document = loaded.value
        assemblies = document.setdefault("assemblies", {})
        if not isinstance(assemblies, dict):
            return Result.err(app_error(AppErrorCode.PARSE_ERROR, "Trace file has invalid assemblies section"))
        assemblies[payload.subtask.subtask_id] = payload
        return write_trace_document(self.config, payload.task_id, document)

    def validate_handoff_payload(self, payload: object, *, path: str | None = None) -> Result[AgentHandoffValidationPayload, AppError]:
        if not isinstance(payload, Mapping):
            return Result.err(app_error(AppErrorCode.PARSE_ERROR, "Handoff payload must be a JSON object", path=path))
        required_strings = ("task_id", "subtask_id", "summary")
        for key in required_strings:
            value = payload.get(key)
            if not isinstance(value, str) or not value.strip():
                return Result.err(app_error(AppErrorCode.PARSE_ERROR, f"Handoff field '{key}' must be a string", path=path))
        producer_role = payload.get("producer_role")
        consumer_role = payload.get("consumer_role")
        if producer_role not in {item.value for item in AgentRole}:
            return Result.err(app_error(AppErrorCode.PARSE_ERROR, "producer_role must be a valid agent role", path=path))
        if consumer_role not in {item.value for item in AgentRole}:
            return Result.err(app_error(AppErrorCode.PARSE_ERROR, "consumer_role must be a valid agent role", path=path))
        for list_key in ("decisions", "artifacts", "acceptance_criteria", "open_questions"):
            value = payload.get(list_key, [])
            if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
                return Result.err(app_error(AppErrorCode.PARSE_ERROR, f"Handoff field '{list_key}' must be a list of strings", path=path))
        return Result.ok(
            AgentHandoffValidationPayload(
                valid=True,
                task_id=str(payload["task_id"]),
                subtask_id=str(payload["subtask_id"]),
                producer_role=AgentRole(str(producer_role)),
                consumer_role=AgentRole(str(consumer_role)),
                artifact_count=len(payload.get("artifacts", [])),
            )
        )

    def validate_handoff_file(self, handoff_file: Path) -> Result[AgentHandoffValidationPayload, AppError]:
        try:
            payload = read_json(handoff_file)
        except Exception as exc:  # pragma: no cover
            return Result.err(app_error(AppErrorCode.PARSE_ERROR, str(exc), path=str(handoff_file)))
        return self.validate_handoff_payload(payload, path=str(handoff_file))

    def read_trace(self, task_id: str) -> Result[dict[str, object], AppError]:
        loaded = load_trace_document(self.config, task_id)
        if loaded.is_err:
            return Result.err(loaded.error)
        path = trace_path(self.config, task_id)
        if not path.exists():
            return Result.err(app_error(AppErrorCode.NOT_FOUND, f"Trace not found for task '{task_id}'", path=str(path)))
        return Result.ok(loaded.value)


__all__ = ["AgentService"]
