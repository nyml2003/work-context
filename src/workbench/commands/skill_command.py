from __future__ import annotations

from pathlib import Path

from ..core import Result
from ..domain.command_output import ArchivePathPayload, CreatedPathPayload
from ..domain.errors import AppError, AppErrorCode, app_error
from ..domain.skill import SkillLinkPayload
from .base import ArgumentSpec, CommandGroup, CommandResult, CommandSpec, RuntimeContext


class SkillCommandGroup(CommandGroup):
    name = "skill"
    order = 30

    @property
    def spec(self) -> CommandSpec:
        return CommandSpec(
            name="skill",
            help="Codex skill management commands",
            subcommand_dest="skill_command",
            subcommands=(
                CommandSpec(
                    name="new",
                    help="Create a new Codex skill",
                    arguments=(
                        ArgumentSpec(("name",), {}),
                        ArgumentSpec(("--description",), {"default": "Describe what this skill does and when to use it."}),
                        ArgumentSpec(("--role",), {"choices": ["director", "policy", "worker", "review"], "default": "worker"}),
                        ArgumentSpec(("--resources",), {"nargs": "*", "choices": ["scripts", "references", "assets"], "default": []}),
                        ArgumentSpec(("--examples",), {"action": "store_true"}),
                        ArgumentSpec(("--short-description",), {}),
                        ArgumentSpec(("--default-prompt",), {}),
                        ArgumentSpec(("--domain-tag",), {"action": "append", "default": []}),
                        ArgumentSpec(("--capability",), {"action": "append", "default": []}),
                        ArgumentSpec(("--handoff-output",), {"action": "append", "default": []}),
                        ArgumentSpec(("--recommend",), {"action": "append", "default": []}),
                    ),
                ),
                CommandSpec(name="lint", help="Validate Codex skill definitions", arguments=(ArgumentSpec(("name",), {"nargs": "?"}),)),
                CommandSpec(name="inspect", help="Inspect a single skill manifest", arguments=(ArgumentSpec(("name",), {}),)),
                CommandSpec(name="test", help="Run skill bundle fixtures", arguments=(ArgumentSpec(("name",), {"nargs": "?"}),)),
                CommandSpec(
                    name="pack",
                    help="Package a skill directory as a zip",
                    arguments=(ArgumentSpec(("name",), {}), ArgumentSpec(("--output",), {})),
                ),
                CommandSpec(name="link", help="Link skills into a Codex skills directory", arguments=(ArgumentSpec(("name",), {"nargs": "?"}),)),
            ),
        )

    def run(self, args: object, runtime: RuntimeContext) -> Result[CommandResult, AppError]:
        services = runtime.services()
        if services.is_err:
            return Result.err(services.error)
        service = services.value.skill
        if args.skill_command == "new":
            created = service.create_skill(
                args.name,
                description=args.description,
                role=args.role,
                resources=args.resources,
                include_examples=args.examples,
                short_description=args.short_description,
                default_prompt=args.default_prompt,
                domain_tags=args.domain_tag or None,
                capabilities=args.capability or None,
                handoff_outputs=args.handoff_output or None,
                recommends=args.recommend or None,
            )
            if created.is_err:
                return Result.err(created.error)
            return Result.ok(CommandResult(0, CreatedPathPayload(created=str(created.value))))
        if args.skill_command == "lint":
            payload = service.lint_skills(args.name)
            if payload.is_err:
                return Result.err(payload.error)
            exit_code = 1 if any(issue.level == "error" for issue in payload.value.issues) else 0
            return Result.ok(CommandResult(exit_code, payload.value))
        if args.skill_command == "inspect":
            payload = service.inspect_skill(args.name)
            if payload.is_err:
                return Result.err(payload.error)
            return Result.ok(CommandResult(0, payload.value))
        if args.skill_command == "test":
            payload = service.test_skills(args.name)
            if payload.is_err:
                return Result.err(payload.error)
            return Result.ok(CommandResult(1 if payload.value.failure_count else 0, payload.value))
        if args.skill_command == "pack":
            output = Path(args.output).resolve() if args.output else None
            archive = service.pack_skill(args.name, output_path=output)
            if archive.is_err:
                return Result.err(archive.error)
            return Result.ok(CommandResult(0, ArchivePathPayload(archive=str(archive.value))))
        if args.skill_command == "link":
            linked = service.link_skills(name=args.name, target_root=services.value.config.codex_install_root)
            if linked.is_err:
                return Result.err(linked.error)
            payload = SkillLinkPayload(target=str(services.value.config.codex_install_root), linked=linked.value)
            return Result.ok(CommandResult(0, payload))
        return Result.err(app_error(AppErrorCode.UNSUPPORTED_COMMAND, f"Unsupported skill command: {args.skill_command}"))


COMMAND_GROUP = SkillCommandGroup()
