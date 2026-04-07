---
name: "frontend-testing"
description: "当前端实现已经完成，需要评估测试覆盖、验收路径和可测试性是否足够时使用。"
metadata:
  short-description: "评审前端测试覆盖与验收路径"
  workbench:
    role-fit:
      - "review"
    domain-tags:
      - "frontend"
      - "review"
    capabilities:
      - "testing-review"
    default-blocks:
      - "overview"
      - "coverage-review"
      - "reporting-template"
    recommends:
      - "regression-review"
    handoff-outputs:
      - "testing-review-summary"
    blocks:
      - name: "overview"
        kind: "overview"
      - name: "coverage-review"
        kind: "reference"
        path: "references/coverage-review.md"
      - name: "reporting-template"
        kind: "reference"
        path: "references/reporting-template.md"
---

# Frontend Testing

## 默认立场

- 测试评审先看验收路径是否被覆盖，再看数量。
- 不把“可以再补点测试”当成有信息量的结论。
- 要区分缺测试和难测试，这会影响后续改法。
- review 负责指出覆盖缺口，不直接接管实现。

## 评审工作流

1. 先按 `references/coverage-review.md` 把验收标准映射到验证路径。
2. 再按 `references/reporting-template.md` 输出覆盖结论、风险和建议。
3. 重点识别 loading、empty、error、retry、恢复路径是否被验证。
4. 对不可测或难测结构，要明确指出是测试问题还是架构问题。

## 输出要求

- 已覆盖哪些路径
- 哪些路径仍未验证
- 最高风险缺口是什么
- 当前实现是否具备可测试性

