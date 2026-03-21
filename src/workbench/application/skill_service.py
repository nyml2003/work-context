from __future__ import annotations

from pathlib import Path
from typing import Any

from ..config import WorkbenchConfig
from ..core import Result
from ..domain.errors import AppError, AppErrorCode, app_error
from ..domain.skill import Skill
from ..infrastructure.skill_loader import discover_skills
from ..infrastructure.skill_packaging import pack_skill, sync_skills
from .skill_bundle import render_bundle, test_skills
from .skill_creation import create_skill
from .skill_validation import lint_skills


class SkillService:
    def __init__(self, config: WorkbenchConfig) -> None:
        self.config = config

    def create_skill(
        self,
        name: str,
        *,
        description: str,
        resources: list[str] | None = None,
        include_examples: bool = False,
        short_description: str | None = None,
        default_prompt: str | None = None,
    ) -> Result[Path, AppError]:
        return create_skill(
            self.config,
            name,
            description=description,
            resources=resources,
            include_examples=include_examples,
            short_description=short_description,
            default_prompt=default_prompt,
        )

    def lint_skills(self, name: str | None = None) -> Result[dict[str, Any], AppError]:
        return lint_skills(self.config, name)

    def test_skills(self, name: str | None = None) -> Result[dict[str, Any], AppError]:
        return test_skills(self.config, name)

    def pack_skill(self, name: str, *, output_path: Path | None = None) -> Result[Path, AppError]:
        return pack_skill(self.config, name, output_path=output_path)

    def sync_skills(
        self,
        *,
        name: str | None = None,
        target_root: Path | None = None,
        overwrite: bool = True,
    ) -> Result[list[dict[str, str]], AppError]:
        return sync_skills(self.config, skill_name=name, target_root=target_root, overwrite=overwrite)

    def discover_skills(self) -> Result[list[Skill], AppError]:
        return discover_skills(self.config)

    def find_skill(self, name: str) -> Result[Skill, AppError]:
        discovered = self.discover_skills()
        if discovered.is_err:
            return Result.err(discovered.error)
        skill = next((item for item in discovered.value if item.name == name), None)
        if skill is None:
            return Result.err(app_error(AppErrorCode.NOT_FOUND, f"Skill not found: {name}", skill=name))
        return Result.ok(skill)

    def render_bundle(self, skill: Skill) -> Result[tuple[str, list[dict[str, str]]], AppError]:
        return render_bundle(skill, self.config)
