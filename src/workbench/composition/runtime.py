from __future__ import annotations

"""CLI 运行时的 composition root。

这里负责把配置、service graph 和只依赖 repo root 的轻量服务装配起来。
"""

from dataclasses import dataclass
from pathlib import Path

from ..application import ContextService, LocalService, ReportService, SkillService, WorkspaceService
from ..config import WorkbenchConfig, ensure_base_layout, load_config
from ..core import Result
from ..domain.errors import AppError


@dataclass
class ServiceContainer:
    """集中承载需要配置驱动的 application service。"""

    config: WorkbenchConfig
    skill: SkillService
    workspace: WorkspaceService
    context: ContextService
    report: ReportService


def build_service_container(config: WorkbenchConfig) -> ServiceContainer:
    """按共享依赖一次性装配 service graph。"""

    skill_service = SkillService(config)
    workspace_service = WorkspaceService(config)
    return ServiceContainer(
        config=config,
        skill=skill_service,
        workspace=workspace_service,
        context=ContextService(config, skill_service=skill_service, workspace_service=workspace_service),
        report=ReportService(config, skill_service=skill_service, workspace_service=workspace_service),
    )


class RuntimeContext:
    """按需加载运行时资源，避免每个命令都重复装配完整依赖树。"""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root.resolve()
        self.cached_config: WorkbenchConfig | None = None
        self.cached_services: ServiceContainer | None = None
        self.cached_local_service: LocalService | None = None

    def config(self) -> Result[WorkbenchConfig, AppError]:
        """加载并缓存配置，同时确保基础目录已经就绪。"""

        if self.cached_config is not None:
            return Result.ok(self.cached_config)
        config = load_config(self.repo_root)
        if config.is_err:
            return Result.err(config.error)
        ensured = ensure_base_layout(config.value)
        if ensured.is_err:
            return Result.err(ensured.error)
        self.cached_config = config.value
        return Result.ok(self.cached_config)

    def services(self) -> Result[ServiceContainer, AppError]:
        """返回完整的 application service container。"""

        if self.cached_services is not None:
            return Result.ok(self.cached_services)
        config = self.config()
        if config.is_err:
            return Result.err(config.error)
        self.cached_services = build_service_container(config.value)
        return Result.ok(self.cached_services)

    def local(self) -> LocalService:
        """`local` 命令只依赖 repo root，因此单独懒加载。"""

        if self.cached_local_service is None:
            self.cached_local_service = LocalService(self.repo_root)
        return self.cached_local_service
