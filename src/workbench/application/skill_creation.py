from __future__ import annotations

"""Use case for scaffolding a new skill package."""

from pathlib import Path

from ..config import WorkbenchConfig
from ..core import Result
from ..domain.errors import AppError, AppErrorCode, app_error
from ..domain.skill import RESOURCE_CHOICES, title_from_skill_name
from ..fs import render_template, slugify, write_text
from ..infrastructure.skill_templates import load_skill_templates
from ..yamlish import dumps as yaml_dumps, loads as yaml_loads


def normalize_resource_choices(resources: list[str] | None) -> Result[list[str], AppError]:
    selected_resources = list(dict.fromkeys(resources or []))
    for resource in selected_resources:
        if resource not in RESOURCE_CHOICES:
            return Result.err(app_error(AppErrorCode.INVALID_ARGUMENT, f"Unknown resource type: {resource}", resource=resource))
    return Result.ok(selected_resources)


def build_skill_context(
    skill_name: str,
    description: str,
    *,
    short_description: str | None = None,
    default_prompt: str | None = None,
) -> dict[str, str]:
    title = title_from_skill_name(skill_name)
    short = short_description or title
    prompt = default_prompt or f"Use ${skill_name} to handle this task."
    return {
        "name": skill_name,
        "title": title,
        "description": description,
        "short_description": short,
        "default_prompt": prompt,
        "overview": "Describe what this skill enables and what it should avoid.",
    }


def create_skill(
    config: WorkbenchConfig,
    name: str,
    *,
    description: str,
    resources: list[str] | None = None,
    include_examples: bool = False,
    short_description: str | None = None,
    default_prompt: str | None = None,
) -> Result[Path, AppError]:
    skill_name = slugify(name)
    skill_dir = config.skills_dir / skill_name
    if skill_dir.exists():
        return Result.err(app_error(AppErrorCode.ALREADY_EXISTS, f"Skill already exists: {skill_dir}", path=str(skill_dir)))
    selected_resources = normalize_resource_choices(resources)
    if selected_resources.is_err:
        return Result.err(selected_resources.error)
    templates = load_skill_templates(config)
    if templates.is_err:
        return Result.err(templates.error)
    context = build_skill_context(
        skill_name,
        description,
        short_description=short_description,
        default_prompt=default_prompt,
    )
    try:
        write_text(skill_dir / "SKILL.md", render_template(templates.value["skill"], context))

        # Normalize the generated YAML through the local parser so the scaffold stays canonical.
        openai_content = render_template(templates.value["openai"], context)
        openai_payload = yaml_loads(openai_content)
        if openai_payload.is_err:
            return Result.err(openai_payload.error.with_context(path=str(skill_dir / "agents" / "openai.yaml")))
        dumped = yaml_dumps(openai_payload.value)
        if dumped.is_err:
            return Result.err(dumped.error.with_context(path=str(skill_dir / "agents" / "openai.yaml")))
        write_text(skill_dir / "agents" / "openai.yaml", dumped.value)

        write_text(skill_dir / "examples" / "basic.json", '{\n  "request": "Replace with a realistic user request."\n}\n')
        write_text(
            skill_dir / "tests" / "basic.json",
            '{\n  "bundle_contains": ["%s"],\n  "reference_count": %d\n}\n'
            % (skill_name, 1 if include_examples and "references" in selected_resources.value else 0),
        )
        for resource in selected_resources.value:
            resource_dir = skill_dir / resource
            resource_dir.mkdir(parents=True, exist_ok=True)
            if not include_examples:
                continue
            if resource == "references":
                write_text(
                    resource_dir / "overview.md",
                    render_template(templates.value["reference"], {"title": context["title"]}),
                )
            elif resource == "scripts":
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
