from __future__ import annotations

"""skill 相关的 application façade。"""

from pathlib import Path

from ..core import Result
from ..domain.config import WorkbenchConfig
from ..domain.errors import AppError, AppErrorCode, app_error
from ..domain.skill import Skill, SkillAssembly, SkillLintPayload, SkillLinkRecord, SkillSummary, SkillTestPayload
from ..infrastructure.skill_loader import discover_skills
from ..infrastructure.skill_packaging import link_skills, pack_skill
from .skill_bundle import assemble_skill_context, test_skills
from .skill_creation import create_skill
from .skill_validation import lint_skills, skill_to_summary


class SkillService:
    """向命令层暴露稳定的 skill 用例入口。"""

    def __init__(self, config: WorkbenchConfig) -> None:
        self.config = config

    def create_skill(
        self,
        name: str,
        *,
        description: str,
        role: str = "worker",
        resources: list[str] | None = None,
        include_examples: bool = False,
        short_description: str | None = None,
        default_prompt: str | None = None,
        domain_tags: list[str] | None = None,
        capabilities: list[str] | None = None,
        handoff_outputs: list[str] | None = None,
        recommends: list[str] | None = None,
    ) -> Result[Path, AppError]:
        return create_skill(
            self.config,
            name,
            description=description,
            role=role,
            resources=resources,
            include_examples=include_examples,
            short_description=short_description,
            default_prompt=default_prompt,
            domain_tags=domain_tags,
            capabilities=capabilities,
            handoff_outputs=handoff_outputs,
            recommends=recommends,
        )

    def lint_skills(self, name: str | None = None) -> Result[SkillLintPayload, AppError]:
        return lint_skills(self.config, name)

    def test_skills(self, name: str | None = None) -> Result[SkillTestPayload, AppError]:
        return test_skills(self.config, name)

    def pack_skill(self, name: str, *, output_path: Path | None = None) -> Result[Path, AppError]:
        return pack_skill(self.config, name, output_path=output_path)

    def link_skills(
        self,
        *,
        name: str | None = None,
        target_root: Path | None = None,
    ) -> Result[list[SkillLinkRecord], AppError]:
        return link_skills(self.config, skill_name=name, target_root=target_root)

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

    def inspect_skill(self, name: str) -> Result[SkillSummary, AppError]:
        skill = self.find_skill(name)
        if skill.is_err:
            return Result.err(skill.error)
        return Result.ok(skill_to_summary(skill.value, self.config.root))

    def assemble_skill(self, skill: Skill, *, block_names: list[str] | None = None) -> Result[SkillAssembly, AppError]:
        return assemble_skill_context(skill, self.config, block_names=block_names)

