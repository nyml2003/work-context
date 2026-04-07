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
    recommends: []
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

这个 skill 用来维护 Codex 原生 skill。每个顶层 skill 都是 `skills/<name>/` 下的目录，核心是 `SKILL.md`，并可按需带上 `agents/`、`references/`、`scripts/` 和 `assets/`。当需要减少入口但保留完整模块结构时，也允许在某个 skill 的 `references/**/<name>/SKILL.md` 下维护内部 skill-shaped module。

## 工作流程

1. 先基于当前仓库结构工作，不要额外发明新的 skill 元数据文件。
2. 顶层 skill 的 `SKILL.md` 保持简洁，把细节性内容放进 `references/`；内部模块也保留 `SKILL.md`，但只承担阶段化装载和结构化维护，不作为独立入口。
3. 顶层 skill 才强制维护 `agents/openai.yaml`；内部模块可以保留同形态文件，但不要求作为独立发现入口。
4. 对重复性高或容易出错的操作，优先用确定性的 `scripts/` 处理。
5. 如果 skill 或内部模块已经写完，接下来要用当前仓库 CLI 或本地结构检查做自检，改用 `$skill-validation`。
