# 验收清单

在当前仓库里，一个新建或修改后的 skill 至少应满足下面这些条件。

## 基础结构

- 顶层 skill 位于 `skills/<name>/`
- 顶层 skill 或内部模块目录里都有 `SKILL.md`
- 顶层 skill 推荐有 `agents/openai.yaml`
- 如果正文中提到了 `references/...`、`scripts/...`、`assets/...`，这些路径必须真实存在

## `SKILL.md` 要点

- `name` 和当前目录名一致
- `description` 明确说明“做什么”和“什么时候用”
- 正文聚焦流程和规则，不把所有细节都塞进去
- 需要细节时，改放到 `references/`

## `agents/openai.yaml` 要点

- 只对顶层 skill 强制要求
- `interface` 是对象
- `interface.default_prompt` 显式提到 `$skill-name`
- `policy.allow_implicit_invocation` 如果存在，必须是布尔值

## 内部模块要点

- 内部模块允许位于任意父 skill 的 `references/**/<name>/`
- 内部模块不独立 link，也不要求独立被发现
- 内部模块仍应保留 skill-shaped 结构，便于分阶段装载和结构检查
- 如果保留了 `agents/openai.yaml`、`tests/` 或 `examples/`，它们应该和当前模块内容一致

## 测试与 bundle

- `skill lint` 通过
- `skill test` 通过
- `context build` 后，bundle 中确实出现期望的 skill 描述、UI 元数据和参考资料

## 链接边界

只会把 `skills/` 下面的顶层 skill 目录逐个链接到 `~/.codex/skills`。

不会独立链接内部模块目录，例如 `references/**/<name>/`。

不会链接这些维护工具目录：

- `src/`
- `templates/`
- `tests/`
- `workspace-config/`
- `reports/`
