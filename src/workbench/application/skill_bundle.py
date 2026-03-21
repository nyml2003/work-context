from __future__ import annotations

"""Use cases for bundle rendering and fixture execution."""

from typing import Any

from ..config import WorkbenchConfig
from ..core import Result
from ..domain.errors import AppError, AppErrorCode, app_error
from ..domain.skill import Skill
from ..fs import read_json, short_path
from ..infrastructure.skill_loader import discover_skills
from ..yamlish import dumps as yaml_dumps


def render_bundle(skill: Skill, config: WorkbenchConfig) -> Result[tuple[str, list[dict[str, str]]], AppError]:
    dumped_frontmatter = yaml_dumps(skill.frontmatter)
    if dumped_frontmatter.is_err:
        return Result.err(dumped_frontmatter.error.with_context(path=str(skill.path / "SKILL.md")))
    references = [path for path in skill.references if path.is_file()]
    sections = [
        "# Skill Bundle",
        "",
        f"- name: {skill.name}",
        f"- path: {short_path(skill.path, config.root)}",
        "",
        "## SKILL.md Front Matter",
        "",
        dumped_frontmatter.value.strip(),
        "",
        "## SKILL.md Body",
        "",
        skill.body.strip(),
        "",
    ]
    if skill.agents_path and skill.agents_config:
        dumped_agents = yaml_dumps(skill.agents_config)
        if dumped_agents.is_err:
            return Result.err(dumped_agents.error.with_context(path=str(skill.agents_path)))
        sections.extend(["## agents/openai.yaml", "", dumped_agents.value.strip(), ""])
    linked_references: list[dict[str, str]] = []
    try:
        if references:
            sections.extend(["## references/", ""])
            for reference_path in references:
                linked_references.append({"path": short_path(reference_path, config.root), "name": reference_path.name})
                sections.extend([f"### {reference_path.name}", "", reference_path.read_text(encoding="utf-8").strip(), ""])
    except OSError as exc:
        return Result.err(app_error(AppErrorCode.INTERNAL_ERROR, str(exc), path=str(skill.path)))
    return Result.ok(("\n".join(sections).rstrip() + "\n", linked_references))


def test_skills(config: WorkbenchConfig, skill_name: str | None = None) -> Result[dict[str, Any], AppError]:
    discovered = discover_skills(config)
    if discovered.is_err:
        return Result.err(discovered.error)
    results: list[dict[str, Any]] = []
    failures = 0
    for skill in discovered.value:
        if skill_name is not None and skill.name != skill_name:
            continue
        bundle_result = render_bundle(skill, config)
        if bundle_result.is_err:
            return Result.err(bundle_result.error)
        bundle, references = bundle_result.value
        if not skill.tests:
            results.append({"skill": skill.name, "status": "skipped", "reason": "No test fixtures"})
            continue
        for fixture_path in skill.tests:
            try:
                fixture = read_json(fixture_path)
            except Exception as exc:  # pragma: no cover
                return Result.err(app_error(AppErrorCode.PARSE_ERROR, str(exc), path=str(fixture_path)))
            missing_strings = [token for token in fixture.get("bundle_contains", []) if token not in bundle]
            expected_count = fixture.get("reference_count")
            count_ok = expected_count is None or expected_count == len(references)
            passed = not missing_strings and count_ok
            if not passed:
                failures += 1
            results.append(
                {
                    "skill": skill.name,
                    "fixture": short_path(fixture_path, config.root),
                    "status": "passed" if passed else "failed",
                    "missing_strings": missing_strings,
                    "expected_reference_count": expected_count,
                    "actual_reference_count": len(references),
                }
            )
    return Result.ok({"failure_count": failures, "results": results})


__all__ = ["render_bundle", "test_skills"]
