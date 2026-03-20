#!/usr/bin/env python3
"""Validate a generated skill name."""

from __future__ import annotations

import re
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_name.py <skill-name>")
        return 1
    if re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", sys.argv[1]):
        print("valid")
        return 0
    print("invalid")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

