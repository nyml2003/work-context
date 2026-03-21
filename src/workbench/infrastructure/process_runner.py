from __future__ import annotations

import subprocess
from pathlib import Path

from ..core import Result
from ..domain.errors import AppError, AppErrorCode, app_error


class CommandRunner:
    def run_args(self, args: list[str], *, cwd: Path) -> Result[subprocess.CompletedProcess[str], AppError]:
        try:
            completed = subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=False)
        except OSError as exc:
            return Result.err(app_error(AppErrorCode.EXTERNAL_TOOL_FAILED, str(exc), args=args, cwd=str(cwd)))
        return Result.ok(completed)
