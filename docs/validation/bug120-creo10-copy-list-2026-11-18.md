# 拷到 Creo 10 机器：一步一步来（小白版）

目标机器只需要三样东西：**代码**、**Python**、**编译器**。Creo 10 的 SDK 不用拷，它本来就在
Creo 安装目录里。

---

## 第 0 步：先搞清目标机器的三个路径

在那台机器上打开 **PowerShell**（开始菜单搜 PowerShell），逐条粘贴：

```powershell
# 1) Creo 10 装在哪
Get-ChildItem "C:\Program Files\PTC" -Directory
```

看到类似 `Creo 10.0.0.0` 就记下来，例如 `C:\Program Files\PTC\Creo 10.0.0.0`。

```powershell
# 2) 有没有 Visual Studio 的编译器（cl.exe 的启动脚本）
Get-ChildItem "C:\Program Files (x86)\Microsoft Visual Studio","C:\Program Files\Microsoft Visual Studio" `
  -Recurse -Filter vcvars64.bat -ErrorAction SilentlyContinue |
  Select-Object -First 3 -ExpandProperty FullName
```

- 有输出：记下其中一条完整路径（后面要用）。
- 没有输出：说明这台机器没装 C++ 编译器，需要装 **Visual Studio Build Tools**，安装时勾选
  "使用 C++ 的桌面开发"。装完再跑这条命令。

```powershell
# 3) 有没有 Python
py -0p
```

- 有 `3.12`（64 位）：记下路径，例如 `C:\Users\你\AppData\Local\Programs\Python\Python312\python.exe`。
- 没有：去 python.org 下 3.12 的 **Windows installer (64-bit)**，安装时勾选 **Add python.exe to PATH**。

---

## 第 1 步：把代码拷过去（二选一）

### 方式 A：那台机器能上内网/外网 git（最省事）

```powershell
cd D:\                       # 换成你想放的位置
git clone <仓库地址> MCP_CREO_MechDog
cd MCP_CREO_MechDog
git checkout codex/bug120-plan-0270
```

### 方式 B：不能联网，用 U 盘/共享目录

在**现在这台机器**上打包。注意：**绝不能把 `.venv`、`build`、`config.json`、
`panel_session_guard.json` 带过去**（前两个是这台机器的环境/产物，后两个会让目标机
路径错乱、甚至被旧的面板保护锁住）。

在现在这台机器上粘贴这一段（只改第一行的路径）：

```powershell
$src = "E:\Projects\MCP_CREO_MechDog"
$tmp = "E:\temp\mechdog-target"
$dst = "$tmp\MCP_CREO_MechDog"

Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $tmp -Force | Out-Null

robocopy $src $dst /E /NFL /NDL /NJH /NJS /XD .venv build jobs models .git .pytest_cache __pycache__ .trae

# 这几个单独删掉：必须由目标机器自己生成
Remove-Item "$dst\config.json","$dst\panel_session_guard.json","$dst\panel_session_guard.tmp","$dst\native\constants.inc" -Force -ErrorAction SilentlyContinue

Compress-Archive -Path $dst -DestinationPath "E:\temp\mechdog-target.zip" -Force
"打包完成: E:\temp\mechdog-target.zip"
```

把 `E:\temp\mechdog-target.zip` 拷到目标机，解压到例如 `D:\MCP_CREO_MechDog`。

> 拷过去的体积参考：代码 + 文档约几十 MB（不含 `.venv` 与 `build`）。如果你看到压缩包几百 MB，
> 说明 `.venv` 或 `build` 被带进去了，删掉重打。

---

## 第 2 步：在目标机器上建 Python 环境

在解压后的仓库目录里打开 PowerShell（地址栏输入 `powershell` 回车即可）：

```powershell
cd D:\MCP_CREO_MechDog

# 建虚拟环境（用第 0 步查到的 Python；若 py -3.12 可用就照下面这样）
py -3.12 -m venv .venv

# 装依赖
.\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

装完自检：

```powershell
.\.venv\Scripts\python.exe -c "import mcp, httpx2; print('deps ok')"
```

---

## 第 3 步：写 config.json（关键，路径必须改成目标机的）

在仓库根目录新建文件 `config.json`，内容照下面改（注意反斜杠要写两个）：

```json
{
    "creo_root":  "D:\\Program Files\\PTC\\Creo 10.0.0.0",
    "vcvars64":  "C:\\Program Files (x86)\\Microsoft Visual Studio\\2022\\BuildTools\\VC\\Auxiliary\\Build\\vcvars64.bat",
    "native_timeout_seconds":  180,
    "generic_timeout_seconds":  600,
    "creo_session_id":  "",
    "auto_start_creo":  false
}
```

> 这台 Creo 10 机器已确认装在 **D 盘**：`D:\Program Files\PTC\Creo 10.0.0.0`，
> SDK 头文件在 `D:\Program Files\PTC\Creo 10.0.0.0\Common Files\protoolkit\includes`。
> `vcvars64` 仍按第 0 步实际查到的路径填（那多半在 C 盘）。

- `creo_root`：第 0 步查到的 **Creo 10** 目录
- `vcvars64`：第 0 步查到的 `vcvars64.bat` 完整路径

写错会怎样？`preflight` 会直接告诉你哪一项不对，不会静默继续。

---

## 第 4 步：自检（还没到编代码）

```powershell
.\.venv\Scripts\python.exe tools\panel_target_check.py preflight
```

逐项看输出：

| 字段 | 正常应该是什么 |
|---|---|
| `config_present` | `true` |
| `creo_root` | 你写的 Creo 10 路径 |
| `sdk_present` | `true` |
| `sdk_headers` | 400 出头（Creo 10 是 415；若显示 430 说明路径指到了 12.4） |
| `vcvars_present` | `true` |
| `artifacts.*` | 现在都是 `false`（还没编译，正常） |
| `panel_profiles` | `[]`（当前版本 profile 库是空的，正常） |

---

## 第 5 步：编译（A 段核心）

```powershell
.\.venv\Scripts\python.exe tools\check_creo10_compile.py --sdk "C:\Program Files\PTC\Creo 10.0.0.0" --full
```

看最后几行：每个 `translation_unit` 的 `"exit_code": 0` 就是过。

然后完整构建 + 收集证据：

```powershell
.\.venv\Scripts\python.exe tools\panel_target_check.py all
```

它会在 `build\panel_target_evidence\<时间戳>\` 生成证据包。

---

## 第 6 步：把证据包拷回来

把 `build\panel_target_evidence\` 下**最新的那个时间戳文件夹**整个拷回来（U 盘/共享都行）。
里面有 `manifest.json` 和 sha256，我据此判断"这份证据没被改过"。

---

## 常见问题

**Q：需要把 Creo 10 的 `protoolkit\includes` 也拷过去吗？**
不需要。那是给"现在这台机器"做编译对照用的临时副本；Creo 10 机器上 SDK 就在
`<Creo 安装目录>\Common Files\protoolkit` 里，脚本自己会找。

**Q：需要在那台机器上装 Creo 之外的许可证工具吗？**
不需要。A 段只编译、不连 Creo、不加载 DLL，也不用 License。

**Q：`build-info` 运行报错怎么办？**
那是正常的：`creo_worker.exe` 直接双击会因为缺 Toolkit DLL 而失败，它的用途是被 Creo 加载。
所以别双击它，按上面的命令走。

**Q：`panel_session_guard.json` 是什么，为什么不能拷？**
它是"上一次面板可能还开着、暂时不许再进原生作业"的本地保护记录，绑这台机器的作业和
model。拷到别的机器会让新机器一上来就被锁，且没有对应作业可解。真被锁了用
`creo_reconcile_model(action="confirm_panel_closed")` 解除，不要手动删。

**Q：`native\constants.inc` 为什么要重新生成？**
它是按本机 SDK 枚举生成的常量表。跨机器必须重编，否则枚举值和 SDK 对不上——
之前的 "Creo10 编译阻断" 就是这个原因。
