---
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

## 概述

这个 skill 用来维护 Codex 原生 skill。每个 skill 都是一个目录，核心是 `SKILL.md`，并可按需带上 `agents/`、`references/`、`scripts/` 和 `assets/`。

## 工作流程

1. 先基于当前仓库结构工作，不要额外发明新的 skill 元数据文件。
2. `SKILL.md` 保持简洁，把细节性内容放进 `references/`。
3. 确保 `agents/openai.yaml` 和 skill 的用途、调用名保持一致。
4. 对重复性高或容易出错的操作，优先用确定性的 `scripts/` 处理。
5. 如果 skill 已经写完，接下来要用当前仓库 CLI 做创建后自检，改用 `$skill-validation`。
