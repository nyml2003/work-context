from __future__ import annotations

"""多 agent 编排相关的强类型模型。"""

from dataclasses import dataclass, field
from enum import StrEnum

from .context import ContextSkillSummary
from .skill import SkillLoadedBlock, SkillScriptEntry


class AgentRole(StrEnum):
    DIRECTOR = "director"
    POLICY = "policy"
    WORKER = "worker"
    REVIEW = "review"


@dataclass(frozen=True, slots=True)
class AgentTask:
    """顶层任务输入。"""

    task_id: str
    domain: str
    title: str
    objective: str
    workstreams: list[str]
    constraints: list[str]
    acceptance_criteria: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class AgentSubtask:
    """orchestrator 输出的单个子任务。"""

    task_id: str
    subtask_id: str
    title: str
    role: AgentRole
    capability_tags: list[str]
    domain_tags: list[str]
    depends_on: list[str]
    parallelizable: bool
    description: str


@dataclass(frozen=True, slots=True)
class SkillSelectionReason:
    """resolver 对单个 skill 的命中原因。"""

    skill: str
    matched_capabilities: list[str]
    matched_domain_tags: list[str]
    recommended_by: str | None = None


@dataclass(frozen=True, slots=True)
class AgentPlanPayload:
    """任务拆解结果。"""

    task: AgentTask
    subtasks: list[AgentSubtask]
    trace_path: str


@dataclass(frozen=True, slots=True)
class AgentResolutionPayload:
    """resolver 的输出。"""

    task_id: str
    subtask: AgentSubtask
    selected_skills: list[str]
    reasons: list[SkillSelectionReason]
    trace_path: str


@dataclass(frozen=True, slots=True)
class AgentAssemblyPayload:
    """assembler 的输出。"""

    task_id: str
    subtask: AgentSubtask
    selected_skills: list[ContextSkillSummary]
    loaded_blocks: list[SkillLoadedBlock]
    script_entries: list[SkillScriptEntry]
    bundle_markdown: str
    trace_path: str


@dataclass(frozen=True, slots=True)
class AgentHandoffPayload:
    """agent 之间唯一允许共享的结构化产物。"""

    task_id: str
    subtask_id: str
    producer_role: AgentRole
    consumer_role: AgentRole
    summary: str
    decisions: list[str]
    artifacts: list[str]
    acceptance_criteria: list[str]
    open_questions: list[str] = field(default_factory=list)
    trace_ref: str | None = None


@dataclass(frozen=True, slots=True)
class AgentHandoffValidationPayload:
    """handoff 校验结果。"""

    valid: bool
    task_id: str
    subtask_id: str
    producer_role: AgentRole
    consumer_role: AgentRole
    artifact_count: int


@dataclass(frozen=True, slots=True)
class TraceEntry:
    """运行时 trace 记录。"""

    phase: str
    message: str


__all__ = [
    "AgentAssemblyPayload",
    "AgentHandoffPayload",
    "AgentHandoffValidationPayload",
    "AgentPlanPayload",
    "AgentResolutionPayload",
    "AgentRole",
    "AgentSubtask",
    "AgentTask",
    "SkillSelectionReason",
    "TraceEntry",
]
