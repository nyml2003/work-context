# 验收清单

在当前仓库里，一个新建或修改后的 skill 至少应满足下面这些条件。

## 基础结构

- skill 目录位于 `skills/<name>/`
- 目录里有 `SKILL.md`
- 推荐有 `agents/openai.yaml`
- 如果正文中提到了 `references/...`、`scripts/...`、`assets/...`，这些路径必须真实存在

## `SKILL.md` 要点

- `name` 和目录名一致
- `description` 明确说明“做什么”和“什么时候用”
- 正文聚焦流程和规则，不把所有细节都塞进去
- 需要细节时，改放到 `references/`

## `agents/openai.yaml` 要点

- `interface` 是对象
- `interface.default_prompt` 显式提到 `$skill-name`
- `policy.allow_implicit_invocation` 如果存在，必须是布尔值

## 测试与 bundle

- `skill lint` 通过
- `skill test` 通过
- `context build` 后，bundle 中确实出现期望的 skill 描述、UI 元数据和参考资料

## 同步边界

只会同步 skills/ 下面的 skill 目录。

不会同步这些维护工具目录：

- `src/`
- `templates/`
- `tests/`
- `workspace-config/`
- `reports/`

