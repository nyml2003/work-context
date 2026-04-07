# 执行脚本

## 首选命令

- clone 使用：`python scripts/git_repo_workflow.py clone --url <repo-url>`
- inspect 使用：`python scripts/git_repo_workflow.py inspect --repo <repo-path>`
- commit 使用：`python scripts/git_repo_workflow.py commit --repo <repo-path>`
- 如果已经执行过 `python scripts/workbench.py workspace link-scripts`，优先用稳定路径：
  `python ~/.work-context/scripts/git_repo_workflow.py clone --url <repo-url>`
  `python ~/.work-context/scripts/git_repo_workflow.py inspect --repo <repo-path>`
  `python ~/.work-context/scripts/git_repo_workflow.py commit --repo <repo-path>`
- 旧入口 `python scripts/clone_repo_into_repos.py --url <repo-url>` 仍保留兼容，但不再作为推荐入口。

## 常用参数

- clone 指定分支或 tag：`--branch <name>`
- clone 指定目标目录名：`--name <dir-name>`
- clone 指定目标根目录：`--dest-root <path>`
- clone 只解析路径和命令、不实际 clone：`--dry-run`
- inspect / commit 指定仓库路径：`--repo <repo-path>`
- commit 用显式 message：`--message "chore: update foo"`
- commit 只预览 message 和命令：`--dry-run`

## 使用规则

1. 目标工作区不明确时，clone 先跑一次 `--dry-run`，确认 `target_path` 是否落在期望的 `repos/` 下。
2. 生成 commit message 前，先跑 `inspect` 读取 `status_short`、`changed_files` 和 diff 摘要，再决定是否直接采用 `suggested_message`。
3. `commit` 默认会 stage 全部当前改动；如果只想提交已 stage 的部分，改用 `commit --stage staged`。
4. 如果 shell 或沙箱拦截了联网 clone，或 git 提示 `safe.directory`，保留错误并按当前环境重新请求授权。
