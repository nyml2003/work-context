from __future__ import annotations

"""Packaging and installation workflows for skill directories."""

import shutil
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from ..config import WorkbenchConfig
from ..core import Result
from ..domain.errors import AppError, AppErrorCode, app_error
from ..infrastructure.skill_loader import discover_skills


def pack_skill(config: WorkbenchConfig, skill_name: str, *, output_path: Path | None = None) -> Result[Path, AppError]:
    discovered = discover_skills(config)
    if discovered.is_err:
        return Result.err(discovered.error)
    skill = next((item for item in discovered.value if item.name == skill_name), None)
    if skill is None:
        return Result.err(app_error(AppErrorCode.NOT_FOUND, f"Skill not found: {skill_name}", skill=skill_name))
    target = output_path or (config.reports_dir / f"{skill.name}.zip")
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with ZipFile(target, "w", compression=ZIP_DEFLATED) as archive:
            for file_path in sorted(path for path in skill.path.rglob("*") if path.is_file()):
                archive.write(file_path, arcname=file_path.relative_to(config.root))
    except OSError as exc:
        return Result.err(app_error(AppErrorCode.INTERNAL_ERROR, str(exc), path=str(target)))
    return Result.ok(target)


def sync_skills(
    config: WorkbenchConfig,
    *,
    skill_name: str | None = None,
    target_root: Path | None = None,
    overwrite: bool = True,
) -> Result[list[dict[str, str]], AppError]:
    discovered = discover_skills(config)
    if discovered.is_err:
        return Result.err(discovered.error)
    target = target_root or config.codex_install_root
    try:
        target.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return Result.err(app_error(AppErrorCode.INTERNAL_ERROR, str(exc), path=str(target)))
    synced: list[dict[str, str]] = []
    for skill in discovered.value:
        if skill_name is not None and skill.name != skill_name:
            continue
        destination = target / skill.name
        try:
            if destination.exists():
                if not overwrite:
                    return Result.err(
                        app_error(AppErrorCode.ALREADY_EXISTS, f"Destination already exists: {destination}", path=str(destination))
                    )
                shutil.rmtree(destination)
            shutil.copytree(skill.path, destination)
        except OSError as exc:
            return Result.err(app_error(AppErrorCode.INTERNAL_ERROR, str(exc), path=str(destination)))
        synced.append({"skill": skill.name, "destination": str(destination)})
    if skill_name is not None and not synced:
        return Result.err(app_error(AppErrorCode.NOT_FOUND, f"Skill not found: {skill_name}", skill=skill_name))
    return Result.ok(synced)


__all__ = ["pack_skill", "sync_skills"]
