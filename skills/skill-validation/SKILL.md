---
name: "skill-validation"
description: "当已经在这个仓库里创建或修改了一个 Codex skill，需要用当前 workbench CLI 做创建后自检时使用，包括结构校验、bundle 检查、测试夹具验证，以及链接前确认。"
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
- 只有当 `lint` 和 `test` 都通过后，才进入 `context build` 或 `skill link` 阶段。

## 工作流程

1. 先确认目标 skill 的目录名、front matter 里的 `name`、以及实际要校验的 skill 名称一致。
2. 按 `references/workbench-validation-flow.md` 中的顺序先跑结构检查，再解决 error 级别问题。
3. 再按同一份 reference 跑 bundle 测试，确认测试夹具要求的内容确实出现在实际 bundle 中。
4. 需要人工确认最终上下文时，继续按 reference 里的 bundle 预览步骤检查 `SKILL.md`、`agents/openai.yaml` 和 `references/`。
5. 如需安装前确认，最后再按 reference 里的链接步骤验证目标目录是否正确。

## 输出要求

- 报告出明确的失败点，优先指出是 `lint`、`test`、bundle 内容还是链接目标的问题。
- 需要具体判断规则时，优先引用 reference 中已经整理好的当前 CLI 说明，而不是重复发明新的校验标准。
