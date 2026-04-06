from __future__ import annotations

"""仓库初始化用例。"""

from pathlib import Path

from ..core import Result
from ..domain.errors import AppError, AppErrorCode, app_error
from ..infrastructure.config_store import load_config, write_default_config
from ..infrastructure.filesystem import ensure_dir, write_text

WORKBENCH_SCRIPT_ENTRY = "python ~/.work-context/scripts/workbench.py"


DEFAULT_TEMPLATES: dict[str, str] = {
    "templates/skill/SKILL.md.tpl": """---
name: "{name}"
description: "{description}"
metadata:
  short-description: "{short_description}"
  workbench:
    role-fit:
      - "{role}"
    domain-tags: {domain_tags_json}
    capabilities: {capabilities_json}
    default-blocks:
{default_blocks_yaml}
    recommends: {recommends_json}
    handoff-outputs: {handoff_outputs_json}
    blocks:
{blocks_yaml}
---

# {title}

{body_markdown}
""",
    "templates/skill/openai.yaml.tpl": """interface:
  display_name: "{title}"
  short_description: "{short_description}"
  default_prompt: "{default_prompt}"
policy:
  allow_implicit_invocation: true
""",
    "templates/skill/reference.md.tpl": """# {title}

## 适用时机

- 说明什么情况下应读取这份 reference。

## 默认规则

1. 写这里的判断规则，而不是泛泛介绍。
2. 说明什么做法应优先、什么做法应避免。

## 输出

- 说明读完这份 reference 后，应该给下游什么结果。
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

SAMPLE_WORKSPACES = """[workspaces]
"""

SAMPLE_SKILLS: dict[str, dict[str, str]] = {
    "codex-skill-authoring": {
        "SKILL.md": """---
name: "codex-skill-authoring"
description: "当需要创建或维护 Codex skill 时使用，包括编写 SKILL.md front matter、维护 agents/openai.yaml 元数据，以及整理 references 或 scripts。"
metadata:
  short-description: "维护 Codex skills"
  workbench:
    role-fit:
      - "policy"
    domain-tags:
      - "skills"
    capabilities:
      - "skill-authoring"
    default-blocks:
      - "overview"
      - "skill-structure"
      - "validation-checklist"
    recommends:
      - "skill-validation"
    handoff-outputs:
      - "skill-authoring-guidance"
    blocks:
      - name: "overview"
        kind: "overview"
      - name: "skill-structure"
        kind: "reference"
        path: "references/skill-structure.md"
      - name: "validation-checklist"
        kind: "reference"
        path: "references/validation-checklist.md"
      - name: "validate-name"
        kind: "script_entry"
        path: "scripts/validate_name.py"
---

# Codex Skill 编写

用这个 skill 约束 skill 结构、参考资料位置和确定性脚本入口。
""",
        "agents/openai.yaml": """interface:
  display_name: "Codex Skill Authoring"
  short_description: "Maintain Codex skills"
  default_prompt: "Use $codex-skill-authoring to create or refine a Codex skill."
policy:
  allow_implicit_invocation: true
""",
        "references/skill-structure.md": """# Skill Structure

Keep SKILL.md as the single machine entry and declare runtime blocks in metadata.workbench.
""",
        "references/validation-checklist.md": """# Validation Checklist

- `SKILL.md` includes `metadata.workbench.role-fit`, `capabilities`, `default-blocks`, and `blocks`.
- Referenced files exist.
""",
        "scripts/validate_name.py": """#!/usr/bin/env python3
from __future__ import annotations

import re
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_name.py <skill-name>")
        return 1
    print("valid" if re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", sys.argv[1]) else "invalid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
""",
        "examples/basic.json": """{
  "request": "Create a new Codex skill for changelog maintenance."
}
""",
        "tests/basic.json": """{
  "bundle_contains": [
    "name: \\"codex-skill-authoring\\"",
    "Skill Structure",
    "Validation Checklist"
  ],
  "reference_count": 2,
  "script_entry_count": 0,
  "loaded_blocks": ["overview", "skill-structure", "validation-checklist"]
}
""",
    },
    "skill-validation": {
        "SKILL.md": f"""---
name: "skill-validation"
description: "当已经在这个仓库里创建或修改了一个 Codex skill，需要用当前 workbench CLI 做创建后自检时使用。"
metadata:
  short-description: "校验新建或修改后的 Codex skill"
  workbench:
    role-fit:
      - "review"
    domain-tags:
      - "skills"
    capabilities:
      - "skill-validation"
    default-blocks:
      - "overview"
      - "workbench-validation-flow"
      - "acceptance-checklist"
    recommends:
      - "local-cli-operations"
    handoff-outputs:
      - "validation-report"
    blocks:
      - name: "overview"
        kind: "overview"
      - name: "workbench-validation-flow"
        kind: "reference"
        path: "references/workbench-validation-flow.md"
      - name: "acceptance-checklist"
        kind: "reference"
        path: "references/acceptance-checklist.md"
---

# Skill 创建校验

用这个 skill 校验 skill 结构、默认块装配和链接前准备情况。
""",
        "agents/openai.yaml": """interface:
  display_name: "Skill Validation"
  short_description: "Validate a Codex skill in this repository"
  default_prompt: "Use $skill-validation to validate a Codex skill in this repository."
policy:
  allow_implicit_invocation: true
""",
        "references/workbench-validation-flow.md": f"""# Workbench Validation Flow

Run:

```powershell
{WORKBENCH_SCRIPT_ENTRY} skill lint <name>
{WORKBENCH_SCRIPT_ENTRY} skill test <name>
```
""",
        "references/acceptance-checklist.md": """# Acceptance Checklist

- The skill can be linted.
- The default blocks assemble correctly.
""",
        "examples/basic.json": """{
  "request": "Validate the newly created skill before linking it."
}
""",
        "tests/basic.json": """{
  "bundle_contains": [
    "name: \\"skill-validation\\"",
    "skill lint <name>",
    "Acceptance Checklist"
  ],
  "reference_count": 2,
  "loaded_blocks": ["overview", "workbench-validation-flow", "acceptance-checklist"]
}
""",
    },
    "local-cli-operations": {
        "SKILL.md": """---
name: "local-cli-operations"
description: "当需要在当前终端工作目录内执行基础本地文件与目录操作时使用，优先通过 workbench 的 local CLI。"
metadata:
  short-description: "用 local CLI 做本地文件操作"
  workbench:
    role-fit:
      - "worker"
    domain-tags:
      - "local"
    capabilities:
      - "local-cli"
    default-blocks:
      - "overview"
      - "cli-quickstart"
      - "path-boundary"
    recommends: []
    handoff-outputs:
      - "local-operation-plan"
    blocks:
      - name: "overview"
        kind: "overview"
      - name: "cli-quickstart"
        kind: "reference"
        path: "references/cli-quickstart.md"
      - name: "path-boundary"
        kind: "reference"
        path: "references/path-boundary.md"
---

# Local CLI 操作

优先使用 workbench 的 local 子命令，不要直接依赖系统相关命令。
""",
        "agents/openai.yaml": """interface:
  display_name: "Local CLI Operations"
  short_description: "Use workbench local CLI inside the current cwd"
  default_prompt: "Use $local-cli-operations to work inside the current terminal cwd."
policy:
  allow_implicit_invocation: true
""",
        "references/cli-quickstart.md": f"""# local CLI Quickstart

```powershell
{WORKBENCH_SCRIPT_ENTRY} local read <path>
{WORKBENCH_SCRIPT_ENTRY} local list <path>
```
""",
        "references/path-boundary.md": """# Path Boundary

All local commands are restricted to the current working directory.
""",
        "examples/basic.json": """{
  "request": "Read a file and then inspect its path information."
}
""",
        "tests/basic.json": """{
  "bundle_contains": [
    "name: \\"local-cli-operations\\"",
    "local read <path>",
    "Path Boundary"
  ],
  "reference_count": 2,
  "loaded_blocks": ["overview", "cli-quickstart", "path-boundary"]
}
""",
    },
}


def initialize_repo(root: Path, *, include_samples: bool = False, overwrite: bool = False) -> Result[list[Path], AppError]:
    """初始化一个新的 workbench 仓库布局。"""

    created: list[Path] = []
    try:
        ensure_dir(root)
    except OSError as exc:
        return Result.err(app_error(AppErrorCode.CONFIG_ERROR, str(exc), root=str(root)))
    wrote_config = write_default_config(root, overwrite=overwrite)
    if wrote_config.is_err:
        return Result.err(wrote_config.error)
    if wrote_config.value:
        created.append(root / "workbench.toml")
    config_result = load_config(root)
    if config_result.is_err:
        return Result.err(config_result.error)
    config = config_result.value

    for path in [
        config.skills_dir,
        config.templates_dir / "skill",
        config.reports_dir,
        config.workspace_config_dir,
        config.managed_repos_dir,
    ]:
        if not path.exists():
            try:
                ensure_dir(path)
            except OSError as exc:
                return Result.err(app_error(AppErrorCode.CONFIG_ERROR, str(exc), path=str(path)))
            created.append(path)
    for relative_path, content in DEFAULT_TEMPLATES.items():
        target = root / relative_path
        if write_text(target, content, overwrite=overwrite):
            created.append(target)
    if write_text(config.workspace_registry, SAMPLE_WORKSPACES, overwrite=overwrite):
        created.append(config.workspace_registry)
    if include_samples:
        for skill_name, files in SAMPLE_SKILLS.items():
            for relative_path, content in files.items():
                target = root / "skills" / skill_name / relative_path
                if write_text(target, content, overwrite=overwrite):
                    created.append(target)
    return Result.ok(created)


__all__ = ["DEFAULT_TEMPLATES", "initialize_repo"]
