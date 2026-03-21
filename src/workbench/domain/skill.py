from __future__ import annotations

"""Skill domain model and shared validation constants."""

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ..fs import short_path

ALLOWED_FRONTMATTER_KEYS = {"name", "description", "license", "allowed-tools", "metadata"}
NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
RESOURCE_PATTERN = re.compile(r"(?P<path>(?:agents|references|scripts|assets)/[A-Za-z0-9._/\-]+)")
RESOURCE_CHOICES = ("scripts", "references", "assets")


@dataclass
class Skill:
    name: str
    description: str
    body: str
    frontmatter: dict[str, Any]
    path: Path
    agents_path: Path | None
    agents_config: dict[str, Any] | None
    references: list[Path]
    scripts: list[Path]
    assets: list[Path]
    examples: list[Path]
    tests: list[Path]


def skill_to_record(skill: Skill, root: Path) -> dict[str, Any]:
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


def title_from_skill_name(name: str) -> str:
    return " ".join(part.capitalize() for part in name.split("-"))


__all__ = [
    "ALLOWED_FRONTMATTER_KEYS",
    "NAME_PATTERN",
    "RESOURCE_CHOICES",
    "RESOURCE_PATTERN",
    "Skill",
    "skill_to_record",
    "title_from_skill_name",
]
