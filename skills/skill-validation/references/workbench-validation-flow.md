# 当前仓库的校验流程

当一个 Codex skill 已经创建或基本写完后，优先按下面的顺序使用当前仓库 CLI。

## 1. 先跑结构检查

```powershell
python ~/.work-context/scripts/workbench.py skill lint <name>
```

这个命令主要检查：

- `SKILL.md` 是否有合法的 YAML front matter
- 是否包含 `name` 和 `description`
- `name` 是否是小写短横线格式
- skill 目录名是否和 `name` 一致
- `agents/openai.yaml` 结构是否可读
- `SKILL.md` 里提到的 `agents/`、`references/`、`scripts/`、`assets/` 路径是否真的存在
- `examples/` 和 `tests/` 里的 JSON 是否可解析

先把 error 级别的问题解决，再看 warning 是否需要人工判断。

## 2. 再跑 bundle 测试

```powershell
python ~/.work-context/scripts/workbench.py skill test <name>
```

这个命令会读取 `tests/*.json`，把 skill 真正拼成 bundle，然后检查：

- `bundle_contains` 里的关键内容是否真的出现在 bundle 中
- `reference_count` 是否符合预期

如果这里失败，优先检查：

- `tests/*.json` 写的断言是不是过严
- `references/` 文件是否缺失或未被 bundle 带上
- `agents/openai.yaml` 或 `SKILL.md` 里的关键字符串是否和测试预期不一致

## 3. 用 context build 做人工确认

```powershell
python ~/.work-context/scripts/workbench.py context build <name>
python ~/.work-context/scripts/workbench.py context build <name> --format json
```

这个命令适合人工确认 bundle 的真实内容，尤其要看：

- front matter 是否正确
- `agents/openai.yaml` 是否和 skill 的用途一致
- 该带上的 `references/` 是否真的带上了
- 有没有把不该进上下文的内容塞进去

## 4. 链接前确认

如需把 skill 暴露给 Codex，先确保 scripts 稳定入口已经建好：

```powershell
python ~/.work-context/scripts/workbench.py workspace link-scripts
```

然后再把目标 skill 链接到默认位置：

```powershell
python ~/.work-context/scripts/workbench.py skill link <name>
```

默认目标目录定义在 `workbench.toml`：

```toml
[codex]
install_root = "~/.codex/skills"
scripts_root = "~/.work-context/scripts"
```
