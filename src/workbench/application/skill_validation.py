from __future__ import annotations

"""Use case for linting skill packages."""

from dataclasses import asdict
from pathlib import Path
from typing import Any

from ..core import Result
from ..domain.config import WorkbenchConfig
from ..domain.errors import AppError
from ..domain.skill import ALLOWED_FRONTMATTER_KEYS, NAME_PATTERN, RESOURCE_PATTERN, Skill
from ..infrastructure.filesystem import short_path
from ..infrastructure.filesystem import read_json
from ..infrastructure.skill_loader import discover_skill_dirs, load_skill

SkillIssue = dict[str, str]


def issue(level: str, message: str, path: str) -> SkillIssue:
    """构造统一的 lint issue 记录。"""

    return {"level": level, "message": message, "path": path}


def skill_to_record(skill: Skill, root: Path) -> dict[str, Any]:
    """把 Skill 投影为适合 CLI 返回的记录结构。"""

    payload = asdict(skill)
    payload.pop("body", None)
    payload["path"] = short_path(skill.path, root)
    payload["agents_path"] = short_path(skill.agents_path, root) if skill.agents_path else None
    payload["references"] = [short_path(path, root) for path in skill.references]
    payload["scripts"] = [short_path(path, root) for path in skill.scripts]
    payload["assets"] = [short_path(path, root) for path in skill.assets]
    payload["examples"] = [short_path(path, root) for path in skill.examples]
    payload["tests"] = [short_path(path, root) for path in skill.tests]
    return payload


def collect_frontmatter_issues(skill: Skill, root: Path) -> list[SkillIssue]:
    """检查 front matter 的语义约束。"""

    issues: list[SkillIssue] = []
    unexpected = sorted(set(skill.frontmatter) - ALLOWED_FRONTMATTER_KEYS)
    if unexpected:
        issues.append(
            issue(
                "error",
                f"Unexpected front matter keys: {', '.join(unexpected)}",
                short_path(skill.path / "SKILL.md", root),
            )
        )
    if not NAME_PATTERN.fullmatch(skill.name):
        issues.append(
            issue(
                "error",
                f"Invalid skill name '{skill.name}'. Use lowercase hyphen-case.",
                short_path(skill.path / "SKILL.md", root),
            )
        )
    if skill.path.name != skill.name:
        issues.append(
            issue(
                "error",
                f"Directory name '{skill.path.name}' does not match skill name '{skill.name}'",
                short_path(skill.path, root),
            )
        )
    description = skill.description.strip()
    if not description:
        issues.append(issue("error", "Description cannot be empty", short_path(skill.path / "SKILL.md", root)))
    if "<" in description or ">" in description:
        issues.append(issue("error", "Description cannot contain angle brackets", short_path(skill.path / "SKILL.md", root)))
    if len(description) > 1024:
        issues.append(issue("error", "Description is too long", short_path(skill.path / "SKILL.md", root)))
    return issues


def collect_agents_issues(skill: Skill, root: Path) -> list[SkillIssue]:
    """检查 `agents/openai.yaml` 的结构和关键字段。"""

    if skill.agents_path is None:
        return []
    issues: list[SkillIssue] = []
    data = skill.agents_config or {}
    interface = data.get("interface", {})
    if not isinstance(interface, dict):
        issues.append(issue("error", "agents/openai.yaml interface must be a mapping", short_path(skill.agents_path, root)))
        return issues
    short_description = interface.get("short_description")
    if short_description is not None and not isinstance(short_description, str):
        issues.append(issue("error", "interface.short_description must be a string", short_path(skill.agents_path, root)))
    default_prompt = interface.get("default_prompt")
    if default_prompt is not None:
        if not isinstance(default_prompt, str):
            issues.append(issue("error", "interface.default_prompt must be a string", short_path(skill.agents_path, root)))
        elif f"${skill.name}" not in default_prompt:
            issues.append(
                issue(
                    "warning",
                    f"interface.default_prompt should mention ${skill.name}",
                    short_path(skill.agents_path, root),
                )
            )
    policy = data.get("policy", {})
    if policy and not isinstance(policy, dict):
        issues.append(issue("error", "policy must be a mapping", short_path(skill.agents_path, root)))
        return issues
    allow_implicit = policy.get("allow_implicit_invocation")
    if allow_implicit is not None and not isinstance(allow_implicit, bool):
        issues.append(issue("error", "policy.allow_implicit_invocation must be boolean", short_path(skill.agents_path, root)))
    return issues


def collect_resource_reference_issues(skill: Skill, root: Path) -> list[SkillIssue]:
    """检查正文里声明的资源路径是否真实存在。"""

    issues: list[SkillIssue] = []
    for match in RESOURCE_PATTERN.finditer(skill.body):
        candidate = skill.path / Path(match.group("path"))
        if not candidate.exists():
            issues.append(
                issue(
                    "error",
                    f"Referenced resource does not exist: {match.group('path')}",
                    short_path(skill.path / "SKILL.md", root),
                )
            )
    return issues


def collect_fixture_issues(skill: Skill, root: Path) -> list[SkillIssue]:
    """检查 example / test 夹具的 JSON 结构。"""

    issues: list[SkillIssue] = []
    for example_path in skill.examples:
        try:
            read_json(example_path)
        except Exception as exc:  # pragma: no cover
            issues.append(issue("error", f"Invalid example JSON: {exc}", short_path(example_path, root)))
    for test_path in skill.tests:
        try:
            fixture = read_json(test_path)
        except Exception as exc:  # pragma: no cover
            issues.append(issue("error", f"Invalid test JSON: {exc}", short_path(test_path, root)))
            continue
        if "bundle_contains" not in fixture:
            issues.append(issue("error", "Test fixture missing bundle_contains", short_path(test_path, root)))
    return issues


def collect_skill_issues(skill: Skill, root: Path) -> list[SkillIssue]:
    """汇总单个 skill 的全部 lint issue。"""

    issues: list[SkillIssue] = []
    issues.extend(collect_frontmatter_issues(skill, root))
    issues.extend(collect_agents_issues(skill, root))
    issues.extend(collect_resource_reference_issues(skill, root))
    issues.extend(collect_fixture_issues(skill, root))
    return issues


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
