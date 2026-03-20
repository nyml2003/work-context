from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import WorkbenchConfig
from .fs import write_json
from .skilllib import discover_skills, render_bundle
from .workspace import load_workspaces


def build_context_payload(config: WorkbenchConfig, skill_name: str, workspace_name: str | None = None) -> dict[str, Any]:
    skill = next((item for item in discover_skills(config) if item.name == skill_name), None)
    if skill is None:
        raise FileNotFoundError(f"Skill not found: {skill_name}")
    bundle, references = render_bundle(skill, config)
    payload: dict[str, Any] = {
        "skill": {
            "name": skill.name,
            "description": skill.description,
            "path": str(skill.path),
        },
        "references": references,
        "bundle_markdown": bundle,
    }
    if workspace_name:
        workspace = next((item for item in load_workspaces(config) if item.name == workspace_name), None)
        if workspace is None:
            raise FileNotFoundError(f"Workspace not found: {workspace_name}")
        payload["workspace"] = {
            "name": workspace.name,
            "path": str(workspace.resolved_path(config.root)),
            "default_branch": workspace.default_branch,
            "check_commands": workspace.check_commands,
        }
    return payload


def build_context_file(
    config: WorkbenchConfig,
    skill_name: str,
    *,
    workspace_name: str | None = None,
    output_path: Path | None = None,
    format_name: str = "md",
) -> Path:
    payload = build_context_payload(config, skill_name, workspace_name)
    if output_path is None:
        suffix = ".json" if format_name == "json" else ".md"
        output_path = config.reports_dir / f"context-{skill_name}{suffix}"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if format_name == "json":
        write_json(output_path, payload)
    else:
        text = payload["bundle_markdown"]
        if "workspace" in payload:
            workspace = payload["workspace"]
            text += "\n## Workspace\n\n"
            text += f"- name: {workspace['name']}\n"
            text += f"- path: {workspace['path']}\n"
            text += f"- default_branch: {workspace['default_branch']}\n"
            text += f"- check_commands: {', '.join(workspace['check_commands'])}\n"
        output_path.write_text(text, encoding="utf-8")
    return output_path
