# BUG-120 目标机（Creo 10）执行手册

目标：把"面板路线在 Creo 10 上到底成不成"从推断变成证据。分三段，每段都有明确产出；
**做完 A 段就能回传**，不必等到 C 段。

在三台机器/角色之间的分工：

- 本机（现在这台）：写代码、审证据
- 目标机（Creo 10）：执行本手册、产出证据包
- 你（WorkBuddy）：在目标机上照抄命令，把 `build/panel_target_evidence/<时间戳>/` 拷回

---

## 准备（两台机器都需要的两项）

1. 把仓库整份拷到目标机（`git clone` 或直接复制该分支 `codex/bug120-plan-0270`）。
2. 按目标机的实际路径改 `config.json`：

```json
{
  "creo_root": "C:\\Program Files\\PTC\\Creo 10.0.0.0",
  "vcvars64": "C:\\MCP_CREO_MechDog\\vcvars64_local.cmd"
}
```

`vcvars64` 指向本机 VS 的 `vcvars64.bat`（或你已有的包装脚本）。改完先跑：

```powershell
.\.venv\Scripts\python.exe tools\panel_target_check.py preflight
```

它会打印 `sdk_headers`（应为 415 左右）、`vcvars_present`、`panel_profiles`（预期为空）。

---

## A 段：编译对照（不需要 Creo、不需要 profile）

```powershell
.\.venv\Scripts\python.exe tools\check_creo10_compile.py --sdk "C:\Program Files\PTC\Creo 10.0.0.0" --full
.\.venv\Scripts\python.exe tools\panel_target_check.py all
```

产出：`build/creo10_check/report.json` + `build/panel_target_check` 会生成
`build/panel_target_evidence/<时间戳>/`（含 `manifest.json` 与 sha256）。

**这一段回答**：Creo 10 SDK 是否以相同签名声明了全部 API、worker/payload 能否在该 SDK 下编译。
**它不回答**：对话框能否打开。

---

## B 段：装面板部署（需要 Creo 10 已安装、需要你在 Creo 里点一次）

```powershell
.\.venv\Scripts\python.exe tools\panel_target_check.py deploy
```

它写出协议 4 / loader ABI 2 的部署（`deployment.json`、`callback_bootstrap.json`、
`protk.dat`），并打印 `registration` 路径。然后**由你**在 Creo 里做一次性注册：

1. Creo → 辅助应用程序（Auxiliary Applications）→ 注册上面打印的 `registry_file`
2. Start 一次，**自己看一眼 DLL 安全提示**
3. 重启 Creo（让面板代际生效）

注意：这一步会把该 loader 目录的部署从 Blend 代际切到面板代际。切换是显式参数
（`allow_generation_switch=True`），且旧的载荷副本仍保留以便回滚。MCP 不改任何安全设置。

---

## C 段：跑一次面板作业（需要有认证 profile）

面板路线的准入要求一份 profile，里面包含**录制好的对话框宏**（`open_macro`）和受限 Done
（`done_macro` / `done_command`）。本版本仓库里 profile 库是空的，因此：

- 如果直接提交，会在**作业创建之前**被拒绝（`creation_route='resident_panel' is not available ... no certified UI profile`）；
  这是正确行为，不是 bug。
- 要做 C 段，需要先有一份 candidate profile（含宏），由我用 `panel_profiles` 生成并与
  candidate ticket 一起交给你。**宏必须来自真实操作记录**：在 Creo 里手工完成一次球鼻艏，
  把界面上的命令序列记下来（或用 Creo 的 trace/macro 录制），交给 profile 认证——我不会
  凭猜写命令名。

拿到 profile + ticket 后，通过 WorkBuddy 调 `creo_surface_loft`：

```json
{
  "model_id": "<当前零件的 model_id>",
  "creation_route": "resident_panel",
  "label": "panel_probe_1",
  "sections": [
    {"label": "<曲线1的标签>", "open_confirmed": true},
    {"label": "<曲线2的标签>", "open_confirmed": true}
  ]
}
```

然后 `creo_get_job` 轮询，并把作业目录回传。

### 结果怎么读（这张表是这次验证的核心）

| 返回 | 含义 | 下一步 |
|---|---|---|
| `PANEL_OPEN_MACRO_MISSING` | 部署/准入过了，但没有认证 profile 的宏 | 正常，等 profile |
| `PANEL_DEPLOYMENT_REQUIRED` | 注册的还是 Blend 代际（协议 3/ABI 1） | 重做 B 段并重启 Creo |
| `PANEL_CURVE_NONE_IN_FEATURE` / `PANEL_CURVE_ID_NOT_IN_FEATURE` | D2 在真机上枚举结果与请求不符 | 回传 `result.json`，我改解析 |
| `PANEL_CURVE_OPENNESS_UNVERIFIED` | 请求没声明 `open_confirmed` | 补字段 |
| `PANEL_SELECTION_INCOMPLETE` | 对话框只消费了部分位置 | 回传 `callback_result.json` + `panel_wait.json` |
| `success=true` 且 `panel_receipt.exit_observation.closed=true` | 全序完成（Done→AfterTerminal→OuterDrain 都被观测到） | 这才是真正的通过 |
| `success=false` + `panel_execution_unconfirmed=true` | Done 排了但没有人观测到关闭 | **预期中的中间态**，不是失败结论 |

---

## 回传什么

```powershell
.\.venv\Scripts\python.exe tools\panel_target_check.py collect
```

把打印出来的 `build/panel_target_evidence/<时间戳>/` 整个目录拷回（里面有 `manifest.json`、
`build.log`、`creo10_check/report.json`、最近若干 `build/jobs/**/{request,result,worker.log,panel_wait.json}`）。
我这边会先校验 manifest 的 sha256，再判断结论。

## 三条纪律（请勿省略）

1. 不要手改 `result.json`、`callback_result.json`、`panel_wait.json` 或 `manifest.json`；
   我会校验摘要，改过就作废。
2. 不要为了让流程继续而删除 `build/panel_session_guard.json`：那是"面板可能还开着"的保护，
   删了等于把未知当已知。要解除请用 `creo_reconcile_model(action="confirm_panel_closed")`。
3. 失败也是证据：把失败时的作业目录原样回传，比"看起来通过了"有用得多。
