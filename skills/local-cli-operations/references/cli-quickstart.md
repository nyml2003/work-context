# local CLI 快速参考

当你需要跨平台地做基础本地文件操作时，优先使用下面这些命令。

## 读取文件

```powershell
python scripts/workbench.py local read <path>
python scripts/workbench.py local read <path> --start-line 10 --end-line 40
```

## 列目录

```powershell
python scripts/workbench.py local list <path>
python scripts/workbench.py local list <path> --recursive --kind file --pattern "*.py"
```

## 搜文本

```powershell
python scripts/workbench.py local grep <path> --pattern "TODO"
python scripts/workbench.py local grep <path> --pattern "build_context" --glob "*.py" --ignore-case
```

## 写入和追加

```powershell
python scripts/workbench.py local write <path> --content "hello"
python scripts/workbench.py local write <path> --content "replace" --overwrite
python scripts/workbench.py local append <path> --content "`nworld"
```

## 建目录和查看状态

```powershell
python scripts/workbench.py local mkdir <path> --parents
python scripts/workbench.py local stat <path>
```
