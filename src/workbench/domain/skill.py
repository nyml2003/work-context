from __future__ import annotations

"""Skill 领域模型与共享约束。"""

import re
from dataclasses import dataclass, field
from pathlib import Path

from ..core.serialization import JsonValue
from ..core.yaml import YamlMapping, YamlValue

ALLOWED_FRONTMATTER_KEYS = {
    "name",
    "description",
    "license",
    "metadata",
    "argument-hint",
    "compatibility",
    "disable-model-invocation",
    "user-invokable",
}
ALLOWED_METADATA_KEYS = {"short-description", "workbench"}
ALLOWED_WORKBENCH_METADATA_KEYS = {
    "role-fit",
    "domain-tags",
    "capabilities",
    "default-blocks",
    "recommends",
    "handoff-outputs",
    "blocks",
}
ALLOWED_BLOCK_KEYS = {"name", "kind", "path"}
ALLOWED_OPENAI_KEYS = {"interface", "policy"}
ALLOWED_INTERFACE_KEYS = {"display_name", "short_description", "default_prompt"}
ALLOWED_POLICY_KEYS = {"allow_implicit_invocation"}
NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
RESOURCE_PATTERN = re.compile(r"(?P<path>(?:references|scripts)/[A-Za-z0-9._/\\-]+)")
RESOURCE_CHOICES = ("scripts", "references", "assets")
ROLE_CHOICES = ("director", "policy", "worker", "review")
BLOCK_KIND_CHOICES = ("overview", "reference", "script_entry")


@dataclass(frozen=True, slots=True)
class SkillMetadata:
    """front matter 里的 metadata 子结构。"""

    short_description: str | None = None


@dataclass(frozen=True, slots=True)
class SkillBlock:
    """`SKILL.md` front matter 中声明的可装配块。"""

    name: str
    kind: str
    path: str | None = None


@dataclass(frozen=True, slots=True)
class SkillFrontmatter:
    """`SKILL.md` front matter 的强类型模型。"""

    name: str
    description: str
    role_fit: list[str]
    domain_tags: list[str]
    capabilities: list[str]
    default_blocks: list[str]
    recommends: list[str]
    handoff_outputs: list[str]
    blocks: list[SkillBlock]
    license: str | None = None
    metadata: SkillMetadata = field(default_factory=SkillMetadata)


@dataclass(frozen=True, slots=True)
class SkillAgentInterface:
    """`agents/openai.yaml` 的 interface 部分。"""

    display_name: str | None = None
    short_description: str | None = None
    default_prompt: str | None = None


@dataclass(frozen=True, slots=True)
class SkillAgentPolicy:
    """`agents/openai.yaml` 的 policy 部分。"""

    allow_implicit_invocation: bool | None = None


@dataclass(frozen=True, slots=True)
class SkillAgentsConfig:
    """`agents/openai.yaml` 的强类型模型。"""

    interface: SkillAgentInterface = field(default_factory=SkillAgentInterface)
    policy: SkillAgentPolicy = field(default_factory=SkillAgentPolicy)


@dataclass(slots=True)
class Skill:
    """运行时 skill 聚合对象。"""

    name: str
    description: str
    body: str
    frontmatter: SkillFrontmatter
    path: Path
    agents_path: Path | None
    agents_config: SkillAgentsConfig | None
    references: list[Path]
    scripts: list[Path]
    assets: list[Path]
    examples: list[Path]
    tests: list[Path]


@dataclass(frozen=True, slots=True)
class SkillIssue:
    """skill lint issue。"""

    level: str
    message: str
    path: str


@dataclass(frozen=True, slots=True)
class SkillLoadedBlock:
    """一次上下文装配中已加载的块。"""

    skill: str
    name: str
    kind: str
    path: str | None = None


@dataclass(frozen=True, slots=True)
class SkillScriptEntry:
    """上下文中暴露给 agent 的脚本入口。"""

    skill: str
    name: str
    path: str


@dataclass(frozen=True, slots=True)
class SkillSummary:
    """面向 CLI / report 的 skill 摘要。"""

    name: str
    description: str
    path: str
    role_fit: list[str]
    domain_tags: list[str]
    capabilities: list[str]
    default_blocks: list[str]
    recommends: list[str]
    handoff_outputs: list[str]
    blocks: list[SkillBlock]
    agents_path: str | None
    agents_config: dict[str, JsonValue] | None
    references: list[str]
    scripts: list[str]
    assets: list[str]
    examples: list[str]
    tests: list[str]


@dataclass(frozen=True, slots=True)
class SkillLintPayload:
    """skill lint 聚合结果。"""

    skill_count: int
    issue_count: int
    skills: list[SkillSummary]
    issues: list[SkillIssue]


@dataclass(frozen=True, slots=True)
class SkillBundleReference:
    """bundle 里暴露给调用方的引用记录。"""

    path: str
    name: str


@dataclass(frozen=True, slots=True)
class SkillAssembly:
    """单个 skill 的装配结果。"""

    skill: str
    loaded_blocks: list[SkillLoadedBlock]
    references: list[SkillBundleReference]
    script_entries: list[SkillScriptEntry]
    bundle_markdown: str


@dataclass(frozen=True, slots=True)
class SkillTestResult:
    """单个 fixture 的执行结果。"""

    skill: str
    fixture: str | None
    status: str
    reason: str | None = None
    missing_strings: list[str] = field(default_factory=list)
    expected_reference_count: int | None = None
    actual_reference_count: int | None = None
    expected_script_entry_count: int | None = None
    actual_script_entry_count: int | None = None
    expected_loaded_blocks: list[str] = field(default_factory=list)
    actual_loaded_blocks: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class SkillTestPayload:
    """skill fixture 测试汇总。"""

    failure_count: int
    results: list[SkillTestResult]


@dataclass(frozen=True, slots=True)
class SkillLinkRecord:
    """skill link 的单项结果。"""

    skill: str
    source: str
    destination: str
    status: str


@dataclass(frozen=True, slots=True)
class SkillLinkPayload:
    """skill link 的命令返回体。"""

    target: str
    linked: list[SkillLinkRecord]


def block_to_payload(block: SkillBlock) -> dict[str, JsonValue]:
    payload: dict[str, JsonValue] = {
        "name": block.name,
        "kind": block.kind,
    }
    if block.path is not None:
        payload["path"] = block.path
    return payload


def block_to_yaml(block: SkillBlock) -> YamlMapping:
    payload: YamlMapping = {
        "name": block.name,
        "kind": block.kind,
    }
    if block.path is not None:
        payload["path"] = block.path
    return payload


def frontmatter_to_yaml(frontmatter: SkillFrontmatter) -> YamlMapping:
    """把 front matter 还原成 YAML 需要的原始键名。"""

    payload: YamlMapping = {
        "name": frontmatter.name,
        "description": frontmatter.description,
    }
    if frontmatter.license is not None:
        payload["license"] = frontmatter.license
    metadata: YamlMapping = {
        "workbench": {
            "role-fit": list(frontmatter.role_fit),
            "domain-tags": list(frontmatter.domain_tags),
            "capabilities": list(frontmatter.capabilities),
            "default-blocks": list(frontmatter.default_blocks),
            "recommends": list(frontmatter.recommends),
            "handoff-outputs": list(frontmatter.handoff_outputs),
            "blocks": [block_to_yaml(block) for block in frontmatter.blocks],
        }
    }
    if frontmatter.metadata.short_description is not None:
        metadata["short-description"] = frontmatter.metadata.short_description
    payload["metadata"] = metadata
    return payload


def frontmatter_to_payload(frontmatter: SkillFrontmatter) -> dict[str, JsonValue]:
    """把 front matter 投影为稳定 JSON 结构。"""

    payload: dict[str, JsonValue] = {
        "name": frontmatter.name,
        "description": frontmatter.description,
    }
    if frontmatter.license is not None:
        payload["license"] = frontmatter.license
    metadata: dict[str, JsonValue] = {
        "workbench": {
            "role-fit": list(frontmatter.role_fit),
            "domain-tags": list(frontmatter.domain_tags),
            "capabilities": list(frontmatter.capabilities),
            "default-blocks": list(frontmatter.default_blocks),
            "recommends": list(frontmatter.recommends),
            "handoff-outputs": list(frontmatter.handoff_outputs),
            "blocks": [block_to_payload(block) for block in frontmatter.blocks],
        }
    }
    if frontmatter.metadata.short_description is not None:
        metadata["short-description"] = frontmatter.metadata.short_description
    payload["metadata"] = metadata
    return payload


def agents_config_to_yaml(config: SkillAgentsConfig) -> YamlMapping:
    """把 agents 配置还原成 YAML 需要的结构。"""

    payload: YamlMapping = {}
    interface: YamlMapping = {}
    if config.interface.display_name is not None:
        interface["display_name"] = config.interface.display_name
    if config.interface.short_description is not None:
        interface["short_description"] = config.interface.short_description
    if config.interface.default_prompt is not None:
        interface["default_prompt"] = config.interface.default_prompt
    if interface:
        payload["interface"] = interface
    policy: YamlMapping = {}
    if config.policy.allow_implicit_invocation is not None:
        policy["allow_implicit_invocation"] = config.policy.allow_implicit_invocation
    if policy:
        payload["policy"] = policy
    return payload


def agents_config_to_payload(config: SkillAgentsConfig) -> dict[str, JsonValue]:
    """把 agents 配置投影为稳定 JSON 结构。"""

    payload: dict[str, JsonValue] = {}
    interface: dict[str, JsonValue] = {}
    if config.interface.display_name is not None:
        interface["display_name"] = config.interface.display_name
    if config.interface.short_description is not None:
        interface["short_description"] = config.interface.short_description
    if config.interface.default_prompt is not None:
        interface["default_prompt"] = config.interface.default_prompt
    if interface:
        payload["interface"] = interface
    policy: dict[str, JsonValue] = {}
    if config.policy.allow_implicit_invocation is not None:
        policy["allow_implicit_invocation"] = config.policy.allow_implicit_invocation
    if policy:
        payload["policy"] = policy
    return payload


def title_from_skill_name(name: str) -> str:
    return " ".join(part.capitalize() for part in name.split("-"))


def block_lookup(blocks: list[SkillBlock]) -> dict[str, SkillBlock]:
    return {block.name: block for block in blocks}


def payload_to_yaml_value(value: JsonValue) -> YamlValue:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return [payload_to_yaml_value(item) for item in value]
    return {key: payload_to_yaml_value(item) for key, item in value.items()}


__all__ = [
    "ALLOWED_BLOCK_KEYS",
    "ALLOWED_FRONTMATTER_KEYS",
    "ALLOWED_INTERFACE_KEYS",
    "ALLOWED_METADATA_KEYS",
    "ALLOWED_OPENAI_KEYS",
    "ALLOWED_POLICY_KEYS",
    "ALLOWED_WORKBENCH_METADATA_KEYS",
    "BLOCK_KIND_CHOICES",
    "NAME_PATTERN",
    "RESOURCE_CHOICES",
    "RESOURCE_PATTERN",
    "ROLE_CHOICES",
    "Skill",
    "SkillAgentInterface",
    "SkillAgentPolicy",
    "SkillAgentsConfig",
    "SkillAssembly",
    "SkillBlock",
    "SkillBundleReference",
    "SkillFrontmatter",
    "SkillIssue",
    "SkillLintPayload",
    "SkillLinkPayload",
    "SkillLinkRecord",
    "SkillLoadedBlock",
    "SkillMetadata",
    "SkillScriptEntry",
    "SkillSummary",
    "SkillTestPayload",
    "SkillTestResult",
    "agents_config_to_payload",
    "agents_config_to_yaml",
    "block_lookup",
    "block_to_payload",
    "frontmatter_to_payload",
    "frontmatter_to_yaml",
    "payload_to_yaml_value",
    "title_from_skill_name",
]
