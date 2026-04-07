---
name: "frontend-project-driver"
description: "当需要把一个前端项目或前端需求作为统一入口推进时使用。它负责先做任务 framing，再判断直接用单 agent 执行，还是拆成多 agent 路线，并为后续阶段装配最小 skill 集合。适用于新页面/模块开发、已有仓库功能迭代、局部重构、联调、验收与交付收尾。"
metadata:
  short-description: "前端项目统一入口与阶段路由器"
  workbench:
    role-fit:
      - "director"
    domain-tags:
      - "frontend"
    capabilities:
      - "frontend-project-driving"
    default-blocks:
      - "overview"
      - "request-framing"
      - "mode-selection"
      - "stage-routing"
      - "delivery-checklist"
    recommends: []
    handoff-outputs:
      - "frontend-project-plan"
    blocks:
      - name: "overview"
        kind: "overview"
      - name: "request-framing"
        kind: "reference"
        path: "references/request-framing.md"
      - name: "mode-selection"
        kind: "reference"
        path: "references/mode-selection.md"
      - name: "stage-routing"
        kind: "reference"
        path: "references/stage-routing.md"
      - name: "delivery-checklist"
        kind: "reference"
        path: "references/delivery-checklist.md"
---

# Frontend Project Driver

## 默认立场

- 用户入口应该只有一个，不应该先自己判断要不要 `plan / resolve / assemble`。
- 先判断任务规模、当前阶段和目标，再决定走单 agent 直做，还是走多 agent 编排。
- 默认只装配当前阶段必需的内部模块，不把 planning、design、policy、execution、review 一次性塞进上下文。
- 这个 skill 负责“该怎么推进”和“下一步读哪个模块”，不重复复制下沉模块正文。

## 驱动工作流

1. 先按 `references/request-framing.md` 整理目标、工作流、限制条件和验收标准。
2. 再按 `references/mode-selection.md` 判断当前任务应走单 agent 路线还是多 agent 路线。
3. 再按 `references/stage-routing.md` 给当前阶段选择最小内部模块集合，并从该文件直达需要的 `references/**/SKILL.md`。
4. 如果走多 agent 路线，先进入 planning 模块产出 task shape、阶段划分和 handoff 边界；如果走单 agent 路线，直接进入 design、policy 或 execution 模块。
5. 结束前按 `references/delivery-checklist.md` 收口测试、评审和交付结果。

## 执行规则

1. 局部改动、单一主工作流、低并发价值的任务，优先单 agent 直做。
2. 同时涉及 UI、逻辑、API、日志、设计评审或明确要求并行的任务，再走多 agent 路线。
3. 需要设计判断时，先读取 `references/design/ui-ux-designer/SKILL.md`；需要统一实现推进时，先读取 `references/execution/frontend-engineer/SKILL.md`。
4. 走多 agent 路线时，不要求用户手写 `task.json`；先在内部整理出任务结构，只有需要兼容 CLI 编排时再物化成文件。
5. 下游 agent 默认消费 handoff 和本 skill 指定的最小模块集合，不继承整包上游上下文。

## 输出要求

- 当前任务 framing
- 单 agent 或多 agent 的模式判断
- 当前阶段应加载的内部模块
- 如需编排时的任务结构、子任务边界与 handoff
- 收尾时的测试、评审和发布检查点
