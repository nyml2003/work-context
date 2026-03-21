from __future__ import annotations

"""Compatibility exports for legacy skill helpers."""

from .application.skill_bundle import render_bundle, test_skills
from .application.skill_creation import create_skill
from .application.skill_validation import lint_skills
from .domain.skill import (
    ALLOWED_FRONTMATTER_KEYS,
    NAME_PATTERN,
    RESOURCE_CHOICES,
    RESOURCE_PATTERN,
    Skill,
    skill_to_record,
    title_from_skill_name,
)
from .infrastructure.skill_loader import (
    discover_skill_dirs,
    discover_skills,
    load_markdown_frontmatter,
    load_openai_yaml,
    load_skill,
    split_frontmatter,
)
from .infrastructure.skill_packaging import pack_skill, sync_skills

__all__ = [
    "ALLOWED_FRONTMATTER_KEYS",
    "NAME_PATTERN",
    "RESOURCE_CHOICES",
    "RESOURCE_PATTERN",
    "Skill",
    "create_skill",
    "discover_skill_dirs",
    "discover_skills",
    "lint_skills",
    "load_markdown_frontmatter",
    "load_openai_yaml",
    "load_skill",
    "pack_skill",
    "render_bundle",
    "skill_to_record",
    "split_frontmatter",
    "sync_skills",
    "test_skills",
    "title_from_skill_name",
]
