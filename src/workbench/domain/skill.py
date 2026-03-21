from __future__ import annotations

"""Skill domain model and shared validation constants."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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

def title_from_skill_name(name: str) -> str:
    return " ".join(part.capitalize() for part in name.split("-"))


__all__ = [
    "ALLOWED_FRONTMATTER_KEYS",
    "NAME_PATTERN",
    "RESOURCE_CHOICES",
    "RESOURCE_PATTERN",
    "Skill",
    "title_from_skill_name",
]
