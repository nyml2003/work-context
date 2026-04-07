---
name: "tailwind-policy"
description: "当前端任务使用 Tailwind，需要先约束原子类组织方式、变体使用和抽象边界，再交给 UI worker 落地时使用。"
metadata:
  short-description: "给出 Tailwind 使用约束"
  workbench:
    role-fit:
      - "policy"
    domain-tags:
      - "frontend"
      - "ui"
    capabilities:
      - "tailwind-rules"
    default-blocks:
      - "overview"
      - "utility-structure"
      - "variants-and-extraction"
    recommends:
      - "tsx-policy"
    handoff-outputs:
      - "tailwind-guidance"
    blocks:
      - name: "overview"
        kind: "overview"
      - name: "utility-structure"
        kind: "reference"
        path: "references/utility-structure.md"
      - name: "variants-and-extraction"
        kind: "reference"
        path: "references/variants-and-extraction.md"
---

# Tailwind Policy

## 默认立场

- Tailwind 是实现工具，不是临时设计系统。
- 先约束类名组织，再写样式。
- 变体和抽象边界必须可读，不能靠超长 class string 硬撑。
- policy 负责定规则，不替代具体页面样式实现。

## 政策工作流

1. 按 `references/utility-structure.md` 约束类名分组、响应式组织和 token 使用。
2. 按 `references/variants-and-extraction.md` 约束重复样式、状态样式和抽象时机。
3. 输出给 worker 的 guidance 应直接回答“哪些可以内联、哪些必须抽离”。

## 执行规则

1. 先复用现有 spacing、color、radius、typography token。
2. 不用动态拼接制造难以审查的 class 组合。
3. 重复样式出现时，优先抽成可命名的变体或组件层封装。
4. 响应式和状态类必须保持清晰顺序，避免阅读时需要来回跳。

## 输出要求

- 原子类组织规则
- token 复用边界
- 变体组织方式
- 抽象与禁止抽象的时机

