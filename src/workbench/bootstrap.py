from __future__ import annotations

from pathlib import Path

from .config import load_config, write_default_config
from .fs import ensure_dir, write_text


DEFAULT_TEMPLATES: dict[str, str] = {
    "templates/skill/SKILL.md.tpl": """---
name: "{name}"
description: "{description}"
metadata:
  short-description: "{short_description}"
---

# {title}

## Overview

{overview}

## When To Use

- Use this skill when the task clearly matches the domain in the description.
- Load bundled references only when they are needed for the current task.
- Prefer scripts for deterministic operations that would otherwise be rewritten often.

## Workflow

1. Inspect the request and confirm this skill is the right fit.
2. Read only the references or scripts needed for the task.
3. Execute the smallest reliable action that moves the task forward.
4. Record assumptions or limits when the request cannot be completed directly.
""",
    "templates/skill/openai.yaml.tpl": """interface:
  display_name: "{title}"
  short_description: "{short_description}"
  default_prompt: "{default_prompt}"
policy:
  allow_implicit_invocation: true
""",
    "templates/skill/reference.md.tpl": """# {title} Reference

Use this file for details that should be loaded only when needed.

## Suggested Contents

- Decision rules
- API or file format notes
- Domain constraints
- Reusable examples
""",
    "templates/skill/script.py.tpl": """#!/usr/bin/env python3
\"\"\"Helper script for {name}.\"\"\"


def main() -> None:
    print("Replace this placeholder with deterministic logic.")


if __name__ == "__main__":
    main()
""",
    "templates/skill/asset.txt.tpl": """Place output templates or other non-context assets here.
""",
}


SAMPLE_SKILL_MD = """---
name: "codex-skill-authoring"
description: "Use this skill when creating or maintaining Codex skills, including SKILL.md frontmatter, agents/openai.yaml metadata, and bundled references or scripts."
metadata:
  short-description: "Maintain Codex skills"
---

# Codex Skill Authoring

## Overview

This skill helps maintain Codex-native skills that live as folders containing `SKILL.md` plus optional `agents/`, `references/`, `scripts/`, and `assets/` resources.

## Workflow

1. Start from the current repository structure rather than inventing new metadata files.
2. Keep `SKILL.md` concise and move deep details into `references/`.
3. Ensure `agents/openai.yaml` stays consistent with the skill purpose and invocation name.
4. Prefer deterministic scripts for repetitive or fragile operations.
"""


SAMPLE_OPENAI_YAML = """interface:
  display_name: "Codex Skill Authoring"
  short_description: "Maintain Codex skills"
  default_prompt: "Use $codex-skill-authoring to create or refine a Codex skill."
policy:
  allow_implicit_invocation: true
"""


SAMPLE_REFERENCE_AUTHORING = """# Skill Structure

Every Codex skill must include a `SKILL.md` file with YAML front matter containing at least `name` and `description`.

Optional directories:

- `agents/` for UI-facing metadata
- `references/` for load-on-demand documentation
- `scripts/` for deterministic helper code
- `assets/` for files used in outputs
"""


SAMPLE_REFERENCE_VALIDATION = """# Validation Checklist

- `SKILL.md` starts with valid YAML front matter.
- `name` uses lowercase hyphen-case and matches the folder name.
- `description` clearly states what the skill does and when to use it.
- `agents/openai.yaml` uses quoted strings and its `default_prompt` mentions `$skill-name`.
"""


SAMPLE_SCRIPT = """#!/usr/bin/env python3
\"\"\"Validate a generated skill name.\"\"\"

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
"""


SAMPLE_EXAMPLE_JSON = """{
  "request": "Create a new Codex skill for changelog maintenance.",
  "constraints": [
    "Keep SKILL.md concise.",
    "Use agents/openai.yaml for UI metadata."
  ]
}
"""


SAMPLE_TEST_JSON = """{
  "bundle_contains": [
    "name: \\"codex-skill-authoring\\"",
    "Use $codex-skill-authoring",
    "Validation Checklist"
  ],
  "reference_count": 2
}
"""


SAMPLE_WORKSPACES = """[workspaces]
"""


def initialize_repo(root: Path, *, include_samples: bool = False, overwrite: bool = False) -> list[Path]:
    created: list[Path] = []
    ensure_dir(root)
    if write_default_config(root, overwrite=overwrite):
        created.append(root / "workbench.toml")
    config = load_config(root)
    for path in [
        config.skills_dir,
        config.templates_dir / "skill",
        config.reports_dir,
        config.workspace_config_dir,
    ]:
        if not path.exists():
            ensure_dir(path)
            created.append(path)
    for relative_path, content in DEFAULT_TEMPLATES.items():
        target = root / relative_path
        if write_text(target, content, overwrite=overwrite):
            created.append(target)
    if write_text(config.workspace_registry, SAMPLE_WORKSPACES, overwrite=overwrite):
        created.append(config.workspace_registry)
    if include_samples:
        sample_files = {
            "skills/codex-skill-authoring/SKILL.md": SAMPLE_SKILL_MD,
            "skills/codex-skill-authoring/agents/openai.yaml": SAMPLE_OPENAI_YAML,
            "skills/codex-skill-authoring/references/skill-structure.md": SAMPLE_REFERENCE_AUTHORING,
            "skills/codex-skill-authoring/references/validation-checklist.md": SAMPLE_REFERENCE_VALIDATION,
            "skills/codex-skill-authoring/scripts/validate_name.py": SAMPLE_SCRIPT,
            "skills/codex-skill-authoring/examples/basic.json": SAMPLE_EXAMPLE_JSON,
            "skills/codex-skill-authoring/tests/basic.json": SAMPLE_TEST_JSON,
        }
        for relative_path, content in sample_files.items():
            target = root / relative_path
            if write_text(target, content, overwrite=overwrite):
                created.append(target)
    return created
