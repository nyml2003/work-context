---
name: "logging-policy"
description: "当前端任务需要先明确日志、埋点和诊断信息的事件设计、隐私边界和信号质量，再交给实现侧接入时使用。"
metadata:
  short-description: "给出日志与诊断约束"
  workbench:
    role-fit:
      - "policy"
    domain-tags:
      - "frontend"
      - "logging"
    capabilities:
      - "logging-rules"
    default-blocks:
      - "overview"
      - "event-design"
      - "privacy-and-signal-quality"
    recommends:
      - "typescript-policy"
    handoff-outputs:
      - "logging-guidance"
    blocks:
      - name: "overview"
        kind: "overview"
      - name: "event-design"
        kind: "reference"
        path: "references/event-design.md"
      - name: "privacy-and-signal-quality"
        kind: "reference"
        path: "references/privacy-and-signal-quality.md"
---

# Logging Policy

## 默认立场

- 日志和埋点是产品与诊断信号，不是任意输出。
- 先定义记录什么，再决定怎么接入。
- 信号必须稳定、可读、可过滤，不能靠海量噪音碰运气。
- policy 负责约束事件设计、隐私边界和信号质量，不负责具体埋点代码。

## 政策工作流

1. 按 `references/event-design.md` 定义事件命名、事件粒度和 payload 结构。
2. 按 `references/privacy-and-signal-quality.md` 定义不能记录什么、哪些信号才有保留价值。
3. 最后整理成可供 logging worker 执行的接入清单。

## 执行规则

1. 不记录秘密、token、原始隐私数据或大段原始响应。
2. 不为了“以后可能有用”而把所有状态都打出来。
3. 用户可见错误、技术异常和诊断 breadcrumb 要分层。
4. guidance 必须告诉 worker 哪些事件该打、哪些不能打、哪些字段必须脱敏。

## 输出要求

- 事件命名与粒度规则
- payload 允许与禁止字段
- 脱敏与保留策略
- 需要打点的关键时机

