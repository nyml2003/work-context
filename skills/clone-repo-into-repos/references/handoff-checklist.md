# 结果回报

## clone 至少说明

- `original_url`
- `clone_url`
- `target_path`
- 是否传了 `--branch`、`--name`、`--dry-run`

## inspect / commit 至少说明

- `repo_path`
- `changed_files` 或 `status_short` 的简要摘要
- `suggested_message` 和最终实际使用的 `message`
- `commit_hash`（如果真的提交了）

## 冲突和失败

1. 目标目录已存在时，要明确说明没有覆盖。
2. 私有仓库、鉴权失败或 `safe.directory` 失败时，要把错误原样带回，不要猜测仓库内容。
3. 只跑了 `--dry-run` 时，要明确说明还没有真正 clone 或 commit。
4. 没有改动时，要明确说明没有创建 commit。
