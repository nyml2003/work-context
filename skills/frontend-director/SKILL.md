---
name: "frontend-director"
description: "当一个前端任务需要被拆成可执行子任务、明确依赖顺序，并为不同子 agent 规划最小 skill 装配边界时使用。"
metadata:
  short-description: "拆解前端任务并规划子 agent 装配"
  workbench:
    role-fit:
      - "director"
    domain-tags:
      - "frontend"
    capabilities:
      - "frontend-directing"
    default-blocks:
      - "overview"
      - "task-decomposition"
      - "handoff-boundaries"
    recommends:
      - "parallel-planner"
    handoff-outputs:
      - "frontend-subtask-plan"
    blocks:
      - name: "overview"
        kind: "overview"
      - name: "task-decomposition"
        kind: "reference"
        path: "references/task-decomposition.md"
      - name: "handoff-boundaries"
        kind: "reference"
        path: "references/handoff-boundaries.md"
---

# Frontend Director

## 默认立场

- 先拆目标，再拆人力；不要为了“多 agent 并行”反过来发明任务。
- 先确定角色边界，再决定 skill 边界；不要把 policy、worker、review 混成一个子任务。
- 默认通过 handoff 共享结果，而不是让每个子 agent 继承整包上下文。
- 拆出来的每个子任务都必须有明确产物、依赖和完成定义。

## 规划工作流

1. 先理解目标、工作流、限制条件和验收标准。
2. 按 `references/task-decomposition.md` 判断是否真的需要 UI、逻辑、API、日志四类工作流。
3. 再按 `references/handoff-boundaries.md` 设计 ownership、depends_on、parallelizable 和 handoff 内容。
4. 最后压缩计划规模，只保留能真正改变交付结果的子任务。

## 执行规则

1. 一个 worker 子任务默认只解决一个主矛盾，不要同时承担页面结构、状态重构、接口适配和埋点接入。
2. policy 子任务只给约束与判断，不直接承担代码实现。
3. review 子任务默认作为下游汇总点，不提前介入未稳定的中间实现。
4. 输出的子任务至少说明：角色、目标、依赖、并行性、需要加载的 skill、预期 handoff。

## 输出要求

- 明确哪些子任务必须串行，哪些可以并行。
- 明确每个子任务最小需要的 skill 装配面。
- 明确哪些约束要先由 policy 总结，再交给 worker 消费。

