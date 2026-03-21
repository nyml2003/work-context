from __future__ import annotations

"""Pure validation rules for skill metadata and fixtures."""

from pathlib import Path

from ..fs import read_json, short_path
from .skill import ALLOWED_FRONTMATTER_KEYS, NAME_PATTERN, RESOURCE_PATTERN, Skill

SkillIssue = dict[str, str]


def issue(level: str, message: str, path: str) -> SkillIssue:
    return {"level": level, "message": message, "path": path}


def collect_frontmatter_issues(skill: Skill, root: Path) -> list[SkillIssue]:
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
    issues: list[SkillIssue] = []
    issues.extend(collect_frontmatter_issues(skill, root))
    issues.extend(collect_agents_issues(skill, root))
    issues.extend(collect_resource_reference_issues(skill, root))
    issues.extend(collect_fixture_issues(skill, root))
    return issues


__all__ = [
    "SkillIssue",
    "collect_agents_issues",
    "collect_fixture_issues",
    "collect_frontmatter_issues",
    "collect_resource_reference_issues",
    "collect_skill_issues",
    "issue",
]
