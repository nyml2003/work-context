# Skill 路由

## 高层入口

- 需要从设计视角定义方向、做体验评审或局部改版判断：`$ui-ux-designer`
- 需要直接以工程师视角推进完整前端任务：`$frontend-engineer`
- 需要明确拆子任务、依赖和并行边界：`$frontend-director` + `$parallel-planner`

## Policy 路由

- 类型边界、状态模型、错误模型：`$typescript-policy`
- TSX 组件边界、props 和结构：`$tsx-policy`
- Tailwind 类名组织、变体和抽象：`$tailwind-policy`
- lint 约束、禁用边界、导入纪律：`$eslint-policy`
- 日志、埋点、诊断信号边界：`$logging-policy`

## Worker 路由

- 页面结构、组件布局、视觉状态：`$ui-worker`
- hooks、状态流、派生逻辑：`$logic-worker`
- API 调用、映射、失败路径：`$api-integration-worker`
- 日志、埋点、诊断接入：`$logging-worker`

## Review 路由

- 测试覆盖、验收路径、可测试性：`$frontend-testing`
- 回归风险、跨功能影响、发布准备：`$regression-review`

## 默认规则

1. 单 agent 路线优先选一个主 skill，再按缺口补 1 到 3 个专项 skill。
2. 多 agent 路线按阶段装 skill，不让每个 agent 都加载全套。
3. 只要 handoff 足够稳定，下游就消费 handoff + 自己的最小 skill 集合。

