from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
import uuid
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
TMP_ROOT = REPO_ROOT / ".tmp-tests"
TMP_ROOT.mkdir(exist_ok=True)

from workbench.application import ContextService, SkillService, WorkspaceService
from workbench.bootstrap import initialize_repo
from workbench.cli import main
from workbench.commands.base import ArgumentSpec, CommandGroup, CommandResult, CommandSpec, ParserFactory, RuntimeContext
from workbench.config import load_config
from workbench.core import Option, Result
from workbench.domain.errors import AppErrorCode


def make_temp_dir() -> Path:
    target = TMP_ROOT / f"case-{uuid.uuid4().hex}"
    target.mkdir(parents=True, exist_ok=False)
    return target


def expect_ok(result: Result[object, object]) -> object:
    if result.is_err:
        raise AssertionError(f"unexpected error result: {result.error}")
    return result.value


def run_cli_json(root: Path, argv: list[str]) -> tuple[int, dict[str, object]]:
    stdout = StringIO()
    old_cwd = Path.cwd()
    try:
        os.chdir(root)
        with redirect_stdout(stdout):
            code = main(argv)
    finally:
        os.chdir(old_cwd)
    payload = json.loads(stdout.getvalue())
    return code, payload


def unwrap_cli_success(testcase: unittest.TestCase, code: int, payload: dict[str, object]) -> dict[str, object]:
    testcase.assertTrue(payload["ok"])
    return payload["value"]


def unwrap_cli_error(testcase: unittest.TestCase, code: int, payload: dict[str, object]) -> dict[str, object]:
    testcase.assertEqual(code, 1)
    testcase.assertFalse(payload["ok"])
    return payload["err"]


def set_github_prefix(root: Path, prefix: str) -> None:
    config_path = root / "workbench.toml"
    content = config_path.read_text(encoding="utf-8")
    updated = content.replace('github_remote_prefix = ""', f'github_remote_prefix = "{prefix}"')
    config_path.write_text(updated, encoding="utf-8")


def initialize_git_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        ["git", "init", "--initial-branch", "main"],
        cwd=path,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        fallback = subprocess.run(["git", "init"], cwd=path, capture_output=True, text=True, check=False)
        if fallback.returncode != 0:
            raise RuntimeError(fallback.stderr.strip() or fallback.stdout.strip() or "git init failed in test")
        subprocess.run(
            ["git", "symbolic-ref", "HEAD", "refs/heads/main"],
            cwd=path,
            capture_output=True,
            text=True,
            check=True,
        )


class WorkbenchTestCase(unittest.TestCase):
    def test_result_and_option_map_helpers(self) -> None:
        self.assertEqual(Option.some("repo").map(str.upper).unwrap_or(""), "REPO")
        self.assertTrue(Option.none().to_result("missing").is_err)
        mapped = Result.ok(2).map(lambda value: value * 3).map_err(lambda err: f"x:{err}")
        self.assertTrue(mapped.is_ok)
        self.assertEqual(mapped.value, 6)

    def test_parser_factory_rejects_duplicate_flags(self) -> None:
        class DuplicateFlagGroup(CommandGroup):
            name = "demo"

            @property
            def spec(self) -> CommandSpec:
                return CommandSpec(
                    name="demo",
                    help="demo",
                    arguments=(
                        ArgumentSpec(("--name",), {}),
                        ArgumentSpec(("--name",), {"dest": "other_name"}),
                    ),
                )

            def run(self, args: object, runtime: RuntimeContext) -> Result[CommandResult, object]:
                return Result.ok(CommandResult(0, {}))

        parser = ParserFactory().build(prog="workbench", description="test", groups=(DuplicateFlagGroup(),))
        self.assertTrue(parser.is_err)
        self.assertEqual(parser.error.code, AppErrorCode.INVALID_ARGUMENT)

    def test_initialize_repo_with_samples(self) -> None:
        root = make_temp_dir()
        created = expect_ok(initialize_repo(root, include_samples=True))
        self.assertTrue(created)
        self.assertTrue((root / "workbench.toml").exists())
        self.assertTrue((root / "skills" / "codex-skill-authoring" / "SKILL.md").exists())
        self.assertTrue((root / "skills" / "codex-skill-authoring" / "agents" / "openai.yaml").exists())
        self.assertTrue((root / "skills" / "skill-validation" / "SKILL.md").exists())
        self.assertTrue((root / "skills" / "local-cli-operations" / "SKILL.md").exists())

    def test_lint_and_skill_tests_pass(self) -> None:
        config = expect_ok(load_config(REPO_ROOT))
        service = SkillService(config)
        self.assertEqual(expect_ok(service.lint_skills())["issue_count"], 0)
        self.assertEqual(expect_ok(service.test_skills())["failure_count"], 0)

    def test_context_payload_contains_references(self) -> None:
        config = expect_ok(load_config(REPO_ROOT))
        payload = expect_ok(ContextService(config).build_context_payload("codex-skill-authoring"))
        self.assertIn("bundle_markdown", payload)
        self.assertIn("Validation Checklist", payload["bundle_markdown"])

    def test_context_payload_contains_validation_flow(self) -> None:
        config = expect_ok(load_config(REPO_ROOT))
        payload = expect_ok(ContextService(config).build_context_payload("skill-validation"))
        self.assertIn("bundle_markdown", payload)
        self.assertIn("python scripts/workbench.py skill lint <name>", payload["bundle_markdown"])

    def test_context_payload_contains_local_cli_references(self) -> None:
        config = expect_ok(load_config(REPO_ROOT))
        payload = expect_ok(ContextService(config).build_context_payload("local-cli-operations"))
        self.assertIn("bundle_markdown", payload)
        self.assertIn("python scripts/workbench.py local read <path>", payload["bundle_markdown"])

    def test_sync_skills_to_custom_target(self) -> None:
        root = make_temp_dir()
        config = expect_ok(load_config(REPO_ROOT))
        target = root / "codex-skills"
        synced = expect_ok(SkillService(config).sync_skills(name="codex-skill-authoring", target_root=target))
        self.assertEqual(len(synced), 1)
        self.assertTrue((target / "codex-skill-authoring" / "SKILL.md").exists())

    def test_cli_generates_context_json(self) -> None:
        root = make_temp_dir()
        expect_ok(initialize_repo(root, include_samples=True))
        output = root / "reports" / "context.json"
        old_cwd = Path.cwd()
        try:
            os.chdir(root)
            code = main(["context", "build", "codex-skill-authoring", "--format", "json", "--output", str(output)])
        finally:
            os.chdir(old_cwd)
        self.assertEqual(code, 0)
        payload = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(payload["skill"]["name"], "codex-skill-authoring")

    def test_workspace_registry_and_safe_check(self) -> None:
        root = make_temp_dir()
        expect_ok(initialize_repo(root, include_samples=True))
        config = expect_ok(load_config(root))
        service = WorkspaceService(config)
        expect_ok(service.register_workspace("self", ".", check_commands=["python --version"]))
        payload = expect_ok(service.check_workspaces("self"))
        self.assertEqual(payload["workspace_count"], 1)
        self.assertEqual(payload["results"][0]["checks"][0]["status"], "ok")

    def test_discover_skills_returns_codex_skill(self) -> None:
        config = expect_ok(load_config(REPO_ROOT))
        names = {skill.name for skill in expect_ok(SkillService(config).discover_skills())}
        self.assertIn("codex-skill-authoring", names)
        self.assertIn("skill-validation", names)
        self.assertIn("local-cli-operations", names)

    def test_local_read_and_line_range(self) -> None:
        root = make_temp_dir()
        (root / "notes.txt").write_text("one\ntwo\nthree\n", encoding="utf-8")
        code, payload = run_cli_json(root, ["local", "read", "notes.txt", "--start-line", "2", "--end-line", "3"])
        value = unwrap_cli_success(self, code, payload)
        self.assertEqual(code, 0)
        self.assertEqual(value["content"], "two\nthree\n")
        self.assertEqual(value["line_count"], 3)
        self.assertFalse((root / "workbench.toml").exists())

    def test_local_list_and_grep(self) -> None:
        root = make_temp_dir()
        (root / "docs").mkdir()
        (root / "docs" / "a.txt").write_text("alpha\nbeta\n", encoding="utf-8")
        (root / "docs" / "skip.md").write_text("gamma\n", encoding="utf-8")
        (root / "docs" / "nested").mkdir()
        (root / "docs" / "nested" / "b.txt").write_text("beta\nomega\n", encoding="utf-8")
        code, payload = run_cli_json(root, ["local", "list", "docs", "--recursive", "--kind", "file", "--pattern", "*.txt"])
        value = unwrap_cli_success(self, code, payload)
        self.assertEqual(code, 0)
        self.assertEqual(value["count"], 2)
        self.assertEqual([entry["path"] for entry in value["entries"]], ["docs/a.txt", "docs/nested/b.txt"])
        code, payload = run_cli_json(root, ["local", "grep", "docs", "--pattern", "beta", "--glob", "*.txt"])
        value = unwrap_cli_success(self, code, payload)
        self.assertEqual(code, 0)
        self.assertEqual(value["match_count"], 2)
        self.assertEqual([match["path"] for match in value["matches"]], ["docs/a.txt", "docs/nested/b.txt"])

    def test_local_write_append_mkdir_and_stat(self) -> None:
        root = make_temp_dir()
        code, payload = run_cli_json(root, ["local", "mkdir", "logs\\daily", "--parents"])
        value = unwrap_cli_success(self, code, payload)
        self.assertTrue(value["created"])
        code, payload = run_cli_json(root, ["local", "write", "logs\\daily\\notes.txt", "--content", "alpha"])
        value = unwrap_cli_success(self, code, payload)
        self.assertEqual(code, 0)
        self.assertTrue(value["created"])
        code, payload = run_cli_json(root, ["local", "append", "logs\\daily\\notes.txt", "--content", "\nbeta"])
        value = unwrap_cli_success(self, code, payload)
        self.assertEqual(code, 0)
        self.assertEqual(value["appended_characters"], 5)
        code, payload = run_cli_json(root, ["local", "stat", "logs\\daily\\notes.txt"])
        value = unwrap_cli_success(self, code, payload)
        self.assertEqual(code, 0)
        self.assertEqual(value["type"], "file")
        self.assertEqual((root / "logs" / "daily" / "notes.txt").read_text(encoding="utf-8"), "alpha\nbeta")
        code, payload = run_cli_json(root, ["local", "write", "logs\\daily\\notes.txt", "--content", "replace"])
        err = unwrap_cli_error(self, code, payload)
        self.assertEqual(err["code"], "ALREADY_EXISTS")
        code, payload = run_cli_json(root, ["local", "write", "logs\\daily\\notes.txt", "--content", "replace", "--overwrite"])
        value = unwrap_cli_success(self, code, payload)
        self.assertEqual(code, 0)
        self.assertTrue(value["overwrote"])

    def test_local_commands_reject_out_of_boundary_path(self) -> None:
        root = make_temp_dir()
        code, payload = run_cli_json(root, ["local", "stat", ".."])
        err = unwrap_cli_error(self, code, payload)
        self.assertEqual(err["code"], "PATH_OUT_OF_BOUNDARY")

    def test_workspace_register_defaults_to_managed_subdir(self) -> None:
        root = make_temp_dir()
        expect_ok(initialize_repo(root, include_samples=True))
        code, payload = run_cli_json(root, ["workspace", "register", "demo"])
        value = unwrap_cli_success(self, code, payload)
        self.assertEqual(code, 0)
        self.assertIn("registry", value)
        config = expect_ok(load_config(root))
        entries = {workspace.name: workspace for workspace in expect_ok(WorkspaceService(config).load_workspaces())}
        self.assertIn("demo", entries)
        self.assertEqual(entries["demo"].path, "repos/demo")

    def test_workspace_check_and_remote_init_use_registered_repos(self) -> None:
        root = make_temp_dir()
        expect_ok(initialize_repo(root, include_samples=True))
        repo = root / "repos" / "demo"
        initialize_git_repo(repo)
        code, payload = run_cli_json(root, ["workspace", "register", "demo"])
        unwrap_cli_success(self, code, payload)
        code, payload = run_cli_json(root, ["workspace", "check", "demo"])
        value = unwrap_cli_success(self, code, payload)
        self.assertEqual(code, 0)
        self.assertEqual(value["results"][0]["remote"]["status"], "unconfigured")

        set_github_prefix(root, "https://github.com/example-user")
        code, payload = run_cli_json(root, ["workspace", "check", "demo"])
        value = unwrap_cli_success(self, code, payload)
        self.assertEqual(code, 1)
        self.assertEqual(value["results"][0]["remote"]["status"], "missing")

        code, payload = run_cli_json(root, ["workspace", "remote-init", "demo"])
        value = unwrap_cli_success(self, code, payload)
        self.assertEqual(code, 0)
        self.assertEqual(value["status"], "added")
        remote = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(remote.stdout.strip(), "https://github.com/example-user/demo.git")

    def test_cli_uses_command_group_loader(self) -> None:
        source = (SRC_DIR / "workbench" / "cli.py").read_text(encoding="utf-8")
        self.assertIn("from .commands import load_command_groups", source)
        self.assertIn("ParserFactory().build", source)
        self.assertNotIn("def _build_init_parser", source)
        self.assertNotIn("group.handled_exceptions", source)

    def test_command_groups_live_outside_cli(self) -> None:
        command_dir = SRC_DIR / "workbench" / "commands"
        command_files = {path.name for path in command_dir.glob("*_command.py")}
        self.assertEqual(
            command_files,
            {
                "context_command.py",
                "init_command.py",
                "local_command.py",
                "report_command.py",
                "skill_command.py",
                "workspace_command.py",
            },
        )

    def test_root_compatibility_wrappers_removed(self) -> None:
        removed = {
            "context.py",
            "localops.py",
            "report.py",
            "skilllib.py",
            "workspace.py",
        }
        existing = {path.name for path in (SRC_DIR / "workbench").glob("*.py")}
        self.assertTrue(removed.isdisjoint(existing))

    def test_domain_workspace_stays_free_of_cli_and_subprocess_dependencies(self) -> None:
        source = (SRC_DIR / "workbench" / "domain" / "workspace.py").read_text(encoding="utf-8")
        self.assertNotIn("argparse", source)
        self.assertNotIn("subprocess", source)

    def test_local_and_report_services_use_infrastructure_modules(self) -> None:
        local_source = (SRC_DIR / "workbench" / "application" / "local_service.py").read_text(encoding="utf-8")
        report_source = (SRC_DIR / "workbench" / "application" / "report_service.py").read_text(encoding="utf-8")
        cli_source = (SRC_DIR / "workbench" / "cli.py").read_text(encoding="utf-8")
        self.assertIn("from ..infrastructure.local_files import", local_source)
        self.assertNotIn("from ..localops import", local_source)
        self.assertIn("from ..infrastructure.report_output import", report_source)
        self.assertIn("from .infrastructure.report_output import to_json_text", cli_source)
        self.assertNotIn("from .report import to_json_text", cli_source)


if __name__ == "__main__":
    unittest.main()
