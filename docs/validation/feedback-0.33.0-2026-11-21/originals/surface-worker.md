# 合并结果无法被 solidify 通过自身 label 引用，worker 在 disconnect 阶段崩溃把作业打成 unknown_outcome

- **日期**：2026-11-20
- **Creo**：Creo Parametric 10.0.0.0，`release_numeric = 42`
- **MCP**：`MCP_CREO_MechDog` **0.32.0**
- **worker**：`build/creo_worker.exe`，`worker_sha256 = 8a36c34dea30568bda27f9b738d5cc2253815f89aafe6168586eecd8260ba0d6`，`source_digest = a9da7033281e06785af24eb9eb80e2ed8265da1163ef126b7ba3a0d184b5d3c9`
- **会话**：`session_fingerprint = 14359338636323523713`，`sessions_observed = 3`
- **目标模型**：`bulb_v2`，`model_id = f6ac96487fb54ad2b0983955207db9b6`
- **任务**：按 `简易护卫舰_跨软件三维建模自然语言说明_v2.txt` 重建球鼻艏，要求走原生曲面能力、不接受近似方法

---

## 0. 一句话结论

0.32.0 上球鼻艏的**曲面链已经全部走通**（7 截面 + 尖点的原生多截面放样 → 镜像 → 合并 → 封盖 → 再合并），
**但把 `surface_fill → quilt_merge → solidify` 三步放进同一个原子计划必然失败**：

1. `solidify` 用 `{kind:"quilt_feature", label:"<merge label>"}` 引用合并结果，报 `ProError -4`，因为合并结果对自己的 feature label 不可见；
2. 该失败触发回滚，回滚**已经成功**之后，worker 在 `PHASE=disconnect` 处以 `3221226505`（`0xC0000409 STATUS_STACK_BUFFER_OVERRUN`）崩溃；
3. 崩溃使 `native_result.json` 未落盘 → 作业转 `unknown_outcome` → 模型被预留 → 必须走 `creo_reconcile_model` 恢复；
4. 恢复作业（`restore_baseline`）在 `waiting_for_channel` 阶段停留约 **8 分钟**，期间 `runner.log` 为 **0 字节**，两次长轮询（180 s、240 s）都等不到，事后才发现它其实已经成功。

把同样的三步**拆成三个独立作业**（每步各自 `save` + 重载校验）则全部一次通过，最终得到实体。

> ⚠️ 这只证明「拆步 + 用 quilt_id 引用」是一条可行的绕行路径，**不等于 MCP 的球鼻艏曲面→实体能力已经修复**。
> 原子计划路径在 0.32.0 上仍然是坏的。

---

## 1. 环境与身份（可复核）

| 项目 | 值 |
|---|---|
| `server_version` | `0.32.0` |
| `tool_count` / `enabled_tool_count` | `109` / `109` |
| `channels` | 1（`reject_busy_without_creating_a_job`） |
| `runner_channel_wait_seconds` | 120 |
| `disconnect_watchdog_seconds` | 20 |
| `surface_loft.available/state` | `true` / `compiled` |
| `surface_loft.evidence` | `create_code=0`、`extract_code=-18`、`feature_incomplete=true` |
| `surface_loft_panel.available/state` | `true` / **`ready`** |
| `unavailable_operations` | `sheetmetal_flange_profile`、`sheetmetal_corner_relief`、`sheetmetal_quilt_form`、**`surface_boundary_fill`** |

TXT 输入文件逐字节未变：1,616 行 / 145,361 B / `sha256 = 60f138eddf4da5f272a6b38e39a1bc7314e971d95adc8173c8f243d98287c1bf` / mtime `2026-11-16 18:43:38`。

---

## 2. 本次作业全链路（10 个作业）

| # | job_id | 类型 | 结果 | revision | 备注 |
|---|---|---|---|---|---|
| 1 | `99dc1fe36d174209bf9dd756dc8b06b7` | element_tree `surface_loft` | **failed** | 1 | `create_code=0` → `extract_code=-18` → 回滚；顺带写入 `release_numeric=42` |
| 2 | `c79ee9ab3fee4bfbabf14a5efdd06997` | **resident_panel `surface_loft`** | **succeeded** | 2 | 7 截面 + 尖点，`feature_id 138` / `quilt_id 144` / 490,915.028962 mm² |
| 3 | `ef82c89bce8740c39e2c47dbae5dfbc5` | `mirror`（quilt 144，plane id 4 = TOP） | succeeded | 3 | 新 quilt 155 / feature 150 |
| 4 | `dd91d5a836b84fb0882fdd3d13dae91d` | `quilt_merge`（144 + 155） | succeeded | 4 | quilt 144 → 2 面 / 981,830.165755 mm² |
| 5 | `359004eef07d46c6baa1e3d4c9b20907` | `sketch` `cap_x64`（双 B 样条闭合） | succeeded | 5 | feature 170，`closed_contours: 1`、`open_ends: 0`、偏差 2.84e-14 mm |
| 6 | `7d1c0414a68143b198952eb378c0a5f1` | plan：`surface_fill` → `quilt_merge` → `solidify` | **unknown_outcome** | 5 | `solidify` 引用失败 + worker 崩溃 `3221226505` |
| 7 | `ec67c27fde59467099e8b401fdb4f035` | reconciliation `restore_baseline` | succeeded | 5 | 卡 `waiting_for_channel` 约 8 分钟后成功 |
| 8 | `ef292d09ecda44fab510ab94e6b6e859` | `surface_fill`（单步） | succeeded | 6 | quilt 196 / feature 177 / 59,827.268099 mm² |
| 9 | `4458a3d2667e4208a3887f202d04baba` | `quilt_merge`（144 + 196，单步） | succeeded | 7 | quilt 144 → 3 面 / 1,041,657.460478 mm²，feature 199 |
| 10 | `cb0dd11419d649ab9a86017ecf13d5dd` | **`solidify`（单步，`{kind:"quilt",id:144}`）** | **succeeded** | 8 | `has_solid: true`，体积 **54,905,286.63066032 mm³** |

最终落盘：`bulb_v2.prt.9`，`sha256 = 0b80258aeb9ba30939f0d10515e52b279e6b4a28840f77c9856f98e8f105e554`，
`saved_file_reloaded_and_verified: true`，`reload_regenerate` + `reload_inspect` + `compare` 全 0。

> 作业 2、3、4、5、8、9、10 每一个都带 `saved_file_reloaded_and_verified: true`。
> 也就是说：**只要拆成单步，这条链每一步都能被独立验证**。

---

## 3. 核心问题（P0）

### P0-1　`solidify` 无法用合并结果自己的 label 引用它

**现象**（作业 6，`jobs/7d1c0414a68143b198952eb378c0a5f1/native.log` 第 619–621 行，原文）：

```
PHASE=execute_solidify
OPERATION_INDEX=2 INPUT={"label":"bulb_solid","mode":"add","new_body":false,"op":"solidify","reference":{"kind":"quilt_feature","label":"bbl_closed"},"side":"positive"}
PHASE=solidify:bulb_solid
ProModelitemInit(board, feature_id(ref), PRO_FEATURE, &f)=0
BUILD_FAILED=Quilt feature "bbl_closed" could not be read for quilt geometry (ProError -4); a merge/solidify/trim result is not always visible through its own feature label. Reference the original target quilt instead — its label, or {kind:"quilt",id:<quilt_id>} from inspect_model(section="quilts") ... known quilts: [{"area_mm2":1041657.4604780453,"face_count":3,"feature_ids":[138],"quilt_id":144},{"area_mm2":550742.3776003177,"face_count":2,"feature_ids":[150],"quilt_id":155},{"area_mm2":59827.29472258923,"face_count":1,"feature_ids":[177],"quilt_id":196}]
```

**根因（可从日志直接读出）**：

合并完成后，`quilt 144` 的 `feature_ids` 仍然是 **`[138]`**（原始放样特征），
**merge 特征 157 / 199 从未被写进任何一个 quilt 的 `feature_ids`**。
因此 `feature_id(ref) = 199` 反查 quilt 时找不到任何面组，返回 `ProError -4`。

**调用方踩坑的必然性**：

- `creo_quilt_merge` 的回执里，能拿到的标识是 **`feature_id`**（本轮为 `157` / `199`）；
- `creo_inspect_model(section="quilts")` 里，能用的标识是 **`quilt_id`**（本轮为 `144`）；
- 两者**不同名、不同值、不同语义**，而 `solidify` 只接受后者。
- 错误信息里才第一次点明这一点，也就是说：**必须先失败一次才能学到正确写法**。

**建议**：

1. `quilt_merge` 的回执同时给出 `quilt_id`（合并后的目标 quilt id），而不只是 `feature_id`；
2. 或者在 `SolidifyOp.reference_matches_mode` 前置校验阶段就拒绝 `quilt_feature` 指向 merge/mirror/trim 结果的写法，并在拒绝信息里直接给出可用的 `{kind:"quilt",id:N}`；
3. 文档里把「merge / mirror / trim 结果必须用 `{kind:"quilt",id:N}` 引用」写成显式规则，而不是藏在一次 `BUILD_FAILED` 里。

**本次绕开方式**（已实测成功，作业 10）：

```json
{"op":"solidify","label":"bulb_solid",
 "reference":{"kind":"quilt","id":144},
 "side":"positive","mode":"add","new_body":true}
```

---

### P0-2　worker 在 `PHASE=disconnect` 崩溃，`0xC0000409`，作业被打成 `unknown_outcome`

**现象**：

- 作业 6 的 `native.log` 最后一行就是 `PHASE=disconnect`，**之后什么都没有**；
- 对照成功的作业（如恢复作业 7），`native.log` 结尾是：

```
PHASE=disconnect
DISCONNECT=0
PHASE=result_delivery_complete
```

- 崩溃作业的 worker 退出码 `3221226505` = `0xC0000409` = `STATUS_STACK_BUFFER_OVERRUN`。

**关键点：崩溃与 `solidify` 失败无因果关系。**

回滚在崩溃之前**已经完整执行并成功**：

```
PHASE=rollback_to_saved_checkpoint
ProSolidRegenerate((ProSolid)board, PRO_REGEN_NO_FLAGS)=0
ProMdlTypeGet(board, &t)=0
ProFeatureTypeGet(f, &t)=0
... （对 5 个特征的 type/status/incomplete 全部回读，全部 0）
ProMdlToModelitem(board, &owner)=0
ProMdlDisplay(board)=0
PHASE=disconnect          ← 到此为止
```

即：失败处理路径走完、`ProMdlDisplay` 都返回 0 了，崩溃发生在**进程退出前的 disconnect 阶段**。

**后果（这才是真正阻断交付的部分）**：

| 后果 | 观测 |
|---|---|
| `native_result.json` 未落盘 | 作业状态只能记 `unknown_outcome`，`job.json` 只有 1,560 B |
| 模型被预留 | `model.pending_job` 未清空 |
| 会话健康降级 | `session_health.status: suspected_damage`，`damage_signals: [unknown_outcome_protection]` |
| 活动窗口丢失 | 崩溃后 `creo_session_status.current_model = ""`、`code = -8` |
| 必须人工恢复 | `creo_reconcile_model(inspect)` → `apply(restore_baseline)`，耗时另计（见 P1-1） |

**建议**：

1. **崩溃本身是独立缺陷**，与具体操作无关。请优先排查 `PHASE=disconnect` 的退出路径（`ProEngineerEnd` / `ProFinalize` 前后的栈使用，或其他 `ProMdlDisplay` 后的资源释放），尤其注意 `0xC0000409` 是**栈缓冲区溢出**而不是普通异常——它不会被 `try/catch` 拦住，所以现有的任何 `try` 包裹都拦不住。
2. 退一步的兜底：**在 `PHASE=disconnect` 之前就把 `native_result.json` 落盘**（哪怕是 `partial: true` 的形态）。这样即使 disconnect 崩了，作业也能拿到「回滚已完成」这个事实，不至于变成 `unknown_outcome` 并锁住模型。
3. 同理，`pending_job` 的清理不应依赖 disconnect 阶段的代码。

---

### P0-3　一个原子计划里前面成功的操作，会因为最后一步失败 + 崩溃而全部丢失

作业 6 的实际情况：

- `surface_fill` **成功**（quilt 196，59,827.294723 mm²）
- `quilt_merge` **成功**（quilt 144 → 3 面 / 1,041,657.460478 mm²，`state=done elapsed_ms=1775`）
- `solidify` **失败**（P0-1）
- 回滚 **成功**
- disconnect **崩溃** → 前面两步的成果与失败原因一起丢失

重新提交时，因为模型已被恢复到 revision 5，**必须把封盖和合并再做一遍**（作业 8、9），多花约 9 分钟。

**建议**：多操作计划如果做不到部分提交，至少应把每个已完成操作的 `{op,label,index,execution_status,effect_status,产出 id}` 增量落盘到 `job.json`，使调用方在 `unknown_outcome` 时仍能读到「前 N 步已经做成过什么」。

---

## 4. 严重问题（P1）

### P1-1　recovery job 停在 `waiting_for_channel` 约 8 分钟，`runner.log` 为 0 字节

**现象**（作业 7，`ec67c27fde59467099e8b401fdb4f035`）：

| 时刻（UTC） | 观测 |
|---|---|
| 10:55:06 | 提交 `creo_reconcile_model(mode="apply", action="restore_baseline")` |
| 10:55:08 | `toolkit-owner.lock` 被写入：`{"job_id":"ec67c27f...","operation":"reconcile_model","pid":1832,"since":"2026-11-20T10:55:08"}` |
| 10:55–11:02 | 两次长轮询（180 s + 240 s）均返回 `status: queued`、`stage: waiting_for_channel`、`wait_expired: true` |
| 11:02 左右 | 读 `jobs/ec67c27f.../runner.log` → **0 字节**；`worker.log` → **0 字节**；`toolkit.lock` 报 `Device or resource busy` |
| 11:03:19 | 作业实际完成：`status: succeeded`、`stage: reconciliation_committed`、`revision 5`、`saved_file_reloaded_and_verified: true` |

**三个独立问题叠在一起**：

1. **锁自持有造成死锁假象**：`toolkit-owner.lock` 的持有者是该作业自己的 runner（pid 1832），而它同时又在 `waiting_for_channel`。调用方看到「锁被占用 + 作业在等通道」会直接判断为死锁，实际只是慢启动。
2. **`runner.log` 完全空白**：`bridge.py:1671-1675` 的 `_run_job_dispatch` 先写 `stage="waiting_for_channel"`，再调 `creo_mechdog.reconciliation.run`。日志 0 字节说明在这段等待里**没有任何进度输出**，用户无法区分「正常等待」和「卡死」。
3. **`creo_get_job(wait_seconds=...)` 帮不上忙**：它只读持久化记录，而作业在 `waiting_for_channel` 阶段不写进度，所以等到 `wait_expired` 也拿不到任何新信息，只能反复重试。文档里写的 `runner_channel_wait_seconds = 120` 与实际观察到的约 8 分钟不一致。

**建议**：

- 恢复作业启动时**不要在等通道之前就占 `toolkit-owner.lock`**，或者把它明确标记为「本作业自持，不是他人占用」，并在 `creo_get_job` 里回显这一点；
- `waiting_for_channel` 阶段每 ≥5 s 至少写一行 `runner.log`（例如 `WAIT_FOR_CHANNEL elapsed_ms=... owner=...`）；
- `creo_get_job` 的 compact 视图在 `waiting_for_channel` 时回显 `channel_owner`、`waited_seconds`、`runner_channel_wait_seconds`，让调用方能判断「还要不要等」。

---

### P1-2　新 worker 下必须先「失败一次」才能使用面板路线

**现象**：

换了新 worker（`8a36c34d...`）后，第一次提交 `creation_route: "resident_panel"` 被拒：

```
panel profile 'creo10-bbl-candidate-3' was measured on Creo release_numeric=42 ...,
but this worker has no recorded host release
```

`panel_profiles.host_release()` 三处取数全空。

**绕法**：先提交一次 element_tree 的 `surface_loft`（作业 1，注定 `-18` 失败），它会把 `release_numeric=42` 写进 `surface_loft_runtime.host_release`，之后面板提交才被受理。

**问题**：

1. 这是**强制性的失败前置**——用户必须先付出一次必然失败的作业（约 4 分钟）才能用面板；
2. 这次失败还进了 `surface_loft.evidence`（`extract_code=-18`、`feature_incomplete=true`），也就是说**正常的准入流程会在熔断/证据记录里留下一次伪故障**；
3. `session_status.features.surface_loft.state` 因此从 `ready` 变成 `compiled`，语义上像是降级，而实际上面板是好的。

**建议**：worker 首次连上 Creo 时，在 `connect` 阶段就把 `release_numeric` 写进 `surface_loft_runtime`，不要等一次失败作业来填。或者面板准入失败时自动补一次只读的 release 探测。

---

### P1-3　面板路线的前置条件从未被文档化：目标模型必须是 GUI 里打开的活动窗口

这是本轮**花掉最多时间**的一个坑，也是 0.31.1 那个「异步恒 -8」结论真正被推翻的原因。

**现象**：

- 面板路线在 `phase: reading_references` 阶段要求 `ProMdlCurrentGet` 成功，失败时上报 `current_model_code: -8`、`panel_never_opened: true`；
- 程序化 `ProMdlOpen` / `ProMdlDisplay` 打开的窗口**不算** current，即使模型的 `origin` 正确、`modified: false`；
- **必须由用户在 GUI 里 `文件 → 打开` 交互式打开一次**，`ProMdlCurrentGet` 才返回 0。

**本轮的正反证据**：

| 场景 | `creo_session_status` |
|---|---|
| 桌面代理用 `文件 → 打开` 手工打开 `bulb_v2.prt` 后 | `current_model: "BULB_V2"`、`current_model_code: 0`、`model_type: 2` → 面板作业随即成功 |
| 恢复作业执行 `ProMdlDisplay(board)=0` 之后，Creo 标题栏明确显示 `BULB_V2 (活动的)` | **仍然是 `current_model: ""`、`code: -8`** |
| 同一次作业内部的 preview 阶段 | `current_set: 0`、`current_get: 0`（全 0，成功） |

也就是说：**GUI 标题栏的「(活动的)」与 Toolkit 的「current model」不是同一个概念**，
而 `session_status` 的 `-8` 又不区分「GUI 里真的没有窗口」和「有窗口但不是 Toolkit 认的 current」。

**建议**：

1. `creo_surface_loft` 的 docstring（`server.py:3153-3155`）目前只写「需要 worker 声明面板后端 + 该 release 有认证 profile」，请补上一句：**「面板路线还要求目标模型是用户在 Creo 界面里打开的活动窗口；程序化打开或保存重载后的模型不满足这个条件」**；
2. `-8` 时回显更具体的分类（`no_window` / `window_without_current` / `current_is_other_model`），而不是统一 `panel_never_opened: true`；
3. 面板作业结束后不要用会丢失 current 的方式收尾——本轮面板作业成功后，后续作业仍然可以正常工作，但崩溃作业（P0-2）直接把 current 打没了。

---

### P1-4　`session_status` 的 `-8` 与作业内部的 `current_set: 0` 相互矛盾

同上表的第 2、3 行。`creo_session_status` 的 `live_probe` 与真正跑作业的 worker 对「current」的判断不一致，且 probe 结果没有任何提示说「这不影响建模」。

**建议**：`live_probe` 里把 `current_model_code: -8` 标注为「不影响 element_tree / generic 路线」，或者在 generic 作业里根本不把 `-8` 当作健康问题。

---

## 5. 中等问题（P2）

### P2-1　`panel` 块仍然没有 `model_name` → `PANEL_MODEL_CHANGED` 守卫永不触发

- `generic_bridge.py:1373-1385` 组装 `operation["panel"]`，键只有 9 个：
  `job_id` / `request_id` / `nonce` / `profile_id` / `open_macro` / `second_direction_macro` / `select_command` / `done_macro` / `done_command`。
- **没有 `model_name`**。
- `native/panel_run.h:422` 的守卫：

```cpp
throw std::runtime_error("PANEL_MODEL_CHANGED: the request names model " + wanted_model + ...
```

- `native/panel_references.h:231` 也有 `failure("PANEL_MODEL_CHANGED", ...)`。

由于上层从不传 `model_name`，这个守卫**永远不会触发**。
一旦用户在面板作业执行期间切换了活动窗口，面板会在错误的模型上打 macro，而没有任何前置拒绝。

**这是 0.31.1 已报的问题，0.32.0 未修。**

---

### P2-2　`creo_capabilities.routes` 这个 section 不存在，但 docstring 仍指路它

- `server.py:3153-3155`：

```
A request is refused before a job unless the loaded
worker declares a panel backend and a certified UI profile for this release
exists; read creo_capabilities.routes.resident_panel for both facts. It never
falls back to the element tree.
```

- 实际 `creo_capabilities(detail="full")` 的分页 sections 只有：
  `overview` / `tools` / `families` / `references` / `seeds` / `evidence` / `runtime` / `known_limitations` / `plan_examples`。
- **没有 `routes`**。按文档去查会得到 `unknown section`。

应该是 `families.surface_loft` + `session_status.features.surface_loft_panel`。
**这是 0.31.1 已报的问题，0.32.0 未修。**

---

### P2-3　quilt 的 `closed` / `closure` 判定结果自相矛盾，无法用来判断能否实体化

同一份模型、相邻三个 revision 的实测：

| quilt | 面数 | 实测 | `closed` / `closure` |
|---|---|---|---|
| 144（merge 前，2 面） | 2 | 981,830.165755 mm² | `closed: false`，`query_code = -18`，`reason: quilt_is_open` |
| 144（merge 后，3 面） | 3 | 1,041,657.460478 mm² | `closed: null`，`query_code = -62`，`reason: quilt_volume_eval_failed` |
| 196（单面 fill） | 1 | 59,827.294723 mm² | **`closed: true`，`query_code = 0`** |

矛盾点：

1. **单面的封盖面被判「闭合」**（`query_code 0`），这在几何上不成立；
2. **3 面完整闭合的球鼻艏壳体被判「体积求值失败」**（`-62`），而它**恰好可以成功实体化**（作业 10，`volume_after = 54,905,286.63 mm³`）；
3. `solidify` 的回执里 `closure` 字段同样报 `{available: false, query_code: -62, reason: "quilt_volume_eval_failed"}`，**但操作本身 `succeeded` + `committed`**。

也就是说：**`closure` 为 `-62` 既不代表不能实体化，`closed: true` 也不代表真闭合。**
调用方无法用这个字段做任何前置判断。

**建议**：区分「拓扑闭合」（边配对）与「可实体化」（体积可求值）两个语义，并在 `solidify` 成功时把 `closure` 字段替换为实体化后的实测结果，而不是回显一个失败的面组查询码。

---

### P2-4　`surface_boundary_fill` 不可用，封口只能绕行

`creo_capabilities.unavailable_operations.surface_boundary_fill` 原文：

> the previous single-direction candidate creates and extracts (ProFeatureWithoptionsCreate=0, ProFeatureExtreeExtract=0) but regeneration fails with feature_status=6 and produces no quilt (quilt visit -4, quilt_count=0, empty element-error list) … so the closed single-direction chain does not yield a measurable filled surface

`server.py` 里 `creo_surface_boundary_fill` 的 docstring（约 3190 行）也写：

> On 2026-11-08 the closed single-direction chain created and extracted but regenerated to no quilt on Creo 12.4.0.0, so the operation stays in UNAVAILABLE_OPERATIONS

**影响**：球鼻艏的后端封口无法用官方能力完成，只能：

1. 在 `X = 6409.473618` 平面上新建一条**闭合双 B 样条草图**（`cap_x64`，两条 A23 曲线 + 镜像，首尾相接）；
2. 用 `surface_fill` 生成平面片（quilt 196）；
3. 用 `quilt_merge` 把它缝到壳体上。

这条路径本轮**实测可用**，但文档里没有任何地方说明它，属于用户自己摸索出来的替代方案。

**建议**：在 `creo_surface_loft` / `creo_surface_fill` 的相关文档里，为「多截面放样得到的开放壳体如何封口」给出这个三步写法，并注明 `surface_boundary_fill` 不可用。

---

### P2-5　`parametric.exe` 长期 `hung_window_observed: true`，但 Creo 实际可用

`creo_process_snapshot` 每次都是：

```json
{"pid": 10848, "name": "parametric.exe",
 "windows": {"state": "hidden_only", "top_level_count": 3,
             "visible_count": 0, "hung_window_observed": true,
             "hung_implies_modal": false}}
```

而同一次快照里 `xtop.exe` 是 `visible`、1 个可见窗口。实际 Creo GUI 完全正常，能建模、能出 preview。
`hidden_only` + `hung_window_observed: true` 会让人误判「Creo 假死」。

**建议**：当 `top_level_count > 0` 但 `visible_count == 0` 时，不要同时报 `hung_window_observed: true`，或者给这个组合一个明确的解释字段。

---

### P2-6　`creo_capabilities.update` 的 GitHub 检查长期失败

```json
{"status": "failed", "error": "GitHub 更新检查超过 5 秒网络预算；可设置 MECHDOG_UPDATE_TIMEOUT_SECONDS（1—30 秒）后重试。",
 "cache_age_seconds": 263, "retry_after_at": "+15min"}
```

5 秒预算在受限网络下基本必失败，`latest_version` 恒为 `null`。
不影响建模，但让「当前是否最新版本」这个问题无法从工具内回答。

**建议**：把默认预算提到 15 s，或者在 `creo_check_update(force=true)` 时不套用缓存退避。

---

## 6. 本次实测通过的分步路径（建议写进文档）

球鼻艏从 7 条截面曲线到实体，**必须拆成 5 个独立作业**（每个都要等它 `saved_file_reloaded_and_verified: true` 再下一步）：

| 步骤 | 工具 | 关键参数 | 产出 |
|---|---|---|---|
| 1 | `creo_surface_loft`（`creation_route: "resident_panel"`） | 7 截面 + 尖点 | quilt 144 / 490,915.028962 mm² |
| 2 | `creo_mirror` | `target: {kind:"quilt",id:144}`，`plane: {id:4}`（TOP，法线 +Y） | quilt 155 |
| 3 | `creo_quilt_merge` | `target: {kind:"quilt",id:144}`，`tool: {kind:"quilt",id:155}` | quilt 144 → 2 面 / 981,830.165755 mm² |
| 4 | `creo_create_sketch` + `creo_execute_plan(surface_fill)` | 闭合双 B 样条草图（`cap_x64`，plane id 41） | quilt 196 / 59,827.268099 mm² |
| 5 | `creo_quilt_merge` | `target: {kind:"quilt",id:144}`，`tool: {kind:"quilt",id:196}` | quilt 144 → 3 面 / 1,041,657.460478 mm² |
| 6 | **`creo_execute_plan(solidify)`** | `reference: {kind:"quilt",id:144}`，`mode:"add"`，`new_body:true`，`side:"positive"` | **实体，54,905,286.63066032 mm³** |

**三条必须遵守的规则**（都是本轮踩出来的）：

1. **`merge` / `mirror` / `trim` 的结果只能用 `{kind:"quilt", id:<quilt_id>}` 引用，不能用 feature label**（P0-1）；
2. **不要把这 6 步放进一个 `operations` 数组**（P0-3），拆步后每步都能独立验证、独立回滚；
3. **`quilt_merge` 之后必须重新 `creo_inspect_model(section="quilts")` 取 `quilt_id`**，不能复用合并前的 id 假设。

`cap_x64` 草图提交参数（实测成功，`closed_contours: 1`、`open_ends: 0`、偏差 2.84e-14 mm）：

```json
{"entities": [
  {"control_points": [[0,-460],[60,-460],[180.725,-469.166667],[181.325,-650.833333],[54,-660],[0,-660]],
   "degree": 3, "knots": [0,0,0,0,0.45,0.55,1,1,1,1], "name": "cap_r", "type": "b_spline",
   "weights": [1,1,1,1,1,1]},
  {"control_points": [[0,-460],[-60,-460],[-180.725,-469.166667],[-181.325,-650.833333],[-54,-660],[0,-660]],
   "degree": 3, "knots": [0,0,0,0,0.45,0.55,1,1,1,1], "name": "cap_l", "type": "b_spline",
   "weights": [1,1,1,1,1,1]}
 ], "label": "cap_x64",
   "plane": {"reference": {"id": 41, "kind": "datum_plane"}}}
```

---

## 7. 与 TXT 的几何核对

### 7.1 单位换算约定（TXT 缺口）

TXT 第 95 行写「本节与附录 A21～A23e 的坐标单位统一为米」，但**没有说明建模时按什么比例换算**。
本机历史约定是 **TXT 米值 × 100 = 模型 mm**，即 **1:10**。佐证：

| 对象 | TXT（米） | 模型（mm） | 比值 |
|---|---|---|---|
| 船长 | 85.6 | 8560 | 1:100 |
| 船宽半值 | ±6.9 | ±690 | 1:100 |
| 水下附件最低点 | −9.1 | −910 | 1:100 |
| 球鼻艏 X 范围 | 64.094736 → 78.098843 | 6409.474 → 7809.594 | 1:100 |

球鼻艏与整船**同一约定**，所以不算错配；但**这个换算规则文档里没有**，跨软件重建时极易被理解成「米 → mm 应该 ×1000」，从而做出 10 倍大的模型。

### 7.2 七个截面与尖点（逐点核对，全部吻合）

| 位置 | TXT 附录 | TXT X（米） | 模型 X（mm） | 控制点数 | 结论 |
|---|---|---|---|---|---|
| 后截面 | A23 / Sketch72 | 64.094736179 | 6409.473618 | 6 | ✓ 逐点一致 |
| 补充 | A23a | 66 | 6600 | 28 | ✓ |
| 补充 | A23b | 68 | 6800 | 28 | ✓ |
| 补充 | A23c | 70 | 7000 | 28 | ✓ |
| 中截面 | A22 / Sketch70 | 72.094736179 | 7209.473618 | 6 | ✓ |
| 补充 | A23d | 74 | 7400 | 28 | ✓ |
| 补充 | A23e | 76 | 7600 | 28 | ✓ |
| 尖点 | A21 / Sketch69 | (78.094736179, 0, −5.6) | (7809.473618, 0, −560) | 点 | ✓ |

抽验 `sec_x66` 与 A23a 的前/中/末三点（×100 换算后）：

| A23a 控制点（米） | 模型草图点（mm） |
|---|---|
| (0, −4.6) | (0, −460) |
| (0.061376, −4.600154) | (6.1376, −460.0154) |
| (1.818286, −5.502774) | (181.8286, −550.2774) |
| (0, −6.6) | (0, −660) |

**七个截面全部按 TXT 附录的原生 B 样条控制点与节点向量建模，没有退化成 2 截面，也没有用插值近似。**

### 7.3 最终实体几何

| 项目 | TXT | 模型实测 | 偏差 |
|---|---|---|---|
| bbox X | 64.094736 → 78.098843 米 | 6409.353613 → 7809.593623 mm | 起点 −0.120 mm、终点 −0.290 mm |
| bbox Y | ±1.818679 米 | ±181.92114972493397 mm | +0.053 mm |
| bbox Z | −6.600046 → −4.599998 米 | −660.478237 → −458.806538 mm | 底 −0.474 mm、顶 +1.193 mm |
| 质心 | —（TXT 未给） | (6917.214015, 0.000000, −559.543320) | Y 精确 0 → 镜像对称成立 |
| 体积 | —（TXT 未给绝对值） | **54,905,286.63066032 mm³** | 见下 |

bbox 的 0.1～1.2 mm 级差异来自曲面内核的包围盒计算，相对 1400 mm 长度属 0.03%～0.09%。

体积的独立核对（三个量级一致的估计）：

| 估计方法 | 结果 | 与实测差 |
|---|---|---|
| 长椭球 `4/3·π·700·181.87·100` | 53,314,700 mm³ | 实测 +2.98% |
| 7 截面梯形数值积分（形状相似缩放） | 59,600,000 mm³ | 实测 −7.9%（梯形法对凸曲线系统性高估） |
| **实测** | **54,905,287 mm³** | — |

结论：体积落在两个独立估计之间，与 TXT 的几何尺度自洽。

> TXT 第 89 行提到「只用 2 截面时半体体积比原件小约 1.27%」，但**没有给出原件的绝对体积**，所以无法做绝对误差判定。如需绝对验收，请在 TXT 里补上原件（SolidWorks）球鼻艏半体的实测体积。

### 7.4 实体状态

`creo_inspect_model` 最终快照：

```json
{"has_solid": true, "volume_mm3": 54905286.63066032,
 "center_of_gravity": [6917.214014709925, 0.0, -559.5433199820098],
 "counts": {"features": 49, "surfaces": 3, "edges": 11, "quilts": 3, "bodies": 2},
 "body_counts": {"objects": 2, "active": 1, "with_material": 1, "without_material": 1}}
```

两个 body 分别是：实体 body 206（`state: active`、`material: true`、`surface_count: 3`、bbox 完整）与空 body −5778（`state_name: no_geometry`）。

---

## 8. 复现步骤（最小）

```
# 前提：Creo 10 已启动，用户已在 GUI 里 文件→打开 bulb_v2.prt 使其成为活动窗口
1. creo_session_status                    → 记录 server_version / worker_sha256
2. creo_surface_loft(creation_route="resident_panel", 7 截面 + 尖点)
3. creo_mirror(target={kind:quilt,id:144}, plane={id:4})
4. creo_quilt_merge(target={kind:quilt,id:144}, tool={kind:quilt,id:155})
5. creo_create_sketch(cap_x64, plane={id:41})    # 双 B 样条闭合
6. creo_execute_plan([surface_fill(cap_x64)])    # → quilt 196
7. creo_quilt_merge(target={kind:quilt,id:144}, tool={kind:quilt,id:196})
8. creo_execute_plan([solidify(reference={kind:quilt,id:144}, mode=add, new_body=true)])
   → 期望：has_solid=true，volume≈5.49e7 mm³
```

**触发 P0-1 / P0-2 / P0-3 的最短路径**：把第 6、7、8 步合成一个 `operations` 数组提交，
`solidify` 用 `{kind:"quilt_feature", label:"<第 7 步的 label>"}` 引用，
即可在 `PHASE=disconnect` 稳定复现 `0xC0000409`。

---

## 9. 证据文件清单

同目录 `证据-球鼻艏-0.32.0/`（22 个文件，共约 600 KB）：

```
jobs/99dc1fe3.../job.json + native.log        # element_tree -18
jobs/c79ee9ab.../job.json + native.log        # 面板路线成功
jobs/ef82c89b.../job.json + native.log        # mirror
jobs/dd91d5a8.../job.json + native.log        # quilt_merge（144+155）
jobs/359004ee.../job.json + native.log        # sketch cap_x64
jobs/7d1c0414.../job.json + native.log        # ★ 崩溃作业（solidify 失败 + 0xC0000409）
jobs/ec67c27f.../job.json + native.log        # ★ 恢复作业（卡 waiting_for_channel 8 分钟）
jobs/ef292d09.../job.json + native.log        # surface_fill 单步成功
jobs/4458a3d2.../job.json + native.log        # quilt_merge 单步成功
jobs/cb0dd114.../job.json + native.log        # ★ solidify 单步成功
toolkit-owner.lock.snapshot.txt               # 恢复作业自持锁的原文快照（锁文件已被系统清理）
model-bulb_v2-final.json                      # 最终模型状态（rev 8 / has_solid true）
toolkit_health.json
README.md                                     # 本证据包索引
```

关键行位置：

| 内容 | 文件 | 行 |
|---|---|---|
| `solidify` 引用失败原文 | `jobs/7d1c0414.../native.log` | 616–621 |
| 回滚成功（全部回读 0） | 同上 | 622–约 790 |
| 崩溃点（最后一行） | 同上 | 794（`PHASE=disconnect`，之后无内容） |
| 恢复作业正常收尾对照 | `jobs/ec67c27f.../native.log` | 末尾 `DISCONNECT=0` + `PHASE=result_delivery_complete` |

---

## 10. 建议的修复优先级

| 优先级 | 问题 | 理由 |
|---|---|---|
| **P0** | worker `PHASE=disconnect` 崩溃 `0xC0000409` | 一次崩溃就把模型锁成 `unknown_outcome`，并需要 8 分钟人工恢复；这是**唯一一个会让整条链前功尽弃**的缺陷 |
| **P0** | `native_result.json` 提前落盘 | 即使崩溃修不掉，这个兜底也能让模型不被锁 |
| **P0** | `solidify` 对 merge/mirror/trim 结果的引用形态 | 必然踩、必然失败、必须失败一次才能学到 |
| **P1** | 多操作计划的中间结果落盘 | 直接决定失败后要不要重做前几步 |
| **P1** | recovery job 的自持锁与空日志 | 让调用方无法判断死锁 vs 慢启动 |
| **P1** | 面板路线的 `release_numeric` 预热 | 强制一次伪失败，还污染 evidence |
| **P1** | 面板路线「GUI 活动窗口」前置条件写进文档 | 本轮最大时间黑洞 |
| **P2** | `panel.model_name` / `creo_capabilities.routes` / `closure` 语义 / `hung_window_observed` | 影响可诊断性，不影响建模本身 |

---

## 11. 附：本轮过程中被推翻的一个旧结论

0.31.1 反馈文档里曾把面板路线的 `ProMdlCurrentGet → -8` 归因为「异步连接恒无当前对象」。
**这个结论是错的**，本轮已用实验推翻：

- 目标模型**必须是用户在 Creo GUI 里交互式打开的活动窗口**；
- 程序化 `ProMdlOpen` / `ProMdlDisplay` 打开的窗口**不满足**这个条件（即使标题栏显示「(活动的)」）；
- 满足条件后，面板路线在 0.32.0 + Creo 10（`release_numeric 42`）上**可以成功**（作业 2，`saved_file_reloaded_and_verified: true`）。

请以本轮结论为准，并请在文档里补上这个前置条件（P1-3）。


---

## 12. 附：整船原生重做阶段（同一 0.32.0）新增问题

本节是同一天、同一 MCP 版本、同一 Creo 10 会话（`session_fingerprint 14359338636323523713`）下，
把球鼻艏按 TXT 重做进**整船模型**时新发现的 8 条问题。它们与 §3–§5 不重叠。

### P1-5　没有「按 quilt 自身闭合边界封口」的路线，封口只能靠重画曲线

`surface_fill` 的入参只有 `sketch`（`FillOp(sketch: SketchRef)`），**不能引用已存在 quilt 的开口边界**；
`surface_boundary_fill` 仍在 `UNAVAILABLE_OPERATIONS` 里。

后果：一个开口 quilt 要闭合，唯一路径是

1. 在草图里把那条边界曲线**逐点重新录一遍**；
2. `surface_fill` 出平面；
3. `quilt_merge` 并回原 quilt。

第 1 步无法引用既有几何，只能靠控制点数值完全一致来保证贴合 —— 这既是能力缺口，也是精度风险来源。
本轮是靠「封盖草图复用 `sec_x64` 的 6 个控制点 + 同一 knot 向量」才把风险压住
（`native_section.max_endpoint_gap_mm = 0.0`、`closed_contours = 1`、`open_ends = 0`、控制点偏差 5.68e-14）。

**建议**：`surface_fill` 增加 `boundary: {kind:"quilt", id:N}` 形态，或提供 `quilt_close` 直接把开口边界缝成平面。

### P1-6　`closed_status` 返回 `-62` 时，公开字段无法判断「还能不能实体化」

同一个模型里，三种 quilt 的公开回执：

| quilt | 来历 | `closed` | `closed_status.query_code` | `reason` | 能否 `solidify` |
|---|---|---|---|---|---|
| 9381 | 单纯平面填充 | `true` | `0` | – | 能 |
| 9327（合并后 3 面） | 放样+镜像+合并+封盖 | `null` | `-62` | `quilt_volume_eval_failed` | **能（实测成功）** |
| 9327（合并前 1 面） | 放样 | `null` | `-18` | `quilt_is_open` | 不能 |

- `native/surfaces.cpp` 里 `generic_surface_solid()` 只把 `quilt_is_open` 当致命，`-62` 是放行的；
- 但公开字段里 `-62` 和 `-18` 长得一样「都不可用」，`closed` 都是 `null`；
- 客户端若按 `closed != true` 拦，就会把一个**实测可以实体化**的 quilt 判死。

**建议**：`closed_status` 增补一个布尔字段（例如 `usable_for_solidify`），或给 `-62` 一个
「封闭但体积积分失败、可继续」的明确语义，并在 `reason` 里写清与 `-18` 的区别。

### P2-7　同一份操作回执里，`profile` 块与 `native_section` 块对 b_spline 草图的结论相反

`cap_x64`（2 条 `b_spline` 拼成闭环）的 sketch 回执：

```
profile.analysis              "partial"
profile.entity_count          0
profile.contour_count         0
profile.closed_contour_count  0
profile.material_area_mm2     0
profile.categories.unsupported  2        <-- 两条样条都被记为 unsupported
native_section.curves           2
native_section.contours         1
native_section.closed_contours  1        <-- 实际是 1 条闭合轮廓
native_section.open_ends        0
native_section.max_endpoint_gap_mm  0.0
```

按 `profile` 块判断会得出「这草图不可用」的错误结论，按 `native_section` 才是对的。
两者在同一份 JSON 里并列输出，且没有任何字段说明以谁为准。

**建议**：`b_spline` 计入 `profile` 的实体统计，或在 `profile.analysis == "partial"` 时
显式给出 `native_section` 为准的指向。

### P2-8　`quilt_merge` 会静默改写「没参与合并」的第三个 quilt

把封盖 quilt `9381` 并进 `9327` 之后，**先前镜像留下、并未参与本次合并的 `9338`** 也变了：

| quilt | 合并前 | 合并后 |
|---|---|---|
| 9327 | 2 面 / 981,829.4064525267 mm² | 3 面 / 1,041,656.7808730027 mm² |
| 9338 | 1 面 / 490,914.7032262633 mm² | **2 面 / 550,742.0776467387 mm²** |
| 9381 | 1 面 / 59,827.37442047542 mm² | 1 面 / 59,827.37442047542 mm² |

`9338` 多出来的面积正好是封盖的 59,827.374 mm²，说明 merge 的新面被同时挂进了另一个 quilt 的引用集。
作业回执对此**没有任何提示**，只有 `feature_id: 9383`。

**建议**：merge 回执列出被改写的所有 quilt id 与其面数变化。

### P2-9　`mirror` / `surface_fill` / `quilt_merge` 都不回传结果 quilt 的 id

三种操作的回执分别只有：

- `mirror` → `succeeded / committed`（连 `feature_id` 都没有）
- `surface_fill` → `succeeded / committed`
- `quilt_merge` → `feature_id`

要拿结果 quilt id 必须**再调一次 `creo_inspect_model(section="quilts")`**，并按 bbox / 面数去猜哪个是新的。
本轮 3 次都是这样猜出来的（镜像件 9338 靠 bbox 的 Y 符号判断，封盖件 9381 靠 bbox 是平面判断）。

**建议**：这三个 op 的结果里直接带 `quilt_id`（`merge` 已经能拿到 `feature_id`，拿 quilt id 是同一层信息）。

### P2-10　`feature_state` 删除不做隐式级联，但也不提供「依赖闭包」查询

删除 `bulb5` 那一组时被拒，回执原文：

```
feature_state targets do not cover every affected dependency; Creo also deleted these features;
list them explicitly (no automatic cascade): [{"feature_id":4857,...,"type_name":"datum_plane"},
{"feature_id":4874,...,"type_name":"datum_plane"}]
```

设计本身是安全取向的、可接受；问题是**没有前置查询**能一次拿到某个特征的完整依赖闭包。
本轮只能先按 label 删 → 被拒 → 读回执里的缺失项 → 补上 → 再被拒 → 再补，
最后靠「拿新鲜快照反推 6 组闭包、一次性提交 30 个 feature id」才成功
（`47ff38c62ae64c17976a92cbeae0f041`，386 → 356 特征）。

**建议**：`feature_state` 加 `dry_run: true`，或在 `creo_inspect_model` 里给出 `dependencies` 段。

### P2-11　`sketch.dimensioning = "coordinates"` 不支持 `b_spline`，报错不指向具体实体

计划准入阶段一次性拒绝，原文：

```
operations[0..6]: Coordinate dimensioning supports line/centerline/rectangle/polyline/circle/arc entities
```

7 条 sketch 全部被拒，但错误信息没有说「你的 `b_spline` 是原因」，也没有在
`SketchOp.dimensioning` 的 Literal 说明里写这条限制。改成 `"auto"` 后正常（`used: autodim`）。
对 NURBS 截面这类必须逐点给出的几何，`coordinates` 是**最自然的选择**，偏偏不支持。

**建议**：把该限制写进 `creo_capabilities` 的 sketch 条目与 `dimensioning` 字段说明。

### P2-12　已有 Creo 实例在跑时，`open_app` 式启动会造出第二个实例，会话直接变 ambiguous

本轮桌面代理为「把整船模型变成 GUI 活动窗口」执行了 `open_app("Creo Parametric")`，
在原有实例（`parametric.exe` 10848 / `xtop.exe` 29260）之外又起了
（19280 / 31276），随后：

```
connection_state: ambiguous
toolkit_code: -36
worker_exit_code: 20
selection_required
sessions_observed: 3
selected_session_configured: false
```

`taskkill /PID 19280 /F /T` 终止整条进程树后，`creo_session_status` 立刻回到
`connected: true` / `current_model: "BULB_V2"` / `code: 0`。

**建议**：`creo_startup` / 自动启动路径在检测到已有实例时应**直接附着**（或直接拒绝并给出明确的
`already_running` 码），而不是再起一个。

---

## 13. 附：整船原生重做的验证链（revision 22 → 32）

背景：整船 rev22 里的旧球鼻艏是 **6 段等距 230.5 mm 拉伸**（`BULB0`–`BULB5`），
实测净贡献只有 **5,308,270.53 mm³**，是 TXT 精确件 54,905,286.63 mm³ 的 **9.7%**。
本轮按 TXT 的**不等距 7 截面**（6409.474 / 6600 / 6800 / 7000 / 7209.474 / 7400 / 7600 + 尖点 7809.474）
整条重做。

| # | 作业 ID | revision | 操作 | 结果 |
|---|---|---|---|---|
| 0 | – | – | 备份 `backup-frigate-rev22/`（59 MB） | 可回退 |
| 1 | `4792d43b7aab4481be90da20bece93a8` | 22 | 一次性删 6 组 BULB（依赖不全） | failed，**回滚成功**，体积/特征数不变 |
| 2 | `47ff38c62ae64c17976a92cbeae0f041` | **23** | 补全闭包后一次删 30 个特征 | succeeded，386 → 356 |
| 3 | `51c80dcbf99143cab9242117132fefe4` | **24** | 7 个 `sketch`（`plane:"YZ"` + `offset`）+ 尖点 | succeeded，7 截面偏差 ≤ 1.14e-13，全 `open_ends: 2` |
| 4 | `690d1f4ea2fb4a5eaea2810ef24068c3` | **25** | `resident_panel` 放样 | succeeded，`quilt 9327`，面积 490,915.3176472564，3 条开边 |
| 5 | `65fee1675da74d6e9ed4865c5345da66` | **26** | `mirror` 关于 TOP（`datum_plane id 4`） | succeeded，`quilt 9338`，面积 490,915.3176472571（差 7e-10） |
| 6 | `4fa71adc213846468e97a24fa21dca1a` | **27** | `quilt_merge(9327, 9338)` | succeeded，9327 → 2 面 / 981,829.4065 mm² |
| 7 | `352b326d8fdf4dcc8d6124ba2626c319` | **28** | 封盖草图 `cap_x64`（2 条 `b_spline` 闭环） | succeeded，`closed_contours: 1`、`open_ends: 0` |
| 8 | `7f1fbc0cec784acf8f0ccf852c159638` | **29** | `surface_fill(cap_x64)` | succeeded，`quilt 9381`，面积 59,827.3695 mm² |
| 9 | `500a99fa7fa84326b9b3f75bce8ec494` | **30** | `quilt_merge(9327, 9381)` | succeeded，9327 → 3 面 / 1,041,656.7809 mm² |
| 10 | `fa77160f99b34a7e8d717b1714cfb13e` | **31** | `solidify({kind:"quilt",id:9327}, new_body:true)` | succeeded，新 `body 9390`，Δ 体积 **54,905,296.14492 mm³** |
| 11 | `377543272799485a90e27e1bbfe22778` | **32** | `boolean_bodies(union, 77 ← 9390)` | succeeded，回到单实体 |

**11 个作业全部 `saved_file_reloaded_and_verified: true`**（除 #1 是失败回滚、#0 是备份）。

### 13.1 体积三重核对

| 对象 | 体积（mm³） | 判据 |
|---|---|---|
| 整船 rev22 基线 | `5,912,880,608.695585` | 重建前 |
| 独立件 `bulb_v2`（同 7 截面） | `54,905,286.63066` | 上一轮已验收 |
| 整船内球鼻艏（`body 9390`） | `54,905,296.14492` | `volume_after − volume_before` |
| 两者差 | **9.51426**（相对 **1.733e-7**） | 同一几何的两处独立实现 |
| 并集后整船 | `5,919,802,387.113947` | 最终 |
| 并集净增 | `6,921,778.418362` = 球鼻艏的 **12.610%** | 布尔差 |
| 旧 6 段拉伸净贡献 | `5,308,270.53` = 精确件的 **9.7%** | 旧结果 |

### 13.2 必须如实记录的一点：球鼻艏 87.4% 埋在既有船体里

船舶 body 77 的 bbox 是 `x 0→8560 / y ±690 / z −910→1920`，球鼻艏 bbox 是
`x 6409.35→7809.59 / y ±181.92 / z −660.48→−458.81`，**完全落在船体包围盒内**；
尖点 `x = 7809.474` 距艏柱 `x = 8560` 还有 **750.5 mm**。

所以按 TXT 坐标，球鼻艏并不凸出艏柱，只在水线下方（`z −460…−660`）从船体下缘透出，
布尔并集净增只有 `6,921,778.42 mm³`。

- 这不是 MCP 的问题，是 **TXT 的球鼻艏坐标与船体坐标的相对关系**问题；
- 但它说明：**只看「整船体积增加了多少」无法验收球鼻艏**，必须像本轮这样先把球鼻艏
  单独成体（`new_body: true`）量出 `54,905,296.14 mm³`，再并回去；
- 如果设计中球鼻艏应当凸出艏柱，那么 TXT 的船体或球鼻艏 X 基准需要复核（本轮未改 TXT）。

### 13.3 最终几何状态

```
status                     ready
revision                   32
part_file                  frigate_txt_rebuild.prt.33
sha256                     a34adabc05e3c3bf9fbdc3317212e515c883facb05293e7c6ef75f28da76dc51
volume_mm3                 5919802387.113947
center_of_gravity          (4212.560267701836, -0.6428556800403801, -89.90239811799984)
bodies                     4 个对象 / 1 个带材料（body 77，607 面）
bbox                       x 0→8560 / y ±690 / z -910→1920
saved_file_reloaded_and_verified   true
```

特征树（球鼻艏部分，`BULB0`–`BULB5` 已全部 tombstone）：

```
9263 SEC_X64_PLANE   9265 SEC_X64     9271 SEC_X66_PLANE   9273 SEC_X66
9279 SEC_X68_PLANE   9281 SEC_X68     9287 SEC_X70_PLANE   9289 SEC_X70
9295 SEC_X72_PLANE   9297 SEC_X72     9303 SEC_X74_PLANE   9305 SEC_X74
9311 SEC_X76_PLANE   9313 SEC_X76
9333 BBL_HALF_MIRROR 9340 BBL_MERGED
9353 CAP_X64_PLANE   9355 CAP_X64      9362 CAP_FILL        9383 BBL_CAPPED
9389 BULB_SOLID (protrusion)            9393 HULL_WITH_BULB
```

> 遗留：`quilt 9327 / 9338 / 9381` 仍留在模型里作为 `BULB_SOLID` 的父引用，**不能删**
> （删掉会连带删掉球鼻艏实体）。`9338` 是镜像产生的冗余引用，见 P2-8。

### 13.4 结论边界（不要越界宣称）

- ✅ 可以说：球鼻艏已按 TXT 的 7 截面（不等距）+ 尖点，用**原生曲面能力**建成
  （放样 → 镜像 → 合并 → 填充封盖 → 合并 → 实体化 → 布尔并回），
  体积与独立验收件一致到 **1.7e-7**，11 个作业全部 save/reload 校验通过。
- ❌ 不能说：`surface_loft` 的元素树路线已修好 —— 它仍然恒 `-18`／`extract_code -18`；
  本轮走的是 `resident_panel` 面板路线，**且要求模型是 GUI 里交互式打开的活动窗口**。
- ❌ 不能说：`solidify` 可以用合并结果的 label 引用 —— 仍然必须用 `{kind:"quilt", id:N}`（P0-1 未修）。
- ❌ 不能说：worker `disconnect` 崩溃已修 —— 本轮只是靠「拆成 11 个单步作业」绕开（P0-2 未修）。
