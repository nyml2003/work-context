from __future__ import annotations

"""Use cases for skill context assembly and fixture execution."""

from collections.abc import Mapping
from pathlib import Path

from ..core import Result
from ..core.serialization import JsonValue
from ..core.yaml import dumps as yaml_dumps
from ..domain.config import WorkbenchConfig
from ..domain.errors import AppError, AppErrorCode, app_error
from ..domain.skill import (
    Skill,
    SkillAssembly,
    SkillBlock,
    SkillBundleReference,
    SkillLoadedBlock,
    SkillScriptEntry,
    SkillTestPayload,
    SkillTestResult,
    agents_config_to_yaml,
    block_lookup,
    frontmatter_to_yaml,
)
from ..infrastructure.filesystem import read_json, short_path
from ..infrastructure.skill_loader import discover_skills


def select_blocks(skill: Skill, block_names: list[str] | None = None) -> Result[list[SkillBlock], AppError]:
    names = list(dict.fromkeys(block_names or skill.frontmatter.default_blocks))
    lookup = block_lookup(skill.frontmatter.blocks)
    missing = [name for name in names if name not in lookup]
    if missing:
        return Result.err(
            app_error(
                AppErrorCode.NOT_FOUND,
                f"Skill '{skill.name}' does not define blocks: {', '.join(missing)}",
                skill=skill.name,
            )
        )
    return Result.ok([lookup[name] for name in names])


def assemble_skill_context(
    skill: Skill,
    config: WorkbenchConfig,
    *,
    block_names: list[str] | None = None,
) -> Result[SkillAssembly, AppError]:
    dumped_frontmatter = yaml_dumps(frontmatter_to_yaml(skill.frontmatter))
    if dumped_frontmatter.is_err:
        return Result.err(dumped_frontmatter.error.with_context(path=str(skill.path / "SKILL.md")))
    selected = select_blocks(skill, block_names=block_names)
    if selected.is_err:
        return Result.err(selected.error)
    sections = [
        "# Skill Context",
        "",
        f"- name: {skill.name}",
        f"- path: {short_path(skill.path, config.root)}",
        "",
        "## SKILL.md Front Matter",
        "",
        dumped_frontmatter.value.strip(),
        "",
    ]
    if skill.agents_path and skill.agents_config:
        dumped_agents = yaml_dumps(agents_config_to_yaml(skill.agents_config))
        if dumped_agents.is_err:
            return Result.err(dumped_agents.error.with_context(path=str(skill.agents_path)))
        sections.extend(["## agents/openai.yaml", "", dumped_agents.value.strip(), ""])
    loaded_blocks: list[SkillLoadedBlock] = []
    references: list[SkillBundleReference] = []
    script_entries: list[SkillScriptEntry] = []
    try:
        for block in selected.value:
            if block.kind == "overview":
                loaded_blocks.append(SkillLoadedBlock(skill=skill.name, name=block.name, kind=block.kind))
                sections.extend(["## overview", "", skill.body.strip(), ""])
                continue
            assert block.path is not None  # narrowed by loader
            target = skill.path / Path(block.path)
            loaded_blocks.append(
                SkillLoadedBlock(skill=skill.name, name=block.name, kind=block.kind, path=short_path(target, config.root))
            )
            if block.kind == "reference":
                references.append(
                    SkillBundleReference(path=short_path(target, config.root), name=target.name)
                )
                sections.extend([f"## {block.name}", "", target.read_text(encoding="utf-8").strip(), ""])
                continue
            script_entries.append(
                SkillScriptEntry(skill=skill.name, name=block.name, path=short_path(target, config.root))
            )
        if script_entries:
            sections.extend(["## script entries", ""])
            for entry in script_entries:
                sections.extend([f"- {entry.name}: {entry.path}"])
            sections.append("")
    except OSError as exc:
        return Result.err(app_error(AppErrorCode.INTERNAL_ERROR, str(exc), path=str(skill.path)))
    return Result.ok(
        SkillAssembly(
            skill=skill.name,
            loaded_blocks=loaded_blocks,
            references=references,
            script_entries=script_entries,
            bundle_markdown="\n".join(sections).rstrip() + "\n",
        )
    )


def expect_fixture_mapping(payload: JsonValue) -> Mapping[str, JsonValue] | None:
    return payload if isinstance(payload, dict) else None


def test_skills(config: WorkbenchConfig, skill_name: str | None = None) -> Result[SkillTestPayload, AppError]:
    discovered = discover_skills(config)
    if discovered.is_err:
        return Result.err(discovered.error)
    results: list[SkillTestResult] = []
    failures = 0
    for skill in discovered.value:
        if skill_name is not None and skill.name != skill_name:
            continue
        assembly_result = assemble_skill_context(skill, config)
        if assembly_result.is_err:
            return Result.err(assembly_result.error)
        assembly = assembly_result.value
        if not skill.tests:
            results.append(SkillTestResult(skill=skill.name, fixture=None, status="skipped", reason="No test fixtures"))
            continue
        for fixture_path in skill.tests:
            try:
                fixture = read_json(fixture_path)
            except Exception as exc:  # pragma: no cover
                return Result.err(app_error(AppErrorCode.PARSE_ERROR, str(exc), path=str(fixture_path)))
            mapping = expect_fixture_mapping(fixture)
            if mapping is None:
                return Result.err(app_error(AppErrorCode.PARSE_ERROR, "Fixture must be a JSON object", path=str(fixture_path)))
            bundle_contains = mapping.get("bundle_contains", [])
            if not isinstance(bundle_contains, list) or any(not isinstance(item, str) for item in bundle_contains):
                return Result.err(app_error(AppErrorCode.PARSE_ERROR, "bundle_contains must be a list of strings", path=str(fixture_path)))
            reference_count = mapping.get("reference_count")
            if reference_count is not None and not isinstance(reference_count, int):
                return Result.err(app_error(AppErrorCode.PARSE_ERROR, "reference_count must be an integer", path=str(fixture_path)))
            script_entry_count = mapping.get("script_entry_count")
            if script_entry_count is not None and not isinstance(script_entry_count, int):
                return Result.err(app_error(AppErrorCode.PARSE_ERROR, "script_entry_count must be an integer", path=str(fixture_path)))
            loaded_blocks = mapping.get("loaded_blocks")
            if loaded_blocks is not None and (
                not isinstance(loaded_blocks, list) or any(not isinstance(item, str) for item in loaded_blocks)
            ):
                return Result.err(app_error(AppErrorCode.PARSE_ERROR, "loaded_blocks must be a list of strings", path=str(fixture_path)))
            missing_strings = [token for token in bundle_contains if token not in assembly.bundle_markdown]
            expected_reference_count = reference_count
            expected_script_entry_count = script_entry_count
            expected_loaded_blocks = list(loaded_blocks or [])
            actual_loaded_blocks = [block.name for block in assembly.loaded_blocks]
            counts_ok = expected_reference_count is None or expected_reference_count == len(assembly.references)
            scripts_ok = expected_script_entry_count is None or expected_script_entry_count == len(assembly.script_entries)
            blocks_ok = not expected_loaded_blocks or expected_loaded_blocks == actual_loaded_blocks
            passed = not missing_strings and counts_ok and scripts_ok and blocks_ok
            if not passed:
                failures += 1
            results.append(
                SkillTestResult(
                    skill=skill.name,
                    fixture=short_path(fixture_path, config.root),
                    status="passed" if passed else "failed",
                    missing_strings=missing_strings,
                    expected_reference_count=expected_reference_count,
                    actual_reference_count=len(assembly.references),
                    expected_script_entry_count=expected_script_entry_count,
                    actual_script_entry_count=len(assembly.script_entries),
                    expected_loaded_blocks=expected_loaded_blocks,
                    actual_loaded_blocks=actual_loaded_blocks,
                )
            )
    return Result.ok(SkillTestPayload(failure_count=failures, results=results))


__all__ = ["assemble_skill_context", "test_skills"]
