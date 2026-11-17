# 0.26.0 六项反馈完善计划

> **For agentic workers:** 按批次顺序执行；每批完成离线专项与统一检查后才进入下一批。原生构建与 Creo 连接须当次授权，不沿用历史授权。P1 的区域切除路线在取得原生选区证据前不得写成已可用。

**Goal:** 把 0.26.0 外部报告的六个问题按可验证顺序收口：先让 Arm7 的区域切除能消费真实 TXT 签名，再解决 23 组件带配合总装挂死后的取消与收尾，随后修正圆柱面选择器和钣金工具 schema 缺口，最后复核 G2。

**Architecture:** 保留 stdio → `server.py` → `bridge.py` → `generic_bridge.py` → C TOOLKIT。区域选择优先在 Python 输入适配层把「已有草图中的一个封闭区域」改写成单区域派生草图；原生选区创建只有在取得目标机的树/轨迹证据后才做。取消与看门狗在 worker 生命周期层实现，装配收尾在 `reconciliation.py` 扩展；几何识别和测量仍在原生端。

**Tech Stack:** Windows x64、Python 3.12 / Pydantic / unittest、C++17、Creo C TOOLKIT；本机 Creo 12.4.0.0 / 匹配 SDK，目标机 Creo 10.0.0.0（`release_numeric=42`）。

**Spec:** 0.26.0 反馈原件 `C:/Users/Administrator/Downloads/0.26.0/2026-11-16-CREO-0.26.0-Arm7区域切除契约可用但未接Extrude且全量配合总装挂死无取消能力.md`、[FEAT-069](../../work-items/FEAT-069.md)、[BUG-131](../../work-items/BUG-131.md)、[BUG-132](../../work-items/BUG-132.md)、[BUG-129](../../work-items/BUG-129.md)、[DEV-090](../../work-items/DEV-090.md)。

## 全局约束

- 长度毫米、角度度；label 规则沿用现有 schema；不新增公开工具除非确实需要（取消 job 是明确需要的一项）。
- busy 立即拒绝，不排队、不自动重交；保持 revision、检查点、回滚与 unknown 保护。
- 原生构建、Creo 连接、故障注入均须当次明确授权；不结束进程、不清锁/unknown、不修改用户模型。
- Creo 12.4 结果不外推 Creo 9/10；目标机结论只以目标机真实几何与保存重载为准。
- 既有 `docs/validation/` 原件不改写；新结论写工作卡与新计划。
- 本轮不改版本、不提交 main、不发布；提交与推送按用户逐次指示执行。

## 1. 基线与问题映射

2026-11-16 检出 `main`（`1ee56d9` 之后），源码版本 `0.26.0`，工作区仅保留 `.trae/` 与 `underwater_plan.json` 未跟踪。报告来自 Creo 10.0.0.0 实机；本机未连接 Creo 10，也未编译。

| 报告项 | 已核对的当前事实 | 归属与处理 |
| --- | --- | --- |
| P1 region_selection 可用但不接 Extrude | `region_selection` 对真实签名解析/唯一匹配通过；`ExtrudeOp.profile` 只接受 sketch 引用，原生无区域选区元素 | [FEAT-069](../../work-items/FEAT-069.md)：先做输入适配层单区域派生草图，再取证原生选区 |
| P2 G2 圆角未开放 | 本地未发布改动已加 `RoundOp.curvature_continuous`（默认关闭），Creo 12.4 实机 R5 通过 | [DEV-090](../../work-items/DEV-090.md)：补目标机与 TXT R30/R5 复测，不重做已完成部分 |
| P3 23 组件挂死且无取消 | 同 op 在 2 组件 9.4 秒失败、23 组件 60 分钟无进展；108 工具无 cancel；装配 unknown 后 reconcile 六动作全不可用 | 新增 [BUG-131](../../work-items/BUG-131.md)：取消、看门狗、装配收尾、进度观测 |
| P3-补 装配无法 reconcile | `restore_baseline/accept_saved/accept_live/abandon_new` 一律返回 "Assembly/drawing reconciliation is not supported" | 并入 BUG-131，先开放「新装配、零提交 revision」的显式放弃 |
| P4 方向断言只拒不改 | 断言与回执已交付；独立工具缺这两个参数 | [BUG-129](../../work-items/BUG-129.md)：本轮补齐独立工具 schema；`width_axis` 旋转控制另立 FEAT |
| P5 小问题 | 独立工具 schema 不一致；无取消；长轮询进度看不出死循环 | BUG-129（schema）、BUG-131（取消、进度停滞） |
| P6 圆柱面拆成两半 | base 198/200、hom 57/59、96/98、224/226；`center+radius+axis` 命中 2 面即拒绝；报错建议补 `radius_mm` 与实际成因不符 | 新增 [BUG-132](../../work-items/BUG-132.md)：候选类型分布、同轴多面策略、缺字段提示 |

## 2. 批次与依赖

| 顺序 | 批次 | 可先交付 | 进入下一步的条件 |
| --- | --- | --- | --- |
| A | P4-2 / BUG-129 | 独立工具 schema 对齐与专项测试 | 已在本轮完成离线部分 |
| B | P5-3 / BUG-131 | 进度停滞观测：扩大标记搜索、日志静默时长、重复行证据 | 已在本轮完成离线部分 |
| C | P1 / FEAT-069 | 区域签名 → 单区域派生草图的计划改写与测试 | 离线专项通过后再申请 Creo 12.4 实机；Creo 10 另测 |
| D | P3 / BUG-131 | `creo_cancel_job`、worker 停滞看门狗、装配 abandon_new | C 不阻塞 D；D 的实机须单独授权 |
| E | P6 / BUG-132 | 候选类型统计、报错分型、缺 `assembly_component` 提示 | 同轴多面放宽须目标机证据，不先默认放宽 |
| F | P2 / DEV-090 | G2 目标机复测与 TXT R30/R5 对照 | 需目标机与实机授权 |

## 3. 任务定义

### A. 独立钣金工具 schema 对齐（P4-2，BUG-129）

**Files:** `server.py`（`creo_sheetmetal_base_flange`）、`tests/unit/test_sheetmetal_base_flange.py`。

**做法:** 独立工具补 `expected_width_direction_world` 与 `width_direction_tolerance_deg`，仅在调用方给出期望方向时写入 op，保持旧调用 payload 不变。

**验收:** 断言到达 op；省略时字段不出现；`SheetmetalBaseFlangeOp` 原有拒绝规则不变。**状态：本轮已完成离线部分。**

### B. 挂死可观测性（P5-3，BUG-131）

**Files:** `src/creo_mechdog/native_stage.py`、`src/creo_mechdog/job_projection.py`、`tests/unit/test_native_stage.py`。

**做法:** 8 KiB 尾窗没有 `PHASE/PROGRESS/STAGE` 时，向历史扩读至 1 MiB 再判断；回执新增 `marker_source`、`marker_scan_bytes`、`log_age_seconds`，以及重复行 `dominant_tail_line`/`dominant_tail_line_count`（至少 3 次才报）。

**验收:** 刷屏把 `PHASE` 挤出尾窗仍能报出阶段；日志静默时长可读；一行重复刷屏被识别；正常日志行为不变。**状态：本轮已完成离线部分。**

### C. 区域切除接入（P1，FEAT-069）

**Files:** `src/creo_mechdog/schema.py`、新增适配模块（建议 `src/creo_mechdog/sketch_regions.py`）、`generic_bridge.py` 或计划归一化层、`tests/unit/test_sketch_regions.py`。

**路线:**
1. `ExtrudeOp` 增可选 `region`：`{signature_yz_mm, tolerance_mm?, sketch_frame?}` 或 `{match:{signature_yz_mm,...}}`，与 `sketch` 二选一；两者同时给出必须显式声明一致性检查。
2. 适配层从目标 `SketchOp` 的实体端点构造闭环，按 `region_selection.match_region` 唯一匹配；把该闭环实体原样复制成派生草图（同 frame、同控制点），再接拉伸切除。
3. 派生草图标注来源（父草图 label + 签名摘要），不修改原草图，不拼接近似曲线。
4. 原生选区（直接引用已有草图的某个区域）只在取得目标机 trail/mapkey 或官方依据后实现；不得用「全草图切除」冒充。

**验收:** 离线：三套真实签名唯一匹配、共享边界/歧义拒绝、派生草图实体逐项与源相同、计划 label 唯一。实机：Arm7 独立件按 `depth=3` 去料、未选区域保留、特征有效、保存重载与 revision 正确；Creo 10 另测。**依赖:** 完整 Arm7 计划输入与实机授权。

**状态（2026-11-16 离线）:** `sketch_regions.py` 与 `ExtrudeOp.region` 已实现，`generic_bridge.submit` 在准入前展开并回执 `region_adaptation`；24 项单测通过。源草图须为坐标草图（无 dimensions/constraints/weld_pairs），只支持简单闭环，圆/矩形/椭圆不可用签名表达；原生选区与实机未验。

### D. 取消与装配收尾（P3/P3-补，BUG-131）

**Files:** `server.py`、`generic_bridge.py`、`src/creo_mechdog/reconciliation.py`、`src/creo_mechdog/capabilities.py`、相应单测。

**做法:**
1. 新增 `creo_cancel_job(job_id)`：只对 `queued/running` 生效；请求标记 + 终止本作业的 worker 子进程；结果写 `cancelled` 或 `unknown_outcome`（取决于是否已提交几何），保留文件与 revision 证据；不可重复取消，终态直接返回当前状态。
2. worker 停滞看门狗：日志字节在显式预算内无增长（默认 600 s，可由作业参数覆盖）时终止 worker 并按未知结果收尾；阈值与来源写入回执，不自动降精度重试。
3. 装配体 `unknown_outcome` 收尾：对 `revision==0` 且无已提交几何的新装配开放 `abandon_new`/`ack_failure`，保留文件、归档 model 记录并释放 pending 预约；已有 revision 的装配仍保持现有限制。
4. 文档写明取消不等于回滚成功；取消后仍需 `creo_session_status`/`creo_reconcile_model` 收尾。

**验收:** 离线状态机与拒绝矩阵；实机在临时装配上验证取消、超时收尾、abandon_new 后 model_id 可重新使用；不得在用户模型上做故障注入。

**状态（2026-11-16 离线）:** `creo_cancel_job`（公开工具 108→109）、runner 侧日志停滞看门狗（`generic_stall_seconds`，默认 600 s，经 `native_owner.json` 定位并终止 worker）与 `revision==0` 无保存文件新装配的 `abandon_new`/`ack_failure` 出口已实现；新增 `tests/unit/test_job_control.py` 18 项。取消不等于回滚：worker 启动后取消记 `unknown_outcome` 并保留预约。实机取消/收尾与挂死根因未验。

### E. 圆柱面选择器（P6/P3-4/P3-5，BUG-132）

**Files:** `native/geometry_selectors.cpp`、`native/advanced.cpp`、`src/creo_mechdog/geometry_selectors.py`、`src/creo_mechdog/references.py`、单测与源文本回归。

**做法:**
1. 报错分型：零命中、多个同类面（列出 id 与类型）、命中类型不符（列出候选类型分布）；明确 `radius_mm` 不是类型过滤器。
2. 缺 `assembly_component` 时在 Python 预检直接指出缺失字段，而不是落到「0 个平面/圆柱面」。
3. 同轴多面：先提供显式选项 `coaxial: "any"`（仅 `insert/concentric` 可用），默认仍要求唯一；该选项的几何等价性须在目标机用真实半圆柱验证后再考虑默认放宽。

**验收:** 两半圆柱算例：默认拒绝且报错列出两个 id 与类型；显式 `coaxial:"any"` 插入成功；`mate/coincident` 不受影响。Creo 10/12.4 分别实机。

**状态（2026-11-16 离线）:** 三点均已实现：面选择器报错分为零命中/多面/类型不符，多面与类型不符均列 `id (plane|cylinder)`，并说明 `radius_mm` 不是类型过滤器；`require_constraint_surface_type` 在已给 `radius_mm` 时不再重复建议补半径；`AssemblyConstraint` 对组装侧选择器缺 `assembly_component` 直接点名拒绝。`coaxial:"any"` 仅 surface 选择器、必须带 `radius_mm`+`axis`，仅 `insert/concentric` 准入，原生仅在多个圆柱命中时取最小 id，默认唯一性未放宽；round/chamfer/flange 与其他操作一律拒绝。两个测试文件共 39 项通过。未编译原生、未连 Creo；半圆柱实机与保存重载未验。

**状态（2026-11-17 本机 Creo 12.4 追加）:** `bridge.build_native()` 通过（修掉 `near` 宏冲突）。100×80×20 方块 + R27.5 通孔把孔壁拆成 id 102/103 两个半圆柱；多命中、类型不符（列出 plane 53/58）、零命中三种报错均按新措辞输出，作业 `rolled_back`，证据 `build/live_bug132/20261117T090714_af80ee73/report.json`。随后用 R27.4×60 销件验证：默认 insert 拒绝并列出 102/103；`coaxial:"any"`（两侧）insert+mate `committed`、`underconstrained=false`、轴与孔轴共线，显式保存重载 revision 5→6，证据 `build/live_bug132_insert/20261117T012115_a6bb73/report.json`。Creo 10 与 Arm7 原半圆柱仍未验。

### F. G2 目标机复测（P2，DEV-090）

**Files:** 不改源码；沿用 `RoundOp.curvature_continuous` 与现有实机驱动。

**验收:** Creo 12.4 与目标 Creo 10 上，对 TXT Arm7 的 R30/R5 实体边分别验证特征提交、体积/圆角半径回读与保存重载；Curvature Continuity 的数值连续性另需独立测量，不以体积相近代替。

**状态（2026-11-17 本机 Creo 12.4）:** 用户当次授权启动/连接 Creo 12.4.0.0。Arm7 TXT/模型不在本工作区，改用 100×80×20 mm 方块竖直实体边的 R5/R30 对照：圆弧与 `curvature_continuous` 四条用例全部 `succeeded`、`effect_status=committed`、`saved_file_reloaded_and_verified=true`；R5 去除 `107.3015`→`80.0793 mm³`，R30 去除 `3862.8331`→`2883.2442 mm³`，G2 相对圆弧均少 25.37%，且 G2 表面不是圆柱面、半径回读仍为请求值（落在 `d12`），排除静默退化。曲率连续性未测量；Arm7 实体边与 Creo 10 目标机仍未验。证据 `build/live_g2/20261117T084440_82e59496/report.json`（SHA256 `30a00534…`）。

## 4. 本轮离线交付

- `creo_sheetmetal_base_flange` 补齐方向断言参数并保持旧 payload；新增两组测试。
- `stall_report` 增加扩窗标记搜索、`log_age_seconds` 与重复行证据；compact 投影同步放行新字段；新增 6 项测试。
- P1 适配层：`ExtrudeOp.region` + `sketch_regions.py` 派生草图展开，`generic_bridge.submit` 准入前接入并回执 `region_adaptation`；新增 24 项测试。
- P3 作业控制：`creo_cancel_job`、worker 日志停滞看门狗与 `revision==0` 新装配 `abandon_new`/`ack_failure` 出口；新增 18 项测试，公开工具 108→109。
- P6 圆柱面选择器：零/多/类型不符三种报错分型（列 `id (plane|cylinder)`）、组装侧缺 `assembly_component` 预检、仅 insert/concentric 可用的 `coaxial:"any"`；两个测试文件共 39 项通过。
- P2/G2 本机 Creo 12.4 实机：R5/R30 方块的圆弧与 `curvature_continuous` 四条用例全部 committed、保存重载通过；G2 去除体积均比圆弧少 25.37%，表面非圆柱，排除静默退化。Arm7 实体边与 Creo 10 未验。
- 本计划、BUG-131、BUG-132 工作卡与台账登记。

## 5. 未验证与风险

- 原生构建已在本机 Creo 12.4 实机复测时执行（`bridge.build_native()` 通过）；P6 的 `near` 宏冲突已修。未重放报告实验；除 G2 外，本轮其余结论仍为源码与离线检查。
- P1 的派生草图路线只保证「同一实体原样复制」；区域嵌套、共享边界的包含关系仍需完整 Arm7 输入验证。源草图若依赖尺寸/约束求解会被明确拒绝，不做静默降级。
- P3 的取消语义涉及进程终止与未知结果保护，必须先离线确定状态机，再申请实机；取消工具不承诺几何回滚。
- P6 的同轴多面放宽会改变唯一性语义，未取得目标机证据前保持默认拒绝。
- P2 的 G2 只用 100×80×20 mm 方块验证了 R5/R30 的提交、体积与保存重载；未测曲率连续性，Arm7 实体边与 Creo 10 目标机仍未验。
