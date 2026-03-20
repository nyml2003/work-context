---
name: "local-cli-operations"
description: "当需要在当前终端工作目录内执行基础本地文件与目录操作时使用，优先通过 workbench 的 local CLI 统一读写、搜索和查看路径信息。"
metadata:
  short-description: "用 local CLI 做本地文件操作"
---

# Local CLI 操作

## 概述

这个 skill 用来在当前终端工作目录内做基础本地文件操作。优先使用 workbench 的 `local` 子命令，不要直接依赖 `cat`、`type`、`ls`、`dir`、`grep`、`findstr` 这类系统相关命令。

## 使用边界

- 所有 local 命令的路径边界都由 CLI 在代码里限制到“调用命令时的当前工作目录”。
- 需要具体命令参数时，读取 `references/cli-quickstart.md`。
- 需要判断某个路径为什么能访问或为什么被拒绝时，读取 `references/path-boundary.md`。

## 工作流程

1. 先确认目标路径位于当前终端工作目录内。
2. 按任务选择最小的 `local` 子命令完成读取、列目录、搜索、写入、追加、建目录或查看状态。
3. 需要改写文件前，优先先用 `local stat` 或 `local list` 确认目标位置。
4. 如果遇到越界错误，不要绕过 CLI，先调整工作目录或把目标路径改成边界内路径。
