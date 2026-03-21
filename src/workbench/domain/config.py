from __future__ import annotations

"""配置领域模型。"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class WorkbenchConfig:
    """运行时可消费的配置快照。

    这里不负责文件加载或默认值决策，只承载已经解析完成的配置语义。
    """

    root: Path
    data: dict[str, Any]
    skills_dir: Path
    templates_dir: Path
    reports_dir: Path
    workspace_config_dir: Path
    workspace_registry: Path
    managed_subdir: str
    managed_repos_dir: Path
    default_remote_name: str
    github_remote_prefix: str
    codex_install_root: Path


__all__ = ["WorkbenchConfig"]
