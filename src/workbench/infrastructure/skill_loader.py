from __future__ import annotations

"""Filesystem-backed loading and discovery for Codex skills."""

from pathlib import Path
from typing import Any

from ..config import WorkbenchConfig
from ..core import Result
from ..domain.errors import AppError, AppErrorCode, app_error
from ..domain.skill import Skill
from ..yamlish import loads as yaml_loads


def split_frontmatter(content: str, path: Path) -> Result[tuple[dict[str, Any], str], AppError]:
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return Result.err(app_error(AppErrorCode.PARSE_ERROR, f"{path} is missing YAML front matter", path=str(path)))
    try:
        end_index = lines[1:].index("---") + 1
    except ValueError:
        return Result.err(app_error(AppErrorCode.PARSE_ERROR, f"{path} has unterminated YAML front matter", path=str(path)))
    metadata_text = "\n".join(lines[1:end_index])
    metadata = yaml_loads(metadata_text)
    if metadata.is_err:
        return Result.err(app_error(AppErrorCode.PARSE_ERROR, f"{path} front matter parse failed: {metadata.error.message}", path=str(path)))
    if not isinstance(metadata.value, dict):
        return Result.err(app_error(AppErrorCode.PARSE_ERROR, f"{path} front matter must be a mapping", path=str(path)))
    body = "\n".join(lines[end_index + 1 :]).strip() + "\n"
    return Result.ok((metadata.value, body))


def load_markdown_frontmatter(path: Path) -> Result[tuple[dict[str, Any], str], AppError]:
    try:
        return split_frontmatter(path.read_text(encoding="utf-8"), path)
    except OSError as exc:
        return Result.err(app_error(AppErrorCode.INTERNAL_ERROR, str(exc), path=str(path)))


def load_openai_yaml(path: Path) -> Result[dict[str, Any], AppError]:
    try:
        raw = yaml_loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        return Result.err(app_error(AppErrorCode.INTERNAL_ERROR, str(exc), path=str(path)))
    if raw.is_err:
        return Result.err(app_error(AppErrorCode.PARSE_ERROR, f"{path} parse failed: {raw.error.message}", path=str(path)))
    if not isinstance(raw.value, dict):
        return Result.err(app_error(AppErrorCode.PARSE_ERROR, f"{path} must contain a YAML mapping", path=str(path)))
    return Result.ok(raw.value)


def collect_files(path: Path, pattern: str = "*", *, recursive: bool = False) -> list[Path]:
    if not path.exists():
        return []
    iterator = path.rglob(pattern) if recursive else path.glob(pattern)
    return sorted(candidate for candidate in iterator if candidate.is_file())


def load_skill(skill_dir: Path) -> Result[Skill, AppError]:
    frontmatter_result = load_markdown_frontmatter(skill_dir / "SKILL.md")
    if frontmatter_result.is_err:
        return Result.err(frontmatter_result.error.with_context(skill=str(skill_dir)))
    frontmatter, body = frontmatter_result.value
    name = frontmatter.get("name")
    description = frontmatter.get("description")
    if not isinstance(name, str):
        return Result.err(
            app_error(
                AppErrorCode.PARSE_ERROR,
                f"{skill_dir / 'SKILL.md'} front matter key 'name' must be a string",
                path=str(skill_dir),
            )
        )
    if not isinstance(description, str):
        return Result.err(
            app_error(
                AppErrorCode.PARSE_ERROR,
                f"{skill_dir / 'SKILL.md'} front matter key 'description' must be a string",
                path=str(skill_dir),
            )
        )
    agents_path = skill_dir / "agents" / "openai.yaml"
    agents_config: dict[str, Any] | None = None
    if agents_path.exists():
        loaded_agents = load_openai_yaml(agents_path)
        if loaded_agents.is_err:
            return Result.err(loaded_agents.error.with_context(skill=str(skill_dir)))
        agents_config = loaded_agents.value
    return Result.ok(
        Skill(
            name=name,
            description=description,
            body=body,
            frontmatter=frontmatter,
            path=skill_dir,
            agents_path=agents_path if agents_path.exists() else None,
            agents_config=agents_config,
            references=collect_files(skill_dir / "references", recursive=True),
            scripts=collect_files(skill_dir / "scripts", recursive=True),
            assets=collect_files(skill_dir / "assets", recursive=True),
            examples=collect_files(skill_dir / "examples", "*.json"),
            tests=collect_files(skill_dir / "tests", "*.json"),
        )
    )


def discover_skill_dirs(config: WorkbenchConfig) -> Result[list[Path], AppError]:
    if not config.skills_dir.exists():
        return Result.ok([])
    try:
        return Result.ok(sorted(skill_md.parent for skill_md in config.skills_dir.rglob("SKILL.md")))
    except OSError as exc:
        return Result.err(app_error(AppErrorCode.INTERNAL_ERROR, str(exc), path=str(config.skills_dir)))


def discover_skills(config: WorkbenchConfig) -> Result[list[Skill], AppError]:
    skill_dirs = discover_skill_dirs(config)
    if skill_dirs.is_err:
        return Result.err(skill_dirs.error)
    skills: list[Skill] = []
    for skill_dir in skill_dirs.value:
        loaded = load_skill(skill_dir)
        if loaded.is_err:
            return Result.err(loaded.error)
        skills.append(loaded.value)
    return Result.ok(skills)


__all__ = [
    "collect_files",
    "discover_skill_dirs",
    "discover_skills",
    "load_markdown_frontmatter",
    "load_openai_yaml",
    "load_skill",
    "split_frontmatter",
]
