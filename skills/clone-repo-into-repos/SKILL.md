---
name: "clone-repo-into-repos"
description: "当需要 clone 仓库、读取当前 git 改动、生成 commit message 并提交时使用。"
metadata:
  short-description: "git clone、inspect、commit 工作流"
  workbench:
    role-fit:
      - "worker"
    domain-tags: ["git", "workspace"]
    capabilities: ["repo-clone", "repo-inspect", "repo-commit"]
    default-blocks:
      - "overview"
      - "execution-playbook"
      - "handoff-checklist"
    recommends: []
    handoff-outputs: ["git-operation-result"]
    blocks:
      - name: "overview"
        kind: "overview"
      - name: "execution-playbook"
        kind: "reference"
        path: "references/execution-playbook.md"
      - name: "handoff-checklist"
        kind: "reference"
        path: "references/handoff-checklist.md"
---

# Git Repo Workflow

## 默认立场

- 这个 skill 现在覆盖一条完整的 git 工作流：clone 仓库、读取当前 worktree 改动、生成 commit message、再执行 commit。
- 为了兼容旧引用，skill 名称仍保留 `clone-repo-into-repos`，但推荐执行入口已经统一收敛到同一个 workflow 脚本。
- 需要联网、访问私有仓库、或遇到 `safe.directory` / 沙箱限制时，保留失败信息并按当前环境提权重试。

## 实施工作流

1. clone 任务先确认仓库 URL、目标目录名、分支和目标根目录；路径不明确时先跑 dry-run。
2. commit 任务先读取当前改动，再根据 `inspect` 输出生成 message；用户没给 message 时，可以直接采用脚本建议或在此基础上精修。
3. 真正提交前，确认是否要 stage 全部改动；默认按当前任务把本次变更完整提交，不拆无关提交。
4. 完成后按 `references/handoff-checklist.md` 汇报 clone 路径、改动摘要、使用的 message、commit hash 和任何阻塞。

## 执行规则

1. 默认目标根目录是当前工作区的 `repos/`；脚本会优先寻找最近祖先目录下已有的 `repos/`，找不到时才落到当前目录下新建 `repos/`。
2. GitHub 的仓库根链接、`/tree/...`、`/blob/...` 页面链接都可以直接交给脚本；脚本会归一化成可 clone 的仓库 URL。
3. commit 默认只处理当前仓库已有改动；没有改动时不创建空提交。
4. 对已存在的 clone 目标目录不做覆盖式 clone；对 commit 任务不隐式 push。

## 输出要求

- clone 时给出原始 URL、归一化后的 clone URL、最终目录和是否使用了 `branch` / `name` / `dry-run`
- commit 时给出 `repo_path`、改动文件摘要、最终 message、是否自动生成 message、commit hash
- 任何网络、权限或鉴权阻塞
