---
name: "parallel-planner"
description: "当前端子任务之间需要明确哪些步骤可以并行、哪些必须串行，以及哪里会发生写入冲突或决策冲突时使用。"
metadata:
  short-description: "规划前端任务的并行与串行边界"
  workbench:
    role-fit:
      - "director"
    domain-tags:
      - "frontend"
    capabilities:
      - "parallel-planning"
    default-blocks:
      - "overview"
      - "dependency-classification"
      - "write-conflict-rules"
    recommends: []
    handoff-outputs:
      - "parallelization-plan"
    blocks:
      - name: "overview"
        kind: "overview"
      - name: "dependency-classification"
        kind: "reference"
        path: "references/dependency-classification.md"
      - name: "write-conflict-rules"
        kind: "reference"
        path: "references/write-conflict-rules.md"
---

# Parallel Planner

## 默认立场

- 并行不是目标，稳定交付才是目标。
- 先看依赖，再看 agent 数量；不要先决定并行再找理由。
- 先看写入面冲突，再看工作流名称；不同名字的任务也可能抢同一处上下文。
- 默认依赖 handoff 并行，不依赖共享完整上下文并行。

## 规划工作流

1. 先按 `references/dependency-classification.md` 把依赖分成信息依赖、结构依赖、验证依赖。
2. 再按 `references/write-conflict-rules.md` 判断哪些子任务会争抢相同文件面或相同决策面。
3. 能通过稳定 handoff 解耦的，优先并行。
4. 无法通过稳定 handoff 解耦的，明确串行顺序和阻塞原因。

## 执行规则

1. policy 总结可以作为多个 worker 的共同上游。
2. 共享类型重构、共享布局系统改造、共享路由变更，默认串行。
3. UI、逻辑、API、日志只有在文件 ownership 和决策 ownership 都基本分离时才并行。
4. review 默认是 fan-in 阶段，等实现收敛后再统一进入。

## 输出要求

- 说明哪些任务可并行、哪些必须等待。
- 每个串行点都给出具体冲突原因。
- 给出下游实际消费的 handoff，而不是泛泛写“等上游完成”。

