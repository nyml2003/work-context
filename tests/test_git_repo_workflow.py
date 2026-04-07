from __future__ import annotations

import json
import subprocess
import sys
import unittest
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "git_repo_workflow.py"
TMP_ROOT = REPO_ROOT / ".tmp-tests"
TMP_ROOT.mkdir(exist_ok=True)


def make_temp_dir() -> Path:
    target = TMP_ROOT / f"git-workflow-{uuid.uuid4().hex}"
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


def initialize_git_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(["git", "init", "--initial-branch", "main"], cwd=path, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        fallback = subprocess.run(["git", "init"], cwd=path, capture_output=True, text=True, check=False)
        if fallback.returncode != 0:
            raise RuntimeError(fallback.stderr.strip() or fallback.stdout.strip() or "git init failed in test")
        subprocess.run(["git", "symbolic-ref", "HEAD", "refs/heads/main"], cwd=path, capture_output=True, text=True, check=True)
    subprocess.run(["git", "config", "user.name", "Codex Test"], cwd=path, capture_output=True, text=True, check=True)
    subprocess.run(["git", "config", "user.email", "codex@example.com"], cwd=path, capture_output=True, text=True, check=True)


def commit_all(path: Path, message: str) -> None:
    subprocess.run(["git", "add", "-A"], cwd=path, capture_output=True, text=True, check=True)
    subprocess.run(["git", "commit", "-m", message], cwd=path, capture_output=True, text=True, check=True)


class GitRepoWorkflowScriptTestCase(unittest.TestCase):
    def test_clone_dry_run_respects_explicit_dest_root(self) -> None:
        root = make_temp_dir()
        code, payload = run_script(root, "clone", "--url", "https://github.com/openai/skills", "--dest-root", "repos", "--dry-run")
        self.assertEqual(code, 0)
        self.assertTrue(payload["ok"])
        value = payload["value"]
        self.assertEqual(value["clone_url"], "https://github.com/openai/skills.git")
        self.assertEqual(value["target_path"], str(root / "repos" / "skills"))
        self.assertFalse(value["executed"])

    def test_clone_dry_run_prefers_nearest_existing_repos_directory(self) -> None:
        workspace = make_temp_dir()
        repos_root = workspace / "repos"
        repos_root.mkdir()
        nested = workspace / "docs" / "notes"
        nested.mkdir(parents=True)
        code, payload = run_script(nested, "clone", "--url", "https://github.com/openai/skills", "--dry-run")
        self.assertEqual(code, 0)
        self.assertTrue(payload["ok"])
        value = payload["value"]
        self.assertEqual(value["destination_root"], str(repos_root))
        self.assertEqual(value["target_path"], str(repos_root / "skills"))

    def test_inspect_reports_changed_files_and_suggested_message(self) -> None:
        repo = make_temp_dir() / "repo"
        initialize_git_repo(repo)
        (repo / "notes.txt").write_text("alpha\n", encoding="utf-8")
        commit_all(repo, "chore: initial commit")
        (repo / "notes.txt").write_text("alpha\nbeta\n", encoding="utf-8")
        (repo / "todo.txt").write_text("item\n", encoding="utf-8")
        code, payload = run_script(repo, "inspect", "--repo", ".", "--max-diff-lines", "20")
        self.assertEqual(code, 0)
        self.assertTrue(payload["ok"])
        value = payload["value"]
        self.assertEqual(value["repo_path"], str(repo.resolve()))
        self.assertTrue(value["has_changes"])
        self.assertEqual(value["changed_file_count"], 2)
        self.assertEqual(value["unstaged_file_count"], 1)
        self.assertEqual(value["untracked_count"], 1)
        self.assertEqual(value["suggested_message"], "chore: update 2 files")

    def test_commit_uses_generated_message_and_stages_all_changes(self) -> None:
        repo = make_temp_dir() / "repo"
        initialize_git_repo(repo)
        (repo / "app.txt").write_text("one\n", encoding="utf-8")
        commit_all(repo, "chore: initial commit")
        (repo / "app.txt").write_text("one\ntwo\n", encoding="utf-8")
        code, payload = run_script(repo, "commit", "--repo", ".")
        self.assertEqual(code, 0)
        self.assertTrue(payload["ok"])
        value = payload["value"]
        self.assertTrue(value["executed"])
        self.assertTrue(value["used_generated_message"])
        self.assertEqual(value["message"], "chore: update app.txt")
        head_message = subprocess.run(["git", "log", "-1", "--pretty=%s"], cwd=repo, capture_output=True, text=True, check=True).stdout.strip()
        status_short = subprocess.run(["git", "status", "--short"], cwd=repo, capture_output=True, text=True, check=True).stdout.strip()
        self.assertEqual(head_message, "chore: update app.txt")
        self.assertEqual(status_short, "")

    def test_commit_dry_run_keeps_repository_unchanged(self) -> None:
        repo = make_temp_dir() / "repo"
        initialize_git_repo(repo)
        (repo / "readme.txt").write_text("start\n", encoding="utf-8")
        commit_all(repo, "chore: initial commit")
        (repo / "readme.txt").write_text("start\nmore\n", encoding="utf-8")
        before_head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True).stdout.strip()
        code, payload = run_script(repo, "commit", "--repo", ".", "--message", "chore: keep dry run", "--dry-run")
        self.assertEqual(code, 0)
        self.assertTrue(payload["ok"])
        value = payload["value"]
        self.assertFalse(value["executed"])
        self.assertEqual(value["message"], "chore: keep dry run")
        after_head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True).stdout.strip()
        self.assertEqual(before_head, after_head)


if __name__ == "__main__":
    unittest.main()
