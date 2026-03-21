from __future__ import annotations

"""Filesystem-backed loading and discovery for Codex skills."""

from pathlib import Path

from ..core import Result
from ..core.yaml import YamlMapping, loads as yaml_loads
from ..domain.config import WorkbenchConfig
from ..domain.errors import AppError, AppErrorCode, app_error
from ..domain.skill import (
    ALLOWED_FRONTMATTER_KEYS,
    ALLOWED_INTERFACE_KEYS,
    ALLOWED_METADATA_KEYS,
    ALLOWED_OPENAI_KEYS,
    ALLOWED_POLICY_KEYS,
    Skill,
    SkillAgentInterface,
    SkillAgentPolicy,
    SkillAgentsConfig,
    SkillFrontmatter,
    SkillMetadata,
)


def reject_unknown_keys(payload: YamlMapping, *, allowed: set[str], label: str, path: Path) -> Result[None, AppError]:
    unknown = sorted(key for key in payload if key not in allowed)
    if unknown:
        return Result.err(app_error(AppErrorCode.PARSE_ERROR, f"{label} contains unknown keys: {', '.join(unknown)}", path=str(path)))
    return Result.ok(None)


def expect_mapping(value: object, *, label: str, path: Path) -> Result[YamlMapping, AppError]:
    if not isinstance(value, dict):
        return Result.err(app_error(AppErrorCode.PARSE_ERROR, f"{label} must be a mapping", path=str(path)))
    return Result.ok(value)


def read_required_string(payload: YamlMapping, *, key: str, label: str, path: Path) -> Result[str, AppError]:
    value = payload.get(key)
    if not isinstance(value, str):
        return Result.err(app_error(AppErrorCode.PARSE_ERROR, f"{label} key '{key}' must be a string", path=str(path)))
    return Result.ok(value)


def read_optional_string(payload: YamlMapping, *, key: str, path: Path) -> Result[str | None, AppError]:
    value = payload.get(key)
    if value is None:
        return Result.ok(None)
    if not isinstance(value, str):
        return Result.err(app_error(AppErrorCode.PARSE_ERROR, f"{path} key '{key}' must be a string", path=str(path)))
    return Result.ok(value)


def read_string_list(payload: YamlMapping, *, key: str, path: Path) -> Result[list[str], AppError]:
    value = payload.get(key)
    if value is None:
        return Result.ok([])
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        return Result.err(app_error(AppErrorCode.PARSE_ERROR, f"{path} key '{key}' must be a list of strings", path=str(path)))
    return Result.ok(list(value))


def read_optional_bool(payload: YamlMapping, *, key: str, path: Path) -> Result[bool | None, AppError]:
    value = payload.get(key)
    if value is None:
        return Result.ok(None)
    if not isinstance(value, bool):
        return Result.err(app_error(AppErrorCode.PARSE_ERROR, f"{path} key '{key}' must be boolean", path=str(path)))
    return Result.ok(value)


def parse_frontmatter_metadata(payload: object, *, path: Path) -> Result[SkillMetadata, AppError]:
    if payload is None:
        return Result.ok(SkillMetadata())
    mapping = expect_mapping(payload, label=f"{path} front matter metadata", path=path)
    if mapping.is_err:
        return Result.err(mapping.error)
    unknown = reject_unknown_keys(mapping.value, allowed=ALLOWED_METADATA_KEYS, label="front matter metadata", path=path)
    if unknown.is_err:
        return Result.err(unknown.error)
    short_description = read_optional_string(mapping.value, key="short-description", path=path)
    if short_description.is_err:
        return Result.err(short_description.error)
    return Result.ok(SkillMetadata(short_description=short_description.value))


def parse_frontmatter(payload: YamlMapping, *, path: Path) -> Result[SkillFrontmatter, AppError]:
    unknown = reject_unknown_keys(payload, allowed=ALLOWED_FRONTMATTER_KEYS, label="front matter", path=path)
    if unknown.is_err:
        return Result.err(unknown.error)
    name = read_required_string(payload, key="name", label=f"{path} front matter", path=path)
    if name.is_err:
        return Result.err(name.error)
    description = read_required_string(payload, key="description", label=f"{path} front matter", path=path)
    if description.is_err:
        return Result.err(description.error)
    license_text = read_optional_string(payload, key="license", path=path)
    if license_text.is_err:
        return Result.err(license_text.error)
    allowed_tools = read_string_list(payload, key="allowed-tools", path=path)
    if allowed_tools.is_err:
        return Result.err(allowed_tools.error)
    metadata = parse_frontmatter_metadata(payload.get("metadata"), path=path)
    if metadata.is_err:
        return Result.err(metadata.error)
    return Result.ok(
        SkillFrontmatter(
            name=name.value,
            description=description.value,
            license=license_text.value,
            allowed_tools=allowed_tools.value,
            metadata=metadata.value,
        )
    )


def parse_agents_interface(payload: object, *, path: Path) -> Result[SkillAgentInterface, AppError]:
    if payload is None:
        return Result.ok(SkillAgentInterface())
    mapping = expect_mapping(payload, label=f"{path} interface", path=path)
    if mapping.is_err:
        return Result.err(mapping.error)
    unknown = reject_unknown_keys(mapping.value, allowed=ALLOWED_INTERFACE_KEYS, label="agents interface", path=path)
    if unknown.is_err:
        return Result.err(unknown.error)
    display_name = read_optional_string(mapping.value, key="display_name", path=path)
    if display_name.is_err:
        return Result.err(display_name.error)
    short_description = read_optional_string(mapping.value, key="short_description", path=path)
    if short_description.is_err:
        return Result.err(short_description.error)
    default_prompt = read_optional_string(mapping.value, key="default_prompt", path=path)
    if default_prompt.is_err:
        return Result.err(default_prompt.error)
    return Result.ok(
        SkillAgentInterface(
            display_name=display_name.value,
            short_description=short_description.value,
            default_prompt=default_prompt.value,
        )
    )


def parse_agents_policy(payload: object, *, path: Path) -> Result[SkillAgentPolicy, AppError]:
    if payload is None:
        return Result.ok(SkillAgentPolicy())
    mapping = expect_mapping(payload, label=f"{path} policy", path=path)
    if mapping.is_err:
        return Result.err(mapping.error)
    unknown = reject_unknown_keys(mapping.value, allowed=ALLOWED_POLICY_KEYS, label="agents policy", path=path)
    if unknown.is_err:
        return Result.err(unknown.error)
    allow_implicit = read_optional_bool(mapping.value, key="allow_implicit_invocation", path=path)
    if allow_implicit.is_err:
        return Result.err(allow_implicit.error)
    return Result.ok(SkillAgentPolicy(allow_implicit_invocation=allow_implicit.value))


def split_frontmatter(content: str, path: Path) -> Result[tuple[SkillFrontmatter, str], AppError]:
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
    mapping = expect_mapping(metadata.value, label=f"{path} front matter", path=path)
    if mapping.is_err:
        return Result.err(mapping.error)
    parsed = parse_frontmatter(mapping.value, path=path)
    if parsed.is_err:
        return Result.err(parsed.error)
    body = "\n".join(lines[end_index + 1 :]).strip() + "\n"
    return Result.ok((parsed.value, body))


def load_markdown_frontmatter(path: Path) -> Result[tuple[SkillFrontmatter, str], AppError]:
    try:
        return split_frontmatter(path.read_text(encoding="utf-8"), path)
    except OSError as exc:
        return Result.err(app_error(AppErrorCode.INTERNAL_ERROR, str(exc), path=str(path)))


def load_openai_yaml(path: Path) -> Result[SkillAgentsConfig, AppError]:
    try:
        raw = yaml_loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        return Result.err(app_error(AppErrorCode.INTERNAL_ERROR, str(exc), path=str(path)))
    if raw.is_err:
        return Result.err(app_error(AppErrorCode.PARSE_ERROR, f"{path} parse failed: {raw.error.message}", path=str(path)))
    mapping = expect_mapping(raw.value, label=str(path), path=path)
    if mapping.is_err:
        return Result.err(mapping.error)
    unknown = reject_unknown_keys(mapping.value, allowed=ALLOWED_OPENAI_KEYS, label="agents/openai.yaml", path=path)
    if unknown.is_err:
        return Result.err(unknown.error)
    interface = parse_agents_interface(mapping.value.get("interface"), path=path)
    if interface.is_err:
        return Result.err(interface.error)
    policy = parse_agents_policy(mapping.value.get("policy"), path=path)
    if policy.is_err:
        return Result.err(policy.error)
    return Result.ok(SkillAgentsConfig(interface=interface.value, policy=policy.value))


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
    agents_path = skill_dir / "agents" / "openai.yaml"
    agents_config: SkillAgentsConfig | None = None
    if agents_path.exists():
        loaded_agents = load_openai_yaml(agents_path)
        if loaded_agents.is_err:
            return Result.err(loaded_agents.error.with_context(skill=str(skill_dir)))
        agents_config = loaded_agents.value
    return Result.ok(
        Skill(
            name=frontmatter.name,
            description=frontmatter.description,
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
