from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .bootstrap import initialize_repo
from .config import ensure_base_layout, load_config
from .context import build_context_file
from .report import timestamp_slug, to_json_text, write_markdown_report
from .skilllib import create_skill, discover_skills, lint_skills, pack_skill, sync_skills, test_skills
from .workspace import add_workspace, check_workspaces, load_workspaces


def _repo_root() -> Path:
    return Path.cwd()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="workbench", description="Codex skills repository workbench")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Initialize the repository layout")
    init_parser.add_argument("path", nargs="?", default=".")
    init_parser.add_argument("--with-samples", action="store_true")
    init_parser.add_argument("--force", action="store_true")

    skill_parser = subparsers.add_parser("skill", help="Codex skill management commands")
    skill_sub = skill_parser.add_subparsers(dest="skill_command", required=True)

    skill_new = skill_sub.add_parser("new", help="Create a new Codex skill")
    skill_new.add_argument("name")
    skill_new.add_argument(
        "--description",
        default="Describe what this skill does and when to use it.",
    )
    skill_new.add_argument("--resources", nargs="*", choices=["scripts", "references", "assets"], default=[])
    skill_new.add_argument("--examples", action="store_true")
    skill_new.add_argument("--short-description")
    skill_new.add_argument("--default-prompt")

    skill_lint = skill_sub.add_parser("lint", help="Validate Codex skill definitions")
    skill_lint.add_argument("name", nargs="?")

    skill_test = skill_sub.add_parser("test", help="Run skill bundle fixtures")
    skill_test.add_argument("name", nargs="?")

    skill_pack = skill_sub.add_parser("pack", help="Package a skill directory as a zip")
    skill_pack.add_argument("name")
    skill_pack.add_argument("--output")

    skill_sync = skill_sub.add_parser("sync", help="Copy skills into a Codex skills directory")
    skill_sync.add_argument("name", nargs="?")
    skill_sync.add_argument("--target")
    skill_sync.add_argument("--no-overwrite", action="store_true")

    skill_install = skill_sub.add_parser("install", help="Alias for skill sync")
    skill_install.add_argument("name", nargs="?")
    skill_install.add_argument("--target")
    skill_install.add_argument("--no-overwrite", action="store_true")

    ws_parser = subparsers.add_parser("workspace", help="External workspace commands")
    ws_sub = ws_parser.add_subparsers(dest="workspace_command", required=True)

    ws_add = ws_sub.add_parser("add", help="Register a workspace")
    ws_add.add_argument("name")
    ws_add.add_argument("path")
    ws_add.add_argument("--default-branch", default="main")
    ws_add.add_argument("--check-command", action="append", default=[])

    ws_check = ws_sub.add_parser("check", help="Run safe checks in workspaces")
    ws_check.add_argument("name", nargs="?")

    context_parser = subparsers.add_parser("context", help="Context bundle commands")
    context_sub = context_parser.add_subparsers(dest="context_command", required=True)
    context_build = context_sub.add_parser("build", help="Build a context bundle from a skill")
    context_build.add_argument("skill")
    context_build.add_argument("--workspace")
    context_build.add_argument("--output")
    context_build.add_argument("--format", choices=["md", "json"], default="md")

    report_parser = subparsers.add_parser("report", help="Report generation commands")
    report_sub = report_parser.add_subparsers(dest="report_command", required=True)
    report_gen = report_sub.add_parser("generate", help="Generate a repository report")
    report_gen.add_argument("--output")

    return parser


def _print_payload(payload: Any) -> None:
    print(to_json_text(payload))


def _sync_from_args(config: Any, args: argparse.Namespace) -> dict[str, Any]:
    target = Path(args.target).expanduser().resolve() if args.target else None
    synced = sync_skills(
        config,
        skill_name=args.name,
        target_root=target,
        overwrite=not args.no_overwrite,
    )
    return {
        "target": str(target or config.codex_install_root),
        "synced": synced,
    }


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "init":
        root = Path(args.path).resolve()
        created = initialize_repo(root, include_samples=args.with_samples, overwrite=args.force)
        _print_payload({"created": [str(path) for path in created], "root": str(root)})
        return 0

    config = load_config(_repo_root())
    ensure_base_layout(config)

    if args.command == "skill":
        if args.skill_command == "new":
            target = create_skill(
                config,
                args.name,
                description=args.description,
                resources=args.resources,
                include_examples=args.examples,
                short_description=args.short_description,
                default_prompt=args.default_prompt,
            )
            _print_payload({"created": str(target)})
            return 0
        if args.skill_command == "lint":
            payload = lint_skills(config, args.name)
            _print_payload(payload)
            return 1 if any(issue["level"] == "error" for issue in payload["issues"]) else 0
        if args.skill_command == "test":
            payload = test_skills(config, args.name)
            _print_payload(payload)
            return 1 if payload["failure_count"] else 0
        if args.skill_command == "pack":
            output = Path(args.output).resolve() if args.output else None
            archive = pack_skill(config, args.name, output_path=output)
            _print_payload({"archive": str(archive)})
            return 0
        if args.skill_command in {"sync", "install"}:
            payload = _sync_from_args(config, args)
            _print_payload(payload)
            return 0

    if args.command == "workspace":
        if args.workspace_command == "add":
            registry = add_workspace(
                config,
                args.name,
                args.path,
                default_branch=args.default_branch,
                check_commands=args.check_command or None,
            )
            _print_payload({"registry": str(registry)})
            return 0
        if args.workspace_command == "check":
            payload = check_workspaces(config, args.name)
            _print_payload(payload)
            return 1 if any(check.get("status") == "failed" for entry in payload["results"] for check in entry.get("checks", [])) else 0

    if args.command == "context" and args.context_command == "build":
        output = Path(args.output).resolve() if args.output else None
        target = build_context_file(config, args.skill, workspace_name=args.workspace, output_path=output, format_name=args.format)
        _print_payload({"context": str(target), "format": args.format})
        return 0

    if args.command == "report" and args.report_command == "generate":
        lint_payload = lint_skills(config)
        workspace_payload = {"workspaces": [entry.name for entry in load_workspaces(config)]}
        report_payload = {
            "skills": lint_payload,
            "workspace_summary": workspace_payload,
        }
        if args.output:
            output = Path(args.output).resolve()
        else:
            output = config.reports_dir / f"status-{timestamp_slug()}.md"
        sections = [
            ("Skill Lint", json.dumps(lint_payload, indent=2, ensure_ascii=False)),
            ("Workspaces", json.dumps(workspace_payload, indent=2, ensure_ascii=False)),
        ]
        target = write_markdown_report(output, "Codex Skills Repository Report", sections)
        _print_payload({"report": str(target), "summary": report_payload})
        return 0

    parser.error("Unsupported command")
    return 2
