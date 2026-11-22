# 开发入口

2026-11-22（0.35.6 发布）：PATCH，公开工具 110→111。0.35.0 反馈批收口。[FEAT-057](work-items/FEAT-057.md) 放开装配质量属性（体积/面积/几何重心/质量重心、只读 occurrence 扫描、有效平均密度标记，缺材料或扫描不完整即拒绝质量）；[FEAT-073](work-items/FEAT-073.md) 新增 `creo_get_mass_properties_batch`（1–16 模型、逐项 `error_kind`、预算截断，仍单通道串行）；[FEAT-072](work-items/FEAT-072.md) 增加 `session_candidates` 与进程内 `session_id` 选定；[BUG-143](work-items/BUG-143.md) 定位固体特征镜像挂死（`PRO_E_MIRROR_REF_ITEMS` 排除 `PRO_FEATURE`）并改为创建前拒绝；[BUG-145](work-items/BUG-145.md) 桌面 worker 去掉批处理编码依赖；[BUG-146](work-items/BUG-146.md) 增加 `stalled_recovery` 与 `abandon_stalled_recovery`；[BUG-147](work-items/BUG-147.md) 补材质密度失败归因；[BUG-148](work-items/BUG-148.md) 区分单个与多个开放轮廓。本机 Creo 10.0.0.0 / release 42 实机取证；干净树全量 4,376 项通过（6 跳过）。未验：缺材料/抑制/嵌套组件、混合密度真实质量、主惯量、完整 120 s 超时窗口、Creo 9/12 与 WorkBuddy 黑盒。发布核对见 [RELEASE-0.35.6](validation/RELEASE-0.35.6.md)。

2026-11-21（0.35.5 发布）：PATCH，公开工具仍 110。[BUG-144](work-items/BUG-144.md) 让 `tools/test_unit.py` 在运行前原子写本轮 `build/unit_test_run.json`（`run_id`、PID、源码身份、`O_EXCL` 锁），`release_integrity` 自本版起要求状态与报告共同支撑“全量通过”声明，`tools/package.py` 新增 `--source-root`/`--unit-report` 并把门禁前移到任何产物之前；[DEV-099](work-items/DEV-099.md) 让 README 工具数引用 `creo_capabilities.tool_count`；[BUG-142](work-items/BUG-142.md) 以断开延迟钩子实机核验被中断的 disconnect 保留 `unknown_outcome` 与预发布事实。发布核对见 [RELEASE-0.35.5](validation/RELEASE-0.35.5.md)。

2026-11-21（0.35.1 发布）：PATCH，公开工具仍 110。[BUG-142](work-items/BUG-142.md) 定位 `0xC0000409` 根因——构建命令缺 `/utf-8`，MSVC 按 CP936 解析窄字面量产生非法 UTF-8，严格 `dump` 抛异常并 abort；`bridge.py` 三条 `cl` 命令加入 `/utf-8`，并把 `NATIVE_BUILD_FLAGS /utf-8-v1` 纳入构建指纹，受控夹具复现退出码与 0 字节文件、替换 handler 后正常发布。[DEV-098](work-items/DEV-098.md) 为通用 `geometry_selector` 零匹配新增只读 `geometry_selector_diagnostic.nearest_edges`（≤5 条），本机 Creo 10 实机 `candidate_count=12`、`matched_ids=[]`、候选 ids 54/55/56/59/60。未验：0.32.0 原始模型、真实 disconnect 阻塞、Creo 12.4/9 与 WorkBuddy 黑盒。发布核对见 [RELEASE-0.35.1](validation/RELEASE-0.35.1.md)。

2026-11-21（0.35.0 发布）：MINOR，公开工具仍 110。桌面 `0.33.0` 三份反馈首批交付：[BUG-143](work-items/BUG-143.md) 曲面结果回执给出实测 `quilt_id`，同计划 merge/fill 标签可被 `solidify` 消费（本机 Creo 10 实机 785.3981633974481 mm³、保存重载通过）；[FEAT-071](work-items/FEAT-071.md) 新增 `d1_d2` 两距离倒角（实机 2/5 与 5/2 各去除 250 mm³）；[BUG-142](work-items/BUG-142.md) 断连前结果预发布与非 UTF-8 容错（实机复现 `0xC0000409`，根因未定位）；[BUG-140](work-items/BUG-140.md)/[BUG-141](work-items/BUG-141.md) 启动指纹惰性求值与已退出进程判断；[DEV-098](work-items/DEV-098.md) 诊断语义与文档契约。未验：Creo 12.4/9、WorkBuddy 黑盒、mirror/trim 标签实机消费。发布核对见 [RELEASE-0.35.0](validation/RELEASE-0.35.0.md)。

2026-11-19（0.29.0 发布）：MINOR，公开工具仍 109。[BUG-120](work-items/BUG-120.md) 把 Creo 10 `resident_panel` 的 candidate-3 升为公开认证 profile：第一方向 2—8 曲线或首/末单点、可选 2—8 条第二方向导线、最多 11 个位置；新增认证记录 `creo10-bbl-2026-11-19.json` 绑定 2+2、2+3、2+点、7+3 与两段式球鼻艏实体五组实机案例，并用 `require_panel_directions()` 把“profile 无第二方向槽却请求导线”改为提交前拒绝。**不认证**：单特征“7 曲线 + 点 + 3 导线”在 Creo 10 再生失败，点收敛段需作为共享末截面的第二个放样；真实船体非圆剖面映射未做。发布核对见 [RELEASE-0.29.0](validation/RELEASE-0.29.0.md)。

2026-11-19（0.28.0 发布）：MINOR，公开工具仍 109。[BUG-120](work-items/BUG-120.md) 的 Creo 10 `resident_panel` 边界混合路线完成认证与实机：认证 profile `creo10-bbl-candidate-2` 的 2—8 曲线放样、WorkBuddy 两轮黑盒（面板曲面链与半圆柱镜像/合并/封口/实体化，体积 6283.1853 mm³）；candidate-3 增加第二方向导线/末端单点与 11 位置票据上限，已验证 2+2、2+3、2+点、7+点、7+3 与两段式球鼻艏演示体实体化（体积 167543.67 mm³）。**未通过**：11 位置“7 曲线 + 点 + 3 导线”单特征在 Creo 10 再生失败，边界收窄为“末端基准点 + 任意导线”组合；真实船体剖面与非圆截面映射未做。发布核对见 [RELEASE-0.28.0](validation/RELEASE-0.28.0.md)。

2026-11-17（0.27.0 发布）：MINOR，公开工具 108→109。[BUG-130](work-items/BUG-130.md) 默认路径切为逐面 STL 导出并新增 `stl_options`，参数域细化把 `bulb_bulged` 最大抽样偏差降到 0.0899mm；[BUG-131](work-items/BUG-131.md) 新增 `creo_cancel_job`、worker 日志停滞看门狗与新装配 `abandon_new` 出口；[BUG-132](work-items/BUG-132.md) 增加 `coaxial:"any"` 与三类选择器报错分型；[FEAT-069](work-items/FEAT-069.md) 增加 `ExtrudeOp.region` 派生草图适配层；[BUG-122](work-items/BUG-122.md) 放样准入改用同 worker 实测身份；[DEV-090](work-items/DEV-090.md) 交付 G2 曲率连续圆角实机与 `curvature_continuous`；[BUG-129](work-items/BUG-129.md) 明确首壁宽度映射；[BUG-106](work-items/BUG-106.md) 裁定不纳入 `adopt_session_copy`；BUG-020 诊断归档实机通过并移入完成档案。旧 14m STL 精度、装配/Creo 9/10、挂死根因、原生选区与 Creo 10/Arm7 未验；发布核对见 [RELEASE-0.27.0](validation/RELEASE-0.27.0.md)。

2026-11-17（BUG-130 拆分曲面：参数域细化，bulb 偏差达标）：单面约 20.4 万片剖分上限无法靠更小弦高突破，[native/stl_export.h](native/stl_export.h) 增加只读的**参数域拆分**：`ProSurfacetessellationinputUvprojectionSet(PRO_SRFTESS_NO_PROJECTION)` + `ProTessellationParamsGet` 取每个剖分顶点 UV 并做 32 点往返自检；对超差三角形做自适应 red-green 细化，**只拆内部边**（边界计数 2），裁剪边界保持 SDK 顶点，邻面缝合/焊接/补洞/绕序流程不变；新顶点由边中点 UV 经 `ProSurfaceXyzdataEval` 精确落回原生面并同时取法向，中点偏离端点超过 `0.75×边长+弦高` 判为参数跨缝并拒绝。判据用顶点法向转角估计弦高 `sag≈L×turn/8`，不做逐片求值（实测约 2ms/次，20 万片/轮会超 600 秒；首版整轮扫描 job `85d2c5fe…` `unknown_outcome`，已按 BUG-074 用 `build/bug130_reconcile_unknown.py --apply-restore` 恢复基线）。预算默认 25 万新顶点，先统计活动实体面数再按“剩余预算/剩余面数”逐面分配，避免首个大面吃光；偏差抽样改为逐面步长 `facet_count/200`、上限 8000（旧实现按全件片序步长 500/上限 4000，细化后后访问的面零样本，此前 bulb 的 0.0648mm 只覆盖面 119）。实机：`bulb_bulged` job `cde4566f…` 737,984 片（368,215/368,241/557）、150,658,502 字节、194 秒，偏差最大 **0.0899mm**（原 0.1581mm，达成 0.1mm）、p99 0.0584、平均 0.0125，边界边/非流形/零面积 0，体积 `55,052,167,307` vs 原生 `55,052,144,699`（0.00004%），trimesh `is_watertight=true`、`is_winding_consistent=true`、`euler_number=2`；旧 14m 默认预算 job `dd659d80…` 0.1559mm（原 0.3086mm）/p99 0.0887，放宽 50 万预算 job `0ec3f531…` 0.1115mm/p99 0.0768，仍未达 0.1mm。诊断开关 `MECHDOG_STL_REFINE`/`_MIN`/`_MAX`/`_ROUNDS`/`_VERTICES`/`MECHDOG_STL_TRACE`，回执新增 `refine` 对象。`tests/native/test_stl_export.cpp` 24 项、`tools/test_stl_export.py`、`dev_check --work-item BUG-130` 全部通过；源件 SHA/revision 未变。

2026-11-17（BUG-130 逐面 STL 导出：两件闭合、流形、法向朝外、绕序一致）：[native/stl_file_check.h](native/stl_file_check.h) 流式验收 ASCII STL，[native/stl_export.h](native/stl_export.h) 提供官方文件导出与默认逐面 `write_stl_per_surface`（活动实体逐面 `ProSurfaceTessellationGet`、单面 input/tessellation/vertices/facets 各自释放、SDK 法向对齐、0.001mm 焊点、边界环质心补洞、**1e-9mm 精确邻接绕序 BFS 与整件体积定向**、流式写盘、uint64 片数/零面积统计、校验后原子发布），[native/stl_mesh_check.h](native/stl_mesh_check.h) 只借用 SDK 数组做计数/索引/有限值/预算检查；11 项 file、12 项 mesh、19 项 export wiring 单测与 native 构建通过。实机：小件官方路径 284 片/73,561 字节；旧 14m 官方路径 600 秒 `unknown_outcome`（Creo 约 10GB）；重启后按 BUG-074 契约恢复两个模型的基线成功。最终逐面导出 `bulb_bulged` 404,652 片/82,166,002 字节、旧 14m 197,722 片/40,068,497 字节，均 succeeded、源件 SHA 与 revision 不变；边界边 0、非流形边 0、零面积 0，有符号体积与原生差 0.0030%/0.0172%，包络一致；trimesh 5.2.1 独立复核两件 `is_watertight=true`、`is_winding_consistent=true`、`euler_number=2`。绕序修复若沿用 0.001mm 邻接会把 5e-4mm 近重合点误焊并掩盖 6 条同向共享边，故绕序阶段单独用 1e-9mm 邻接并保留原始角点坐标。官方文件路径保留 `MECHDOG_STL_OFFICIAL_FILE=1` 诊断。Task 6 已完成：`creo_export_model(format="stl", stl_options={"chord_height_mm":…, "angle_control":…})` 仅 STL 允许，未知键/布尔/NaN/Inf/越界在提交前拒绝，缺省保持 0.05/0.1，回执同时给出 `requested` 毫米值与 `passed` 原生值，逐面回执新增 `surface_facets`。抽样偏差实测（`MECHDOG_STL_DEVIATION=1`，顶点自检 ≤0.004mm）：bulb 平均 0.0367mm/p99 0.1378mm/最大 0.1581mm，旧 14m 平均 0.0814mm/p99 0.3002mm/最大 0.3086mm，≤0.1mm 目标未达成。根因是逐面剖分单面片数上限约 20.4 万：bulb 大面在 0.05 与 0.005mm 弦高下均约 204,000 片，而小件未到上限时 0.05→0.001mm 片数 328→1,488，弦高参数有效、不是会话缓存。受此上限约束，逐面路径无法把大面细化到 0.1mm 以内；装配、Creo 9/10 未测。

2026-11-17（BUG-130 诊断插桩，离线）：新增只读 `tools/diagnose_stl_export.py`，汇总既有 STL 作业的终态/退出码/最后 PHASE/输出字节与 SHA/源件记录哈希/worker 身份及 `STL_*` 阶段；两次失败与旧成功件生成 `build/bug130_evidence/summary.json`（SHA256 `63c936cb…`），两次均为 `0xC0000005`、最后 `PHASE=export`、STL 0 字节、整份日志 SHA 不同，旧成功件 48,847,489 字节。[native/generic.cpp](native/generic.cpp) 的 `write_stl` 增加立即 flush 的 `STL_TESS_*`/`STL_SURFACE_*`/`STL_FACET_BATCH`/`STL_FILE_*`/`STL_TESS_FREE_*`，并在解引用/写盘前检查空数组、坏计数、越界索引、非有限顶点与 IO 失败；异常路径 RAII 释放。新增 8 项证据单测。未构建、未连接 Creo，故障栈/dump 与根因仍未取得。

2026-11-17（实机批：BUG-020 STEP 导出 + BUG-131 取消/收尾/看门狗）：[BUG-020](BACKLOG_COMPLETED.md#legacy-bug-020) 在本机 Creo 12.4 真实导出 STEP：`.stp` 8622 字节且为 `ISO-10303-21`，`__out.log.1` 归档到 `output/diagnostics/`，结果含 `export_artifacts`/`export_diagnostics`，保存重载 true；BUG-020 移入完成档案，台账 193→192（BUG 86）。[BUG-131](work-items/BUG-131.md) 临时件实机：worker 启动前取消 `cancelled`、`geometry_may_have_changed=false`；启动后取消 `unknown_outcome`、`true` 并记录终止 pid；两种均经 `abandon_new` 收尾。当次授权下用 1 秒预算 + 500 圆孔重计划触发看门狗，日志 2 秒零增长后终止 worker，`stall_watchdog` 记录 budget/silent/log_bytes/termination，`abandon_new` 收尾成功，config 已恢复。实机暴露并修复空 owner 列表误判与 `stall_watchdog` 未投影；`test_job_control` 19 项、投影 1 项。`revision==0` 新装配出口未复现；23 组件挂死根因仍需 Creo 10。

2026-11-17（离线收口批：BUG-020 / BUG-106 / BUG-129 / DEV-078）：[BUG-020](BACKLOG_COMPLETED.md#legacy-bug-020) 新增 `creo_mechdog.export_artifacts`，只把本作业 `output` 内含 `_out.log` 的 Creo 诊断摘录移到 `output/diagnostics/`，结果新增 `export_artifacts`/`export_diagnostics`/说明；`.stp/.igs` 与调用方文件不动，4 项单测通过，真实导出待实机。[BUG-106](work-items/BUG-106.md) 离线裁定不纳入 `adopt_session_copy`（一致性判定/身份改写/审计边界未冻结），只剩同名两步链路实机。[BUG-129](work-items/BUG-129.md) 在 [REFERENCE_SYNTAX](REFERENCE_SYNTAX.md) 明确 `width` 映射 XY→+Y、XZ→+Z、YZ→+Z，并写明回执只断言不旋转；`width_axis` 控制另立 FEAT，未静默实现，剩余 Arm2 原模型与实机。[DEV-078](work-items/DEV-078.md) 复核无离线剩余，余项全部依赖真实样件/实机。台账 193 项不变。

2026-11-17（BUG-132 coaxial insert 与保存重载实机）：本机 Creo 12.4 新建带 R27.5 通孔板（孔壁 102/103 两个半圆柱）与 R27.4×60 对称销。默认 insert 作业 `failed`、`rolled_back`，报错列出 `ids 102 (cylinder), 103 (cylinder)`；两侧带 `coaxial:"any"` 的 insert+mate `succeeded`、`committed`、`underconstrained=false`，销轴与孔轴重合、轴平行 Z（对称销被 mate 翻转并置于孔上方，z=50，只断言轴共线）；显式 `creo_save_model` revision 5→6，`saved_file_reloaded_and_verified=true`。证据 `build/live_bug132_insert/20261117T012115_a6bb73/report.json`。Arm7 原半圆柱与 Creo 10 仍未验。

2026-11-17（BUG-132 本机实机报错分型）：本机 Creo 12.4 用 100×80×20 方块 + R27.5 通孔复现圆柱拆半（孔壁 id 102/103，type 36）。三种选择器报错均按新措辞输出：多命中 `matched 2 faces (ids 102 (cylinder), 103 (cylinder))`；类型不符列出 `ids 53 (plane), 58 (plane)` 并说明 `radius_mm` 非类型过滤器；零命中报 `matched none of the 8 planar/cylindrical model faces`。三个作业均 `rolled_back`、未建特征。证据 `build/live_bug132/20261117T090714_af80ee73/report.json`。`coaxial:"any"` 的真实 insert、保存重载与 Creo 10 对照仍未验。

2026-11-17（DEV-090 G2 本机实机复测）：用户当次授权启动/连接本机 Creo 12.4.0.0。100×80×20 mm 方块竖直实体边的 R5/R30 对照：圆弧与 `curvature_continuous` 四条用例全部 `succeeded`、`effect_status=committed`、`saved_file_reloaded_and_verified=true`；R5 去除 `107.3015→80.0793 mm³`，R30 `3862.8331→2883.2442 mm³`，G2 相对圆弧少 25.37%，G2 表面不是圆柱面、半径回读为请求值（`d12`），排除静默退化。曲率连续性未测量；Arm7 TXT/模型不在本工作区，Arm7 实体边与 Creo 10 目标机仍未验。证据 `build/live_g2/20261117T084440_82e59496/report.json`。原生首次构建修掉 P6 新增局部变量与 Windows `near` 宏冲突。

2026-11-16（0.26.0 反馈 P6 / BUG-132）：圆柱面选择器离线改进。[BUG-132](work-items/BUG-132.md) 的面选择器报错分为零命中、多个同类面、类型不符三种，多面与类型不符逐项列出 `id (plane|cylinder)`，并说明 `radius_mm` 只过滤圆柱半径、不是面类型过滤器；`require_constraint_surface_type` 在已给 `radius_mm` 时不再重复建议补半径，改为指出消歧点可能落在端面平面。组装侧 `assembly_reference` 是 `geometry_selector` 而缺 `assembly_component` 时，`AssemblyConstraint` 在准入前直接点名缺失字段（装配本身没有实体面/边，选择器必然枚举 0 项）。新增显式 `coaxial:"any"`：只接受 surface 选择器、必须带 `radius_mm`+`axis`，仅 `insert/concentric` 可用，原生只在多个圆柱命中时确定性取最小 id 并记录 `coaxial_any`/`matched_ids`/`matched_types`；默认唯一性、`mate/coincident` 与 round/chamfer/flange 均不放宽。两个测试文件 39 项通过，含原生报错文本回归。未编译原生、未连接 Creo；半圆柱实机、保存重载与 Creo 10/12.4 对照未验。

2026-11-16（0.26.0 六项反馈计划）：按外部报告 P1—P6 建立[完善计划](superpowers/plans/2026-11-16-feedback-0260-followup.md)，新增 [BUG-131](work-items/BUG-131.md)（23 组件带配合总装挂死、无取消、装配 unknown 无法收尾）与 [BUG-132](work-items/BUG-132.md)（圆柱面拆半导致选择器无法唯一命中）。本轮离线交付：独立 `creo_sheetmetal_base_flange` 补齐 `expected_width_direction_world`/`width_direction_tolerance_deg` 并保持旧 payload；`stall_report` 在尾窗无标记时扩读至 1 MiB，新增 `marker_source`/`marker_scan_bytes`/`log_age_seconds` 与重复行证据，compact 投影同步；P1 区域切除的输入适配层——`ExtrudeOp.region` 按边界签名在计划内唯一匹配闭环，把实体原样复制成派生草图后由 `generic_bridge.submit` 在准入前替换，回执 `region_adaptation`，离线 24 项单测通过；P3 作业控制——`creo_cancel_job`（公开工具 108→109，终态不改写、取消≠回滚）、worker 日志停滞看门狗与 `revision==0` 新装配 `abandon_new`/`ack_failure` 出口，新增 18 项单测。源草图须为坐标草图且只支持简单闭环；取消/看门狗实机与原生选区均未验。未编译原生、未连接 Creo、未改版本/发布。

2026-11-16（G2 实机）：[DEV-090](work-items/DEV-090.md) 的曲率连续圆角在 Creo 12.4.0.0 实机通过：`PRO_ROUND_CURV_CONTINUOUS` 被接受、`effect_status=committed`、保存重载通过，R5 去除 `80.0792756 mm³`，圆弧基线 `107.3015365 mm³`；`RoundOp` 新增可选 `curvature_continuous`（默认关闭，旧行为不变）。证据见 [G1/G2 查证](development/G1-G2-API-GAP-2026-11-16.md) 与 `build/live_g2/20261116T194830_ca3b1511/report.json`；未直接测曲率连续性，未测 Creo 10/9、凹边、变半径与多边组合。该改动未提交、未发版。

2026-11-16（0.26.0 发布）：MINOR 发布，公开工具仍 108。[DEV-091](work-items/DEV-091.md) 的 0.25.0 四份反馈批交付：[BUG-129](work-items/BUG-129.md) 组合首壁宽度方向断言、`width_direction_world`/`center_of_mass_mm` 回执与方向冲突拒绝；[FEAT-068](work-items/FEAT-068.md) 单点直边、圆边 `center_mm`/`radius_mm`/`axis`（含圆弧角度点）与装配 `geometry_selector` 准入，原生解析后复核平面/圆柱；[FEAT-069](work-items/FEAT-069.md) `region_selection` 边界签名契约（未接 `ExtrudeOp`，能力不开放）；[DEV-083](work-items/DEV-083.md) 发布门禁的交付快照、逐 ID 交付版本/Release 列、完成档案覆盖、发布前后证据与审定 TXT 白名单；[DEV-090](work-items/DEV-090.md) 静态复查 G2（不开放）。原生构建成功，离线全量单测通过，Creo 12.4.0.0 实机 M1/A0/A1 通过并保存重载（见 [实机验收](development/LIVE-ACCEPTANCE-0250-2026-11-16.md)）。A2 的 61 条约束、Arm2 完整装配逐条对照、61 条边锚点、G1 原生选区与 G2 实机未验，交接见 [PENDING](development/HANDOFF-0250-2026-11-16.md)；发布核对见 [RELEASE-0.26.0](validation/RELEASE-0.26.0.md)。

2026-11-16（0.25.0 四份反馈规划）：[DEV-091](work-items/DEV-091.md) 已完成指定四原件的字节归档与源码对照，建立[分批计划](superpowers/plans/2026-11-16-feedback-0250.md)：先DEV-083发布门禁，再BUG-129坐标契约/FEAT-068装配锚点，随后FEAT-069区域路线与DEV-090剩余能力。新反馈已补B-REGION签名，但完整草图及原生选区创建仍待核。同日完成实现：DEV-083 发布快照/列校验/发布前后证据/审定TXT，BUG-129 宽度方向断言与原生质心回执，FEAT-068 单点/圆边锚点与装配选择器准入，FEAT-069 区域签名契约；原生构建成功，离线单测通过，M1/A0/A1 实机通过并保存重载（见 development/LIVE-ACCEPTANCE-0250-2026-11-16.md）。A2、Arm2 完整装配逐条对照与 G1 原生选区未验；未改版本、未合main或发布，版本仍以version.py为准。

2026-11-15（0.25.0 机械臂反馈批）：MINOR 发布，公开工具 107→108。[DEV-090](work-items/DEV-090.md) 交付：组合能力 `sheetmetal_base_flange`（native 矩形平面壁 + 90° 法兰，回执 `composed_features` 与实测体积上界，不声称等价单特征基体法兰）；T1 边/面几何选择器与装配坐标空间、T2 `mate`/`align`/`insert`/`csys` 非零 offset 拒绝与 `mate_offset`/`align_offset` 求解、T4 按特征与符号定位尺寸、T5 `coincident`/`concentric` 关系词、T6a 距离+角度倒角、T6b 方向线性阵列、T8 `plan_file` 受控本地 JSON 提交；T6c 区域切除与 T7 弧端点/两阶段形状误差仍不开放。本版同时包含 0.24.1 的启动参数、无图形会话容错、worker 启动回退与 toolkit 提示。Creo 12.4.0.0 实机取证，Creo 10 与 WorkBuddy 黑盒未测，发布核对见[RELEASE-0.25.0](validation/RELEASE-0.25.0.md)。

2026-11-13（0.24.1 启动参数与无图形批）：PATCH 发布。[BUG-125](work-items/BUG-125.md) `config.json` 新增 `creo_startup_args`，参数经 `parametric.exe` 传给 `xtop.exe`；[BUG-126](work-items/BUG-126.md) 无图形会话中 `ProWindowActivate` 失败改为记录 `window_activate_code`，不再判建模失败；[BUG-127](work-items/BUG-127.md) `creo_worker_launch` 三段配置与 `-4` 时经 Explorer 隐藏复核一次 worker；[BUG-128](work-items/BUG-128.md) `toolkit_hint` 区分 `-4`/`-38` 与退出码 20；[DEV-089](work-items/DEV-089.md) 安装文档补编译工具链实物预检与 Creo 13.4 编译层实测。本机 Creo 12.4.0.0 GUI 与 `-g:no_graphics` 两种会话均完成连接、拉伸/圆角/通孔、保存重载与预览；公开工具仍 107。证据见 [STARTUP-HEADLESS-2026-11-13](validation/STARTUP-HEADLESS-2026-11-13.md)，发布核对见 [RELEASE-0.24.1](validation/RELEASE-0.24.1.md)。

2026-11-13（0.24.0 曲面准入与导入批）：MINOR 发布。[BUG-121](work-items/BUG-121.md) 只读型计划自动按只读准入并为写计划失败补动作指引；[BUG-122](work-items/BUG-122.md) 按同一 worker 实测内核签名在 `surface_loft` 提交前拒绝；[BUG-123](work-items/BUG-123.md) 元素树模板 XML 路线（导出、原生 loader、双路线一致性，模板与清单已进源码包）；[BUG-124](work-items/BUG-124.md) STEP/IGES `import_geometry` 导入通道；[FEAT-067](work-items/FEAT-067.md) 计划级 `bbox_mm` 与 `surface_area_mm2` 断言；[DEV-088](work-items/DEV-088.md) 本版发布与收口。Creo 12.4.0.0 实机取得六个驱动回执，Creo 10 复测步骤见[交接包](development/CREO10-RETEST-0232-2026-11-13.md)，发布核对见[RELEASE-0.24.0](validation/RELEASE-0.24.0.md)。

2026-11-13（0.23.2 球鼻艏反馈批）：归档原件到 [feedback-0.23.2-2026-11-12](validation/feedback-0.23.2-2026-11-12/MAPPING.md)，建立[分批计划](superpowers/plans/2026-11-13-feedback-0232-bulb-loft.md)。A 批离线交付 [BUG-121](work-items/BUG-121.md)（只读型计划不受基线漂移影响）、[BUG-122](work-items/BUG-122.md)（实测内核签名下提前拒绝 `surface_loft`）、[FEAT-067](work-items/FEAT-067.md)（`assertions.bbox_mm`）。同日用户当次确认 12.4 实机后推进 B 批：[BUG-123](work-items/BUG-123.md) B1 交付——3 截面 + 3 导线边界混合实测 `create_code=0 / extract_code=0 / incomplete=false / 1600.0 mm2`，两次独立 dump 得同一模板 `templates/elemtree/loft_s3g3_creo12.4.xml`（SHA256 `4ef01eed…`），确认"模型相关只有 6 条曲线引用、TAN_COND 无他模型曲面"；B2 loader/B3 一致性也已完成并在 12.4 实机验收（`tools/test_loft_template.py --live` 11 项 PASS，两路线 1600.0 mm²、相对差 0.0，形状不匹配与坏 XML 两个负例均被拒）。[BUG-124](work-items/BUG-124.md)（STEP/IGES 导入）离线实现完成后同日删除门禁，12.4 实机两轮导入验收通过（STEP 440.0 mm² / IGES 1540.0 mm²，均保存重载）；A 批也于同日补 12.4 实机回执（`build/live_acceptance_20261113T160310` 14 项 PASS，含面积两态）。已随 [0.24.0 发布记录](validation/RELEASE-0.24.0.md)合入 main 并发布，四附件与两个 sidecar 远端核对通过。

2026-11-08 [DEV-076](work-items/DEV-076.md)：本地v0.18.4合入当前开发分支，保留DEV-066/075后续离线修复。新增缺头编译与独立包导入回归，发布资料勘误见[统一核对台账](development/RELEASE-POSTCHECK-2026-11-07.md)。本批未连接Creo、未合main、未发布。

从 [统一台账](BACKLOG.md) 定位 ID，读取工作卡的当前摘要，再查相关源码；历史证据按需打开。根级 [AGENTS.md](../AGENTS.md) 是仓库约束，架构与入口分工见 [ARCHITECTURE](development/ARCHITECTURE.md)，编码规则见 [CODING_STANDARD](development/CODING_STANDARD.md)。当前版本以 [version.py](../version.py) 为准，本节不再重复逐版记录。

## 准入与日常维护

Creo TOOLKIT 的官方资料导航、API/元素树查证及接入方法见 [中文开发指南](development/CREO_TOOLKIT_GUIDE.md)。Git 检出的本项目可使用 [creo-mechdog-dev skill](../.agents/skills/creo-mechdog-dev/SKILL.md)（显式调用 `$creo-mechdog-dev`，也允许按开发任务匹配）；实机授权和 WorkBuddy 黑盒规则继续以 AGENTS 为准。

1. 开始前核对分支、工作树、未提交改动、合并现场和已有 ID，避免覆盖其他任务。默认从可交付 main 创建 `codex/<条目>-<主题>`；关联集成批以指定提交为基点时，在工作卡记录原因与源码身份。
2. BACKLOG 是唯一当前台账。新增工作先登记未占用 ID、目标、范围、验收及环境。小修复沿用工作卡和证据链接，几行即可；复杂跨模块任务才使用[工作卡模板](templates/WORK_ITEM.md)和完整计划，不另建总台账或第二份待办。
3. 已报告缺陷先复现，分别记录现象和推测根因。诊断交付与根因修复、部分子项交付与整卡完成分别记录；缺其他版本测试不等于代码未修。观察项仅在收到同类新证据后重开调查。
4. BACKLOG 每个 ID 只有一行：优先级、当前状态、目标版本、简短剩余工作、工作卡链接。工作卡首页维护当前结论、剩余范围、依赖和最新证据，旧过程保留日期。无保留范围的完成项移至[完成档案](BACKLOG_COMPLETED.md)，部分完成不关整卡。
5. 实现最小完整改动；格式整理、路径迁移与行为修改分开提交。能力变化同步工具描述、README 和能力边界。PR 使用仓库模板；开发分支提交本身不要求发布。

逐版过程留在对应版本说明和发布记录，不在入口重复回填：[0.31.0 版本说明](RELEASE_NOTES_0.31.0.md)、[0.31.0 发布记录](validation/RELEASE-0.31.0.md)、[0.25.0 版本说明](RELEASE_NOTES_0.25.0.md)、[0.25.0 发布记录](validation/RELEASE-0.25.0.md)、[0.24.0 版本说明](RELEASE_NOTES_0.24.0.md)、[0.24.0 发布记录](validation/RELEASE-0.24.0.md)、[0.23.2 版本说明](RELEASE_NOTES_0.23.2.md)、[0.23.2 发布记录](validation/RELEASE-0.23.2.md)、[0.23.1 版本说明](RELEASE_NOTES_0.23.1.md)、[0.23.1 发布记录](validation/RELEASE-0.23.1.md)、[0.23.0 版本说明](RELEASE_NOTES_0.23.0.md)、[0.23.0 发布记录](validation/RELEASE-0.23.0.md)、[0.22.0 版本说明](RELEASE_NOTES_0.22.0.md)、[0.22.0 发布记录](validation/RELEASE-0.22.0.md)、[0.21.1 版本说明](RELEASE_NOTES_0.21.1.md)、[0.21.1 发布记录](validation/RELEASE-0.21.1.md)、[0.21.0 版本说明](RELEASE_NOTES_0.21.0.md)、[0.21.0 发布记录](validation/RELEASE-0.21.0.md)、[0.20.0 版本说明](RELEASE_NOTES_0.20.0.md)、[0.20.0 发布记录](validation/RELEASE-0.20.0.md)、[0.19.3 版本说明](RELEASE_NOTES_0.19.3.md)、[0.19.3 发布记录](validation/RELEASE-0.19.3.md)、[0.19.2 版本说明](RELEASE_NOTES_0.19.2.md)、[0.19.2 发布记录](validation/RELEASE-0.19.2.md)、[0.19.1 版本说明](RELEASE_NOTES_0.19.1.md)、[0.19.1 发布记录](validation/RELEASE-0.19.1.md)、[0.19.0 版本说明](RELEASE_NOTES_0.19.0.md)、[0.19.0 发布记录](validation/RELEASE-0.19.0.md)、[0.18.4 版本说明](RELEASE_NOTES_0.18.4.md)、[0.18.4 发布记录](validation/RELEASE-0.18.4.md)、[0.18.3 版本说明](RELEASE_NOTES_0.18.3.md)、[0.18.3 发布记录](validation/RELEASE-0.18.3.md)、[0.18.2 版本说明](RELEASE_NOTES_0.18.2.md)、[0.18.2 发布记录](validation/RELEASE-0.18.2.md)、[0.18.1 发布记录](validation/RELEASE-0.18.1.md)、[版本说明目录入口](../README.md)。源码版本只认 [version.py](../version.py)，启用工具只认 [包内 capabilities](../src/creo_mechdog/capabilities.py)；本地版本号、标签存在与正式 Release 交付不是同一事实，发布核对归原集成负责人。

## 架构与环境

MCP stdio → `server.py` 工具注册 → `bridge.py` 单通道调度/保护 → `generic_bridge.py` 计划校验/登记 → 原生 Toolkit 执行器 → Creo。几何在原生端计算，Python 不模拟 Creo。新业务实现进入 `src/creo_mechdog/`，根级兼容包装与包内必须共享类型；根级实现入口及资源/生成物边界见 AGENTS 与 ARCHITECTURE。

服务 stdout 只承载 MCP。通道忙碌立即拒绝（`isError=true`、`status=busy`、`blocking_*`），不排队、不自动重试；已接受任务只轮询 `creo_get_job`，不能重复提交。现有并发边界见 [BUG-009](work-items/BUG-009.md)。长度为 mm、角度为度；特征 label 小写字母起始，仅小写字母、数字、下划线，最多 28 字符。

开发环境为 Windows x64 / Python 3.12+。语言与单元检查不需要 Creo SDK。建模需 Creo 9/10/12、匹配 SDK、许可和 MSVC x64；当前本机原生验收环境为 Creo 12.4.0.0。Creo 9 编译探测已有修复，本机无 SDK，实机编译/运行未验；其他环境范围见[兼容矩阵](COMPATIBILITY.md)。不要求全项目 Creo 10 独立复测或双版本发布门槛，也不把本机成功外推至其他环境。

本机联调只启用指向 E 盘项目的 `MCP_CREO_MechDog_dev`。BUG-001 关闭不代表事故会话根因已解决，历史失败与 [2026-10-17 恢复记录](validation/BUG-001-recovery-2026-10-17.md) 按原件保留；按 2026-11-09 用户决定，**用户明确确认后即可用 Creo 进行实机测试**（含新建 Toolkit 连接与建模），不再以根因核对或事前会话可操作判定作为阻断前置，确认按次生效。未获确认时默认不主动连接 Toolkit、不启动 Creo；任何情况下不擅自结束 Creo/nmsd、清锁或 unknown 保护，故障注入与进程/保护状态清理需单独明确授权。单通道、busy 立即拒绝、保存重载与证据边界不变，完整规则见 [AGENTS.md](../AGENTS.md)。

## 命令与检查

在仓库根目录 PowerShell 执行；正式安装步骤见 [INSTALL](INSTALL.md)。`requirements-dev.txt` 包含锁定依赖及 editable 安装，变更包布局后同步安装入口、资源路径和分发。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
.\.venv\Scripts\python.exe tools\dev_check.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe tools\test_unit.py
.\.venv\Scripts\python.exe tools\dev_check.py --skip-unit
.\.venv\Scripts\python.exe tools\dev_check.py --strict --skip-unit
```

统一检查覆盖 Ruff、Python/C++ 格式、存量基线比较及全部单元，报告为 `build/development_check.json`、`build/unit_test_report.json`。`--skip-unit` 只提供语言证据，`--strict` 暴露全部欠账。[风格基线](development/style-baseline.json) 按诊断及内容身份容许存量，不能掩盖工具/配置错误、单测失败或新增问题；正常开发与 CI 不重建基线，不新增豁免。

单元阶段默认 900 秒，可用 `--unit-timeout-seconds 1200 --work-item <ID>` 调整；报告区分 passed/failed/timed_out，超时不算通过。单测必须 mock 外部通道和进程，真实 busy 时修夹具，不绕过产品保护。新增用例放 `tests/unit/test_*.py`，使用 unittest；校验或保护变化补回归。冻结源码后执行最终全量，不能用分拆测试代替统一检查。

以下仅为获准原生任务的操作入口，本次文档整理不执行：

```powershell
.\setup.ps1 -CreoRoot 'C:\Program Files\PTC\Creo 10.0.0.0'
.\.venv\Scripts\python.exe bridge.py build
.\.venv\Scripts\python.exe server.py
.\.venv\Scripts\python.exe tools\test_general.py
```

`native/constants.inc` 必须由本机 SDK 生成，不复制、不提交、不分发。DEV-049 的默认离线驱动与双开关门槛见 [T04](development/DEV049-T04-ACCEPTANCE.md)、[T05](development/DEV049-T05-ACCEPTANCE.md)、[T06](development/DEV049-T06-ACCEPTANCE.md)，历史结果不等于新源码已测。

## 验收与交付

| 改动 | 必要证据 |
| --- | --- |
| 文档 | 链接、ID 唯一性、状态/工作卡、历史原件字节、冲突标记和打包引用；涉及工具或配置时加对应回归 |
| Python 校验/调度/保护 | 统一检查及专项回归；外部进程/会话行为另取实机证据 |
| C++/建模/单位 | 匹配 SDK 构建、对应驱动、实际几何/尺寸/单位、保存重载及适用失败回滚；mm/英寸/混合/未知单位分别声明 |
| 路径/布局迁移 | 安装/客户端/后台入口、资源和数据根、解压源码包验证；原生变化补实机 |
| 合入 main | 未发布新版本、版本元数据、适用验收和打包、标签/Release/附件及 SHA256 远端核对 |

原生成功须任务成功、特征有效、几何断言通过且 `saved_file_reloaded_and_verified=true`。拒绝、超时、unknown、编译通过均不能代替建模成功。证据记录日期、条目、版本、提交、dirty、受测指纹、命令、环境与未测范围；历史证据保留原日期，引用时说明复用边界。

每次合入或直接提交 main（包括文档）都须同次完成对应 GitHub Release；仅合并、推送、标签或草稿不算交付。`version.py` 递增至未发布版本，标签指向合入后的主干提交，附件由该提交生成；旧标签与同名附件不可覆盖，细则见 [RELEASING](development/RELEASING.md)。独立开发分支可以按用户要求只交付本地提交。

<a id="workbuddy-测试约定"></a>

WorkBuddy 一律指公开 MCP 黑盒验收：仅给操作场景、输入、预期和报告要求，不读取源码/配置/Git、不跑本地测试。环境和版本由 MCP 公开接口确认，未提供则“无法确认”；只有实际并发才能报并发通过。内部文件占用/重试预算不纳入黑盒结论。开发者证据与 WorkBuddy 分别记录，完整约定见 AGENTS。

`docs/validation/` 历史原件逐字节保留。稳定契约、安装说明、兼容矩阵和第三方许可继续沿用；`tools/package.py` 递归收集 docs 的 Markdown/JSON，归档不会缩小分发范围，本批不改打包协议。
