---
name: "skill-validation"
description: "当已经在这个仓库里创建或修改了一个 Codex skill，需要用当前 workbench CLI 做创建后自检时使用，包括结构校验、bundle 检查、测试夹具验证，以及链接前确认。"
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
    recommends: []
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

## 概述

这个 skill 只负责“skill 写完之后怎么验”，不负责通用的 skill 设计方法论。  
如果任务是设计目录结构、编写 `SKILL.md`、决定哪些内容放 `references/` 或 `scripts/`，优先使用 `$codex-skill-authoring`。  
这里的校验对象既可以是顶层 `skills/<name>/`，也可以是保留 skill 格式的内部模块 `references/**/<name>/SKILL.md`。

## 使用原则

- 先围绕单个目标对象工作，不要在一次校验里混入多个顶层 skill 或多个内部模块。
- 优先使用当前仓库已有 CLI，而不是手工猜测是否合格。
- 遇到具体命令、输出解释或验收清单时，读取 `references/workbench-validation-flow.md` 和 `references/acceptance-checklist.md`。
- 顶层 skill 只有当 `lint` 和 `test` 都通过后，才进入 `context build` 或 `skill link` 阶段；内部模块不做独立 link。

## 工作流程

1. 先确认目标对象是顶层 `skills/<name>/`，还是内部模块 `references/**/<name>/SKILL.md`，并检查目录名、front matter 里的 `name` 与目标名称一致。
2. 顶层 skill 按 `references/workbench-validation-flow.md` 中的顺序先跑结构检查，再解决 error 级别问题。
3. 顶层 skill 再按同一份 reference 跑 bundle 测试，并在需要时做 `context build` 与 link 前确认。
4. 内部模块不走独立 link；改为按 `references/workbench-validation-flow.md` 里的内部模块检查项确认 `SKILL.md`、局部 `references/` 和可选元数据完整。
5. 最后按 `references/acceptance-checklist.md` 汇总失败点，明确是顶层 CLI 校验失败，还是内部模块结构失败。

## 输出要求

- 报告出明确的失败点，优先指出是顶层 `lint`、`test`、bundle 内容、链接目标，还是内部模块结构的问题。
- 需要具体判断规则时，优先引用 reference 中已经整理好的当前 CLI 说明，而不是重复发明新的校验标准。
