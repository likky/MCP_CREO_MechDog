# 2026-11-23_CREO_0.36.0_核心问题：升级重启后旧Creo会话无法接管且unknown_outcome恢复在会话变更后被永久拒绝

> 反馈对象：MCP_CREO_MechDog **0.36.0**
> 环境：Windows 10 x64 19045 / Creo Parametric **9.0.0.0**（`D:\CREO\Creo 9.0.0.0`，`release_numeric=41`）
> 现场：M113 履带轮 P05（1163 面 / **6428 边**，rev 12，文件 `p05_v360.prt.13` sha256 `3fbeebd6…`）
> 会话：旧 `5148678456263465631`（11-22 14:39 记录）→ 新 `4124381274872279242`（11-23 14:07）
> 性质：**这是 0.35.5 问题 N（只读挂起锁死 + 恢复预算）在 0.36.0 的复核**。只读挂起这一半已修好，写作业的 `unknown_outcome` 这一半**仍然没有出口**，并且在"升级 → 重启 Creo"这个必经场景下变成永久锁死。
> 附带：圆角无按锚点选边能力、边表分页成本、零件预览不隐藏基准面、更新检查网络预算。

---

## 一、结论先行

| 项 | 结果 | 证据 |
| --- | --- | --- |
| 版本与工具表 | ✅ 0.36.0 / 111 工具 / worker 身份 `0f0980a2…` 校验通过 | `creo_capabilities`、`creo_session_status` |
| 只读挂起可释放 | ✅ 0.36.0 新增路径有效 | 作业 `8e7d87dd…` 一次 `creo_cancel_job` → `readonly_release.released=true`，revision 不变 |
| 连续多次保存（BUG-152） | ✅ 连存 3 次全过 | rev 2→3→4→5，`.prt.4/.5/.6` 三个新版本，均 `saved_file_reloaded_and_verified=true` |
| 大模型 JPEG 导出（WinError 1450） | ✅ 未再现 | 745 面/3920 边，1200×1200，97 s，`effect_status=no_effect` |
| **升级后旧会话接管** | ❌ **无出口**（问题 A） | `-4` → `probe_timeout`，`PRO_TK_BAD_CONTEXT`，两次重试均 `startup_timeout`，只能人工关 Creo |
| **unknown_outcome 写作业恢复** | ❌ **永久锁死**（问题 B） | `restore_baseline` 两次在 96 s 处 `recovery_phase_timeout`；`abandon_new` 被"会话已变"拒绝 |
| reconcile 参数语义 | ⚠ 不一致（问题 C） | `pending_job=null` 但准入报 `blocking_operation="pending_job"`；apply 传该 id 反而 `Stale` |
| 圆角按锚点选边 | ❌ 能力缺口（问题 D） | 只收 edge id / face pair；边表 84 条/页，6428 边 = 77 页 |
| 零件 JPEG 预览 | ⚠ 画面被基准面遮挡（问题 E） | `datum_display.applicable=false` |
| 更新检查 | ⚠ 5 s 网络预算必失败（问题 F） | `status=failed`，`GitHub 更新检查超过 5 秒网络预算` |

一句话：**0.36.0 把"只读作业可以退"补上了，但"写作业失败后怎么退"没有补；而这个缺口恰好被"升级后必须重启 Creo"触发，一旦触发就是模型记录级的永久不可用（保存、导出、装配全被拒）。**

---

## 二、问题 A（P0）：升级/重启后，旧 Creo 会话无法被新 worker 接管，且没有工具侧出口

### 2.1 事实链（时间均为 2026-11-23，UTC+8）

| 时刻 | 事件 | 证据 |
| --- | --- | --- |
| 12:34:03 | 旧 worker 启动 Creo（`parametric.exe` pid 2328 + `xtop.exe` pid 17228） | `creo_process_snapshot` |
| 12:34:16 | 旧 worker 连上并读到 `release_numeric=41` | `toolkit_health.json.host_release`，`worker_sha256=2b93d7b5…` |
| 12:53–12:55 | MCP 升级到 0.36.0，`build/creo_worker.exe` 重建为 `0f0980a2…` | 文件时间、`worker_build_identity` |
| 13:44:05 | 新 worker 探测：`toolkit_code=-4`，`connection_state=not_found_or_unreadable`，`worker_exit_code=20` | `creo_session_status` |
| 13:45:25 | 再探测：仍 `-4`，附带 `toolkit_hint="PRO_TK_BAD_CONTEXT: this worker process has no Toolkit context"` | 同上 |
| 13:45:52 | `creo_startup_status(retry=true)` 重试第 1 次 | `retry_id=08a19be15ef3` |
| 13:48:16 | 重试终态 `startup_timeout`；`message="…Existing Creo processes were preserved"`；`launch_attempt` 仍为 43 | `creo_startup_status` |
| 14:07:18 | 旧进程退出后，服务拉起新 Creo（pid 9296/2160，伴生 `pro_comm_msg` pid 14692） | `creo_process_snapshot` |
| 14:07:47 | 新会话连接成功：`toolkit_code=0`，`session_fingerprint=4124381274872279242` | `creo_session_status` |

### 2.2 为什么这是死循环

1. Creo 的 Toolkit 上下文由**拉起它的进程**建立。MCP 服务进程被替换（升级/重启连接器）后，新 worker 对旧 Creo 只剩 `PRO_TK_BAD_CONTEXT`。
2. 此时服务判定"已有 Creo 进程存在"，**不新建会话**（`launch_attempt` 不增加，终态 `Existing Creo processes were preserved`）。
3. 工具侧只有 `creo_startup_status(retry=true)` 一个动作；它重试两次都是 `startup_timeout`。**没有任何"关闭会话 / 强制新会话 / 选择进程"的能力**（`creo_session_status` 的 `session_candidates` 只读，`session_id` 永远是 `null`）。
4. 唯一出路是人工关闭 Creo。实测关闭后 10 s 内服务自动拉起并连接成功。

### 2.3 影响

"升级完就验收"这个动作本身会先失败一次，且失败信息指向 `PRO_TK_BAD_CONTEXT`（进程上下文），使用者会去查许可证/Creo 安装，而真正要做的是**关掉 Creo**。

### 2.4 建议

1. 增加显式能力：`creo_session_relaunch`（或 `creo_startup_status(force_new_session=true)`），在检测到"进程在但 Toolkit 不可达"时允许新建会话；对旧进程只做提示，不自动杀。
2. 把"进程在 + 连接 `-4/PRO_TK_BAD_CONTEXT`"识别成独立状态（如 `stale_session_needs_restart`），并在 `next_steps` 第一条直接写"关闭 Creo 后重试"，而不是现在排在第 6 条的 `operator`。
3. `session_candidates` 已经能列出 pid，却没有可用的 `session_id`；既然无法把 pid 映射成 session id，就把它标成"仅诊断"，避免使用者以为可以选。

---

## 三、问题 B（P0）：`unknown_outcome` 写作业在会话变更后再也无法恢复（模型记录级永久锁死）

### 3.1 现场起点

`p05_v360`（`9ea0fdd97c234775b2c6682877090fd4`）在 11-22 因只读导出 `WinError 1450` 留下：
`status=ready`、`pending_job=null`、`recovery_pending=a9ab8b7dbc…`（`unknown_outcome`，`failure_phase=native_worker_started`，`completion_stage=recovery_phase_timeout`）。

**0.36.0 修好的那一半**（值得肯定）：

```
creo_cancel_job("8e7d87dda7914db68e14a89eb53e511d")
→ status=cancelled, readonly=true, geometry_may_have_changed=false
→ readonly_release.released=true, revision=12
```

只读挂起当场清掉，`pending_job` 变 `null`。**但 `recovery_pending` 仍是 `a9ab8b7d…`。**

### 3.2 第一次尝试：`restore_baseline`（实测 96 s 被切）

```
creo_reconcile_model(mode=apply, action=restore_baseline, expected_pending_job_id=null,
                     evidence_token=b383a5ae…, idempotency_key=p05v360-restore-baseline-20261123b)
→ job 4e8fae56891a43c9982cf6e6b86b1dad
```

- 06:10:36 开始，06:12:12 结束，**96 s**；
- `status=unknown_outcome`，`recovery.native_checkpoint.completion_stage="recovery_phase_timeout"`；
- `native_progress.stage="recovery_verify_source"`，`log_bytes=597 492`；
- 日志统计：`ProEdgeIdGet` **15 131 次**、`ProSurfaceContourVisit` **1 207 次**（模型 1163 面 / 6428 边）。

对照 11-22 的同一动作（作业 `a9ab8b7d…`）：`completion_stage` 完全相同，`log_bytes=525 880`。**两次都是同一个死法。**

### 3.3 为什么必然超时（可算）

`restore_baseline` 在原生侧是：`ProSolidRegenerate` → `inspection()`（before）→ `verify_recovery` →（restore 时读回基线）→ `inspection()`（after）→ `verify_recovery`，即**至少 2 次全量 inspection**。

单次 inspection 的成本可以拿同一台机器上的成功作业标定：

| 证据 | 数值 |
| --- | --- |
| 作业 `f44c3eee…`（v359，745 面/**3920 边**，只读导出）`verify_start` 阶段 | **52 352 ms**（含加载 + inspection） |
| 按边数线性外推到 6428 边 | 52.4 × 6428/3920 ≈ **86 s**（单次） |
| `restore_baseline` 至少 2 次 | **≥ 172 s** |
| `creo_reconcile_model` 的 `budgets.native_phase_seconds` | **90 s**（硬编码） |

结论：**任何一次 inspection 已经接近 90 s 的模型，其 `restore_baseline` 在数学上不可能成功。** 这不是"偶发超时"，是预算与工作量的量级不匹配。

代码位置（供作者定位）：
- 预算：`src/creo_mechdog/reconciliation.py:1207` → `"native_phase_seconds": 90`（常量，无配置项）
- 恢复原生段：`native/generic.cpp:7105` `generic_stage("recovery_verify_source")` → `inspection()`；`inspection()` 逐面 `ProSurfaceContourVisit` + 逐边 `ProEdgeIdGet`
- 外层：`outer_seconds=115`

### 3.4 第二次尝试：`abandon_new`（被"会话已变"拒绝）

对另一条 `adopt_pending` 记录（`p05_wheel_final`，`7f481d3e…`）预检时 `abandon_new` 是**可用**的，提交后：

```
job 2353a6249dc84201821fb13e0f4e82a3
→ status=unknown_outcome, toolkit_code=-1
→ message="Recovery refused: Creo session changed since recorded evidence"
→ failed_stage="recovery_abandon_new", model_unchanged=true
```

原因：该作业的证据绑定旧会话指纹 `5148678456263465631`，当前是 `4124381274872279242`。而"重启 Creo"正是问题 A 的唯一出路 —— **解决 A 的动作，恰好让 B 的所有恢复动作失效。**

`docs/MODEL_RECOVERY.md:92` 明确写着这类拒绝"保守保留 unknown 与保护，不得清保护"。于是：

### 3.5 终局：所有入口都被堵死，且没有出口

| 动作 | 结果 |
| --- | --- |
| `creo_save_model(rev 12)` | `{"status":"busy","blocking_job_id":"4e8fae…","blocking_operation":"pending_job"}` |
| `creo_export_model(jpeg)`（**只读**） | 同样 `busy`，同一 `blocking_job_id` |
| `creo_cancel_job` | 只对 `readonly=true` 的作业有效，对 recovery 作业无效 |
| `ack_no_mutation` | 不可用：`Only a failed model can acknowledge zero mutation` |
| `ack_failure` | 不可用：`Only a model whose last job ended in failure`（本模型 `last_job` 是成功的 `ead9fd19…`） |
| `abandon_stalled_recovery` | 不可用：`stage_advanced`（worker 已启动） |
| `abandon_new` | 可用但被"会话已变"拒绝（见 3.4） |
| `restore_baseline` | 唯一能提交的动作，必然 90 s 超时（见 3.3） |

**实测后果**：`p05_v360` 的 4.2 MB 文件完好（sha256 `3fbeebd6…`），但记录不可用 —— 不能保存、不能导出预览、不能作为装配组件。这是"文件没坏、模型废了"。

### 3.6 建议（按优先级）

1. **让恢复校验不再依赖全量枚举**：`restore_baseline` 的 before/after 只需要体积、质心、面数/边数、特征数、单位与基线文件摘要；边级 id 表只在选择器需要时才枚举。现在为了"验证"把 6428 条边扫两遍，成本比目标本身高两个数量级。
2. **预算按模型规模放开或可配**：把 `native_phase_seconds` 提到与作业 `timeout_seconds`（600 s）同量级，或提供 `budget_seconds` 入参；至少不要让它小于"一次 inspection"的实测成本。
3. **补一个面向运维的终态出口**：`abandon_unknown_recovery(confirm=true)` —— 语义为"承认本次原生结果不可知，保留文件与审计，把记录放回 ready 但**不**推进 revision、**不**改基线"，并在回执里写明 `disk_state_verified=false`。现在 `ack_failure` 的判据是 `last_job` 失败，而"恢复作业自己失败"并不改变 `last_job`，所以永远进不去。
4. **恢复证据对会话变更分级**：`abandon_new`（不写几何、只擦命名对象）应允许在新会话里重新取证（当前 `native_result_present=true, model_unchanged=true` 已证明没动模型），而不是一律按 `session_changed` 拒绝。至少把 `model_unchanged=true` 作为可继续的条件。
5. **`recovery_pending` 与 `pending_job` 在准入里用同一个字段名**：见问题 C。

---

## 四、问题 C（P1）：`creo_reconcile_model` 的 `expected_pending_job_id` 与准入的 blocking job 不同源

实测同一时刻：

- `inspect` 返回 `"pending_job": null`；
- `apply` 传 `expected_pending_job_id="a9ab8b7dbc…"` → `Stale expected_pending_job_id: model pending_job is None`；
- 但 `creo_save_model` / `creo_export_model` 被拒时返回 `"blocking_operation": "pending_job"`，`blocking_job_id="a9ab8b7d…"`（其实是 `recovery_pending`）。

即：**准入把 `recovery_pending` 当 `pending_job` 用，而 apply 的校验只看真正的 `pending_job`。** 使用者按文档"预检返回 null 就传 null"才能提交（这一点文档写对了），但错误信息会把人引向"pending 不匹配"的死胡同。

建议：准入的 `blocking_operation` 改报真实字段名（`recovery_pending`），或在 reject 里同时列出 `pending_job` 与 `recovery_pending` 两个值。

---

## 五、问题 D（P1）：圆角没有"按锚点/按点选边"的能力，边表分页成本使锚点法不可用

TXT 给圆角的方式是**锚点坐标**（`F03 P05 R20`：`(92.075,-123.98,76.332)`、`(92.075,-123.98,-76.332)`、`(22.075,-123.98,88.666)`、`(162.075,-123.98,88.666)`），这与"源模型重建后 id 会变"的现实一致。

但 `creo_round.references` 只接受：

- `{"edge":{"kind":"edge","id":N}}`（显式 id）；
- `{"surfaces":[A,B]}`（共边面配对）。

没有 `{kind:"geometry_selector", target:"edge", points_mm:[...]}`，也没有 `edge_geometry` 端点配对（后者只有 `creo_sheetmetal_flange` 支持）。0.35.5 已报过"selector 匹配到了但 `ProModelitemInit=-23`"，0.36.0 的 FEAT-074 只给**面**加了 `feature` 标签，**边这条路径没变**。

要退回显式 id，唯一手段是 `creo_inspect_model(detail="full", section="edges")`，实测：

- 每页 **84 条**（32 KiB 上限），6428 边 = **77 次调用**；
- 返回里没有按坐标/长度/所属特征过滤的参数，只能整表翻。

**影响**：凡"按锚点圆角"的零件（本项目 4 处圆角全部如此），在千边级模型上实际不可执行。本次 F03 因此未完成。

建议：
1. 边也支持 `geometry_selector`（points_mm + tolerance + 所属 `feature`），并像面一样在 native 侧落到 `ProEdgeInit`；
2. `creo_inspect_model(section="edges")` 增加 `near=[x,y,z]` + `k` 过滤（SolidWorks 侧的 `analyze_model(analysis_type="edges", near=…)` 已有此形态，见同仓另一个 MCP）。

---

## 六、问题 E（P2）：零件 JPEG 预览不隐藏基准面

`creo_export_model(format="jpeg")` 在 v359 上成功，但渲染图里 6 张基准面与 `PRT_CSYS_DEF` 文字直接压在模型上：

```
preview.datum_display = {"model_type":"part","applicable":false,"attempted":false,"hide_status":"not_applicable"}
```

同一个 `preview` 块的 12 个 code 全 0，`file_verified=true` —— 只是**没有做**隐藏，不是失败。对"验收截图"用途来说画面不可用。

建议：零件也走一次"隐藏基准要素 → 渲染 → 恢复显示"，或在渲染前用 `ProDisp` 层设置而不落 config.pro。

---

## 七、问题 F（P2）：更新检查的 5 s 预算在本机必失败

```
update.status="failed"
error="GitHub 更新检查超过 5 秒网络预算；可设置 MECHDOG_UPDATE_TIMEOUT_SECONDS（1—30 秒）后重试。"
network_timeout_seconds=5.0
```

`status=failed` 与"已是最新"在调用方很容易混（文案已说明，但字段本身无区分度）。建议默认 15 s，或在 `creo_capabilities` 里把 `update` 块降级为 `advisory` 并明确"不参与版本判定"。

---

## 八、本轮通过项（0.36.0 确实修好的部分，供回归）

| 场景 | 输入 | 结果 |
| --- | --- | --- |
| 连续保存 ×3 | `p02_seat_v355` rev 2/3/4 | 3/3 成功：`.prt.4`（`81fa3690…`）、`.prt.5`（`f6f2b58a…`）、`.prt.6`（`fa320e23…`），每次 15–17 s，`saved_file_reloaded_and_verified=true`，`preview_status=written`（18 608 B） |
| 大模型只读导出 | `p05_roadwheel_v359`（745 面/3920 边）1200×1200 isometric | 97 s 成功，75 153 B，`revision` 不变，`effect_status=no_effect`，未再现 `WinError 1450` |
| 只读挂起释放 | `p05_v360` 的 `8e7d87dd…` | `readonly_release.released=true`，`geometry_may_have_changed=false` |
| 会话重建 | 关掉旧 Creo 后 | 10 s 内拉起并 `toolkit_code=0` |

---

## 九、最短复现路径

**问题 A（约 6 分钟）**
1. 用 0.36.0 启动 Creo 并确认 `connected=true`；
2. 记录 `creo_worker.exe` 的 sha256；
3. 重新构建/替换 worker（或重启 MCP 连接器）；
4. `creo_session_status` → 得到 `-4` / `PRO_TK_BAD_CONTEXT`；
5. `creo_startup_status(retry=true)` → `startup_timeout`，`launch_attempt` 不变；
6. 观察：不关 Creo 就永远连不上；关掉后自动恢复。

**问题 B（约 8 分钟，需一个 ≥5000 边的零件）**
1. 造一个 inspection 单次 > 60 s 的零件（本项目 6428 边即可）；
2. 让任意一个写作业以 `unknown_outcome` 结束（例如在恢复/保存中触发超时），或直接把一条记录置为 `recovery_pending`；
3. 重启 Creo（会话指纹变化）；
4. `creo_reconcile_model(apply, restore_baseline, expected_pending_job_id=null)` → 96 s 后 `recovery_phase_timeout`；
5. `creo_reconcile_model(apply, abandon_new)` → `Recovery refused: Creo session changed since recorded evidence`；
6. `creo_save_model` / `creo_export_model` → 永久 `busy`，`blocking_operation="pending_job"`。

---

## 十、影响与待办

- **P05（`9ea0fdd9…`）**：几何与文件完好（rev 12，7 374 502.8 mm³，`.prt.13` sha256 `3fbeebd6…`），但记录仍被 `recovery_pending` 锁住，`save` / `export` / 再编辑不可用。F03（窗角 4 边 R20）未做。**不采用任何"手工改 model.json / 删预留"的手段。**
  ⚠ **本节原判断已更正**：原先写的"`assemble_component` 需要'无 pending mutation'的组件源"不成立，记录被锁并不妨碍它作为装配取源——见第十一节。
- **装配**：`assem2_v355b`（`aabc94eb…`）已按第十一节的路径换入 v360，现 rev 16、269 组件、124 192 383.39 mm³。
- **建议的最小修复组合**：`native_phase_seconds` 从 90 s 提到与作业预算同量级（或可配）+ `restore_baseline` 不做全量边枚举 + 一个 `abandon_unknown_recovery` 运维出口。三者任二即可解除本现场。

---

## 十一、补充验证与一处更正（当日 18:15，装配 rev 16）

### 11.1 更正：`recovery_pending` 不阻挡装配取源

第十节原判断「`assemble_component` 需要无 pending mutation 的组件源」**不成立**。实测：

- `p05_v360` 的 `snapshot.mutation_pending` 仍为 `true`（`model_queries.py:159` 的定义是 `bool(pending_job or recovery_pending)`），其中 `pending_job=null`、`recovery_pending=89afd44f…`；
- 直接以该记录作 `source_model_id` 提交 `assemble_component`，**入口接受**并建出作业 `255e5771…`，没有任何准入门错误。

结论：装配取源的准入实际只检查 **`pending_job is None`**，`recovery_pending` 不在检查项内。所以「记录被锁」与「记录能否当装配源」是两件事——文档标题里「恢复被永久拒绝」仍然成立，但影响面应限定为**该模型自身的 save / export / 再次编辑**，不扩大到「不可被装配引用」。第十一节同时给出一条正面回归用例：

> 通用作业用 600 s 默认预算，在同一台机器、同一个 6428 边零件上完成了「加载 + 换件 + 保存 + 擦除 + 重载 + 比对」全流程，共 170 s；而 `reconciliation` 的 `native_phase_seconds=90` 连「加载 + 一次全量 inspection」都放不下（三次实测均在 95 s 被切）。**问题 B 的根因是预算口径不一致，不是模型跑不动。**

### 11.2 换件实测（可直接作回归用例）

作业 `255e5771c2db4b5cbdc6a547d4500699`，`timeout_seconds=1200`（job 级），总耗时 170 s：

| 项 | 结果 |
|---|---|
| 计划 | `remove_component(component=850)` + `assemble_component(label=part5_1_part5_2, source=9ea0fdd9…, placement=fixed)` |
| 净变更 | `component_changes.status=committed`：removed `part5_1_part5_1` / 850，added `part5_1_part5_2` / 853 |
| 位姿 | 读回 `transform` 与旧组件**逐位相同**（`transform_code=0`，row-vector，绕 Z 174.276°，translation `[64.679, -277.913, 0]`） |
| 体积 | 124 299 085.81 → 124 192 383.39，Δ=−106 702.42 = v360 7 374 502.80 − v359 7 481 205.22，分毫不差 |
| 组件数 | 269 → 269 |
| 保存 | `assem2_v355b.asm.17`，`saved_file_reloaded_and_verified=true`，sha256 `1dcd5ed5…` |

`verify_stages` 明细供作者参考预算分布：`verify_model_start` 111.1 s、`assertions` 15.2 s、`compare` 15.7 s、保存+擦除+重载 8.5 s，合计 170 s。

### 11.3 仍待作者处理

- **问题 A**（升级后旧会话接管不了）未变：0.36.0 仍无「关闭/强制新建会话」入口，只能人工关 Creo。
- **问题 B** 的修复建议不变，但优先级下调一档：它挡住的是「模型自己的写路径」，不再是「装配无法引用该模型」。
- **`remove_component` + 同 label `assemble_component` 在同一计划内仍被拒**（本文档 §11.2 用了新 label `part5_1_part5_2` 绕开）。文档 `docs/ASSEMBLY_REBUILD.md` 已写明这是设计行为，此处只记录一次实测符合文档，不算缺陷。
