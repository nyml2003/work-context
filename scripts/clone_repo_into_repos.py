#!/usr/bin/env python
from __future__ import annotations

import sys

from git_repo_workflow import main as workflow_main


def main(argv: list[str] | None = None) -> int:
    return workflow_main(["clone", *(argv or sys.argv[1:])])


if __name__ == "__main__":
    raise SystemExit(main())
