#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse, urlunparse

DOC_EXTENSIONS = {".md", ".mdx", ".rst", ".adoc"}
SAFE_DIRECTORY_NAME = re.compile(r"^[A-Za-z0-9._-]+$")
GITHUB_HOSTS = {"github.com", "www.github.com"}


@dataclass(frozen=True)
class ClonePlan:
    original_url: str
    clone_url: str
    destination_root: Path
    target_path: Path
    repo_name: str
    branch: str | None
    depth: int | None
    dry_run: bool

    def command(self) -> list[str]:
        command = ["git", "clone"]
        if self.branch:
            command.extend(["--branch", self.branch, "--single-branch"])
        if self.depth is not None:
            command.extend(["--depth", str(self.depth)])
        command.extend([self.clone_url, str(self.target_path)])
        return command


class GitWorkflowError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Clone repositories, inspect git changes, and create commits.")
    subparsers = parser.add_subparsers(dest="command")

    clone_parser = subparsers.add_parser("clone", help="Clone a repository into the nearest repos/ directory.")
    clone_parser.add_argument("--url", required=True, help="GitHub or git repository URL.")
    clone_parser.add_argument(
        "--dest-root",
        help="Optional destination root. Defaults to the nearest ancestor repos/ directory or ./repos.",
    )
    clone_parser.add_argument(
        "--name",
        help="Optional destination directory name. Defaults to the repository name derived from the URL.",
    )
    clone_parser.add_argument("--branch", help="Optional branch, tag, or ref to clone.")
    clone_parser.add_argument("--depth", type=int, help="Optional clone depth. Must be a positive integer.")
    clone_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the resolved clone plan without creating directories or running git clone.",
    )

    inspect_parser = subparsers.add_parser("inspect", help="Inspect current changes in a git repository.")
    inspect_parser.add_argument("--repo", default=".", help="Repository path. Defaults to the current directory.")
    inspect_parser.add_argument("--max-diff-lines", type=int, default=120, help="Max diff lines per excerpt.")

    commit_parser = subparsers.add_parser("commit", help="Stage current changes, generate a message, and commit.")
    commit_parser.add_argument("--repo", default=".", help="Repository path. Defaults to the current directory.")
    commit_parser.add_argument("--message", help="Explicit commit message. If omitted, one is generated.")
    commit_parser.add_argument("--stage", choices=("all", "staged"), default="all", help="Use all changes or only staged changes.")
    commit_parser.add_argument("--max-diff-lines", type=int, default=120, help="Max diff lines to inspect.")
    commit_parser.add_argument("--dry-run", action="store_true", help="Preview message and commands without committing.")
    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.error("a subcommand is required")
    if hasattr(args, "max_diff_lines") and args.max_diff_lines <= 0:
        parser.error("--max-diff-lines must be greater than 0")
    if hasattr(args, "depth") and args.depth is not None and args.depth <= 0:
        parser.error("--depth must be greater than 0")
    return args


def error_payload(code: str, message: str, *, command: list[str] | None = None, stdout: str = "", stderr: str = "") -> dict[str, object]:
    payload: dict[str, object] = {"ok": False, "err": {"code": code, "message": message}}
    if command is not None:
        payload["err"]["command"] = command
    if stdout:
        payload["err"]["stdout"] = stdout
    if stderr:
        payload["err"]["stderr"] = stderr
    return payload


def print_error(exc: GitWorkflowError, *, command: list[str] | None = None, stdout: str = "", stderr: str = "") -> int:
    print(json.dumps(error_payload(exc.code, exc.message, command=command, stdout=stdout, stderr=stderr), ensure_ascii=False, indent=2))
    return 1


def normalize_repo_url(raw_url: str) -> str:
    url = raw_url.strip()
    if not url:
        raise GitWorkflowError("INVALID_URL", "repository URL is required")
    if url.startswith("git@"):
        return normalize_ssh_url(url)
    parsed = urlparse(url)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        if parsed.netloc.lower() in GITHUB_HOSTS:
            segments = [segment for segment in parsed.path.split("/") if segment]
            if len(segments) < 2:
                raise GitWorkflowError("INVALID_URL", f"GitHub URL does not contain owner/repo: {raw_url}")
            owner, repo = segments[0], strip_git_suffix(segments[1])
            normalized_path = f"/{owner}/{repo}.git"
            return urlunparse((parsed.scheme, parsed.netloc, normalized_path, "", "", ""))
        return url
    return url


def normalize_ssh_url(raw_url: str) -> str:
    if ":" not in raw_url:
        raise GitWorkflowError("INVALID_URL", f"unsupported SSH repository URL: {raw_url}")
    prefix, _, path_part = raw_url.partition(":")
    user, _, host = prefix.partition("@")
    if not user or not host:
        raise GitWorkflowError("INVALID_URL", f"unsupported SSH repository URL: {raw_url}")
    segments = [segment for segment in path_part.split("/") if segment]
    if host.lower() in GITHUB_HOSTS:
        if len(segments) < 2:
            raise GitWorkflowError("INVALID_URL", f"GitHub SSH URL does not contain owner/repo: {raw_url}")
        owner, repo = segments[0], strip_git_suffix(segments[1])
        return f"{user}@{host}:{owner}/{repo}.git"
    return raw_url


def strip_git_suffix(name: str) -> str:
    return name[:-4] if name.endswith(".git") else name


def derive_repo_name(clone_url: str) -> str:
    if clone_url.startswith("git@"):
        _, _, path_part = clone_url.partition(":")
        candidate = path_part.rsplit("/", 1)[-1]
        return strip_git_suffix(candidate)
    parsed = urlparse(clone_url)
    candidate = parsed.path.rstrip("/").rsplit("/", 1)[-1]
    if not candidate:
        raise GitWorkflowError("INVALID_URL", f"cannot derive repository name from URL: {clone_url}")
    return strip_git_suffix(candidate)


def validate_repo_name(name: str) -> str:
    candidate = name.strip()
    if not candidate:
        raise GitWorkflowError("INVALID_NAME", "destination directory name cannot be empty")
    if not SAFE_DIRECTORY_NAME.fullmatch(candidate):
        raise GitWorkflowError(
            "INVALID_NAME",
            "destination directory name must contain only letters, digits, dots, underscores, or hyphens",
        )
    return candidate


def find_nearest_repos_directory(cwd: Path) -> Path:
    current = cwd.resolve()
    for base in (current, *current.parents):
        candidate = base / "repos"
        if candidate.exists() and candidate.is_dir():
            return candidate.resolve()
    return (current / "repos").resolve()


def resolve_destination_root(cwd: Path, override: str | None) -> Path:
    if override:
        target = Path(override).expanduser()
        if not target.is_absolute():
            target = cwd / target
        resolved = target.resolve()
    else:
        resolved = find_nearest_repos_directory(cwd)
    if resolved.exists() and not resolved.is_dir():
        raise GitWorkflowError("INVALID_DESTINATION", f"destination root is not a directory: {resolved}")
    return resolved


def build_clone_plan(args: argparse.Namespace, cwd: Path | None = None) -> ClonePlan:
    current_dir = (cwd or Path.cwd()).resolve()
    clone_url = normalize_repo_url(args.url)
    repo_name = validate_repo_name(args.name or derive_repo_name(clone_url))
    destination_root = resolve_destination_root(current_dir, args.dest_root)
    target_path = destination_root / repo_name
    if target_path.exists():
        raise GitWorkflowError("ALREADY_EXISTS", f"target directory already exists: {target_path}")
    return ClonePlan(
        original_url=args.url,
        clone_url=clone_url,
        destination_root=destination_root,
        target_path=target_path,
        repo_name=repo_name,
        branch=args.branch,
        depth=args.depth,
        dry_run=bool(args.dry_run),
    )


def clone_success_payload(
    plan: ClonePlan,
    *,
    executed: bool,
    git_result: subprocess.CompletedProcess[str] | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "ok": True,
        "value": {
            "original_url": plan.original_url,
            "clone_url": plan.clone_url,
            "destination_root": str(plan.destination_root),
            "target_path": str(plan.target_path),
            "repo_name": plan.repo_name,
            "branch": plan.branch,
            "depth": plan.depth,
            "dry_run": plan.dry_run,
            "executed": executed,
            "command": plan.command(),
        },
    }
    if git_result is not None:
        payload["value"]["stdout"] = git_result.stdout.strip()
        payload["value"]["stderr"] = git_result.stderr.strip()
    return payload


def run_git(repo_path: Path, args: list[str], code: str, default_message: str) -> subprocess.CompletedProcess[str]:
    command = ["git", *args]
    completed = subprocess.run(command, cwd=repo_path, capture_output=True, text=True, check=False)
    if completed.returncode == 0:
        return completed
    message = completed.stderr.strip() or completed.stdout.strip() or default_message
    if "detected dubious ownership" in message:
        raise GitWorkflowError("GIT_SAFE_DIRECTORY_REQUIRED", message)
    if "not a git repository" in message:
        raise GitWorkflowError("NOT_A_GIT_REPOSITORY", message)
    if "nothing to commit" in message or "nothing added to commit" in message:
        raise GitWorkflowError("NO_CHANGES", message)
    raise GitWorkflowError(code, message)


def resolve_repo_path(repo: str) -> Path:
    candidate = Path(repo).expanduser()
    if not candidate.is_absolute():
        candidate = Path.cwd() / candidate
    resolved = candidate.resolve()
    if not resolved.exists():
        raise GitWorkflowError("REPO_NOT_FOUND", f"repository path does not exist: {resolved}")
    if not resolved.is_dir():
        raise GitWorkflowError("INVALID_REPO_PATH", f"repository path is not a directory: {resolved}")
    top = run_git(resolved, ["rev-parse", "--show-toplevel"], "NOT_A_GIT_REPOSITORY", "not a git repository").stdout.strip()
    return Path(top).resolve()


def normalize_path(text: str) -> str:
    normalized = text.replace("\\", "/").strip()
    if " -> " in normalized:
        return normalized.split(" -> ", 1)[1]
    return normalized


def parse_status_line(line: str) -> dict[str, object]:
    index_status = line[0]
    worktree_status = line[1]
    path = normalize_path(line[3:])
    return {
        "path": path,
        "index_status": index_status,
        "worktree_status": worktree_status,
        "staged": index_status not in {" ", "?"},
        "unstaged": worktree_status not in {" ", "?"},
        "untracked": index_status == "?" and worktree_status == "?",
    }


def truncate_lines(text: str, max_lines: int) -> str:
    stripped = text.strip()
    if not stripped:
        return ""
    lines = stripped.splitlines()
    if len(lines) <= max_lines:
        return "\n".join(lines)
    return "\n".join(lines[:max_lines]) + f"\n... ({len(lines) - max_lines} more lines)"


def is_docs_path(path: str) -> bool:
    normalized = path.lower()
    return Path(normalized).suffix in DOC_EXTENSIONS or normalized.startswith("docs/") or "/docs/" in normalized


def is_test_path(path: str) -> bool:
    normalized = path.lower()
    return (
        normalized.startswith("test/")
        or normalized.startswith("tests/")
        or "/test/" in normalized
        or "/tests/" in normalized
        or normalized.endswith("_test.py")
        or normalized.endswith(".spec.ts")
        or normalized.endswith(".spec.tsx")
        or normalized.endswith(".test.ts")
        or normalized.endswith(".test.tsx")
        or normalized.endswith(".spec.js")
        or normalized.endswith(".test.js")
    )


def suggest_commit_message(changes: list[dict[str, object]]) -> str:
    if not changes:
        raise GitWorkflowError("NO_CHANGES", "there are no changes to summarize")
    paths = [str(change["path"]) for change in changes]
    if all(is_docs_path(path) for path in paths):
        prefix = "docs"
    elif all(is_test_path(path) for path in paths):
        prefix = "test"
    else:
        prefix = "chore"
    if len(paths) == 1:
        target = paths[0]
    else:
        top_levels = {path.split("/", 1)[0] for path in paths}
        target = next(iter(top_levels)) if len(top_levels) == 1 else f"{len(paths)} files"
    return f"{prefix}: update {target}"


def build_snapshot(repo_path: Path, max_diff_lines: int) -> dict[str, object]:
    branch = run_git(repo_path, ["branch", "--show-current"], "GIT_BRANCH_FAILED", "failed to read current branch").stdout.strip()
    status_lines = [line.rstrip() for line in run_git(repo_path, ["status", "--short"], "GIT_STATUS_FAILED", "failed to read git status").stdout.splitlines() if line.strip()]
    changes = [parse_status_line(line) for line in status_lines]
    staged_diff_stat = run_git(repo_path, ["diff", "--cached", "--stat", "--no-color"], "GIT_DIFF_FAILED", "failed to inspect staged diff").stdout.strip()
    unstaged_diff_stat = run_git(repo_path, ["diff", "--stat", "--no-color"], "GIT_DIFF_FAILED", "failed to inspect unstaged diff").stdout.strip()
    staged_diff_excerpt = truncate_lines(run_git(repo_path, ["diff", "--cached", "--unified=0", "--no-color"], "GIT_DIFF_FAILED", "failed to inspect staged diff").stdout, max_diff_lines)
    unstaged_diff_excerpt = truncate_lines(run_git(repo_path, ["diff", "--unified=0", "--no-color"], "GIT_DIFF_FAILED", "failed to inspect unstaged diff").stdout, max_diff_lines)
    return {
        "repo_path": str(repo_path),
        "branch": branch,
        "has_changes": bool(changes),
        "changed_file_count": len(changes),
        "staged_file_count": sum(1 for change in changes if change["staged"]),
        "unstaged_file_count": sum(1 for change in changes if change["unstaged"]),
        "untracked_count": sum(1 for change in changes if change["untracked"]),
        "status_short": status_lines,
        "changed_files": changes,
        "staged_diff_stat": staged_diff_stat,
        "unstaged_diff_stat": unstaged_diff_stat,
        "staged_diff_excerpt": staged_diff_excerpt,
        "unstaged_diff_excerpt": unstaged_diff_excerpt,
        "suggested_message": suggest_commit_message(changes) if changes else None,
    }


def handle_clone(args: argparse.Namespace) -> int:
    try:
        plan = build_clone_plan(args)
    except GitWorkflowError as exc:
        return print_error(exc)
    if plan.dry_run:
        print(json.dumps(clone_success_payload(plan, executed=False), ensure_ascii=False, indent=2))
        return 0
    plan.destination_root.mkdir(parents=True, exist_ok=True)
    command = plan.command()
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        return print_error(
            GitWorkflowError("GIT_CLONE_FAILED", completed.stderr.strip() or completed.stdout.strip() or "git clone failed"),
            command=command,
            stdout=completed.stdout.strip(),
            stderr=completed.stderr.strip(),
        )
    print(json.dumps(clone_success_payload(plan, executed=True, git_result=completed), ensure_ascii=False, indent=2))
    return 0


def handle_inspect(args: argparse.Namespace) -> int:
    try:
        payload = build_snapshot(resolve_repo_path(args.repo), args.max_diff_lines)
    except GitWorkflowError as exc:
        return print_error(exc)
    print(json.dumps({"ok": True, "value": payload}, ensure_ascii=False, indent=2))
    return 0


def handle_commit(args: argparse.Namespace) -> int:
    try:
        repo_path = resolve_repo_path(args.repo)
        snapshot = build_snapshot(repo_path, args.max_diff_lines)
        if not snapshot["has_changes"]:
            raise GitWorkflowError("NO_CHANGES", "there are no changes to commit")
        message = args.message or snapshot["suggested_message"]
        if not isinstance(message, str) or not message.strip():
            raise GitWorkflowError("INVALID_MESSAGE", "commit message cannot be empty")
        stage_command = ["git", "add", "-A"] if args.stage == "all" else None
        commit_command = ["git", "commit", "-m", message]
        payload: dict[str, object] = {
            "repo_path": str(repo_path),
            "branch": snapshot["branch"],
            "message": message,
            "used_generated_message": args.message is None,
            "stage_mode": args.stage,
            "dry_run": bool(args.dry_run),
            "executed": False,
            "changed_file_count": snapshot["changed_file_count"],
            "suggested_message": snapshot["suggested_message"],
            "status_short": snapshot["status_short"],
            "changed_files": snapshot["changed_files"],
            "stage_command": stage_command,
            "commit_command": commit_command,
        }
        if args.dry_run:
            print(json.dumps({"ok": True, "value": payload}, ensure_ascii=False, indent=2))
            return 0
        if stage_command is not None:
            run_git(repo_path, stage_command[1:], "GIT_ADD_FAILED", "failed to stage changes")
        completed = run_git(repo_path, ["commit", "-m", message], "GIT_COMMIT_FAILED", "git commit failed")
        payload["executed"] = True
        payload["commit_hash"] = run_git(repo_path, ["rev-parse", "HEAD"], "GIT_COMMIT_FAILED", "failed to read commit hash").stdout.strip()
        payload["stdout"] = completed.stdout.strip()
        payload["stderr"] = completed.stderr.strip()
    except GitWorkflowError as exc:
        return print_error(exc)
    print(json.dumps({"ok": True, "value": payload}, ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.command == "clone":
        return handle_clone(args)
    if args.command == "inspect":
        return handle_inspect(args)
    if args.command == "commit":
        return handle_commit(args)
    raise AssertionError(f"unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
