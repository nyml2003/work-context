from __future__ import annotations

from pathlib import Path

from ..core import Option, Result
from ..domain.errors import AppError, AppErrorCode, app_error
from ..domain.workspace import normalize_remote_url
from .process_runner import CommandRunner


class GitClient:
    def __init__(self, runner: CommandRunner | None = None) -> None:
        self.runner = runner or CommandRunner()

    def is_repository(self, path: Path) -> bool:
        return (path / ".git").exists()

    def remote_url(self, path: Path, remote_name: str) -> Result[Option[str], AppError]:
        completed = self.runner.run_args(["git", "remote", "get-url", remote_name], cwd=path)
        if completed.is_err:
            return Result.err(completed.error)
        process = completed.value
        if process.returncode != 0:
            return Result.ok(Option.none())
        url = process.stdout.strip()
        return Result.ok(Option.some(url) if url else Option.none())

    def add_remote(self, path: Path, remote_name: str, url: str) -> Result[None, AppError]:
        completed = self.runner.run_args(["git", "remote", "add", remote_name, url], cwd=path)
        if completed.is_err:
            return Result.err(completed.error)
        process = completed.value
        if process.returncode != 0:
            return Result.err(
                app_error(
                    AppErrorCode.EXTERNAL_TOOL_FAILED,
                    process.stderr.strip() or process.stdout.strip() or "git remote add failed",
                    path=str(path),
                    remote_name=remote_name,
                    url=url,
                )
            )
        return Result.ok(None)

    def set_remote_url(self, path: Path, remote_name: str, url: str) -> Result[None, AppError]:
        completed = self.runner.run_args(["git", "remote", "set-url", remote_name, url], cwd=path)
        if completed.is_err:
            return Result.err(completed.error)
        process = completed.value
        if process.returncode != 0:
            return Result.err(
                app_error(
                    AppErrorCode.EXTERNAL_TOOL_FAILED,
                    process.stderr.strip() or process.stdout.strip() or "git remote set-url failed",
                    path=str(path),
                    remote_name=remote_name,
                    url=url,
                )
            )
        return Result.ok(None)

    def remote_matches(self, path: Path, remote_name: str, expected_url: str) -> Result[tuple[bool, Option[str]], AppError]:
        actual_url = self.remote_url(path, remote_name)
        if actual_url.is_err:
            return Result.err(actual_url.error)
        actual = actual_url.value
        if actual.is_none:
            return Result.ok((False, Option.none()))
        return Result.ok((normalize_remote_url(actual.value) == normalize_remote_url(expected_url), actual))
