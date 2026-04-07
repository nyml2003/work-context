---
name: "eslint-policy"
description: "当前端任务需要先明确 lint 判断规则、禁用边界、导入纪律和安全写法，再交给实现侧执行时使用。"
metadata:
  short-description: "给出前端 lint 约束"
  workbench:
    role-fit:
      - "policy"
    domain-tags:
      - "frontend"
      - "ui"
      - "logic"
      - "api"
      - "logging"
    capabilities:
      - "eslint-rules"
    default-blocks:
      - "overview"
      - "lint-decision-rules"
      - "suppression-and-imports"
    recommends: []
    handoff-outputs:
      - "eslint-guidance"
    blocks:
      - name: "overview"
        kind: "overview"
      - name: "lint-decision-rules"
        kind: "reference"
        path: "references/lint-decision-rules.md"
      - name: "suppression-and-imports"
        kind: "reference"
        path: "references/suppression-and-imports.md"
---

# ESLint Policy

## 默认立场

- lint 约束是实现边界的一部分，不是最后收尾时顺手修。
- 先修根因，再考虑 disable comment。
- 导入、异步、未使用代码、临时日志都要在实现过程中就受控。
- policy 负责告诉 worker 哪些写法可接受，哪些必须避免。

## 政策工作流

1. 按 `references/lint-decision-rules.md` 明确当前仓库里哪些 lint 类问题会改变实现选择。
2. 按 `references/suppression-and-imports.md` 定义 disable comment、导入纪律和临时代码边界。
3. 输出 guidance 时明确“允许的妥协”和“不能碰的红线”。

## 执行规则

1. 不把 lint 当成纯样式问题，尤其是未处理 promise、无效 effect、死代码。
2. 如果需要 suppression，必须给出仓库相关的具体理由。
3. console、未使用变量、宽松导入必须有明确边界，不让 worker 自行发挥。
4. repo 现有 config 优先级高于通用意见。

## 输出要求

- 会影响实现结构的 lint 规则
- suppression 使用条件
- 导入与未使用代码边界
- 临时调试代码的处理方式

