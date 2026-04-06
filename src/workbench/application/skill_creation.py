from __future__ import annotations

"""Use case for scaffolding a new skill package."""

import json
from dataclasses import dataclass
from pathlib import Path

from ..core import Result
from ..core.yaml import dumps as yaml_dumps, loads as yaml_loads
from ..domain.config import WorkbenchConfig
from ..domain.errors import AppError, AppErrorCode, app_error
from ..domain.skill import RESOURCE_CHOICES, ROLE_CHOICES, title_from_skill_name
from ..infrastructure.filesystem import write_text
from ..infrastructure.skill_templates import load_skill_templates
from ..infrastructure.template_rendering import render_template, slugify


@dataclass(frozen=True, slots=True)
class ScaffoldReference:
    name: str
    title: str
    content: str


@dataclass(frozen=True, slots=True)
class RoleBlueprint:
    default_stance: list[str]
    workflow_steps: list[str]
    execution_rules: list[str]
    output_expectations: list[str]
    references: list[ScaffoldReference]
    example_request: str

    @property
    def default_blocks(self) -> list[str]:
        return ["overview", *[reference.name for reference in self.references]]


def normalize_resource_choices(resources: list[str] | None) -> Result[list[str], AppError]:
    selected_resources = list(dict.fromkeys(resources or []))
    for resource in selected_resources:
        if resource not in RESOURCE_CHOICES:
            return Result.err(app_error(AppErrorCode.INVALID_ARGUMENT, f"Unknown resource type: {resource}", resource=resource))
    return Result.ok(selected_resources)


def bullet_lines(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def numbered_lines(items: list[str]) -> str:
    return "\n".join(f"{index}. {item}" for index, item in enumerate(items, start=1))


def yaml_list(items: list[str], *, indent: int) -> str:
    prefix = " " * indent
    return "\n".join(f'{prefix}- "{item}"' for item in items)


def yaml_blocks(reference_blocks: list[ScaffoldReference], *, indent: int) -> str:
    prefix = " " * indent
    lines = [f'{prefix}- name: "overview"', f'{prefix}  kind: "overview"']
    for block in reference_blocks:
        lines.extend(
            [
                f'{prefix}- name: "{block.name}"',
                f'{prefix}  kind: "reference"',
                f'{prefix}  path: "references/{block.name}.md"',
            ]
        )
    return "\n".join(lines)


def director_blueprint(*, include_references: bool) -> RoleBlueprint:
    references = []
    if include_references:
        references = [
            ScaffoldReference(
                name="task-framing",
                title="任务 framing",
                content="""# 任务 framing

## 适用时机

- 需要把一个任务拆成多个可执行子任务。

## 默认规则

1. 先定目标和验收，再定子任务。
2. 每个子任务都要有明确产物、依赖和边界。
3. 不为了并行数量而制造没有价值的任务。

## 输出

- 子任务列表
- 依赖关系
- 最小 skill 装配建议
""",
            ),
            ScaffoldReference(
                name="handoff-contract",
                title="交接契约",
                content="""# 交接契约

## 默认字段

- `summary`
- `decisions`
- `artifacts`
- `acceptance_criteria`
- `open_questions`

## 默认规则

1. 交接只保留下游必须知道的结果与决策。
2. 下游默认消费 handoff，不消费完整上游上下文。

## 输出

- 给下游的最小可执行摘要
""",
            ),
        ]
    return RoleBlueprint(
        default_stance=[
            "先拆目标，再拆子任务。",
            "先定角色和边界，再定 agent 数量。",
            "默认通过 handoff 共享结果，不共享完整上下文。",
        ],
        workflow_steps=[
            "先读取目标、约束和验收标准。",
            "按 `references/task-framing.md` 判断应该拆成哪些子任务。",
            "按 `references/handoff-contract.md` 约束依赖和交接结构。",
            "最后压缩计划规模，只保留真正改变交付结果的子任务。",
        ],
        execution_rules=[
            "每个子任务默认只承担一个主能力。",
            "policy 不直接承担实现，review 不提前消费未稳定结果。",
            "子任务必须明确并行性、依赖和产物。",
        ],
        output_expectations=[
            "子任务列表",
            "依赖顺序",
            "最小 skill 装配面",
            "交接结构",
        ],
        references=references,
        example_request="把一个前端任务拆成多个可执行子任务，并说明依赖顺序与最小 skill 装配。",
    )


def policy_blueprint(*, include_references: bool) -> RoleBlueprint:
    references = []
    if include_references:
        references = [
            ScaffoldReference(
                name="decision-rules",
                title="判断规则",
                content="""# 判断规则

## 适用时机

- 需要先给 worker 总结约束和决策边界。

## 默认规则

1. 先写会改变实现选择的判断，不写泛泛而谈的常识。
2. 优先总结边界、禁忌和可接受写法。
3. 如果仓库已有约定，优先服从仓库约定。

## 输出

- worker 可直接消费的约束摘要
""",
            ),
            ScaffoldReference(
                name="output-contract",
                title="输出契约",
                content="""# 输出契约

## 至少说明

- 哪些做法允许
- 哪些做法禁止
- 哪些决策已收敛
- 哪些问题仍需上游确认

## 默认规则

1. 输出必须让 worker 能直接执行。
2. 不把完整思考过程塞给下游。
""",
            ),
        ]
    return RoleBlueprint(
        default_stance=[
            "先定约束，再交给实现侧。",
            "只总结会改变实现选择的规则。",
            "输出给 worker 的是可执行约束，不是概念解释。",
        ],
        workflow_steps=[
            "先识别哪些边界会改变实现方式。",
            "按 `references/decision-rules.md` 收敛允许与禁止做法。",
            "按 `references/output-contract.md` 整理给 worker 的约束摘要。",
        ],
        execution_rules=[
            "不要直接承担实现。",
            "不要重复解释基础常识，优先说明仓库相关边界。",
            "每条规则都要能回答为什么会影响实现。",
        ],
        output_expectations=[
            "允许的写法",
            "禁止的写法",
            "边界条件",
            "待确认问题",
        ],
        references=references,
        example_request="先总结这个任务的实现约束和边界，再给 worker 一份可直接执行的指导摘要。",
    )


def worker_blueprint(*, include_references: bool) -> RoleBlueprint:
    references = []
    if include_references:
        references = [
            ScaffoldReference(
                name="execution-playbook",
                title="实施流程",
                content="""# 实施流程

## 默认顺序

1. 先确认上游 handoff 和验收标准。
2. 再锁定最小写入面。
3. 先完成主路径，再补边界状态。

## 默认规则

- 不擅自扩权重写上游 policy。
- 只在自己的 ownership 内实现。
""",
            ),
            ScaffoldReference(
                name="handoff-checklist",
                title="交接清单",
                content="""# 交接清单

## 至少说明

- 改了哪些文件
- 实现了哪些能力
- 还缺什么
- 依赖了哪些上游假设

## 默认规则

1. 交接必须能让 review 快速进入状态。
2. 不写“已完成”这种无信息量结论。
""",
            ),
        ]
    return RoleBlueprint(
        default_stance=[
            "worker 只在自己的实现面内推进，不重写上游决策。",
            "先消费 handoff，再实现代码。",
            "交付必须留下可供 review 消费的结构化摘要。",
        ],
        workflow_steps=[
            "先确认消费的 handoff 和验收标准。",
            "按 `references/execution-playbook.md` 实施主路径和边界状态。",
            "按 `references/handoff-checklist.md` 整理交付摘要。",
        ],
        execution_rules=[
            "优先修改最小文件面。",
            "不要把无关逻辑塞进当前实现层。",
            "主路径和边界状态都要有交付落点。",
        ],
        output_expectations=[
            "实现范围",
            "改动产物",
            "剩余风险",
            "上游依赖假设",
        ],
        references=references,
        example_request="根据上游 handoff 完成当前实现面，并给 review 留下一份可直接消费的交接摘要。",
    )


def review_blueprint(*, include_references: bool) -> RoleBlueprint:
    references = []
    if include_references:
        references = [
            ScaffoldReference(
                name="review-checklist",
                title="评审清单",
                content="""# 评审清单

## 默认检查项

1. 主要路径是否被覆盖或验证。
2. 边界状态是否有明确处理。
3. 是否存在明显回归或结构风险。

## 默认规则

- 先写高风险问题，再写一般建议。
- 结论要落到具体路径或模块。
""",
            ),
            ScaffoldReference(
                name="reporting-template",
                title="报告模板",
                content="""# 报告模板

## 输出顺序

1. 主要结论
2. 高风险问题
3. 其余建议
4. 剩余风险

## 默认规则

- 不写泛泛的“需要更多测试”。
- 要说明风险影响和优先级。
""",
            ),
        ]
    return RoleBlueprint(
        default_stance=[
            "review 先看风险和路径，不只看表面完成度。",
            "问题要按严重程度输出。",
            "结论必须能支撑后续是否可继续推进。",
        ],
        workflow_steps=[
            "先读取 worker handoff 和验收标准。",
            "按 `references/review-checklist.md` 扫描主要路径与风险。",
            "按 `references/reporting-template.md` 输出结构化结论。",
        ],
        execution_rules=[
            "高风险问题优先于风格建议。",
            "明确区分阻塞项和观察项。",
            "不要复述实现过程，重点说风险与缺口。",
        ],
        output_expectations=[
            "主要结论",
            "高风险问题",
            "一般建议",
            "剩余风险",
        ],
        references=references,
        example_request="评审当前实现的主要风险、覆盖缺口和剩余问题，并给出结构化结论。",
    )


def build_role_blueprint(role: str, *, include_references: bool) -> RoleBlueprint:
    if role == "director":
        return director_blueprint(include_references=include_references)
    if role == "policy":
        return policy_blueprint(include_references=include_references)
    if role == "worker":
        return worker_blueprint(include_references=include_references)
    if role == "review":
        return review_blueprint(include_references=include_references)
    raise ValueError(f"Unknown role: {role}")


def build_body_markdown(blueprint: RoleBlueprint) -> str:
    sections = [
        "## 默认立场",
        "",
        bullet_lines(blueprint.default_stance),
        "",
        "## 工作流",
        "",
        numbered_lines(blueprint.workflow_steps),
        "",
        "## 执行规则",
        "",
        numbered_lines(blueprint.execution_rules),
        "",
        "## 输出要求",
        "",
        bullet_lines(blueprint.output_expectations),
    ]
    return "\n".join(sections)


def build_skill_context(
    skill_name: str,
    description: str,
    *,
    role: str,
    blueprint: RoleBlueprint,
    domain_tags: list[str] | None = None,
    capabilities: list[str] | None = None,
    handoff_outputs: list[str] | None = None,
    recommends: list[str] | None = None,
    short_description: str | None = None,
    default_prompt: str | None = None,
) -> dict[str, str]:
    title = title_from_skill_name(skill_name)
    short = short_description or title
    prompt = default_prompt or f"使用 ${skill_name} 处理当前任务。"
    domains = list(dict.fromkeys(domain_tags or ["general"]))
    caps = list(dict.fromkeys(capabilities or [f"{role}-capability"]))
    outputs = list(dict.fromkeys(handoff_outputs or [f"{skill_name}-summary"]))
    recommended = list(dict.fromkeys(recommends or []))
    return {
        "name": skill_name,
        "title": title,
        "description": description,
        "short_description": short,
        "default_prompt": prompt,
        "body_markdown": build_body_markdown(blueprint),
        "role": role,
        "domain_tags_json": json.dumps(domains, ensure_ascii=False),
        "capabilities_json": json.dumps(caps, ensure_ascii=False),
        "handoff_outputs_json": json.dumps(outputs, ensure_ascii=False),
        "recommends_json": json.dumps(recommended, ensure_ascii=False),
        "default_blocks_yaml": yaml_list(blueprint.default_blocks, indent=6),
        "blocks_yaml": yaml_blocks(blueprint.references, indent=6),
    }


def create_skill(
    config: WorkbenchConfig,
    name: str,
    *,
    description: str,
    role: str = "worker",
    resources: list[str] | None = None,
    include_examples: bool = False,
    short_description: str | None = None,
    default_prompt: str | None = None,
    domain_tags: list[str] | None = None,
    capabilities: list[str] | None = None,
    handoff_outputs: list[str] | None = None,
    recommends: list[str] | None = None,
) -> Result[Path, AppError]:
    if role not in ROLE_CHOICES:
        return Result.err(app_error(AppErrorCode.INVALID_ARGUMENT, f"Unknown role: {role}", resource=role))
    skill_name = slugify(name)
    skill_dir = config.skills_dir / skill_name
    if skill_dir.exists():
        return Result.err(app_error(AppErrorCode.ALREADY_EXISTS, f"Skill already exists: {skill_dir}", path=str(skill_dir)))
    selected_resources = normalize_resource_choices(resources or ["references"])
    if selected_resources.is_err:
        return Result.err(selected_resources.error)
    include_references = "references" in selected_resources.value
    blueprint = build_role_blueprint(role, include_references=include_references)
    templates = load_skill_templates(config)
    if templates.is_err:
        return Result.err(templates.error)
    context = build_skill_context(
        skill_name,
        description,
        role=role,
        blueprint=blueprint,
        domain_tags=domain_tags,
        capabilities=capabilities,
        handoff_outputs=handoff_outputs,
        recommends=recommends,
        short_description=short_description,
        default_prompt=default_prompt,
    )
    try:
        write_text(skill_dir / "SKILL.md", render_template(templates.value["skill"], context))

        openai_content = render_template(templates.value["openai"], context)
        openai_payload = yaml_loads(openai_content)
        if openai_payload.is_err:
            return Result.err(openai_payload.error.with_context(path=str(skill_dir / "agents" / "openai.yaml")))
        dumped = yaml_dumps(openai_payload.value)
        if dumped.is_err:
            return Result.err(dumped.error.with_context(path=str(skill_dir / "agents" / "openai.yaml")))
        write_text(skill_dir / "agents" / "openai.yaml", dumped.value)

        if include_references:
            for reference in blueprint.references:
                write_text(skill_dir / "references" / f"{reference.name}.md", reference.content)

        example_payload = {"request": blueprint.example_request}
        write_text(skill_dir / "examples" / "basic.json", json.dumps(example_payload, ensure_ascii=False, indent=2) + "\n")

        test_payload = {
            "bundle_contains": [f'name: "{skill_name}"', *[reference.title for reference in blueprint.references]],
            "loaded_blocks": blueprint.default_blocks,
            "reference_count": len(blueprint.references),
            "script_entry_count": 0,
        }
        write_text(skill_dir / "tests" / "basic.json", json.dumps(test_payload, ensure_ascii=False, indent=2) + "\n")

        for resource in selected_resources.value:
            resource_dir = skill_dir / resource
            resource_dir.mkdir(parents=True, exist_ok=True)
            if not include_examples:
                continue
            if resource == "scripts":
                write_text(
                    resource_dir / "example.py",
                    render_template(templates.value["script"], {"name": skill_name}),
                )
            elif resource == "assets":
                write_text(resource_dir / "README.txt", templates.value["asset"])
    except OSError as exc:
        return Result.err(app_error(AppErrorCode.INTERNAL_ERROR, str(exc), path=str(skill_dir)))
    return Result.ok(skill_dir)


__all__ = ["build_skill_context", "create_skill", "normalize_resource_choices"]
