# Workbench 架构说明

这份文档描述的是当前仓库里的实际结构，不是历史状态，也不是未来愿景图。

它主要回答 4 个问题：

- 新维护者应该先看哪里
- CLI 到业务逻辑的调用链怎么走
- 模块分层边界是什么
- 当前技术债具体还剩哪些

## 1. 一眼看懂

`workbench` 当前是一个分层 CLI，推荐按下面的顺序建立心智模型：

- `cli.py`
  - 进程入口、统一 JSON 输出、命令分发
- `composition/`
  - 运行时装配
- `commands/`
  - 命令声明、参数协议、parser 构建
- `application/`
  - 用例编排
- `domain/`
  - 领域对象、配置模型、错误语义
- `infrastructure/`
  - 文件、git、子进程、配置存储、注册表等外部交互
- `core/`
  - `Result` / `Option` 与轻量格式协议实现

```mermaid
flowchart TD
    CLI["cli.py"]
    Composition["composition/"]
    Commands["commands/"]
    Application["application/"]
    Domain["domain/"]
    Infrastructure["infrastructure/"]
    Core["core/"]

    CLI --> Commands
    CLI --> Composition
    Commands --> Application
    Commands --> Core
    Composition --> Application
    Composition --> Infrastructure
    Composition --> Core
    Application --> Domain
    Application --> Infrastructure
    Application --> Core
    Infrastructure --> Domain
    Infrastructure --> Core
    Domain --> Core
```

主规则很简单：

- 外层依赖内层
- CLI 不承载业务规则
- 配置、文件、格式解析各自有明确落点
- 公开边界统一走 `Result` / `Option`

## 2. 分层职责

### `core/`

这里只放跨全项目的基础协议和轻量格式能力：

- `result.py`
  - `Result[T, E]`
  - `Option[T]`
- `toml.py`
  - 受限 TOML 解析 / 序列化
- `yaml.py`
  - 受限 YAML 解析 / 序列化

这层不应该知道 skill、workspace、CLI 这些业务概念。

### `domain/`

这里放业务语义本身，而不是参数解析或 IO 编排。

当前主要有：

- `config.py`
  - `WorkbenchConfig`
- `errors.py`
  - `AppErrorCode`
  - `AppError`
- `workspace.py`
  - `Workspace`
  - remote URL 规则
  - check command 规则
- `skill.py`
  - `Skill`
  - skill 共享常量

这层的约束：

- 不依赖 `argparse`
- 不直接起子进程
- 不负责文件格式读写

### `infrastructure/`

这里负责与外部世界交互：

- `config_store.py`
- `filesystem.py`
- `template_rendering.py`
- `git_client.py`
- `process_runner.py`
- `workspace_registry.py`
- `local_files.py`
- `report_output.py`
- `skill_loader.py`
- `skill_templates.py`
- `skill_packaging.py`

这层可以做 IO，但不负责跨多个对象的业务流程编排。

### `application/`

这里是用例层，负责把 domain 规则和 infrastructure 适配器拼起来。

当前主要入口：

- `bootstrap_service.py`
- `SkillService`
- `WorkspaceService`
- `ContextService`
- `LocalService`
- `ReportService`

skill 相关 use case 目前主要分成：

- `skill_creation.py`
- `skill_validation.py`
- `skill_bundle.py`

这层的定位是：

- 给命令层提供稳定入口
- 不把命令行参数对象泄漏进来
- 不把底层文件布局细节扩散出去

### `composition/`

这里是运行时 composition root。

- `runtime.py`
  - `RuntimeContext`
  - `ServiceContainer`
  - `build_service_container`

它负责：

- 加载 `WorkbenchConfig`
- 保证基础目录存在
- 延迟装配 service graph
- 为 `local` 命令单独缓存 `LocalService`

### `commands/`

这里是命令层，不是业务层。

关键抽象：

- `ArgumentSpec`
- `CommandSpec`
- `CommandGroup`
- `CommandResult`
- `ParserFactory`

每个 `*_command.py` 文件只做两件事：

1. 声明命令结构
2. 把解析后的参数转交给 application service

## 3. 启动链路

CLI 启动过程在 [cli.py](/C:/Users/nyml/code/work-context/src/workbench/cli.py) 很薄：

1. 调用 `load_command_groups()`
2. 用 `ParserFactory` 构建 parser
3. 创建 `RuntimeContext`
4. 根据 `args.command` 找到对应 `CommandGroup`
5. 统一输出 JSON

```mermaid
sequenceDiagram
    participant User
    participant CLI as cli.py
    participant Loader as commands.__init__
    participant Factory as ParserFactory
    participant Runtime as RuntimeContext
    participant Group as CommandGroup

    User->>CLI: workbench ...
    CLI->>Loader: load_command_groups()
    Loader-->>CLI: Result[tuple[CommandGroup]]
    CLI->>Factory: build(groups)
    Factory-->>CLI: Result[argparse.ArgumentParser]
    CLI->>Runtime: RuntimeContext(cwd)
    CLI->>Group: run(args, runtime)
    Group-->>CLI: Result[CommandResult, AppError]
    CLI-->>User: {ok: true, value: ...} / {ok: false, err: ...}
```

这个链路的关键点是：

- `cli.py` 不再手工堆一大串 subparser
- parser 冲突在构建阶段提前失败
- 业务错误和参数错误都能走统一错误协议回传

## 4. 配置与初始化链路

这次重构后，配置和初始化已经从根级模块收口到了明确边界。

```mermaid
flowchart LR
    Init["application/bootstrap_service.py"]
    ConfigStore["infrastructure/config_store.py"]
    ConfigDomain["domain/config.py"]
    Fs["infrastructure/filesystem.py"]
    CoreToml["core/toml.py"]

    Init --> ConfigStore
    Init --> Fs
    ConfigStore --> ConfigDomain
    ConfigStore --> CoreToml
    ConfigStore --> Fs
```

职责分布如下：

- `domain/config.py`
  - 运行时配置对象
- `infrastructure/config_store.py`
  - 默认配置
  - `workbench.toml` 读写
  - 基础目录布局创建
- `application/bootstrap_service.py`
  - 仓库初始化用例
  - 模板与 sample skill 的落盘编排

这意味着根级已经不再保留：

- `bootstrap.py`
- `config.py`
- `fs.py`
- `simple_toml.py`
- `yamlish.py`

## 5. 命令是怎么接入的

[commands/__init__.py](/C:/Users/nyml/code/work-context/src/workbench/commands/__init__.py) 负责装载命令组。

当前机制是命令包内约定式发现：

- 扫描 `commands/` 下模块
- 跳过 `base.py`
- 导入模块
- 收集模块导出的 `COMMAND_GROUP`
- 按 `(order, name)` 排序

新增一级命令的标准做法是：

1. 新建一个 `*_command.py`
2. 暴露 `COMMAND_GROUP`
3. 让装载器发现它

而不是继续去改 `cli.py`。

```mermaid
flowchart LR
    Modules["commands/*.py"]
    Loader["load_command_groups()"]
    Group["COMMAND_GROUP"]
    Parser["ParserFactory"]

    Modules --> Loader
    Loader --> Group
    Group --> Parser
```

## 6. 主要业务链路

### Skill 链路

```mermaid
flowchart LR
    SkillService["application/skill_service.py"]
    Creation["application/skill_creation.py"]
    Validation["application/skill_validation.py"]
    Bundle["application/skill_bundle.py"]
    Loader["infrastructure/skill_loader.py"]
    Packaging["infrastructure/skill_packaging.py"]
    Templates["infrastructure/skill_templates.py"]
    SkillDomain["domain/skill.py"]
    ConfigDomain["domain/config.py"]
    CoreYaml["core/yaml.py"]

    SkillService --> Creation
    SkillService --> Validation
    SkillService --> Bundle
    SkillService --> Loader
    SkillService --> Packaging
    Creation --> Templates
    Creation --> SkillDomain
    Creation --> ConfigDomain
    Creation --> CoreYaml
    Validation --> Loader
    Validation --> SkillDomain
    Validation --> ConfigDomain
    Bundle --> Loader
    Bundle --> SkillDomain
    Bundle --> ConfigDomain
    Loader --> CoreYaml
```

职责分布如下：

- `SkillService`
  - application façade
  - 对命令层暴露稳定接口
- `skill_creation.py`
  - 创建 skill 脚手架
- `skill_validation.py`
  - lint 编排
  - lint 规则收集
  - skill 结果投影
- `skill_bundle.py`
  - bundle 渲染
  - fixture 执行
- `skill_loader.py`
  - 发现 skill
  - 解析 `SKILL.md`
  - 读取 `agents/openai.yaml`
- `skill_packaging.py`
  - 打包与同步

### Workspace 链路

[workspace_service.py](/C:/Users/nyml/code/work-context/src/workbench/application/workspace_service.py) 负责编排：

- workspace 注册
- safe check 执行
- git remote 状态比对
- remote 初始化 / 修复

它依赖的主要基础设施是：

- [workspace_registry.py](/C:/Users/nyml/code/work-context/src/workbench/infrastructure/workspace_registry.py)
- [git_client.py](/C:/Users/nyml/code/work-context/src/workbench/infrastructure/git_client.py)
- [process_runner.py](/C:/Users/nyml/code/work-context/src/workbench/infrastructure/process_runner.py)

### Context 链路

[context_service.py](/C:/Users/nyml/code/work-context/src/workbench/application/context_service.py) 会编排：

- `SkillService.find_skill`
- `SkillService.render_bundle`
- 可选的 `WorkspaceService.get_workspace`

它既能返回 payload，也能直接写出 `.json` / `.md` 文件。

### Local 链路

`local` 这条链当前是：

- [local_command.py](/C:/Users/nyml/code/work-context/src/workbench/commands/local_command.py)
- [local_service.py](/C:/Users/nyml/code/work-context/src/workbench/application/local_service.py)
- [local_files.py](/C:/Users/nyml/code/work-context/src/workbench/infrastructure/local_files.py)

`LocalService` 很薄，主要作用是把命令层调用转成稳定应用接口。

`local_files.py` 当前承担：

- boundary 检查
- 文件读写
- grep
- list
- mkdir
- stat

### Report 链路

[report_service.py](/C:/Users/nyml/code/work-context/src/workbench/application/report_service.py) 当前是轻量编排器：

- 先跑 skill lint
- 再读 workspace 列表
- 最后调用 [report_output.py](/C:/Users/nyml/code/work-context/src/workbench/infrastructure/report_output.py) 写 Markdown report

## 7. 根级模块的现状

当前根目录只保留真正的包入口：

- [__init__.py](/C:/Users/nyml/code/work-context/src/workbench/__init__.py)
- [__main__.py](/C:/Users/nyml/code/work-context/src/workbench/__main__.py)
- [cli.py](/C:/Users/nyml/code/work-context/src/workbench/cli.py)

过去的兼容 façade 和根级基础模块都已经删除。

这意味着现在如果要引用实现，应直接从分层目录进入：

- 配置模型走 `domain/config.py`
- 配置存储走 `infrastructure/config_store.py`
- 仓库初始化走 `application/bootstrap_service.py`
- 文件系统辅助走 `infrastructure/filesystem.py`
- 格式协议走 `core/toml.py` / `core/yaml.py`

## 8. 统一返回协议

项目公开边界统一走 `Result` / `Option`：

- 成功：`Result.ok(value)`
- 失败：`Result.err(AppError(...))`
- 缺失但不是错误：`Option.none()`

CLI 输出协议固定为：

```json
{"ok": true, "value": {...}}
```

```json
{"ok": false, "err": {"code": "...", "message": "...", "context": {...}}}
```

这样命令层、业务流程和基础设施失败都能用同一套结构回传。

## 9. 当前技术债

下面这些是现在仍然真实存在的技术债。

### `local_files.py` 仍然偏大

虽然已经迁到 infrastructure，但 boundary 校验、读写、grep、list、stat 仍集中在一个模块里。

### `skill_validation.py` 现在承担的职责偏多

为了把 lint 规则从 domain 清出去，`skill_validation.py` 目前同时承担：

- lint 编排
- issue 规则收集
- skill 结果投影

这比原来的层次更正确，但后续仍值得继续拆成更清晰的纯函数模块。

### 某些 service 仍偏 façade

以 `SkillService`、`LocalService` 为例，它们现在承担的是稳定应用边界，但内部仍有不少直接转调。

这不是错误，但后续仍要持续判断：

- 哪些 façade 值得保留
- 哪些能力应该继续细化成显式 use case 函数

## 10. 建议下一步

按当前结构，下一阶段最合理的顺序是：

1. 继续拆 `local_files.py`
2. 把 `skill_validation.py` 的规则收集与结果投影拆成更清晰的纯函数模块
3. 视收益再决定是否进一步细分 façade service 与 use case 函数边界

当前不建议做的事：

- 再把命令注册逻辑塞回 `cli.py`
- 为了“纯函数化”而引入过度抽象
- 在没有明确收益时把模块拆得过碎

## 11. 阅读顺序

第一次接手这个仓库，建议这样看：

1. [cli.py](/C:/Users/nyml/code/work-context/src/workbench/cli.py)
2. [runtime.py](/C:/Users/nyml/code/work-context/src/workbench/composition/runtime.py)
3. [base.py](/C:/Users/nyml/code/work-context/src/workbench/commands/base.py)
4. [config_store.py](/C:/Users/nyml/code/work-context/src/workbench/infrastructure/config_store.py)
5. [bootstrap_service.py](/C:/Users/nyml/code/work-context/src/workbench/application/bootstrap_service.py)
6. [workspace_service.py](/C:/Users/nyml/code/work-context/src/workbench/application/workspace_service.py)
7. [skill_service.py](/C:/Users/nyml/code/work-context/src/workbench/application/skill_service.py)
8. [workspace.py](/C:/Users/nyml/code/work-context/src/workbench/domain/workspace.py)
9. [skill.py](/C:/Users/nyml/code/work-context/src/workbench/domain/skill.py)
10. [result.py](/C:/Users/nyml/code/work-context/src/workbench/core/result.py)
