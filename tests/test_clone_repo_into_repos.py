from __future__ import annotations

import json
import subprocess
import sys
import unittest
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "clone_repo_into_repos.py"
TMP_ROOT = REPO_ROOT / ".tmp-tests"
TMP_ROOT.mkdir(exist_ok=True)


def make_temp_dir() -> Path:
    target = TMP_ROOT / f"clone-case-{uuid.uuid4().hex}"
    target.mkdir(parents=True, exist_ok=False)
    return target


def run_script(cwd: Path, *args: str) -> tuple[int, dict[str, object]]:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    payload = json.loads(completed.stdout)
    return completed.returncode, payload


class CloneRepoIntoReposScriptTestCase(unittest.TestCase):
    def test_dry_run_respects_explicit_dest_root(self) -> None:
        root = make_temp_dir()
        code, payload = run_script(root, "--url", "https://github.com/openai/skills", "--dest-root", "repos", "--dry-run")
        self.assertEqual(code, 0)
        self.assertTrue(payload["ok"])
        value = payload["value"]
        self.assertEqual(value["clone_url"], "https://github.com/openai/skills.git")
        self.assertEqual(value["target_path"], str(root / "repos" / "skills"))
        self.assertFalse(value["executed"])

    def test_dry_run_normalizes_github_tree_url(self) -> None:
        root = make_temp_dir()
        code, payload = run_script(
            root,
            "--url",
            "https://github.com/openai/skills/tree/main/skills/.curated",
            "--dry-run",
        )
        self.assertEqual(code, 0)
        self.assertTrue(payload["ok"])
        value = payload["value"]
        self.assertEqual(value["clone_url"], "https://github.com/openai/skills.git")
        self.assertEqual(value["repo_name"], "skills")

    def test_dry_run_prefers_nearest_existing_repos_directory(self) -> None:
        workspace = make_temp_dir()
        repos_root = workspace / "repos"
        repos_root.mkdir()
        nested = workspace / "docs" / "notes"
        nested.mkdir(parents=True)
        code, payload = run_script(nested, "--url", "https://github.com/openai/skills", "--dry-run")
        self.assertEqual(code, 0)
        self.assertTrue(payload["ok"])
        value = payload["value"]
        self.assertEqual(value["destination_root"], str(repos_root))
        self.assertEqual(value["target_path"], str(repos_root / "skills"))

    def test_existing_target_directory_returns_error(self) -> None:
        root = make_temp_dir()
        target = root / "repos" / "skills"
        target.mkdir(parents=True)
        code, payload = run_script(root, "--url", "https://github.com/openai/skills", "--dry-run")
        self.assertEqual(code, 1)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["err"]["code"], "ALREADY_EXISTS")

    def test_invalid_destination_name_is_rejected(self) -> None:
        root = make_temp_dir()
        code, payload = run_script(
            root,
            "--url",
            "https://github.com/openai/skills",
            "--name",
            "nested/path",
            "--dry-run",
        )
        self.assertEqual(code, 1)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["err"]["code"], "INVALID_NAME")


if __name__ == "__main__":
    unittest.main()
