from __future__ import annotations

"""Skill 领域模型与共享约束。"""

import re
from dataclasses import dataclass, field
from pathlib import Path

from ..core.serialization import JsonValue
from ..core.yaml import YamlMapping

ALLOWED_FRONTMATTER_KEYS = {"name", "description", "license", "allowed-tools", "metadata"}
ALLOWED_METADATA_KEYS = {"short-description"}
ALLOWED_OPENAI_KEYS = {"interface", "policy"}
ALLOWED_INTERFACE_KEYS = {"display_name", "short_description", "default_prompt"}
ALLOWED_POLICY_KEYS = {"allow_implicit_invocation"}
NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
RESOURCE_PATTERN = re.compile(r"(?P<path>(?:agents|references|scripts|assets)/[A-Za-z0-9._/\\-]+)")
RESOURCE_CHOICES = ("scripts", "references", "assets")


@dataclass(frozen=True, slots=True)
class SkillMetadata:
    """front matter 里的 metadata 子结构。"""

    short_description: str | None = None


@dataclass(frozen=True, slots=True)
class SkillFrontmatter:
    """`SKILL.md` front matter 的强类型模型。"""

    name: str
    description: str
    license: str | None = None
    allowed_tools: list[str] = field(default_factory=list)
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
class SkillSummary:
    """面向 CLI / report 的 skill 摘要。"""

    name: str
    description: str
    path: str
    frontmatter: dict[str, JsonValue]
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
class SkillTestResult:
    """单个 fixture 的执行结果。"""

    skill: str
    fixture: str | None
    status: str
    reason: str | None = None
    missing_strings: list[str] = field(default_factory=list)
    expected_reference_count: int | None = None
    actual_reference_count: int | None = None


@dataclass(frozen=True, slots=True)
class SkillTestPayload:
    """skill fixture 测试汇总。"""

    failure_count: int
    results: list[SkillTestResult]


@dataclass(frozen=True, slots=True)
class SkillSyncRecord:
    """skill sync 的单项结果。"""

    skill: str
    destination: str


@dataclass(frozen=True, slots=True)
class SkillSyncPayload:
    """skill sync/install 的命令返回体。"""

    target: str
    synced: list[SkillSyncRecord]


def frontmatter_to_yaml(frontmatter: SkillFrontmatter) -> YamlMapping:
    """把 front matter 还原成 YAML 需要的原始键名。"""

    payload: YamlMapping = {
        "name": frontmatter.name,
        "description": frontmatter.description,
    }
    if frontmatter.license is not None:
        payload["license"] = frontmatter.license
    if frontmatter.allowed_tools:
        payload["allowed-tools"] = list(frontmatter.allowed_tools)
    metadata: YamlMapping = {}
    if frontmatter.metadata.short_description is not None:
        metadata["short-description"] = frontmatter.metadata.short_description
    if metadata:
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
    if frontmatter.allowed_tools:
        payload["allowed-tools"] = list(frontmatter.allowed_tools)
    metadata: dict[str, JsonValue] = {}
    if frontmatter.metadata.short_description is not None:
        metadata["short-description"] = frontmatter.metadata.short_description
    if metadata:
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


__all__ = [
    "ALLOWED_FRONTMATTER_KEYS",
    "ALLOWED_INTERFACE_KEYS",
    "ALLOWED_METADATA_KEYS",
    "ALLOWED_OPENAI_KEYS",
    "ALLOWED_POLICY_KEYS",
    "NAME_PATTERN",
    "RESOURCE_CHOICES",
    "RESOURCE_PATTERN",
    "Skill",
    "SkillAgentInterface",
    "SkillAgentPolicy",
    "SkillAgentsConfig",
    "SkillBundleReference",
    "SkillFrontmatter",
    "SkillIssue",
    "SkillLintPayload",
    "SkillMetadata",
    "SkillSummary",
    "SkillSyncPayload",
    "SkillSyncRecord",
    "SkillTestPayload",
    "SkillTestResult",
    "agents_config_to_payload",
    "agents_config_to_yaml",
    "frontmatter_to_payload",
    "frontmatter_to_yaml",
    "title_from_skill_name",
]
