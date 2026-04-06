---
name: "api-integration-worker"
description: "当前端任务需要实现 API 调用、响应映射、失败处理和 transport 到 view-model 的边界，并且希望 API worker 只加载必要执行材料时使用。"
metadata:
  short-description: "实现前端 API 调用与响应映射"
  workbench:
    role-fit:
      - "worker"
    domain-tags:
      - "frontend"
      - "api"
    capabilities:
      - "api-integration"
    default-blocks:
      - "overview"
      - "transport-boundary-playbook"
      - "error-and-retry-checklist"
    recommends:
      - "frontend-testing"
    handoff-outputs:
      - "api-integration-summary"
    blocks:
      - name: "overview"
        kind: "overview"
      - name: "transport-boundary-playbook"
        kind: "reference"
        path: "references/transport-boundary-playbook.md"
      - name: "error-and-retry-checklist"
        kind: "reference"
        path: "references/error-and-retry-checklist.md"
---

# API Integration Worker

## 默认立场

- API worker 负责 transport 边界，不让原始响应 shape 深入 UI。
- 先明确成功、失败、空态和重试路径，再接调用。
- transport 映射要可读、可审查，不做隐式魔法转换。
- 交付必须说明契约假设和错误路径处理结果。

## 实施工作流

1. 先确认上游类型约束、接口约束和页面需要的状态位。
2. 按 `references/transport-boundary-playbook.md` 处理调用、映射和 view-model 边界。
3. 按 `references/error-and-retry-checklist.md` 检查失败路径、重试和竞态问题。
4. 最后输出给下游的契约假设与剩余风险。

## 执行规则

1. 原始 payload 进入业务层前先收窄或映射。
2. loading、error、empty 状态必须有明确来源。
3. 不把错误吞掉，也不把所有异常都直接甩给 UI。
4. 如果后端契约有不确定性，必须在 handoff 里写明。

## 输出要求

- 接了哪些调用或映射层
- 成功/失败/重试路径如何处理
- 对后端契约的关键假设
- 仍待验证的接口边界

