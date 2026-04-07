---
name: "regression-review"
description: "当前端改动已经完成，需要从回归风险、跨功能影响和发布准备角度做最终评审时使用。"
metadata:
  short-description: "评审前端回归风险与发布准备"
  workbench:
    role-fit:
      - "review"
    domain-tags:
      - "frontend"
      - "review"
    capabilities:
      - "regression-review"
    default-blocks:
      - "overview"
      - "risk-scan"
      - "release-report"
    recommends: []
    handoff-outputs:
      - "regression-review-summary"
    blocks:
      - name: "overview"
        kind: "overview"
      - name: "risk-scan"
        kind: "reference"
        path: "references/risk-scan.md"
      - name: "release-report"
        kind: "reference"
        path: "references/release-report.md"
---

# Regression Review

## 默认立场

- 回归评审先看跨面影响，再看局部实现细节。
- 不重复测试报告，而是聚焦行为耦合、共享面和发布风险。
- 风险必须落到具体流转或模块，不写泛泛的“注意回归”。
- review 结论要能支撑是否可发布，而不是只列问题。

## 评审工作流

1. 先按 `references/risk-scan.md` 扫描共享组件、共享类型、共享路由、接口契约和日志面。
2. 再按 `references/release-report.md` 输出风险等级、阻塞项和建议跟踪项。
3. 重点识别 happy path 之外的恢复路径、联动路径和默认值变化。
4. 如果问题属于测试缺口，用回归风险语言说明影响，而不是复述测试意见。

## 输出要求

- 最高风险回归向量
- 风险等级与原因
- 发布阻塞项与观察项
- 建议合并后继续监控什么

