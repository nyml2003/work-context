---
name: "ui-worker"
description: "当前端任务需要具体实现页面结构、组件布局、视觉状态和交互外观，并且希望 UI worker 只加载必要的 UI 执行材料时使用。"
metadata:
  short-description: "实现前端 UI 结构与交互外观"
  workbench:
    role-fit:
      - "worker"
    domain-tags:
      - "frontend"
      - "ui"
    capabilities:
      - "ui-implementation"
    default-blocks:
      - "overview"
      - "implementation-playbook"
      - "handoff-checklist"
    recommends:
      - "frontend-testing"
    handoff-outputs:
      - "ui-implementation-summary"
    blocks:
      - name: "overview"
        kind: "overview"
      - name: "implementation-playbook"
        kind: "reference"
        path: "references/implementation-playbook.md"
      - name: "handoff-checklist"
        kind: "reference"
        path: "references/handoff-checklist.md"
---

# UI Worker

## 默认立场

- UI worker 负责页面壳、组件结构、状态外观和交互表层，不重新定义上游架构。
- 默认先消费上游 handoff，再动手写 UI，不主动回溯所有 policy skill。
- 先把结构和状态位搭好，再做细节 polish。
- 交付时必须给下游清晰 handoff，而不是只说“页面已完成”。

## 实施工作流

1. 先确认自己消费的是哪份 UI handoff，以及有哪些必须满足的状态和约束。
2. 按 `references/implementation-playbook.md` 实施页面结构、组件拆分和状态外观。
3. 按 `references/handoff-checklist.md` 整理交付摘要，说明实现范围和剩余风险。
4. 如果发现上游 handoff 不足，只补必要缺口，不擅自扩权重写 policy。

## 执行规则

1. 优先修改拥有当前 UI slice 的最小文件面。
2. 不把复杂逻辑、接口映射或埋点判断硬塞进 UI 文件。
3. loading、empty、error、disabled 等状态必须进入 UI 实现面。
4. 如果 JSX 或 class 组织开始失控，优先拆结构，不要继续堆。

## 输出要求

- 实现了哪些 UI 状态与交互外观
- 改了哪些文件
- 对数据形态或上游逻辑的依赖假设
- 仍待补齐的视觉、文案或状态风险

