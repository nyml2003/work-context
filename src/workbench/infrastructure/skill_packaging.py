from __future__ import annotations

"""Packaging and installation workflows for skill directories."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from ..core import Result
from ..domain.config import WorkbenchConfig
from ..domain.errors import AppError, AppErrorCode, app_error, from_exception
from ..domain.skill import SkillLinkRecord
from .filesystem import ensure_dir, ensure_directory_symlink
from .skill_loader import discover_skills


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


def link_skills(
    config: WorkbenchConfig,
    *,
    skill_name: str | None = None,
    target_root: Path | None = None,
) -> Result[list[SkillLinkRecord], AppError]:
    discovered = discover_skills(config)
    if discovered.is_err:
        return Result.err(discovered.error)
    target = target_root or config.codex_install_root
    try:
        ensure_dir(target)
    except OSError as exc:
        return Result.err(app_error(AppErrorCode.INTERNAL_ERROR, str(exc), path=str(target)))
    linked: list[SkillLinkRecord] = []
    for skill in discovered.value:
        if skill_name is not None and skill.name != skill_name:
            continue
        destination = target / skill.name
        try:
            status = ensure_directory_symlink(skill.path, destination)
        except OSError as exc:
            return Result.err(from_exception(exc, default_code=AppErrorCode.INTERNAL_ERROR, path=str(destination), skill=skill.name))
        linked.append(
            SkillLinkRecord(
                skill=skill.name,
                source=str(skill.path.resolve()),
                destination=str(destination),
                status=status,
            )
        )
    if skill_name is not None and not linked:
        return Result.err(app_error(AppErrorCode.NOT_FOUND, f"Skill not found: {skill_name}", skill=skill_name))
    return Result.ok(linked)


__all__ = ["link_skills", "pack_skill"]
