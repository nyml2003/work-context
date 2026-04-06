---
name: "typescript-policy"
description: "当前端任务需要先明确 TypeScript 类型边界、状态模型、错误模型和可接受写法，再交给 worker 实现时使用。"
metadata:
  short-description: "给出前端 TypeScript 约束"
  workbench:
    role-fit:
      - "policy"
    domain-tags:
      - "frontend"
      - "logic"
      - "api"
      - "logging"
    capabilities:
      - "typescript-rules"
    default-blocks:
      - "overview"
      - "type-boundaries"
      - "state-and-error-models"
    recommends:
      - "eslint-policy"
    handoff-outputs:
      - "typescript-guidance"
    blocks:
      - name: "overview"
        kind: "overview"
      - name: "type-boundaries"
        kind: "reference"
        path: "references/type-boundaries.md"
      - name: "state-and-error-models"
        kind: "reference"
        path: "references/state-and-error-models.md"
---

# TypeScript Policy

## 默认立场

- 先定义边界，再写实现；不要先写代码再补类型。
- 外部输入默认不可信，进入业务层之前先收窄。
- 类型的目标是让边界清晰、状态显式，而不是炫技。
- policy 负责给 worker 可消费的类型约束，不替代具体实现。

## 政策工作流

1. 先按 `references/type-boundaries.md` 判断输入、输出、共享类型和运行时收窄边界。
2. 再按 `references/state-and-error-models.md` 给出状态模型、错误模型和异步状态表达方式。
3. 最后把这些约束压缩成 worker 能直接消费的指导摘要。

## 执行规则

1. 明确哪些值可以是 `undefined`，哪些必须显式用 `null` 或 discriminated union 表达。
2. 明确外部 payload 是否需要 runtime guard，不要让 worker 自己猜。
3. 明确共享类型应该放在哪里，避免每个实现面各自定义近似类型。
4. 如果 repo 现有约定与通用 TypeScript 最佳实践冲突，优先尊重 repo 约定并解释原因。

## 输出要求

- 类型边界说明
- 状态与错误模型
- 需要的 runtime guard 或 narrowing 规则
- 交给 worker 的类型落点建议

