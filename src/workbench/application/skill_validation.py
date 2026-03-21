from __future__ import annotations

"""Use case for linting skill packages."""

from typing import Any

from ..config import WorkbenchConfig
from ..core import Result
from ..domain.errors import AppError
from ..domain.skill import skill_to_record
from ..domain.skill_rules import collect_skill_issues, issue
from ..fs import short_path
from ..infrastructure.skill_loader import discover_skill_dirs, load_skill


def lint_skills(config: WorkbenchConfig, skill_name: str | None = None) -> Result[dict[str, Any], AppError]:
    loaded_dirs = discover_skill_dirs(config)
    if loaded_dirs.is_err:
        return Result.err(loaded_dirs.error)
    selected_dirs = loaded_dirs.value
    if skill_name is not None:
        selected_dirs = [item for item in selected_dirs if item.name == skill_name]
    issues: list[dict[str, str]] = []
    skills = []
    if skill_name is not None and not selected_dirs:
        issues.append(issue("error", f"Skill '{skill_name}' not found", short_path(config.skills_dir, config.root)))
    for skill_dir in selected_dirs:
        loaded = load_skill(skill_dir)
        if loaded.is_err:
            issues.append(issue("error", loaded.error.message, short_path(skill_dir, config.root)))
            continue
        skills.append(loaded.value)
        issues.extend(collect_skill_issues(loaded.value, config.root))
    return Result.ok(
        {
            "skill_count": len(skills),
            "issue_count": len(issues),
            "skills": [skill_to_record(skill, config.root) for skill in skills],
            "issues": issues,
        }
    )


__all__ = ["lint_skills"]
