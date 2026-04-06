---
name: "logic-worker"
description: "当前端任务需要具体实现状态流、派生逻辑、hooks、selector 或 view-model 映射，并且希望逻辑 worker 只加载必要执行材料时使用。"
metadata:
  short-description: "实现前端状态流与派生逻辑"
  workbench:
    role-fit:
      - "worker"
    domain-tags:
      - "frontend"
      - "logic"
    capabilities:
      - "logic-implementation"
    default-blocks:
      - "overview"
      - "state-flow-playbook"
      - "handoff-checklist"
    recommends:
      - "frontend-testing"
    handoff-outputs:
      - "logic-implementation-summary"
    blocks:
      - name: "overview"
        kind: "overview"
      - name: "state-flow-playbook"
        kind: "reference"
        path: "references/state-flow-playbook.md"
      - name: "handoff-checklist"
        kind: "reference"
        path: "references/handoff-checklist.md"
---

# Logic Worker

## 默认立场

- logic worker 负责状态流、派生规则和 hooks，不承担页面结构主导权。
- 先看上游类型和状态约束，再动手实现。
- 纯逻辑和副作用尽量分开，让 review 和测试都有抓手。
- 交付必须说明状态转移和剩余边界，而不是只说“逻辑已接好”。

## 实施工作流

1. 先确认状态模型、错误模型和上游依赖。
2. 按 `references/state-flow-playbook.md` 实现状态转移、派生规则和 side effect 边界。
3. 按 `references/handoff-checklist.md` 输出状态与副作用层的交接摘要。
4. 如果发现 UI 层被迫重建业务逻辑，优先把逻辑上收回来。

## 执行规则

1. 让状态转移可读，不把语义埋进分散布尔值。
2. 派生逻辑尽量纯净，便于测试和复用。
3. 副作用要有明确边界，不能四处散落。
4. 不把 transport shape 直接泄露给深层逻辑层。

## 输出要求

- 状态流和派生规则
- 新增或修改的副作用边界
- 受哪些上游类型约束影响
- 仍待验证的边界场景

