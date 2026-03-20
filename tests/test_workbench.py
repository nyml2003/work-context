from __future__ import annotations

import json
import os
import sys
import unittest
import uuid
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


class WorkbenchTestCase(unittest.TestCase):
    def test_initialize_repo_with_samples(self) -> None:
        root = make_temp_dir()
        created = initialize_repo(root, include_samples=True)
        self.assertTrue(created)
        self.assertTrue((root / "workbench.toml").exists())
        self.assertTrue((root / "skills" / "codex-skill-authoring" / "SKILL.md").exists())
        self.assertTrue((root / "skills" / "codex-skill-authoring" / "agents" / "openai.yaml").exists())
        self.assertTrue((root / "skills" / "skill-validation" / "SKILL.md").exists())

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


if __name__ == "__main__":
    unittest.main()
