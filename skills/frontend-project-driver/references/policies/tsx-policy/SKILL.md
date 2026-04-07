---
name: "tsx-policy"
description: "当前端任务需要先约束 TSX 组件拆分、props 设计、渲染边界和可访问性结构，再交给 UI worker 落地时使用。"
metadata:
  short-description: "给出 TSX 组件与渲染约束"
  workbench:
    role-fit:
      - "policy"
    domain-tags:
      - "frontend"
      - "ui"
    capabilities:
      - "tsx-rules"
    default-blocks:
      - "overview"
      - "component-boundaries"
      - "rendering-and-accessibility"
    recommends:
      - "tailwind-policy"
      - "eslint-policy"
    handoff-outputs:
      - "tsx-guidance"
    blocks:
      - name: "overview"
        kind: "overview"
      - name: "component-boundaries"
        kind: "reference"
        path: "references/component-boundaries.md"
      - name: "rendering-and-accessibility"
        kind: "reference"
        path: "references/rendering-and-accessibility.md"
---

# TSX Policy

## 默认立场

- 先定组件边界，再谈 JSX 写法。
- props 代表意图，不代表“把所有上游变量打包传下去”。
- 结构可访问性是组件约束的一部分，不是最后补救项。
- policy 只定义组件和渲染规则，不直接承担 UI 实现。

## 政策工作流

1. 按 `references/component-boundaries.md` 确定容器、叶子组件、局部 helper 的拆分方式。
2. 按 `references/rendering-and-accessibility.md` 约束条件渲染、交互结构和基础可访问性。
3. 最后把组件边界、props 设计和渲染禁忌整理成 handoff。

## 执行规则

1. 如果 JSX 分支过多，优先拆结构，不要把所有判断都塞进 return。
2. 不把复杂数据映射直接写进 JSX，先准备 render-ready 数据。
3. 能用原生语义结构表达的，不默认发明额外包装层。
4. 组件之间的状态 ownership 必须写清楚，避免 UI worker 重新猜。

## 输出要求

- 推荐组件拆分
- 关键 props 边界
- 状态 ownership 说明
- 结构和可访问性约束

