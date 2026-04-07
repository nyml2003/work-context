#!/usr/bin/env python3
"""Upsert confirmed plan-flow memory entries into a Markdown memory file."""

from __future__ import annotations

import argparse
import re
from datetime import datetime, timezone
from pathlib import Path


HEADER = """# Plan Flow Memory

This file stores user-approved workflow optimizations for recurring planning and process issues.
Update entries only after explicit user approval.

## Entries
"""


ENTRY_PATTERN = re.compile(
    r"(?ms)^### (?P<title>.+?)\n<!-- plan-flow-memory:key=(?P<key>[a-z0-9-]+) -->\n(?P<body>.*?)(?=^### |\Z)"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--key", required=True, help="Stable ASCII key for the memory entry.")
    parser.add_argument("--title", help="Human-readable title. Defaults to Title Case derived from --key.")
    parser.add_argument("--pattern", required=True, help="Summary of the recurring issue.")
    parser.add_argument(
        "--trigger",
        action="append",
        default=[],
        help="Trigger signal for this pattern. Repeat for multiple signals.",
    )
    parser.add_argument(
        "--workflow-step",
        action="append",
        default=[],
        help="Recommended workflow step. Repeat for each step.",
    )
    parser.add_argument(
        "--scope",
        default="Planning, scoping, and execution-prep conversations.",
        help="Where this rule should apply.",
    )
    parser.add_argument(
        "--skip-when",
        action="append",
        default=[],
        help="Condition where the rule should not be applied. Repeat for multiple conditions.",
    )
    parser.add_argument("--source-note", required=True, help="Short note about how this rule was confirmed.")
    parser.add_argument(
        "--memory-file",
        default=str(Path.home() / ".codex" / "memories" / "plan-flow-memory.md"),
        help="Target Markdown memory file.",
    )
    parser.add_argument(
        "--confirmed",
        choices=("yes", "no"),
        default="yes",
        help="Write only when the user explicitly approved the optimization.",
    )
    parser.add_argument(
        "--updated",
        help="Explicit timestamp in ISO-8601 format. Defaults to current UTC time.",
    )
    return parser.parse_args()


def slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    normalized = re.sub(r"-{2,}", "-", normalized).strip("-")
    if not normalized:
        raise ValueError("key must contain at least one ASCII letter or digit")
    return normalized


def title_from_key(key: str) -> str:
    return " ".join(part.capitalize() for part in key.split("-"))


def current_timestamp(explicit: str | None) -> str:
    if explicit:
        return explicit
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def render_bullets(items: list[str]) -> list[str]:
    return [f"  - {item}" for item in items]


def render_numbered(items: list[str]) -> list[str]:
    return [f"  {index}. {item}" for index, item in enumerate(items, start=1)]


def render_entry(
    *,
    key: str,
    title: str,
    pattern: str,
    triggers: list[str],
    workflow_steps: list[str],
    scope: str,
    skip_when: list[str],
    source_note: str,
    updated: str,
) -> str:
    lines = [
        f"### {title}",
        f"<!-- plan-flow-memory:key={key} -->",
        f"- Pattern: {pattern}",
        "- Trigger Signals:",
        *render_bullets(triggers),
        "- Recommended Workflow:",
        *render_numbered(workflow_steps),
        f"- Scope: {scope}",
    ]
    if skip_when:
        lines.extend(["- Skip When:", *render_bullets(skip_when)])
    else:
        lines.append("- Skip When: none noted")
    lines.extend(
        [
            f"- Source Note: {source_note}",
            f"- Updated: {updated}",
            "",
        ]
    )
    return "\n".join(lines)


def ensure_header(text: str) -> str:
    stripped = text.strip()
    if stripped:
        return stripped + "\n"
    return HEADER.rstrip() + "\n"


def upsert_entry(document: str, *, key: str, entry: str) -> tuple[str, str]:
    for match in ENTRY_PATTERN.finditer(document):
        if match.group("key") != key:
            continue
        updated = document[: match.start()] + entry + document[match.end() :]
        return updated.rstrip() + "\n", "updated"
    separator = "" if document.endswith("\n\n") else "\n"
    return document.rstrip() + f"{separator}\n{entry}", "created"


def main() -> int:
    args = parse_args()
    if args.confirmed != "yes":
        print("skipped: confirmation was not yes")
        return 0

    key = slugify(args.key)
    if not args.trigger:
        raise SystemExit("at least one --trigger is required")
    if not args.workflow_step:
        raise SystemExit("at least one --workflow-step is required")

    memory_path = Path(args.memory_file).expanduser()
    memory_path.parent.mkdir(parents=True, exist_ok=True)

    existing = ""
    if memory_path.exists():
        existing = memory_path.read_text(encoding="utf-8")
    document = ensure_header(existing)
    entry = render_entry(
        key=key,
        title=args.title or title_from_key(key),
        pattern=args.pattern.strip(),
        triggers=[item.strip() for item in args.trigger if item.strip()],
        workflow_steps=[item.strip() for item in args.workflow_step if item.strip()],
        scope=args.scope.strip(),
        skip_when=[item.strip() for item in args.skip_when if item.strip()],
        source_note=args.source_note.strip(),
        updated=current_timestamp(args.updated),
    )
    updated_document, action = upsert_entry(document, key=key, entry=entry)
    memory_path.write_text(updated_document, encoding="utf-8")
    print(f"{action}: {memory_path}")
    print(f"key: {key}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
