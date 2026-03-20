from __future__ import annotations

import json
import os
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

from workbench.bootstrap import initialize_repo
from workbench.cli import main
from workbench.config import load_config
from workbench.context import build_context_payload
from workbench.skilllib import discover_skills, lint_skills, sync_skills, test_skills
from workbench.workspace import add_workspace, check_workspaces


def make_temp_dir() -> Path:
    target = TMP_ROOT / f"case-{uuid.uuid4().hex}"
    target.mkdir(parents=True, exist_ok=False)
    return target


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


class WorkbenchTestCase(unittest.TestCase):
    def test_initialize_repo_with_samples(self) -> None:
        root = make_temp_dir()
        created = initialize_repo(root, include_samples=True)
        self.assertTrue(created)
        self.assertTrue((root / "workbench.toml").exists())
        self.assertTrue((root / "skills" / "codex-skill-authoring" / "SKILL.md").exists())
        self.assertTrue((root / "skills" / "codex-skill-authoring" / "agents" / "openai.yaml").exists())
        self.assertTrue((root / "skills" / "skill-validation" / "SKILL.md").exists())
        self.assertTrue((root / "skills" / "local-cli-operations" / "SKILL.md").exists())

    def test_lint_and_skill_tests_pass(self) -> None:
        config = load_config(REPO_ROOT)
        self.assertEqual(lint_skills(config)["issue_count"], 0)
        self.assertEqual(test_skills(config)["failure_count"], 0)

    def test_context_payload_contains_references(self) -> None:
        config = load_config(REPO_ROOT)
        payload = build_context_payload(config, "codex-skill-authoring")
        self.assertIn("bundle_markdown", payload)
        self.assertIn("Validation Checklist", payload["bundle_markdown"])

    def test_context_payload_contains_validation_flow(self) -> None:
        config = load_config(REPO_ROOT)
        payload = build_context_payload(config, "skill-validation")
        self.assertIn("bundle_markdown", payload)
        self.assertIn("python scripts/workbench.py skill lint <name>", payload["bundle_markdown"])

    def test_context_payload_contains_local_cli_references(self) -> None:
        config = load_config(REPO_ROOT)
        payload = build_context_payload(config, "local-cli-operations")
        self.assertIn("bundle_markdown", payload)
        self.assertIn("python scripts/workbench.py local read <path>", payload["bundle_markdown"])

    def test_sync_skills_to_custom_target(self) -> None:
        root = make_temp_dir()
        config = load_config(REPO_ROOT)
        target = root / "codex-skills"
        synced = sync_skills(config, skill_name="codex-skill-authoring", target_root=target)
        self.assertEqual(len(synced), 1)
        self.assertTrue((target / "codex-skill-authoring" / "SKILL.md").exists())

    def test_cli_generates_context_json(self) -> None:
        root = make_temp_dir()
        initialize_repo(root, include_samples=True)
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
        initialize_repo(root, include_samples=True)
        config = load_config(root)
        add_workspace(config, "self", ".", check_commands=["python --version"])
        payload = check_workspaces(config, "self")
        self.assertEqual(payload["workspace_count"], 1)
        self.assertEqual(payload["results"][0]["checks"][0]["status"], "ok")

    def test_discover_skills_returns_codex_skill(self) -> None:
        config = load_config(REPO_ROOT)
        names = {skill.name for skill in discover_skills(config)}
        self.assertIn("codex-skill-authoring", names)
        self.assertIn("skill-validation", names)
        self.assertIn("local-cli-operations", names)

    def test_local_read_and_line_range(self) -> None:
        root = make_temp_dir()
        (root / "notes.txt").write_text("one\ntwo\nthree\n", encoding="utf-8")
        code, payload = run_cli_json(root, ["local", "read", "notes.txt", "--start-line", "2", "--end-line", "3"])
        self.assertEqual(code, 0)
        self.assertEqual(payload["content"], "two\nthree\n")
        self.assertEqual(payload["line_count"], 3)
        self.assertFalse((root / "workbench.toml").exists())

    def test_local_list_and_grep(self) -> None:
        root = make_temp_dir()
        (root / "docs").mkdir()
        (root / "docs" / "a.txt").write_text("alpha\nbeta\n", encoding="utf-8")
        (root / "docs" / "skip.md").write_text("gamma\n", encoding="utf-8")
        (root / "docs" / "nested").mkdir()
        (root / "docs" / "nested" / "b.txt").write_text("beta\nomega\n", encoding="utf-8")
        code, payload = run_cli_json(root, ["local", "list", "docs", "--recursive", "--kind", "file", "--pattern", "*.txt"])
        self.assertEqual(code, 0)
        self.assertEqual(payload["count"], 2)
        self.assertEqual([entry["path"] for entry in payload["entries"]], ["docs/a.txt", "docs/nested/b.txt"])
        code, payload = run_cli_json(root, ["local", "grep", "docs", "--pattern", "beta", "--glob", "*.txt"])
        self.assertEqual(code, 0)
        self.assertEqual(payload["match_count"], 2)
        self.assertEqual([match["path"] for match in payload["matches"]], ["docs/a.txt", "docs/nested/b.txt"])

    def test_local_write_append_mkdir_and_stat(self) -> None:
        root = make_temp_dir()
        code, payload = run_cli_json(root, ["local", "mkdir", "logs\\daily", "--parents"])
        self.assertEqual(code, 0)
        self.assertTrue(payload["created"])
        code, payload = run_cli_json(root, ["local", "write", "logs\\daily\\notes.txt", "--content", "alpha"])
        self.assertEqual(code, 0)
        self.assertTrue(payload["created"])
        code, payload = run_cli_json(root, ["local", "append", "logs\\daily\\notes.txt", "--content", "\nbeta"])
        self.assertEqual(code, 0)
        self.assertEqual(payload["appended_characters"], 5)
        code, payload = run_cli_json(root, ["local", "stat", "logs\\daily\\notes.txt"])
        self.assertEqual(code, 0)
        self.assertEqual(payload["type"], "file")
        self.assertEqual((root / "logs" / "daily" / "notes.txt").read_text(encoding="utf-8"), "alpha\nbeta")
        code, payload = run_cli_json(root, ["local", "write", "logs\\daily\\notes.txt", "--content", "replace"])
        self.assertEqual(code, 1)
        self.assertEqual(payload["error"]["type"], "FileExistsError")
        code, payload = run_cli_json(root, ["local", "write", "logs\\daily\\notes.txt", "--content", "replace", "--overwrite"])
        self.assertEqual(code, 0)
        self.assertTrue(payload["overwrote"])

    def test_local_commands_reject_out_of_boundary_path(self) -> None:
        root = make_temp_dir()
        code, payload = run_cli_json(root, ["local", "stat", ".."])
        self.assertEqual(code, 1)
        self.assertEqual(payload["error"]["type"], "PathBoundaryError")


if __name__ == "__main__":
    unittest.main()
