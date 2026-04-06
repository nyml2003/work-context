---
name: "logging-worker"
description: "当前端任务需要接入日志、埋点或诊断信息，并且希望 logging worker 只加载必要执行材料时使用。"
metadata:
  short-description: "实现前端日志与诊断接入"
  workbench:
    role-fit:
      - "worker"
    domain-tags:
      - "frontend"
      - "logging"
    capabilities:
      - "logging-implementation"
    default-blocks:
      - "overview"
      - "instrumentation-playbook"
      - "handoff-checklist"
    recommends:
      - "regression-review"
    handoff-outputs:
      - "logging-implementation-summary"
    blocks:
      - name: "overview"
        kind: "overview"
      - name: "instrumentation-playbook"
        kind: "reference"
        path: "references/instrumentation-playbook.md"
      - name: "handoff-checklist"
        kind: "reference"
        path: "references/handoff-checklist.md"
---

# Logging Worker

## 默认立场

- logging worker 只负责按既定 policy 接入高价值信号，不发明新的事件体系。
- 先明确事件与 payload，再动手埋点。
- 诊断信号要可读、可筛、可复盘，不能制造噪音。
- 交付时要说明埋点点位和隐私边界，而不是只说“日志已加上”。

## 实施工作流

1. 先确认上游 logging guidance、事件字段和禁止字段。
2. 按 `references/instrumentation-playbook.md` 接入日志、埋点或诊断 breadcrumb。
3. 按 `references/handoff-checklist.md` 输出点位、payload 和剩余风险。
4. 发现 policy 未定义的事件时，不擅自扩 schema，先把缺口写进 handoff。

## 执行规则

1. 不记录敏感信息、不保留大段原始对象。
2. 不把 console 调试残留当成正式日志。
3. 成功、失败、关键状态转移的事件边界必须可审查。
4. 同类事件保持稳定 payload 结构。

## 输出要求

- 新增了哪些日志或埋点点位
- payload 包含哪些字段
- 哪些字段做了脱敏或被禁止
- review 还应重点检查什么

