from __future__ import annotations

"""skill 相关的 application façade。"""

from pathlib import Path

from ..core import Result
from ..domain.config import WorkbenchConfig
from ..domain.errors import AppError, AppErrorCode, app_error
from ..domain.skill import Skill, SkillBundleReference, SkillLintPayload, SkillLinkRecord, SkillTestPayload
from ..infrastructure.skill_loader import discover_skills
from ..infrastructure.skill_packaging import link_skills, pack_skill
from .skill_bundle import render_bundle, test_skills
from .skill_creation import create_skill
from .skill_validation import lint_skills


class SkillService:
    """向命令层暴露稳定的 skill 用例入口。

    具体实现拆在纯函数模块里，这里负责提供一层清晰、可复用的应用边界。
    """

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
        """创建新的 skill 脚手架。"""

        return create_skill(
            self.config,
            name,
            description=description,
            resources=resources,
            include_examples=include_examples,
            short_description=short_description,
            default_prompt=default_prompt,
        )

    def lint_skills(self, name: str | None = None) -> Result[SkillLintPayload, AppError]:
        """执行 skill lint。"""

        return lint_skills(self.config, name)

    def test_skills(self, name: str | None = None) -> Result[SkillTestPayload, AppError]:
        """执行 skill fixture 测试。"""

        return test_skills(self.config, name)

    def pack_skill(self, name: str, *, output_path: Path | None = None) -> Result[Path, AppError]:
        """将单个 skill 打包为归档文件。"""

        return pack_skill(self.config, name, output_path=output_path)

    def link_skills(
        self,
        *,
        name: str | None = None,
        target_root: Path | None = None,
    ) -> Result[list[SkillLinkRecord], AppError]:
        """把 skill 链接到目标目录。"""

        return link_skills(self.config, skill_name=name, target_root=target_root)

    def discover_skills(self) -> Result[list[Skill], AppError]:
        """发现并加载当前仓库中的全部 skill。"""

        return discover_skills(self.config)

    def find_skill(self, name: str) -> Result[Skill, AppError]:
        """按名称查找 skill。"""

        discovered = self.discover_skills()
        if discovered.is_err:
            return Result.err(discovered.error)
        skill = next((item for item in discovered.value if item.name == name), None)
        if skill is None:
            return Result.err(app_error(AppErrorCode.NOT_FOUND, f"Skill not found: {name}", skill=name))
        return Result.ok(skill)

    def render_bundle(self, skill: Skill) -> Result[tuple[str, list[SkillBundleReference]], AppError]:
        """把 skill 渲染为 bundle 文本与引用清单。"""

        return render_bundle(skill, self.config)
