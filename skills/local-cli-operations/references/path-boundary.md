# 路径边界说明

`local` 命令不会把路径访问范围绑死在仓库根，而是绑在“调用命令时的当前工作目录”。

## 规则

- CLI 会先把输入路径解析成绝对路径。
- 解析后如果路径不在当前工作目录之内，命令会直接失败。
- 这个限制在代码里强制执行，不依赖 agent 是否自觉。
- 相对路径和绝对路径都会做同样的边界检查。

## 例子

如果当前终端工作目录是 `C:\repo\project`：

- `notes/todo.md` 可以访问
- `C:\repo\project\src\main.py` 可以访问
- `..\shared\data.txt` 会被拒绝
- `C:\repo\other\README.md` 会被拒绝
