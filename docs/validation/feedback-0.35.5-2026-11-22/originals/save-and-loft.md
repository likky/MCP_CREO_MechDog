# 2026-11-22 · CREO 10.0.0.0 · MCP_CREO_MechDog 0.35.5 · 核心问题

> 环境：CREO Parametric 10.0.0.0（release_numeric = 42），MCP_CREO_MechDog **0.35.5**，Toolkit 已连接，mmns 模板，Windows。
> 任务：仅通过 `MCP_CREO_MechDog` 打开 CREO，按一份纯文本自然语言说明（约 1600 行）从零重建一条简化护卫舰（81.5 m × 13.8 m × 25.4 m，含船体、外飘、开孔、上层建筑、桅杆、直升机甲板等 65 个特征）。
> 结论：最终 65 个特征一次性建成并 `saved_file_reloaded_and_verified: true`，但**过程中被 4 个阻塞级缺陷反复打断**，实际耗时是本该有的 8～10 倍。

---

## 0. 一句话摘要（按危害排序）

| # | 核心问题 | 危害 |
|---|---------|------|
| **P1** | **每个模型只能成功保存一次**：第 3 次 `ProMdlnameBackup` 必定返回 -1 | 多步建模被物理禁止，只能"一个模型 = 一个巨型计划"，任何一处失误整舰重来 |
| **P2** | 保存失败后**模型永久锁死**：`restore_baseline`/`accept_live` 全部在同一处失败，会话内模型无法复位 | 失败代价 = 丢弃整个模型，无任何可用的退出通道 |
| **P3** | `b_spline` 草图做切除时"切不掉任何材料"，报错却指向"检查草图位置/方向/深度" | 误导性诊断，浪费 4 次整舰重建 |
| **P4** | `loft`（Blend）、`surface_loft`、`creo_new_loft_part` 三条放样路径在 Creo 10 全部不可用 | 文本要求的"两截面/多截面放样船体"无法实现，只能用拉伸+拔模近似 |
| P5 | `creo_reconcile_model` 的 `expected_pending_job_id` 传 JSON `null` 被适配层变成 `''` 并拒绝 | 恢复流程第一步就卡死 |
| P6 | `creo_erase_session_models` 拒绝清理 MCP 托管模型；也没有"把托管模型从磁盘重新载入会话"的工具 | 会话内模型一旦脏掉就无解 |
| P7 | `feature_state delete` + 保存 = 模型损坏 | 无法用"删特征重做"的方式迭代 |
| P8 | `draft` / 切除无法引用**同一计划内**新建特征的面（只能写死 surface id） | 迫使调用方猜 id，重构计划即失效 |

---

## 1. P1（阻塞级）每个托管模型只能成功保存一次

### 现象
同一个 `model_id` 上，第 1、2 次保存成功，**第 3 次及以后必定失败**：

```
Toolkit call ProMdlnameBackup(board, destination) failed with code -1 during save_and_reload
save_failure: {
  "call": "ProMdlnameBackup", "code": -1, "stage": "verify_model_save",
  "destination": "probe_z7.prt", "source_checkpoint": "probe_z7.prt.3",
  "source_checkpoint_readable": true,
  "candidate_files": ["probe_z7.prt.1","probe_z7.prt.2","probe_z7.prt.3"]
}
```

### 复现（最小用例，与几何无关）
| 步骤 | 模型 | 结果 |
|---|---|---|
| `creo_new_part` | probe_z7 | ✅ `probe_z7.prt.2` |
| 计划 A：矩形草图 + 拉伸 50 | probe_z7 | ✅ `probe_z7.prt.3`（保存成功） |
| 计划 B：圆 Ø40 + 对称切除 200 | probe_z7 | ❌ `ProMdlnameBackup -1`（**切除本身成功**，removed 62831.85 mm³） |

同一现象在 4 个模型上 100% 复现：`bfeba6e7…`、`aa03c274…`（未走到第 3 次保存）、`c2b0fb4b…`（draft 那一次）、`d3422abf…`、`df030df3…`。

### 已排除
- 不是版本文件数量上限：删掉 `.prt.1/.prt.2` 只留 `.prt.3` 后重试，仍然 -1。
- 不是磁盘权限/占用：目录可写，`source_checkpoint_readable: true`。
- 不是几何问题：同一个 probe_z7 上，仅"圆孔切除"这一步就触发；而完全相同的保存调用在前一次是 0。
- 不是版本/路径长度/中文路径。

### 危害
这条限制把 API 的语义从"增量建模"降级成"**一次成型**"。本次任务的 65 个特征必须塞进一个 26 KB 的计划文件，一次性提交、一次性成功；否则整船重来。实际为此重建了 4 次整舰（每次 ~7 分钟 + 65 个特征全部重算）。

### 建议
1. 保存前先 `ProMdlErase` 会话副本，或改用 `ProMdlSave` + 显式版本重命名，避免复用已 rename 过的 backup 路径；
2. 若 `ProMdlnameBackup` 返回 -1，抓取 `ProTK` 的 `ProError` 明细（当前 `pro_error: -1` 无下文）并给出可执行的下一步；
3. 至少让 `save_and_reload` 失败**不至于**让模型进入不可恢复状态（见 P2）。

---

## 2. P2（阻塞级）保存失败后模型永久锁死，两条恢复通道都走同一条坏路

### 现象
`save_and_reload` 失败后 `status: failed`，此后：
- `creo_execute_plan` → `Model is not ready; inspect its last job before recovery`
- `creo_save_model` → 同上
- `creo_reconcile_model(action=restore_baseline)` → `failed_stage: recovery_verify_source`，`Regeneration produced a failed, suppressed or incomplete feature`，最终 `unknown_outcome` / `native_outcome_unconfirmed`
- `creo_reconcile_model(action=accept_live)` → `failed_stage: recovery_save_and_reload`，**同一个** `ProMdlnameBackup -1`，同样 `unknown_outcome`

证据作业：`3cf170be…`（restore_baseline）、`06c976477e…`（accept_live）、`13d9017e…`（probe 上的 accept_live）。

### 关键矛盾
`recovery_verify_source` 报的错是"**Regeneration 产生失败/压缩/不完整特征**"，但同一时刻用 `live=true` 做的只读检查明确显示：

```
live.inspection_summary: { healthy: true, has_solid: true, volume_mm3: 4377544308139.5,
                          counts: { features: 9, surfaces: 29, edges: 77, bodies: 1 } }
features: HULL_FLARE status=0 incomplete=false
```

即**模型是健康的**，失败来自"从磁盘 restore"这条路径本身（高度怀疑：会话里已存在同名模型，`ProMdlRetrieve` 静默复用内存副本，而撤销又要求它回到文件中没有的特征数）。

### 危害
- 任何一次保存失败 = 该 `model_id` 报废，只能新建模型从头再来（本次因此产生 6 个废弃模型：`7e997c28`、`0a24d3db`、`bfeba6e7`、`c2b0fb4b`、`df030df3`、`d3422abf`、`e68beefb`…）。
- `rollback_difference` 里的 `before/after` 在这种场景下是**误导**的：`before: 8, after: 9`（added 193）其实说明"回滚根本没发生"，而不是"回滚失败"——后者才是事实。

### 建议
1. `restore_baseline` 先 `ProMdlErase` 再 `ProMdlRetrieve`，或改用 `ProMdlnameCopy` 到临时名再打开；
2. 提供 `action=reload_from_disk`（擦除会话副本 + 只读打开），这是唯一能把脏会话救回来的动作；
3. 恢复路径不要把 `ProMdlnameBackup` 作为验证手段（P1 已证明它脆弱）。

---

## 3. P3（阻塞级 + 误导诊断）`b_spline` 草图做切除 = 切不掉材料

### 复现
按文本 A21 段：艉底抬升切除，轮廓 = 直线 `(0,-6.6)→(30,-6.6)` + **3 次非周期样条**（控制点 `(30,0,-6.6) (12.30505408,0,-6.6) (2.3333333333,0,-5.1) (0,0,-5.1)`）+ 直线 `(0,-5.1)→(0,-6.6)`，XZ 平面、沿 Y 对称贯穿 30 m。

```
sketch: entities 3, native_section.closed_contours: 1, open_ends: 0
        （Creo 侧认为轮廓是闭合的）
extrude: mode=cut, direction=symmetric, depth=30000
→ "Extrude cut removes no material ... Sketch origin (mm) = (0,0,0); normal = (-0,-1,-0);
   direction sign = -1. Effective depth 30000 mm spans [-15000, 15000]"
cut_geometry_context.volume_mm3: { before: 4377544308139.5, after: 4377544308139.5, removed: 0.0 }
```

**把同一条曲线按贝塞尔公式采样成 21 段折线、其余完全不变，同一次切除立刻成功**（同一模型、同一平面、同一深度）。
另外，同一会话里"XZ + symmetric 切除"本身是正常的（probe_d4：三角切除 removed 58333.2 mm³），所以不是平面/方向/深度问题。

### 危害
- 报错把责任推给调用方（"检查草图位置、方向、深度"），实际是 `b_spline` → 切除这条组合不通；
- 由于 P1/P2，这次"切不掉"直接导致两次整舰重建；
- 更隐蔽的是：剖面在 **analytic 侧被标为 `unsupported`**（`categories.unsupported: 1`、`solver.selection_reason: "unsupported_coordinate_entity"`），但流程仍然继续走到建成特征，最后以"移除 0 材料"收场。

### 建议
1. 计划准入阶段就把"含 `b_spline` 的切除轮廓"标为**不支持**并拒绝（而不是建完特征再说没切到）；
2. 或者在内部把 `b_spline` 自动离散为折线/`spline`（插值点）再交给 Creo；
3. 报错文本改为："轮廓虽被 Creo 判为闭合，但切除体积为 0，可能是 NURBS 剖面未被内核采纳"，并附 `material_area_mm2` 与轮廓包围盒。

---

## 4. P4（阻塞级）三条放样路径在 Creo 10 全部不可用

文本第 311–313 行要求"建立 Z=0 与 Z=-6.6 两个封闭轮廓，放样成主船体"。实际三条路都断了：

| 路径 | 结果 |
|---|---|
| `creo_execute_plan` + `loft` | `callback_preflight` 失败：`BLEND_CALLBACK_SETUP_REQUIRED`（需要常驻 DLL 回调，部署在 `D:\MechDog-BUG120\build\blend_callback\…`，本会话不可用） |
| `creo_execute_plan` + `loft` + `new_body:true` | 直接拒绝：*"Direct Blend supports solid add into the default body only; cut, surface and new_body are not accepted"* |
| `creo_new_loft_part`（免回调种子路线） | 第 1 次 `loaded_blend_validation`：`ProMdlCurrentGet → -8`；第 2 次：`-2 Cannot read seed Blend edit references`；**成功的那次生成的实体体积只有 7000 mm³（种子自带的 10×10×70 方块），传入的 7 个截面完全没生效** |
| `creo_execute_plan` + `surface_loft` | `create_code = 0`（特征建出来了），但 `extract_code = -18` → `SURFACE_LOFT_EXTRACT_UNSUPPORTED`；随后 rollback 失败，模型 `status: failed`、`has_solid: false` |

### 建议
1. `loft` 若必须依赖常驻回调，应在 `creo_capabilities` 里**明确标为不可用**，而不是等到提交后 `callback_preflight` 才失败；
2. `creo_new_loft_part` 必须校验"生成实体体积 ≠ 种子体积"，否则这是**静默错误**（返回成功、几何是错的）；
3. `surface_loft` 在 Creo 10 上 `ProFeatureElemtreeExtract` 返回 -18 是已知内核缺陷，应在版本探测后自动降级为"截面折线 + 拉伸/拔模"，而不是建完再回滚失败。

> 本次最终用 `拉伸 6600 + 拔模 36.0274°（neutral = 甲板面）` 近似外飘船体，体积 4.3775e12 mm³，底缘收敛到 ±2.1 m，与文本一致，但这是**替代方案**，不是放样。

---

## 5. P5（阻塞级，低级但致命）`expected_pending_job_id` 的 `null` 被适配成空串

```
creo_reconcile_model(model_id=…, mode="apply", action="restore_baseline",
                     expected_revision=1, expected_pending_job_id=null)
→ expected_pending_job_id must be the pending job id returned by inspect,
  or null when inspect returned pending_job=null; received ''
```
工具描述明确写"Send JSON null (or omit the parameter)"，但 MCP 传输层把 `null` 变成了 `''`，而服务端又只接受真正的 `null`。**唯一可通过的写法是彻底省略该字段**，这与"必须与 inspect 结果一致"的语义自相矛盾。

### 建议
服务端把 `''` 归一化为 `None`（一行代码），或 schema 用 `str | None` + `BeforeValidator(lambda v: v or None)`。

---

## 6. P6（阻塞级）会话内模型脏掉之后没有任何清理手段

- `creo_erase_session_models`：`targets qualify only when … not MCP-managed`，因此**托管模型永远无法擦除**（提示 "Managed models stay with creo_reconcile_model"）。
- 而 `creo_reconcile_model` 的两条 action 又都失败（P2）。
- 也没有"把某个 `model_id` 的 `.prt.N` 重新载入会话"的工具：`creo_open_file` 明确"Same-name/same-type session models cause rejection"。

结果：一旦 P1 触发，唯一出路是新建一个不同名字的模型（本次被迫用了 `frigate`、`frigate_main`、`frigate_v2`、`frigate_v3` 四个名字）。

### 建议
提供 `creo_reload_model(model_id)`：`ProMdlErase` 同名会话对象 → `ProMdlRetrieve` 最新 `.prt.N` → 只读校验 → 允许后续写入。这是整天都在缺失的那一个动作。

---

## 7. P7（阻塞级）`feature_state delete` + 保存 = 模型损坏

```
1) feature_state: delete hull_flare  → 成功
2) 重新加 draft                      → 成功（几何也对了）
3) save_and_reload                   → ProMdlnameBackup -1，feature id 193 → 383
```
即"删掉一个特征再补一个"这种最基本的迭代手法不可用。加上 P1/P2，等于**计划一旦提交就不可修改**。

---

## 8. P8（设计缺陷）同一计划内无法引用新建特征的面

`draft` 只接受 `surfaces: [{kind:"surface", id:N}]` + `neutral_plane: {id:N}`，而 N 是**模型内已存在的面 id**。于是：
- 想在"拉伸 → 拔模"同一个计划里做外飘，只能**预先猜** id。本次实测 Creo 10 对同一轮廓的 id 分配是确定的（132,134,…,184 / neutral 76），所以猜对了两次；但这是运气，不是契约。
- 一旦在前面插入/删除一个特征，全部 id 位移，计划立刻失效（`feature_state delete` 之后 id 从 193 变 383 即为例证）。

### 建议
允许按**特征标签 + 面角色**引用，例如
`surfaces: {feature: "hull_body", faces: "side"}`、`neutral_plane: {feature: "hull_body", face: "start"}`，
由服务端在计划内解析成实际 id。这是让"自然语言 → 计划"真正可组合的前提。

---

## 9. 其他问题（不阻塞，但影响体验/可信度）

1. **`creo_get_job` compact 会把关键诊断截断**：`sketch` 记录被标 `detail_truncated: true`，`profile` / `native_section` / `geometry_deviation` 全部消失，只能翻 `detail="full"` 的分页（`section="operations_result"`，每页 32 KiB）。排查 P3 时必须翻 3 页才看到"closed_contours: 1"。
2. **`h_mark` 多轮廓校验的报错很好**（`[intersecting] contours whose boundaries cross (h_bar1_1/h_cross_3)`），但它把"H 形三段矩形共边"这种**完全合法**的建模意图也拒了——`tangent` 与 `intersecting` 的判定过于严格，应允许"共边可合并"的多轮廓，或直接提示"请合并为单一折线"。
3. **闭合容差语义不一致**：schema 声称 Creo 约 1e-6 mm 可焊合，实测两段圆弧在 **1.51e-7 mm** 间隙时仍被判"structurally open ... no candidate join exists inside the 1e-04 mm diagnostic scale"。诊断尺度（1e-4）与焊合尺度（1e-9）差 5 个数量级，导致"看起来完全闭合"的轮廓被拒。
4. **`preview.jpg` 可读性差**：800×600 的线框/浅着色图，模型占画面 1/3，很难判断上层建筑是否成功（本次必须靠 `bodies.bbox` = `[[0,-6900,-6600],[81500,6900,18800]]` 才能确认桅杆建出来了）。建议提供等轴测 + 正视 + 俯视三视图，或允许指定视角/分辨率。
5. **`loft` 的 `sections` 上限 20、`surface_loft` 3 段以上强制 `interpolation="smooth"`** 这类约束只写在 schema 注释里，报错时不复述，容易被忽略。
6. **`creo_erase_session_models` 的 inspect 需要 `creo_list_session_models` 的清单**，但后者返回的字段名与 targets 需要的 `{name, model_type}` 不完全一致，需手工映射。

---

## 10. 本次实际可用的最小能力集（供参考）

在 Creo 10 + 0.35.5 上，**稳定可用**的组合只有：

```
sketch(plane=XY|XZ|YZ, offset, entities=[line | arc | circle | polyline])
extrude(mode=add|cut, direction=positive|negative|symmetric, depth, depth_type=blind)
draft(angle, surfaces=[id], neutral_plane={id}, flip)   ← id 需预知
```

65 个特征（船体、外飘、7 组开孔、12 层上层建筑、6 段桅杆、横翼平台、圆台、直升机甲板 + H 标记）全部由这三种算子堆出。**能做的事不少，但每一步都要绕开 P1/P2 的雷区**。

---

## 11. 给作者的最小修复优先级

1. **P1 + P2**：让保存可重复；保存失败必须能回到 `ready`（`creo_reload_model`）。
2. **P3**：`b_spline` 切除要么禁用、要么内部离散化；报错别再指向"位置/方向/深度"。
3. **P4**：`capabilities` 如实上报 `loft/surface_loft/loft_part` 在本版本不可用，并给出替代建议。
4. **P5**：`''` → `None` 归一化。
5. **P8**：按标签引用面，替代裸 id。

修完 1、2 两项，本次任务的实测耗时预计从 ~4 小时降到 ~40 分钟。

---

### 附：本次任务的关键作业 id
| 用途 | job_id |
|---|---|
| 成功建成整舰（65 特征） | `49bb0adeb7bb482092f5b2eddeee7d6e` |
| 首次整舰尝试（b_spline 切除失败） | `999ecff58a884ab99656bca12fa0a268` |
| 整舰尝试 2（同样失败） | `12faabbfa89842c397be6cceaaa0b3fd` |
| 保存失败最小复现（probe_z7） | `6084ffc7eb1e4ba8b849ef3155d9abe8` |
| restore_baseline 失败 | `3cf170be6dbe40a485b57edb5a357ff6` |
| accept_live 失败 | `06c976477e064532be7847d57a0e5c18` |
| surface_loft extract -18 | `938e1693a5b9428f8591af85b938fe91` |
| Blend 回调缺失 | `callback_preflight`（`BLEND_CALLBACK_SETUP_REQUIRED`） |
