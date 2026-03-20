# Workbench

这是一个专门用来**维护 Codex skills 仓库**的工作台。

它不是业务项目脚手架，也不是通用知识库系统。它做的事情更具体：

- 维护仓库里的 Codex skill
- 校验 skill 目录结构和 `SKILL.md` 格式
- 生成新的 skill 骨架
- 预览一个 skill 实际会被打包成什么上下文
- 把 skill 同步到本机 `~/.codex/skills`

运行时只使用 Python 标准库。

## 这个仓库管理的 skill 长什么样

每个 skill 都是一个目录，结构和 Codex 原生格式对齐：

```text
skills/<skill-name>/
├── SKILL.md
├── agents/openai.yaml        # 可选，但推荐
├── references/              # 可选，按需加载的参考资料
├── scripts/                 # 可选，确定性脚本
├── assets/                  # 可选，输出时要用到的文件
├── examples/                # 仓库内示例输入
└── tests/                   # 仓库内测试夹具
```

其中：

- `SKILL.md` 是核心文件，Codex 真正认的是它
- `agents/openai.yaml` 是 UI 和调用体验相关元数据
- `references/` 放详细文档，不要把所有细节都塞进 `SKILL.md`
- `scripts/` 放重复性高、要求稳定的脚本

## 仓库目录

- `skills/`：所有 Codex skill
- `templates/skill/`：新建 skill 时使用的模板
- `src/workbench/`：CLI 和内部实现
- `workspace-config/`：外部代码仓库登记表
- `reports/`：生成的报告、打包结果、上下文预览

## 当前自带的 skill

- `codex-skill-authoring`：负责“怎么设计和编写一个 Codex skill”
- `skill-validation`：负责“skill 写完以后，怎么用当前 workbench CLI 做创建后自检”

## 最常用的用法

### 1. 先检查仓库里的 skill 有没有问题

```powershell
python scripts/workbench.py skill lint
python scripts/workbench.py skill test
```

这两个命令分别会做：

- `skill lint`：检查 `SKILL.md` front matter、`agents/openai.yaml`、示例文件、测试文件
- `skill test`：把 skill 实际拼成 bundle，再检查测试夹具里要求出现的内容是否真的出现

### 2. 新建一个 Codex skill

```powershell
python scripts/workbench.py skill new release-note-helper `
  --description "当需要编写、整理或审查仓库发布说明时使用这个 skill。" `
  --resources references scripts `
  --examples
```

执行后会生成：

```text
skills/release-note-helper/
├── SKILL.md
├── agents/openai.yaml
├── references/
├── scripts/
├── examples/
└── tests/
```

然后你主要去改这几个地方：

- `skills/release-note-helper/SKILL.md`
- `skills/release-note-helper/agents/openai.yaml`
- `skills/release-note-helper/references/`
- `skills/release-note-helper/scripts/`

### 3. 预览一个 skill 最终会带上什么内容

```powershell
python scripts/workbench.py context build codex-skill-authoring
```

它会把这个 skill 的：

- `SKILL.md`
- `agents/openai.yaml`
- `references/`

整理成一个可读的 bundle，输出到 `reports/`。

如果你想看 JSON：

```powershell
python scripts/workbench.py context build codex-skill-authoring --format json
```

### 4. 安装或同步到本机 Codex skills 目录

把仓库里的全部 skill 同步到默认位置：

```powershell
python scripts/workbench.py skill sync
```

只同步某一个 skill：

```powershell
python scripts/workbench.py skill sync codex-skill-authoring
```

同步到自定义目录做测试：

```powershell
python scripts/workbench.py skill sync codex-skill-authoring --target C:\temp\codex-skills
```

默认目标目录定义在 `workbench.toml`：

```toml
[codex]
install_root = "~/.codex/skills"
```

注意：同步时只会复制 `skills/` 下面的 skill 目录，不会复制 `src/`、`templates/`、`tests/`、`workspace-config/`、`reports/` 这些维护工具目录。

## 推荐工作流

如果你平时就是维护 skill，最简单的流程就是：

1. 先改 `skills/<skill-name>/SKILL.md`
2. 如果需要 UI 元数据，再改 `agents/openai.yaml`
3. 把大段参考资料放进 `references/`
4. 跑 `skill lint`
5. 跑 `skill test`
6. 用 `context build` 看一下最终 bundle
7. 用 `skill sync` 同步到本机 Codex

## 所有命令

- `init`：初始化或补齐仓库结构
- `skill new`：创建一个新的 Codex skill 骨架
- `skill lint`：校验 skill 结构和格式
- `skill test`：运行 skill 的 bundle 测试
- `skill pack`：把一个 skill 打成 zip
- `skill sync`：把 skill 复制到 Codex skill 目录
- `skill install`：`skill sync` 的别名
- `context build`：生成一个 skill 的上下文预览
- `workspace add`：登记外部代码仓库
- `workspace check`：对登记过的仓库执行只读检查
- `report generate`：生成仓库状态报告

## Skill 格式规则

### `SKILL.md`

必须以 YAML front matter 开头，用 `---` 包起来，例如：

```md
---
name: "my-skill"
description: "当需要处理某类任务时使用这个 skill。"
metadata:
  short-description: "简短描述"
---
```

当前校验器要求：

- 必须有 `name`
- 必须有 `description`
- `name` 必须是小写短横线风格，例如 `release-note-helper`
- skill 目录名必须和 `name` 一致

支持的可选字段：

- `license`
- `allowed-tools`
- `metadata`

### `agents/openai.yaml`

这是可选文件，但推荐保留。当前会检查：

- `interface` 必须是对象
- `interface.default_prompt` 最好显式提到 `$skill-name`
- `policy.allow_implicit_invocation` 如果存在，必须是布尔值

## 示例 skill

仓库里已经带了一个示例：

- `skills/codex-skill-authoring/`
- `skills/skill-validation/`

如果你想先理解格式，先看它最直接。
