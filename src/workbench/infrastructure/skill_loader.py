from __future__ import annotations

"""Filesystem-backed loading and discovery for Codex skills."""

from collections.abc import Mapping
from pathlib import Path

from ..core import Result
from ..core.yaml import YamlMapping, YamlValue, loads as yaml_loads
from ..domain.config import WorkbenchConfig
from ..domain.errors import AppError, AppErrorCode, app_error
from ..domain.skill import (
    ALLOWED_BLOCK_KEYS,
    ALLOWED_FRONTMATTER_KEYS,
    ALLOWED_INTERFACE_KEYS,
    ALLOWED_METADATA_KEYS,
    ALLOWED_OPENAI_KEYS,
    ALLOWED_POLICY_KEYS,
    ALLOWED_WORKBENCH_METADATA_KEYS,
    BLOCK_KIND_CHOICES,
    NAME_PATTERN,
    ROLE_CHOICES,
    Skill,
    SkillAgentInterface,
    SkillAgentPolicy,
    SkillAgentsConfig,
    SkillBlock,
    SkillFrontmatter,
    SkillMetadata,
)


def reject_unknown_keys(payload: YamlMapping, *, allowed: set[str], label: str, path: Path) -> Result[None, AppError]:
    unknown = sorted(key for key in payload if key not in allowed)
    if unknown:
        return Result.err(app_error(AppErrorCode.PARSE_ERROR, f"{label} contains unknown keys: {', '.join(unknown)}", path=str(path)))
    return Result.ok(None)


def expect_mapping(value: object, *, label: str, path: Path) -> Result[YamlMapping, AppError]:
    if not isinstance(value, Mapping):
        return Result.err(app_error(AppErrorCode.PARSE_ERROR, f"{label} must be a mapping", path=str(path)))
    return Result.ok(dict(value))


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
    return Result.ok(list(dict.fromkeys(value)))


def read_required_string_list(payload: YamlMapping, *, key: str, path: Path) -> Result[list[str], AppError]:
    values = read_string_list(payload, key=key, path=path)
    if values.is_err:
        return Result.err(values.error)
    if not values.value:
        return Result.err(app_error(AppErrorCode.PARSE_ERROR, f"{path} key '{key}' must not be empty", path=str(path)))
    return values


def read_optional_bool(payload: YamlMapping, *, key: str, path: Path) -> Result[bool | None, AppError]:
    value = payload.get(key)
    if value is None:
        return Result.ok(None)
    if not isinstance(value, bool):
        return Result.err(app_error(AppErrorCode.PARSE_ERROR, f"{path} key '{key}' must be boolean", path=str(path)))
    return Result.ok(value)


def read_required_sequence(payload: YamlMapping, *, key: str, path: Path) -> Result[list[YamlValue], AppError]:
    value = payload.get(key)
    if not isinstance(value, list) or not value:
        return Result.err(app_error(AppErrorCode.PARSE_ERROR, f"{path} key '{key}' must be a non-empty list", path=str(path)))
    return Result.ok(list(value))


def parse_frontmatter_metadata(payload: object, *, path: Path) -> Result[tuple[SkillMetadata, YamlMapping], AppError]:
    if payload is None:
        return Result.err(app_error(AppErrorCode.PARSE_ERROR, f"{path} front matter must declare metadata.workbench", path=str(path)))
    mapping = expect_mapping(payload, label=f"{path} front matter metadata", path=path)
    if mapping.is_err:
        return Result.err(mapping.error)
    unknown = reject_unknown_keys(mapping.value, allowed=ALLOWED_METADATA_KEYS, label="front matter metadata", path=path)
    if unknown.is_err:
        return Result.err(unknown.error)
    short_description = read_optional_string(mapping.value, key="short-description", path=path)
    if short_description.is_err:
        return Result.err(short_description.error)
    workbench = mapping.value.get("workbench")
    if workbench is None:
        return Result.err(app_error(AppErrorCode.PARSE_ERROR, f"{path} metadata must declare workbench", path=str(path)))
    workbench_mapping = expect_mapping(workbench, label=f"{path} metadata.workbench", path=path)
    if workbench_mapping.is_err:
        return Result.err(workbench_mapping.error)
    workbench_unknown = reject_unknown_keys(
        workbench_mapping.value,
        allowed=ALLOWED_WORKBENCH_METADATA_KEYS,
        label="metadata.workbench",
        path=path,
    )
    if workbench_unknown.is_err:
        return Result.err(workbench_unknown.error)
    return Result.ok((SkillMetadata(short_description=short_description.value), workbench_mapping.value))


def parse_block_definition(payload: object, *, path: Path) -> Result[SkillBlock, AppError]:
    mapping = expect_mapping(payload, label=f"{path} block", path=path)
    if mapping.is_err:
        return Result.err(mapping.error)
    unknown = reject_unknown_keys(mapping.value, allowed=ALLOWED_BLOCK_KEYS, label="front matter block", path=path)
    if unknown.is_err:
        return Result.err(unknown.error)
    name = read_required_string(mapping.value, key="name", label=f"{path} block", path=path)
    if name.is_err:
        return Result.err(name.error)
    kind = read_required_string(mapping.value, key="kind", label=f"{path} block", path=path)
    if kind.is_err:
        return Result.err(kind.error)
    if kind.value not in BLOCK_KIND_CHOICES:
        return Result.err(
            app_error(
                AppErrorCode.PARSE_ERROR,
                f"{path} block '{name.value}' uses unsupported kind '{kind.value}'",
                path=str(path),
            )
        )
    block_path = read_optional_string(mapping.value, key="path", path=path)
    if block_path.is_err:
        return Result.err(block_path.error)
    if kind.value == "overview" and block_path.value not in {None, "body"}:
        return Result.err(
            app_error(AppErrorCode.PARSE_ERROR, f"{path} overview block must omit path or use 'body'", path=str(path)))
    if kind.value != "overview" and block_path.value is None:
        return Result.err(
            app_error(AppErrorCode.PARSE_ERROR, f"{path} block '{name.value}' must declare path", path=str(path)))
    if kind.value == "reference" and block_path.value is not None and not block_path.value.startswith("references/"):
        return Result.err(
            app_error(AppErrorCode.PARSE_ERROR, f"{path} reference block must point inside references/", path=str(path)))
    if kind.value == "script_entry" and block_path.value is not None and not block_path.value.startswith("scripts/"):
        return Result.err(
            app_error(AppErrorCode.PARSE_ERROR, f"{path} script_entry block must point inside scripts/", path=str(path)))
    return Result.ok(SkillBlock(name=name.value, kind=kind.value, path=None if block_path.value == "body" else block_path.value))


def parse_blocks(payload: object, *, path: Path) -> Result[list[SkillBlock], AppError]:
    if not isinstance(payload, list) or not payload:
        return Result.err(app_error(AppErrorCode.PARSE_ERROR, f"{path} key 'blocks' must be a non-empty list", path=str(path)))
    blocks: list[SkillBlock] = []
    names: set[str] = set()
    overview_count = 0
    for item in payload:
        parsed = parse_block_definition(item, path=path)
        if parsed.is_err:
            return Result.err(parsed.error)
        if parsed.value.name in names:
            return Result.err(
                app_error(AppErrorCode.PARSE_ERROR, f"{path} block names must be unique: {parsed.value.name}", path=str(path)))
        names.add(parsed.value.name)
        if parsed.value.kind == "overview":
            overview_count += 1
            if parsed.value.name != "overview":
                return Result.err(
                    app_error(AppErrorCode.PARSE_ERROR, f"{path} overview block must be named 'overview'", path=str(path)))
        blocks.append(parsed.value)
    if overview_count != 1:
        return Result.err(app_error(AppErrorCode.PARSE_ERROR, f"{path} must declare exactly one overview block", path=str(path)))
    return Result.ok(blocks)


def validate_frontmatter(frontmatter: SkillFrontmatter, *, path: Path) -> Result[None, AppError]:
    if not NAME_PATTERN.fullmatch(frontmatter.name):
        return Result.err(app_error(AppErrorCode.PARSE_ERROR, f"{path} skill name must use lowercase hyphen-case", path=str(path)))
    if not frontmatter.role_fit:
        return Result.err(app_error(AppErrorCode.PARSE_ERROR, f"{path} metadata.workbench.role-fit must not be empty", path=str(path)))
    invalid_roles = [role for role in frontmatter.role_fit if role not in ROLE_CHOICES]
    if invalid_roles:
        return Result.err(
            app_error(
                AppErrorCode.PARSE_ERROR,
                f"{path} metadata.workbench.role-fit contains unsupported values: {', '.join(sorted(set(invalid_roles)))}",
                path=str(path),
            )
        )
    if not frontmatter.domain_tags:
        return Result.err(app_error(AppErrorCode.PARSE_ERROR, f"{path} metadata.workbench.domain-tags must not be empty", path=str(path)))
    if not frontmatter.capabilities:
        return Result.err(app_error(AppErrorCode.PARSE_ERROR, f"{path} metadata.workbench.capabilities must not be empty", path=str(path)))
    if not frontmatter.handoff_outputs:
        return Result.err(app_error(AppErrorCode.PARSE_ERROR, f"{path} metadata.workbench.handoff-outputs must not be empty", path=str(path)))
    block_names = {block.name for block in frontmatter.blocks}
    if not frontmatter.default_blocks:
        return Result.err(app_error(AppErrorCode.PARSE_ERROR, f"{path} metadata.workbench.default-blocks must not be empty", path=str(path)))
    if "overview" not in frontmatter.default_blocks:
        return Result.err(app_error(AppErrorCode.PARSE_ERROR, f"{path} metadata.workbench.default-blocks must include overview", path=str(path)))
    missing_defaults = sorted(name for name in frontmatter.default_blocks if name not in block_names)
    if missing_defaults:
        return Result.err(
            app_error(
                AppErrorCode.PARSE_ERROR,
                f"{path} metadata.workbench.default-blocks references unknown blocks: {', '.join(missing_defaults)}",
                path=str(path),
            )
        )
    return Result.ok(None)


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
    metadata = parse_frontmatter_metadata(payload.get("metadata"), path=path)
    if metadata.is_err:
        return Result.err(metadata.error)
    workbench = metadata.value[1]
    role_fit = read_required_string_list(workbench, key="role-fit", path=path)
    if role_fit.is_err:
        return Result.err(role_fit.error)
    domain_tags = read_required_string_list(workbench, key="domain-tags", path=path)
    if domain_tags.is_err:
        return Result.err(domain_tags.error)
    capabilities = read_required_string_list(workbench, key="capabilities", path=path)
    if capabilities.is_err:
        return Result.err(capabilities.error)
    default_blocks = read_required_string_list(workbench, key="default-blocks", path=path)
    if default_blocks.is_err:
        return Result.err(default_blocks.error)
    recommends = read_string_list(workbench, key="recommends", path=path)
    if recommends.is_err:
        return Result.err(recommends.error)
    handoff_outputs = read_required_string_list(workbench, key="handoff-outputs", path=path)
    if handoff_outputs.is_err:
        return Result.err(handoff_outputs.error)
    blocks = parse_blocks(workbench.get("blocks"), path=path)
    if blocks.is_err:
        return Result.err(blocks.error)
    license_text = read_optional_string(payload, key="license", path=path)
    if license_text.is_err:
        return Result.err(license_text.error)
    frontmatter = SkillFrontmatter(
        name=name.value,
        description=description.value,
        role_fit=role_fit.value,
        domain_tags=domain_tags.value,
        capabilities=capabilities.value,
        default_blocks=default_blocks.value,
        recommends=recommends.value,
        handoff_outputs=handoff_outputs.value,
        blocks=blocks.value,
        license=license_text.value,
        metadata=metadata.value[0],
    )
    validated = validate_frontmatter(frontmatter, path=path)
    if validated.is_err:
        return Result.err(validated.error)
    return Result.ok(frontmatter)


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


def validate_block_files(skill_dir: Path, frontmatter: SkillFrontmatter) -> Result[None, AppError]:
    for block in frontmatter.blocks:
        if block.kind == "overview":
            continue
        assert block.path is not None  # narrowed above
        candidate = skill_dir / Path(block.path)
        if not candidate.exists():
            return Result.err(
                app_error(
                    AppErrorCode.PARSE_ERROR,
                    f"{skill_dir / 'SKILL.md'} block '{block.name}' points to missing file: {block.path}",
                    path=str(skill_dir / "SKILL.md"),
                )
            )
        if not candidate.is_file():
            return Result.err(
                app_error(
                    AppErrorCode.PARSE_ERROR,
                    f"{skill_dir / 'SKILL.md'} block '{block.name}' must point to a file: {block.path}",
                    path=str(skill_dir / "SKILL.md"),
                )
            )
    return Result.ok(None)


def load_skill(skill_dir: Path) -> Result[Skill, AppError]:
    frontmatter_result = load_markdown_frontmatter(skill_dir / "SKILL.md")
    if frontmatter_result.is_err:
        return Result.err(frontmatter_result.error.with_context(skill=str(skill_dir)))
    frontmatter, body = frontmatter_result.value
    block_files = validate_block_files(skill_dir, frontmatter)
    if block_files.is_err:
        return Result.err(block_files.error.with_context(skill=str(skill_dir)))
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
