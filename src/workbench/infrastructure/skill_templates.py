from __future__ import annotations

"""Template loading for skill scaffolding."""

from ..config import WorkbenchConfig
from ..core import Result
from ..domain.errors import AppError, AppErrorCode, app_error

TEMPLATE_PATHS = {
    "skill": ("skill", "SKILL.md.tpl"),
    "openai": ("skill", "openai.yaml.tpl"),
    "reference": ("skill", "reference.md.tpl"),
    "script": ("skill", "script.py.tpl"),
    "asset": ("skill", "asset.txt.tpl"),
}


def load_skill_templates(config: WorkbenchConfig) -> Result[dict[str, str], AppError]:
    templates: dict[str, str] = {}
    try:
        for name, parts in TEMPLATE_PATHS.items():
            templates[name] = (config.templates_dir / parts[0] / parts[1]).read_text(encoding="utf-8")
    except OSError as exc:
        return Result.err(app_error(AppErrorCode.INTERNAL_ERROR, str(exc), path=str(config.templates_dir)))
    return Result.ok(templates)


__all__ = ["TEMPLATE_PATHS", "load_skill_templates"]
