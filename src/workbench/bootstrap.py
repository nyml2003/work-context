from __future__ import annotations

from pathlib import Path

from .core import Result
from .domain.errors import AppError, AppErrorCode, app_error
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


SAMPLE_LOCAL_SKILL_MD = """---
name: "local-cli-operations"
description: "当需要在当前终端工作目录内执行基础本地文件与目录操作时使用，优先通过 workbench 的 local CLI 统一读写、搜索和查看路径信息。"
metadata:
  short-description: "用 local CLI 做本地文件操作"
---

# Local CLI 操作

## 概述

这个 skill 用来在当前终端工作目录内做基础本地文件操作。优先使用 workbench 的 `local` 子命令，不要直接依赖 `cat`、`type`、`ls`、`dir`、`grep`、`findstr` 这类系统相关命令。

## 使用边界

- 所有 local 命令的路径边界都由 CLI 在代码里限制到“调用命令时的当前工作目录”。
- 需要具体命令参数时，读取 `references/cli-quickstart.md`。
- 需要判断某个路径为什么能访问或为什么被拒绝时，读取 `references/path-boundary.md`。

## 工作流程

1. 先确认目标路径位于当前终端工作目录内。
2. 按任务选择最小的 `local` 子命令完成读取、列目录、搜索、写入、追加、建目录或查看状态。
3. 需要改写文件前，优先先用 `local stat` 或 `local list` 确认目标位置。
4. 如果遇到越界错误，不要绕过 CLI，先调整工作目录或把目标路径改成边界内路径。
"""


SAMPLE_LOCAL_OPENAI_YAML = """interface:
  display_name: "Local CLI Operations"
  short_description: "Use workbench local CLI for file operations inside the current cwd"
  default_prompt: "使用 $local-cli-operations 在当前终端工作目录内通过 workbench local CLI 处理本地文件和目录操作。"
policy:
  allow_implicit_invocation: true
"""


SAMPLE_LOCAL_CLI_QUICKSTART = """# local CLI 快速参考

当你需要跨平台地做基础本地文件操作时，优先使用下面这些命令。

## 读取文件

```powershell
python scripts/workbench.py local read <path>
python scripts/workbench.py local read <path> --start-line 10 --end-line 40
```

## 列目录

```powershell
python scripts/workbench.py local list <path>
python scripts/workbench.py local list <path> --recursive --kind file --pattern "*.py"
```

## 搜文本

```powershell
python scripts/workbench.py local grep <path> --pattern "TODO"
python scripts/workbench.py local grep <path> --pattern "build_context" --glob "*.py" --ignore-case
```

## 写入和追加

```powershell
python scripts/workbench.py local write <path> --content "hello"
python scripts/workbench.py local write <path> --content "replace" --overwrite
python scripts/workbench.py local append <path> --content "`nworld"
```

## 建目录和查看状态

```powershell
python scripts/workbench.py local mkdir <path> --parents
python scripts/workbench.py local stat <path>
```
"""


SAMPLE_LOCAL_PATH_BOUNDARY = """# 路径边界说明

`local` 命令不会把路径访问范围绑死在仓库根，而是绑在“调用命令时的当前工作目录”。

## 规则

- CLI 会先把输入路径解析成绝对路径。
- 解析后如果路径不在当前工作目录之内，命令会直接失败。
- 这个限制在代码里强制执行，不依赖 agent 是否自觉。
- 相对路径和绝对路径都会做同样的边界检查。

## 例子

如果当前终端工作目录是 `C:\\repo\\project`：

- `notes/todo.md` 可以访问
- `C:\\repo\\project\\src\\main.py` 可以访问
- `..\\shared\\data.txt` 会被拒绝
- `C:\\repo\\other\\README.md` 会被拒绝
"""


SAMPLE_LOCAL_EXAMPLE = """{
  "request": "在当前终端目录里读取 docs/plan.md 的前 40 行，搜索 TODO，并把结果追加到 reports/notes.txt。",
  "preferred_commands": [
    "local read",
    "local grep",
    "local append"
  ]
}
"""


SAMPLE_LOCAL_TEST = """{
  "bundle_contains": [
    "name: \\"local-cli-operations\\"",
    "python scripts/workbench.py local read <path>",
    "调用命令时的当前工作目录",
    "CLI 会先把输入路径解析成绝对路径。"
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


def initialize_repo(root: Path, *, include_samples: bool = False, overwrite: bool = False) -> Result[list[Path], AppError]:
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
            "skills/local-cli-operations/SKILL.md": SAMPLE_LOCAL_SKILL_MD,
            "skills/local-cli-operations/agents/openai.yaml": SAMPLE_LOCAL_OPENAI_YAML,
            "skills/local-cli-operations/references/cli-quickstart.md": SAMPLE_LOCAL_CLI_QUICKSTART,
            "skills/local-cli-operations/references/path-boundary.md": SAMPLE_LOCAL_PATH_BOUNDARY,
            "skills/local-cli-operations/examples/basic.json": SAMPLE_LOCAL_EXAMPLE,
            "skills/local-cli-operations/tests/basic.json": SAMPLE_LOCAL_TEST,
        }
        for relative_path, content in sample_files.items():
            target = root / relative_path
            if write_text(target, content, overwrite=overwrite):
                created.append(target)
    return Result.ok(created)
