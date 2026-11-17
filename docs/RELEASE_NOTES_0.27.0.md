# MCP_CREO_MechDog 0.27.0

一句话：把大件 STL 导出从「崩溃或超时」推进到「可完成且可量化偏差」，同时补上作业取消/停滞看门狗、圆柱面拆半的显式选面方式与区域切除的输入适配层；精度余项、装配与目标机验证仍明确留在下个版本。

- 类型：MINOR（新增公开工具 `creo_cancel_job`、`stl_options`、`region` 等可选输入与回执字段；无破坏性改名）
- 日期：2026-11-17
- 公开工具：**109 个**（108→109，新增 `creo_cancel_job`）
- 上一版本：0.26.0
- 主台账：[BACKLOG](BACKLOG.md) · 发布记录：[RELEASE-0.27.0](validation/RELEASE-0.27.0.md) · 工作卡：[BUG-130](work-items/BUG-130.md)、[BUG-131](work-items/BUG-131.md)

## 对外可见变化

### 1. STL 逐面导出与参数域细化（BUG-130）

- `creo_export_model(format="stl")` 默认走逐面导出：活动实体逐面剖分、SDK 法向对齐、0.001mm 焊点、边界环质心补洞、1e-9mm 精确邻接绕序修复、流式写盘与校验后原子发布；官方文件导出保留 `MECHDOG_STL_OFFICIAL_FILE=1` 诊断。
- 新增可选 `stl_options`：`chord_height_mm`（默认 0.05）与 `angle_control`（默认 0.1），仅 STL 接受；未知键、布尔、NaN/Inf 与越界在提交前拒绝；回执同时给出 `requested` 毫米值与 `passed` 原生值，逐面回执含 `surface_facets`。
- 新增只读参数域拆分：取剖分顶点 UV 后对超差三角形做 red-green 细化，只拆内部边、裁剪边界保持 SDK 顶点，新顶点经 `ProSurfaceXyzdataEval` 落回原生面。默认 25 万新顶点预算逐面分配，偏差抽样改为逐面步长。
- 实机：`bulb_bulged` 737,984 片、150,658,502 字节、194 秒，最大抽样偏差 **0.0899mm**、p99 0.0584、平均 0.0125，边界边/非流形/零面积为 0，体积与原生差 0.00004%，trimesh 复核 `is_watertight=true`、`is_winding_consistent=true`、`euler_number=2`。

### 2. 作业取消、停滞看门狗与新装配收尾（BUG-131）

- 新增公开工具 `creo_cancel_job`：取消不改变已完成几何，也不承诺自动回滚；终态如实记录 `cancelled` / `unknown_outcome` 与 `geometry_may_have_changed`。
- worker 日志停滞看门狗在零增长超过预算后终止 worker，并记录 `stall_watchdog`（budget/silent/log_bytes/termination）；`revision==0` 的新装配可用 `abandon_new` 收尾。
- 实机：worker 启动前取消返回 `cancelled`、`geometry_may_have_changed=false`；启动后取消返回 `unknown_outcome`、`true` 并记录终止 pid；1 秒预算 + 500 圆孔重计划触发看门狗并成功收尾。

### 3. 圆柱面拆半的选择与报错分型（BUG-132）

- 面选择器报错分零命中、多个同类面与类型不符三类，逐项列出 `id (plane|cylinder)`，并说明 `radius_mm` 只过滤圆柱半径、不是面类型过滤器。
- 新增显式 `coaxial:"any"`：只接受面选择器且必须带 `radius_mm` 与 `axis`，仅 `insert`/`concentric` 可用；多个圆柱命中时确定性取最小 id 并记录 `coaxial_any`/`matched_ids`/`matched_types`；默认唯一性、`mate`/`coincident` 不放宽。
- 实机（Creo 12.4.0.0）：R27.5 通孔拆成 102/103 两个半面，默认 insert 拒绝并列出两 ID；`coaxial:"any"` 的 insert+mate `committed`、`underconstrained=false`、轴共线，显式保存重载 revision 5→6。

### 4. 区域切除的输入适配层（FEAT-069，部分交付）

- `ExtrudeOp.region` 按边界签名在计划内唯一匹配，命中后把闭环实体原样复制成派生草图，由 `generic_bridge.submit` 在准入前替换，回执新增 `region_adaptation`。
- 源草图必须是坐标草图，且只支持简单闭环；原生「直接选中已有区域」仍未开放，区域切除能力不因此解禁。

### 5. 放样准入改用同 worker 实测身份（BUG-122）

- 新增 `bridge.surface_loft_admission_identity()`：只合并同一 worker SHA 的已落盘运行观测，`generic_bridge.submit()` 在取得通道、创建 job 之前使用该身份，与能力披露保持一致；跨 worker 或未知观测维持旧准入。
- 同 worker 已知元素树抽取失败会在占用通道前拒绝，不再创建空壳后回滚；保护修复不等于球鼻艏成型成功。

### 6. G2 曲率连续圆角实机（DEV-090）

- `RoundOp` 新增可选 `curvature_continuous`（默认关闭，旧行为不变）。
- 本机 Creo 12.4.0.0 方块实体边对照：R5/R30 与 `curvature_continuous` 四条用例全部 `committed` 且保存重载通过；R5 去除 `107.3015→80.0793 mm³`，R30 `3862.8331→2883.2442 mm³`，G2 表面不是圆柱面、半径回读为请求值。
- 曲率连续性本身未测量；凹边、变半径与多边组合未验。

### 7. 首壁宽度映射与同名会话残留裁定（BUG-129、BUG-106）

- [REFERENCE_SYNTAX](REFERENCE_SYNTAX.md) 明确 `width` 映射 XY→+Y、XZ→+Z、YZ→+Z，并写明回执只断言、不旋转；`width_axis` 旋转控制另立条目，未静默实现。
- BUG-106 离线裁定**不纳入** `adopt_session_copy`：一致性判定、受管身份改写与审计边界尚未冻结，现有两步恢复文案已覆盖可恢复路径；只剩真实同名外部模型的 save/erase 实机复测。

### 8. 导出诊断归档（BUG-020，已归档）

新增 `creo_mechdog.export_artifacts`：作业终结时只把本作业 `output` 中名称含 `_out.log` 的 Creo 诊断摘录移动到 `output/diagnostics/`，结果新增 `export_artifacts`/`export_diagnostics`/`export_diagnostics_note`，不移动或删除 `.stp/.igs/.stl` 与调用方文件。本机 Creo 12.4.0.0 实机 STEP 导出通过（`.stp` 8622 字节、`ISO-10303-21`、保存重载 true），条目已移入[完成档案](BACKLOG_COMPLETED.md)；该 ID 无独立工作卡，不列入逐 ID 表。

## 行为变化与升级注意

1. STL 默认路径变了：默认使用逐面导出，官方文件导出只在显式诊断开关下启用；大件输出片数和文件体积会明显增加。
2. `stl_options` 只对 STL 生效，传其它格式会被拒绝；不传时保持 0.05mm / 0.1。
3. `creo_cancel_job` 是异步控制工具：取消成功不代表几何回滚，`unknown_outcome` 仍按既有保护处理。
4. `coaxial:"any"` 只放宽 insert/concentric 的多圆柱命中，其它关系与默认唯一性不变。
5. 本版修改 `native/generic.cpp`、`native/stl_export.h`、`native/geometry_selectors.cpp`、`native/advanced.cpp` 等原生文件，升级后必须重编译 worker（`bridge.py build`）。
6. 种子库 `compatible_server_version=0.27.0`，与 0.26.x 的种子包不通用。

## 验证

- 离线：`tools/dev_check.py` 单测 3810 项通过（0 失败/0 错误/0 跳过）、`lint_findings=0`、`unformatted_files=0`；`bridge.py build` 退出码 0。
- 原生单测：`tests/native/test_stl_export.cpp` 24 项、`test_stl_file_check.cpp` 11 项、`test_stl_mesh_check.cpp` 12 项。
- 实机（本机 Creo 12.4.0.0，用户当次授权）：BUG-130 两件闭合导出与参数域细化、BUG-131 取消/看门狗、BUG-132 选择器与 insert+mate、DEV-090 G2、BUG-020 STEP 导出，均记录作业号与保存重载结果；证据见各工作卡与 `build/live_*` 报告。
- 发布资料：`tools/check_release_records.py --version 0.27.0` 与 `tools/package.py` 的四附件/发布记录门禁通过。

## 仍未验（本版不声称）

- 旧 14m 球鼻艏：默认预算最大偏差 0.1559mm、加大到 50 万顶点 0.1115mm，均未达 0.1mm；需更多顶点或先优化 ASCII 写出。
- 装配件的逐面/细化 STL、Creo 9/10 的 STL 与选择器路径、官方文件路径在同质量下可完成性。
- BUG-131 的 23 组件挂死根因（需 Creo 10 栈/轨迹）与 `revision==0` 新装配实机复现。
- BUG-132 的 Arm7 原半圆柱与 Creo 10 对照。
- FEAT-069 的原生选区创建、实机去料与 Creo 10。
- BUG-122 的 Creo 10 第二次提交无空壳与 WorkBuddy 黑盒。
- WorkBuddy 黑盒、非 mm 单位与本机之外的环境未复测。

## 源码包与校验

本版发布四个附件（逐个列出，不使用通配）：

- `MCP_CREO_MechDog-0.27.0-source.zip`
- `MCP_CREO_MechDog-0.27.0-source.zip.sha256`（源码包摘要记录在同名 sidecar 中，一行 `<64 位 SHA256>  文件名`）
- `MCP_CREO_MechDog-0.27.0-seed-library.zip`
- `MCP_CREO_MechDog-0.27.0-seed-library.zip.sha256`（种子包摘要同样在 sidecar 中）

- 种子包：24 个文件、9 个种子，SHA256 `72cdd8053298981b7fc9ac6665bb66033b9f91daacd4194d3360d2bc0389b36f`，见[发布记录](validation/RELEASE-0.27.0.md)与 `docs/seed_package.json`。
- Release：<https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.27.0>
- 发布后核对：发布后执行，当前未验证；`docs/releases/0.27.0.json` 的 `remote_verification` 在打包时为 `pending`，远端列表、标签指向与附件摘要只追加到 `main` 的 [POSTCHECK](development/RELEASE-POSTCHECK-2026-11-07.md)。

## 升级

1. 覆盖源码后运行 `python bridge.py build` 重编译 worker（本版含原生修改）。
2. 种子库换成本版 `seed-library.zip`（`compatible_server_version=0.27.0`）。
3. 大件 STL 若仍需要更高精度，先确认作业时限与磁盘空间，再评估是否提高 `stl_options.chord_height_mm` 或等待下个版本的预算/写出优化。
