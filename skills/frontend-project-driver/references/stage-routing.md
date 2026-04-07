# 阶段路由

## 总规则

- 先决定当前阶段，再读取对应模块；不要先把所有模块都读进来。
- 所有下沉模块都保留在 `references/**/<module>/SKILL.md`，先读模块自己的 `SKILL.md`，再按需读该模块的 `references/`。
- 阶段路由保持一层直达；如果需要换阶段或换模块，回到本文件重新选择，不做深层模块互跳。

## Planning

- 需要拆任务、划 ownership、定义 handoff：`references/planning/frontend-director/SKILL.md`
- 需要判断并行、串行和写入冲突：`references/planning/parallel-planner/SKILL.md`

## Design

- 需要做界面方向判断、体验评审、局部改版建议：`references/design/ui-ux-designer/SKILL.md`

## Policy

- 类型边界、状态模型、错误模型：`references/policies/typescript-policy/SKILL.md`
- TSX 组件边界、props 和可访问性结构：`references/policies/tsx-policy/SKILL.md`
- Tailwind 原子类组织、变体和抽象边界：`references/policies/tailwind-policy/SKILL.md`
- lint 约束、禁用边界、导入纪律：`references/policies/eslint-policy/SKILL.md`
- 日志、埋点、诊断信号边界：`references/policies/logging-policy/SKILL.md`

## Execution

- 需要完整工程实现路线、生命周期判断或统一推进：`references/execution/frontend-engineer/SKILL.md`
- 主矛盾是页面结构、组件布局、视觉状态：`references/execution/ui-worker/SKILL.md`
- 主矛盾是 hooks、状态流、派生逻辑：`references/execution/logic-worker/SKILL.md`
- 主矛盾是 API 调用、响应映射、失败路径：`references/execution/api-integration-worker/SKILL.md`
- 主矛盾是日志、埋点、诊断接入：`references/execution/logging-worker/SKILL.md`

## Review

- 测试覆盖、验收路径、可测试性：`references/review/frontend-testing/SKILL.md`
- 回归风险、跨功能影响、发布准备：`references/review/regression-review/SKILL.md`

## 默认顺序

1. 先做 framing，再做 mode selection。
2. 如果需要拆任务，先进入 planning。
3. 如果需要界面方向判断，先进入 design。
4. 如果需要规则约束，进入对应 policy 模块。
5. 实现阶段先选一个主 execution 模块，缺口再补专项 execution 模块。
6. 收尾时进入 review，再按 delivery checklist 汇总结论。
