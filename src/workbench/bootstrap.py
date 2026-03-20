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
description: "当需要创建或维护 Codex skill 时使用，包括编写 SKILL.md front matter、维护 agents/openai.yaml 元数据，以及整理 references 或 scripts。"
metadata:
  short-description: "维护 Codex skills"
---

# Codex Skill 编写

## 概述

这个 skill 用来维护 Codex 原生 skill。每个 skill 都是一个目录，核心是 `SKILL.md`，并可按需带上 `agents/`、`references/`、`scripts/` 和 `assets/`。

## 工作流程

1. 先基于当前仓库结构工作，不要额外发明新的 skill 元数据文件。
2. `SKILL.md` 保持简洁，把细节性内容放进 `references/`。
3. 确保 `agents/openai.yaml` 和 skill 的用途、调用名保持一致。
4. 对重复性高或容易出错的操作，优先用确定性的 `scripts/` 处理。
5. 如果 skill 已经写完，接下来要用当前仓库 CLI 做创建后自检，改用 `$skill-validation`。
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


SAMPLE_VALIDATION_SKILL_MD = """---
name: "skill-validation"
description: "当已经在这个仓库里创建或修改了一个 Codex skill，需要用当前 workbench CLI 做创建后自检时使用，包括结构校验、bundle 检查、测试夹具验证，以及同步前确认。"
metadata:
  short-description: "校验新建或修改后的 Codex skill"
---

# Skill 创建校验

## 概述

这个 skill 只负责“skill 写完之后怎么验”，不负责通用的 skill 设计方法论。  
如果任务是设计目录结构、编写 `SKILL.md`、决定哪些内容放 `references/` 或 `scripts/`，优先使用 `$codex-skill-authoring`。

## 使用原则

- 先围绕单个目标 skill 工作，不要在一次校验里混入多个 skill。
- 优先使用当前仓库已有 CLI，而不是手工猜测是否合格。
- 遇到具体命令、输出解释或验收清单时，读取 `references/workbench-validation-flow.md` 和 `references/acceptance-checklist.md`。
- 只有当 `lint` 和 `test` 都通过后，才进入 `context build` 或 `skill sync` 阶段。

## 工作流程

1. 先确认目标 skill 的目录名、front matter 里的 `name`、以及实际要校验的 skill 名称一致。
2. 按 `references/workbench-validation-flow.md` 中的顺序先跑结构检查，再解决 error 级别问题。
3. 再按同一份 reference 跑 bundle 测试，确认测试夹具要求的内容确实出现在实际 bundle 中。
4. 需要人工确认最终上下文时，继续按 reference 里的 bundle 预览步骤检查 `SKILL.md`、`agents/openai.yaml` 和 `references/`。
5. 如需安装前确认，最后再按 reference 里的同步步骤验证目标目录是否正确。

## 输出要求

- 报告出明确的失败点，优先指出是 `lint`、`test`、bundle 内容还是同步目标的问题。
- 需要具体判断规则时，优先引用 reference 中已经整理好的当前 CLI 说明，而不是重复发明新的校验标准。
"""


SAMPLE_VALIDATION_OPENAI_YAML = """interface:
  display_name: "Skill 创建校验"
  short_description: "校验新建或修改后的 Codex skill 结构、测试与同步准备情况"
  default_prompt: "使用 $skill-validation 校验这个仓库里刚创建或刚修改的 Codex skill。"
policy:
  allow_implicit_invocation: true
"""


SAMPLE_VALIDATION_FLOW = """# 当前仓库的校验流程

当一个 Codex skill 已经创建或基本写完后，优先按下面的顺序使用当前仓库 CLI。

## 1. 先跑结构检查

```powershell
python scripts/workbench.py skill lint <name>
```

这个命令主要检查：

- `SKILL.md` 是否有合法的 YAML front matter
- 是否包含 `name` 和 `description`
- `name` 是否是小写短横线格式
- skill 目录名是否和 `name` 一致
- `agents/openai.yaml` 结构是否可读
- `SKILL.md` 里提到的 `agents/`、`references/`、`scripts/`、`assets/` 路径是否真的存在
- `examples/` 和 `tests/` 里的 JSON 是否可解析
"""


SAMPLE_VALIDATION_CHECKLIST = """# 验收清单

在当前仓库里，一个新建或修改后的 skill 至少应满足下面这些条件。

## 基础结构

- skill 目录位于 `skills/<name>/`
- 目录里有 `SKILL.md`
- 推荐有 `agents/openai.yaml`
- 如果正文中提到了 `references/...`、`scripts/...`、`assets/...`，这些路径必须真实存在

## 同步边界

只会同步 skills/ 下面的 skill 目录。
"""


SAMPLE_VALIDATION_EXAMPLE = """{
  "request": "我刚创建了一个新的 Codex skill，帮我用当前仓库的 CLI 做创建后自检。",
  "target_skill": "release-note-helper",
  "checks": [
    "skill lint",
    "skill test",
    "context build"
  ]
}
"""


SAMPLE_VALIDATION_TEST = """{
  "bundle_contains": [
    "name: \\"skill-validation\\"",
    "使用 $skill-validation 校验这个仓库里刚创建或刚修改的 Codex skill。",
    "python scripts/workbench.py skill lint <name>",
    "只会同步 skills/ 下面的 skill 目录。"
  ],
  "reference_count": 2
}
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
            "skills/skill-validation/SKILL.md": SAMPLE_VALIDATION_SKILL_MD,
            "skills/skill-validation/agents/openai.yaml": SAMPLE_VALIDATION_OPENAI_YAML,
            "skills/skill-validation/references/workbench-validation-flow.md": SAMPLE_VALIDATION_FLOW,
            "skills/skill-validation/references/acceptance-checklist.md": SAMPLE_VALIDATION_CHECKLIST,
            "skills/skill-validation/examples/basic.json": SAMPLE_VALIDATION_EXAMPLE,
            "skills/skill-validation/tests/basic.json": SAMPLE_VALIDATION_TEST,
        }
        for relative_path, content in sample_files.items():
            target = root / relative_path
            if write_text(target, content, overwrite=overwrite):
                created.append(target)
    return created
