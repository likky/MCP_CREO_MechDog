# 统一开发台账

2026-11-18（BUG-120 D3 接线）：[BUG-120](work-items/BUG-120.md)把面板状态机接进`blend_sync.cpp`：`select_section`按`panel_run`分派、首位OVERRIDE后续TOGGLE、票据用尽即`PANEL_SELECTION_EXHAUSTED`、SDK失败`abandon`；新增`MechDogPanelInitialize/Prepare/Finalize/Event/State/Release`导出与`panel_exports`校验（面板代只找`MechDogPanelInitialize`，ABI1仍走原入口，协议4请求到Blend入口被明确拒绝）；Done用`ProCmdCmdIdFind`+`ProMacroLoad`执行请求提供的受限宏（不硬编码命令名，缺宏则保持可选）；`panel_wait.json`有了原生生产者（字段与`read_marker()`一致、phase由状态推导、原子写）。`bridge.py build`通过并重编payload，3978单测通过。真实对话框的TOGGLE语义、回调次数、Done宏能否关闭、面板部署生成仍待D6。

2026-11-18（BUG-120 D3 协议4/ABI2）：[BUG-120](work-items/BUG-120.md)新增`panel_protocol.h`（协议4/ABI2、3/1混用拒绝、marker只认本job+nonce+已知类型+递增序号、原子写）与`panel_selection_state.h`（一位置一票据、首位OVERRIDE后续TOGGLE各一次、重复/旧票/错nonce/错模型/跳序不推进、Done仅全选后排队且返回非0不算committed、`Done或Quit/yes→AfterTerminal→OuterDrain`严格递增、反序即锁死unknown、release不可复位）。`MechDogCallbackApi2`在ABI1前缀后追加macro_load/命令查询/bracket/曲线查询，loader同时支持ABI1与ABI2并拒绝混用。`bridge.py build`通过（含loader与payload），`tools/test_panel_selection_state.py`与3973单测通过。loader二进制已变：目标机需重新注册loader，ABI1载荷行为不变。collector接线、SDK侧finalize与实机时序仍待D6。

2026-11-18（BUG-120 D2+首次原生编译）：[BUG-120](work-items/BUG-120.md)完成曲线引用解析：`panel_references.h` 承载无SDK规则（API失败、特征/owner归属、基准面反例、复合/闭合/开闭未证实、长度有效、2—8段、换模型/换会话拒绝），`panel_references_sdk.h` 用仓库已在用的 `ProFeatureInit`/`ProFeatureGeomitemVisit(PRO_CURVE)`/`ProCurveInit`/`ProCurveTypeGet`/`ProCurveLengthEval` 实现适配；`tools/test_panel_references.py` 离线编译运行通过。授权下执行首次 `bridge.py build` 成功，并修复 D1 遗留的 `worker.cpp` build-info JSON 多余 `}`（此前原生半部分从未编译）。产物 `creo_worker.exe` 在无 Creo 环境运行缺 ToolKit DLL（0xC0000135），故"编译成功"未当作"已运行"；真实枚举、闭合性证明、面板流程接线仍待 D6，3964 单测通过，工具数不变。

2026-11-17（BUG-120 续批：恢复/D5/D8）：[BUG-120](work-items/BUG-120.md)补齐`creo_reconcile_model`的`confirm_panel_closed`恢复动作（令牌+人工确认+不取Toolkit锁，只解除会话保护不改模型unknown）、worker前取消退役预留、`panel_receipt`回执投影（未确证退出强制失败、quilt/选取/面组/面积/关联/树完成冒充均记问题、bbox保近似标记）、panel库打包门禁（manifest白名单+认证摘要+路径逃逸拒绝，空库为合法关闭态）。3964单测与Ruff通过。仍未编译、未连接Creo：D2/D3原生后端、D6/D7目标机验收、发布待专门批次；工具数不变。

2026-11-17（BUG-120 D1/D4离线实现）：[BUG-120](work-items/BUG-120.md)落地不依赖构建授权的三批：`creo_surface_loft`的`creation_route`契约与按路线准入/能力分路线披露、panel profile认证与候选票据库、面板等待阶段预算接入`worker.log`看门狗、跨模型持久会话guard（拦截所有Toolkit入口，仅原生退出观测或runner未启动可退役）。3918项单测与Ruff通过。未编译执行器、未连接Creo：原生后端、协议4/ABI2、几何保存重载、目标机验收与分发均未实施；guard本版无MCP侧退役动作，需人工确认面板已关闭后删除`panel_session_guard.json`，已列入后续任务。109工具数不变。

2026-11-17（BUG-120计划纳入0.27.0）：以已发布fc1efae及发布后f6da633为基线更新[D1—D8计划](superpowers/plans/2026-11-17-bug120-resident-panel-implementation.md)，复用BUG-122准入/Python unknown与BUG-131作业控制；D4补强制cancel和面板Quit分界、面板等待看门狗接线、跨模型持久会话保护。最终实体可选复用STL导出，BUG-130下版余项及装配/G2/原生选区保留独立范围；109工具数不因内部模块增加。仅计划/台账更新，无新产品实现或Creo操作，不改已发布记录/附件。

2026-11-17（BUG-120正式实现任务）：新增[T1-C后D1—D8实现计划](superpowers/plans/2026-11-17-bug120-resident-panel-implementation.md)，先2—8纯曲线第一方向，再导线/末点和完整球鼻艏。明确协议4/ABI2、不可复用请求票据、宏链最后观察与unknown、候选实测入口及panel严格打包清单；已有保护复用。当前为任务规划，未实施新后端、未编译或连接Creo，旧几何验收矩阵继续适用。

2026-11-17（BUG-120 T1-C复核）：[247项清单全匹配](validation/bug120-creo10-t1c-2026-11-17/manifest.json)，376帧未列清单；12份检查/测量原件和收养回执补齐关联，近似bbox来源、Quit+yes取消、中间截面抬高3mm已取得证据。可进入第一方向正式协议开发，尚未开放入口：需把Done入队与实际结束分开、加强真实曲线/源特征校验和请求幂等，新非平面件还未保存重载。详见[T1-C复核](development/CREO10-T1C-REVIEW-2026-11-17.md)。本轮仅离线复核/归档，无新产品实现或本机Creo操作。

2026-11-17（BUG-130 转入下个版本的余项）：本轮拆分曲面/参数域细化已把 `bulb_bulged` 最大抽样偏差降到 0.0899mm（达成 0.1mm）。以下未完成项明确转入下个版本，不在本版声称完成：① 旧 14m 默认预算 0.1559mm、放宽到 50 万顶点 0.1115mm，仍未达 0.1mm；按片数-偏差曲线需约 45 万+新顶点，或先优化 ASCII 写出（当前约 166µs/片，600 秒作业预算是硬约束）；② 装配件与 Creo 9/10 的逐面/细化路径未测；③ 官方文件路径在同质量下仍不可完成，未纳入默认路径；④ 默认细化预算 25 万是否提高（影响文件大小与作业时限）待定；⑤ 安装器测试 90 秒超时（与 BUG-130 无关，低优先级，未排期）。见[BUG-130](work-items/BUG-130.md)。

2026-11-17（BUG-130 拆分曲面：参数域细化，bulb 偏差达标）：单面约 20.4 万片上限使大面无法按弦高继续细化。`native/stl_export.h` 改为只读参数域拆分：`PRO_SRFTESS_NO_PROJECTION` + `ProTessellationParamsGet` 取剖分顶点 UV（32 点往返自检），对超差三角形做自适应 red-green 细化，只拆内部边、裁剪边界保持 SDK 顶点，新顶点经 `ProSurfaceXyzdataEval` 落回原生面并返回法向；判据用顶点法向转角估计弦高，避免逐片求值（实测约 2ms/次，首版整轮扫描 job `85d2c5fe…` 超 600 秒 `unknown_outcome`，已 `--apply-restore` 恢复基线）；预算默认 25 万新顶点，按“剩余预算/剩余面数”逐面分配。偏差抽样改为逐面步长（上限 8000），修掉后访问面零样本的偏差。实机：`bulb_bulged` job `cde4566f…` 737,984 片、偏差最大 **0.0899mm**（原 0.1581mm，**达成 0.1mm**）、p99 0.0584、平均 0.0125，194 秒，边界边/非流形/零面积均 0，体积差 0.00004%，trimesh `is_watertight/is_winding_consistent=true`、`euler_number=2`；旧 14m 默认预算 job `dd659d80…` 0.1559mm（原 0.3086mm）、放宽 50 万预算 job `0ec3f531…` 0.1115mm，仍未达 0.1mm（受 600 秒预算与 ASCII 写出速度约束）。源件 SHA/revision 未变；`tests/native/test_stl_export.cpp` 24 项、`tools/test_stl_export.py`、`dev_check --work-item BUG-130` 全部通过。详见[BUG-130](work-items/BUG-130.md)。

2026-11-17（BUG-120 T1-B完整包）：六份PRT大小/SHA与六组按ID选择日志匹配；文本[原件归档](validation/bug120-creo10-t1b-2026-11-17/manifest.json)。新增离线审计/补证工具，仍缺6份inspection和6份测量作业原件，三/五截面bbox未过；Task 1可靠结束/取消、顺序与复杂曲面未闭环，panel入口未开放。先补BUG-122真实观测准入和面板未知结果保护，详见[BUG-120](work-items/BUG-120.md)、[BUG-122](work-items/BUG-122.md)及[T1-C交接](development/CREO10-T1C-HANDOFF-2026-11-17.md)。本机未构建或连接Creo，未提交/发布。

2026-11-17（BUG-120原始mapkey）：接收用户294B录制文件并[逐字节归档](validation/bug120-creo10-t1a-2026-11-17/originals/t1_blend_mapkey.pro)，SHA256 `04098e18…818326`；确认实际命令ProCmdFtBndBlend、第一方向表格FocusOut、3个拾取暂停和Done。没有ID/Ctrl/选集记录，不能直接逐暂停替换回调。T1-B先按owner/ID验证两线普通选择＋Ctrl追加、真实collector接受及几何收尾，再验证换模型/数量；完整原生回执仍待接收。仅离线解析归档/方案更新，无Creo连接或产品实现，整卡状态不变。

2026-11-17（BUG-120外部T1-A摘要）：用户报告Creo10 GUI及半自动mapkey回放产物均经MCP收养取得800mm²、120mm边界、20×40×0包围盒、单面开放quilt和保存重载通过；最小GUI成面已有外部结果，原始录制/回执待接收。实际命令报告为ProCmdFtBndBlend，3次拾取暂停尚需人工/脚本，不能等同通用回调成功。下一步T1-B按ID验证普通选择与Ctrl追加；官方OVERRIDE/TOGGLE语义已查证，现回调只用OVERRIDE。见[BUG-120](work-items/BUG-120.md)与[计划](superpowers/plans/2026-11-16-creo10-bulb-native-creation.md)。本轮仅离线评审，无新的本机实机/产品实现；整卡状态不变。

2026-11-17（BUG-130 官方文件式导出，离线完成 + 实机：小件通过、旧 14m 超时）：新增 `native/stl_file_check.h`（流式 ASCII STL 语法/有限坐标/片数与字节预算）与 11 项 native 用例、`tools/test_stl_file_check.py`；新增 `native/stl_export.h`（3 元素 `ProArrayAlloc`、`PRO_SLA_ASCII_FILE`、仅 `PRO_FACET_STEP_SIZE_OFF`、短 ASCII 暂存名、工作目录保存/恢复、校验后同盘原子发布）与 12 项 native 用例、`tools/test_stl_export.py`，两组均实跑 `success=true`。旧剖分路径保留为仅 `MECHDOG_STL_LEGACY_TESSELLATE=1` 的诊断探针，不是自动回退。旧路径只读实机 job `da08c43e…` 定位到 `n=3`、surface 0 `n_facets=201551` 配 `facets=null`，防护在解引用前安全失败，STL 仅 19 字节，源件 SHA/revision 不变。官方路径实机：小件 `bug007_three_straight` job `5ec450a8…` 成功，STL 73,561 字节/284 片、包络匹配、源件与 revision 不变；旧 14m `bulb_verified_03989988` job `8eb45948…` 在相同 0.05mm/0.1 下 600 秒内未完成，`unknown_outcome`、暂存 0 字节，worker 终止后 Creo `xtop.exe` 仍持续计算（约 10GB 工作集）。官方路径同质量在当前预算下不可完成，`bulb_bulged` 未再提交；需在 Creo 空闲后决定提高有界超时、显式质量对照或转 Task 4。

2026-11-17（BUG-130 诊断插桩，离线）：新增只读 `tools/diagnose_stl_export.py`，汇总既有作业的终态/退出码/最后 PHASE/输出字节与 SHA/源件记录哈希/worker 身份及 `STL_*` 阶段；对两次失败与旧成功件生成 `build/bug130_evidence/summary.json`（SHA256 `63c936cb…`）：两次 `0xC0000005`、最后 `PHASE=export`、STL 0 字节、整份日志 SHA 不同，旧成功件 48,847,489 字节。`native/generic.cpp` 的 `write_stl` 增加立即 flush 的 `STL_TESS_*`/`STL_SURFACE_*`/`STL_FACET_BATCH`/`STL_FILE_*`/`STL_TESS_FREE_*`，并在解引用/写盘前检查空数组、坏计数、越界索引、非有限顶点与 IO 失败；异常路径 RAII 释放。新增 8 项证据单测。未构建、未连接 Creo，故障栈/dump 与根因仍未取得。

2026-11-17（实机批：BUG-020 STEP 导出 + BUG-131 取消/收尾/看门狗）：① BUG-020 在本机 Creo 12.4 真实导出 STEP：`.stp` 8622 字节、`ISO-10303-21`；`__out.log.1` 已归档到 `output/diagnostics/`，结果含 `export_artifacts`/`export_diagnostics`，保存重载 true，其它文件未动。BUG-020 已移入完成档案，台账 193→**192**（BUG 86）。② BUG-131 临时件实机：worker 启动前取消返回 `cancelled`、模型 `failed`、`geometry_may_have_changed=false`；worker 启动后取消返回 `unknown_outcome`、`geometry_may_have_changed=true` 并记录终止 pid；两种都能经 `abandon_new` 收尾（`Explicit recovery committed`）。③ 看门狗（当次授权受控注入）：临时件 1 秒预算 + 500 圆孔重计划，日志 2 秒零增长后终止 worker，作业 `unknown_outcome`，`stall_watchdog` 记录 budget/silent/log_bytes/termination，`abandon_new` 收尾成功，config 已恢复。④ 实机暴露并修复：空 owner 列表误判为“无法证明停止”（恢复动作全不可用），以及 `stall_watchdog` 未投影到 `creo_get_job` 摘要；新增 2 项单测（`test_job_control` 19 项、投影 1 项）。证据 `build/live_bug020/20261117T100224_defe4eb0/`、`build/live_bug131/20261117T020648_b6092f/`、`build/live_bug131_post/20261117T020755_b040a7/`、`build/live_bug131_watchdog/20261117T022502_912c1d/`。`revision==0` 新装配出口未复现；23 组件挂死根因仍需 Creo 10。

2026-11-17（离线收口批：BUG-020 / BUG-106 / BUG-129 / DEV-078）：① BUG-020 新增 `creo_mechdog.export_artifacts`，本作业 `output` 内含 `_out.log` 的 Creo 摘录移动到 `output/diagnostics/`，结果新增 `export_artifacts`/`export_diagnostics`/说明；只动本作业诊断文件，`.stp/.igs` 与调用方文件不动，4 项单测通过，真实 STEP/IGES 导出待实机。② BUG-106 离线裁定不纳入 `adopt_session_copy`（一致性判定/身份改写/审计边界未冻结，现有两步文案已覆盖），反向断言保持 0 命中，只剩同名两步链路实机。③ BUG-129 在 REFERENCE_SYNTAX 明确 `width` 映射 XY→+Y、XZ→+Z、YZ→+Z，docstring 同步“只断言不旋转”；`width_axis` 控制另立 FEAT，未静默实现，剩余 Arm2 原模型与实机。④ DEV-078 复核无离线剩余，余项全部依赖真实样件/实机。表行仍 **193**。

2026-11-17（BUG-132 coaxial insert 与保存重载实机）：本机 Creo 12.4 新建 100×80×20 带 R27.5 通孔板（孔壁 102/103 两个半圆柱）与 R27.4×60 对称销。默认 insert 作业 `failed`、`rolled_back`，报错列出 `ids 102 (cylinder), 103 (cylinder)`；两侧带 `coaxial:"any"` 的 insert+mate `succeeded`、`committed`、`underconstrained=false`，销轴与孔轴重合、轴平行 Z（对称销被 mate 翻转并置于孔上方，z=50，只断言轴共线）；显式 `creo_save_model` revision 5→6，`saved_file_reloaded_and_verified=true`。证据 `build/live_bug132_insert/20261117T012115_a6bb73/report.json`（SHA256 `548066c4…`），`success=true`。Arm7 原半圆柱与 Creo 10 仍未验。表行仍 **193**。

2026-11-17（BUG-132 本机实机报错分型）：本机 Creo 12.4 用 100×80×20 方块 + R27.5 通孔复现圆柱拆半：孔壁为 id 102/103 两个半圆柱（type 36）。三种选择器报错全部按新措辞输出：多命中 `matched 2 faces (ids 102 (cylinder), 103 (cylinder))`；类型不符列出 `ids 53 (plane), 58 (plane)` 并说明 `radius_mm` 非类型过滤器；零命中报 `matched none of the 8 planar/cylindrical model faces`。三个作业均 `rolled_back`、未建特征。证据 `build/live_bug132/20261117T090714_af80ee73/report.json`（SHA256 `7136b549…`）。`coaxial:"any"` 的真实 insert、保存重载与 Creo 10 对照仍未验。表行仍 **193**。

2026-11-17（DEV-090 G2 本机实机复测）：用户当次授权启动/连接本机 Creo 12.4.0.0（`release_numeric=44`）。Arm7 TXT/模型不在本工作区，改用 100×80×20 mm 方块竖直实体边做 R5/R30 圆弧与 `curvature_continuous` 对照：四条用例全部 `succeeded`、`effect_status=committed`、`saved_file_reloaded_and_verified=true`；R5 去除 `107.3015→80.0793 mm³`，R30 `3862.8331→2883.2442 mm³`，G2 相对圆弧均少 25.37%，且 G2 表面不是圆柱面、半径回读为请求值（落在 `d12`），排除静默退化。曲率连续性未测量；Arm7 实体边与 Creo 10 目标机仍未验。证据 `build/live_g2/20261117T084440_82e59496/report.json`（SHA256 `30a005341eefda2e9bf3cbe4394ef45278b1a641e02d25a69a59b91202edf68a`）。原生首次构建修掉 `near` 宏冲突（BUG-132 改动）。表行仍 **193**。

2026-11-16（0.26.0 反馈 P6 / BUG-132 离线）：圆柱面选择器完成三点离线改进。零命中/多个同类面/类型不符分开报错，多面与类型不符逐项列出 `id (plane|cylinder)`，并说明 `radius_mm` 只过滤半径、不是类型过滤器；`require_constraint_surface_type` 在已给 `radius_mm` 时不再重复建议补半径，改为指出消歧点可能落在端面平面。`AssemblyConstraint` 对组装侧 `assembly_reference` 是 `geometry_selector` 而缺 `assembly_component` 的情况在准入前直接点名缺失字段。新增显式 `coaxial:"any"`：仅 surface 选择器、必须带 `radius_mm`+`axis`、仅 `insert/concentric` 可用，原生只在多个圆柱命中时确定性取最小 id；默认唯一性、`mate/coincident` 与 round/chamfer/flange 均不放宽。两个测试文件共 39 项通过。离线阶段未编译原生；2026-11-17 实机复测已构建通过并修掉 `near` 宏冲突。半圆柱实机与保存重载未验，表行仍 **193**。

2026-11-16（0.26.0 六项反馈计划）：按用户指示以 [P1—P6 计划](superpowers/plans/2026-11-16-feedback-0260-followup.md) 推进；新增 [BUG-131](work-items/BUG-131.md)（23 组件带配合装配挂死、无取消、装配 unknown 无法收尾）与 [BUG-132](work-items/BUG-132.md)（圆柱面拆半导致选择器无法唯一命中且报错误导）。本轮离线交付：独立 `creo_sheetmetal_base_flange` 补齐方向断言参数（BUG-129/P4-2）；`stall_report` 扩窗标记搜索、`log_age_seconds` 与重复行证据（BUG-131/P5-3）；`ExtrudeOp.region` + `sketch_regions.py` 单区域派生草图适配，在 `generic_bridge.submit` 准入前展开并回执 `region_adaptation`（FEAT-069/P1，24 项单测）；P3 作业控制——新增 `creo_cancel_job`（公开工具 108→109）、worker 日志停滞看门狗（`generic_stall_seconds`，默认 600 s，经 `native_owner.json` 定位并终止）与 `revision=0` 无保存文件新装配的 `abandon_new`/`ack_failure` 出口。[FEAT-069](work-items/FEAT-069.md) 补 0.26.0 契约复核；P2 沿用 DEV-090 已提交的 `curvature_continuous`，待目标机复测。未编译原生、未连接 Creo、未改版本/发布；表行 191→**193**（BUG 85→87）。

2026-11-16（Creo10原生球鼻艏计划）：形成[BUG-120实施计划](superpowers/plans/2026-11-16-creo10-bulb-native-creation.md)，主方案为限定目标版本的原生面板＋驻留回调；先验800mm²最小曲面，再做显式路线、协议4、事务/真实几何回执与七截面球鼻艏闭环。BUG-122只作按路线准入配套；备用内存NURBS/STEP不等同原生放样完成。当前仅规划和离线输入交点计算（最大分量差0.004305模型mm），无产品实现/构建/Creo连接，分类/行数不变。

2026-11-16（Creo 10 球鼻艏优先）：按用户本次指示，优先推进 [BUG-120](work-items/BUG-120.md) 的实质成型修复，BUG-130 STL 后排。0.26.0 外部回执确认 `INCOMPLETE` 创建后在 `Extract=-18` 中断，PTC 官方说明边界混合元素树在 Creo 11 加入；现有 Creo 10 路径无法完成特征。修正“GUI 手工创建也失败”的过强摘要，原件只证明 GUI 特征也不能取树。首选验证驻留回调驱动原生边界混合面板，先800mm²最小面，再7截面/尖点/完整导线和封闭实体；BUG-122 仅作保护配套。当前是离线定位与验证设计，未实现、未编译或连接 Creo，整卡分类/台账行数不变。

2026-11-16（G2 实机）：[DEV-090](work-items/DEV-090.md) 的曲率连续圆角已在 Creo 12.4.0.0 实机验证：`PRO_ROUND_CURV_CONTINUOUS` 成功、`effect_status=committed`、保存重载通过，R5 去除 `80.0792756 mm³` vs 圆弧基线 `107.3015365 mm³`；`RoundOp` 增可选 `curvature_continuous`（默认关闭）。证据 `build/live_g2/20261116T194830_ca3b1511/report.json`，未测曲率连续性、Creo 10/9 与凹边/变半径/多边。该改动未提交、未发版。

2026-11-16 [BUG-130](work-items/BUG-130.md) STL崩溃离线复核：确认两次复杂球鼻艏worker访问冲突，根因仍待定位；纠正78m坐标误当长度、仅尺度致因和已排除远程桌面/几何等过强判断。旧约14m球鼻艏曾成功导出197118片/48.85MB，是需保留的反例。核实SDK参数/资源所有权及官方文件式STL导出入口，形成[实施提案](superpowers/plans/2026-11-16-bug130-stl-export.md)：诊断与文件验证→官方文件导出→必要时逐面备选→受控实机矩阵→可选质量参数。本轮仅资料/计划，无Creo连接、构建、源码修复、保护清理、提交或发布；台账行数/分类不变。

2026-11-16 [FEAT-065](work-items/FEAT-065.md) 原始SW球鼻艏对比：读取用户打开的 `baquebo .SLDPRT` 并实际孤立查看后恢复船体；同坐标原生体积、真实网格截面和五个原生曲面最近点抽查确认中间鼓度差异（Creo半体积小1.27%，源灰/红分区也未复现）。[原件比对记录](development/FRIGATE-BULB-SW-COMPARE-2026-11-16.md) 区分显示网格与精确双CAD公差；补充截面/Creo改形仍待实施，本轮只读源几何、无Creo新任务，整卡状态不变。

2026-11-16 [FEAT-065](work-items/FEAT-065.md) 球鼻艏原图复核：只读导出实际实体网格，revision 6、体积和原生文件 SHA256 保持；截面尺寸与 TXT 大体吻合。Creo 放大查看已实施，但同视角和船体叠加仍未完成，期间桌面重新锁屏后停止输入。独立实体创建成功不等于原图外观验收通过，见[比对记录](development/FRIGATE-BULB-COMPARE-2026-11-16.md)。本轮不改模型形状、源码或既有保护状态，整卡状态不变。

2026-11-16（A2/A0 数据准入）：收到测试机 `mates_preserved.json`（61 条）、`assembly_ops_v0250.json`（23 条）与 `edge_anchors.json`（6 条）。离线结果：24 条 `coincident` 可准入但缺组件映射，26 条 `concentric` 缺半径/轴，6 `parallel` + 4 `distance` + 1 `gear` 未支持；23 条位姿全部合法但缺 Arm2 模型；4 条圆角锚点可准入，`Hom n7/n8` 缺角度参考面。未实机，见 [A2/A0 数据准入](development/A2-A0-ADMISSION-2026-11-16.md)。

2026-11-16（0.26.0 发布）：MINOR 部分交付，公开工具仍 108。[DEV-091](work-items/DEV-091.md) 的 0.25.0 四份反馈批交付：[BUG-129](work-items/BUG-129.md) 首壁宽度方向断言、`width_direction_world`/`center_of_mass_mm` 回执与方向冲突拒绝；[FEAT-068](work-items/FEAT-068.md) 单点直边、圆边中心/半径/轴（含圆弧角度点）与装配选择器准入，解析后复核平面/圆柱；[FEAT-069](work-items/FEAT-069.md) 区域签名契约（原生选区未开放）；[DEV-083](work-items/DEV-083.md) 交付快照与发布前后证据；[DEV-090](work-items/DEV-090.md) G2 静态查证。Creo 12.4.0.0 实机 M1/A0/A1 通过并保存重载，离线全量单测与原生构建通过。A2 的 61 条约束、Arm2 完整装配逐条对照、61 条边锚点、区域切除与 G2 实机未验，见[交接](development/HANDOFF-0250-2026-11-16.md)与[发布记录](validation/RELEASE-0.26.0.md)。表行仍 190（BUG84/FEAT66/DEV40）。

2026-11-16 [DEV-091](work-items/DEV-091.md)：归档用户指定 `Downloads/0.25.0` 四份反馈，原件共75,407字节、SHA256与源文件逐项一致，建立[分批计划](superpowers/plans/2026-11-16-feedback-0250.md)与[映射](validation/feedback-0.25.0-2026-11-16/MAPPING.md)。发布门禁续项沿用DEV-083；新增 [BUG-129](work-items/BUG-129.md)（Arm2目标方向/坐标偏差，待复现）、[FEAT-068](work-items/FEAT-068.md)（装配锚点准入接通）、[FEAT-069](work-items/FEAT-069.md)（区域签名切除，待核实原生路线）。DEV-090保留多约束、parallel/distance、G2与T7；新报告已补三区域签名，不能继续笼统写缺签名。当前190行（BUG84/FEAT66/DEV40）。本次只读核对与规划，未实施、未运行产品测试/构建/Creo，未改版本、合main或发布。

2026-11-15 [DEV-090](work-items/DEV-090.md)：核对指定 0.24.1 机械臂反馈与当时 0.24.0 源码、本机 SDK 及既有条目，建立[分批计划](superpowers/plans/2026-11-15-feedback-0241-sheetmetal-assembly.md)。按用户决定 T3 以“组合能力”开放为 `sheetmetal_base_flange`（native 平面壁 + 90° 法兰、回执 `composed_features`，不声称等价单特征基体法兰），同批交付 T1 几何选择器（含装配坐标空间）、T2 约束偏移语义、T4 符号定位尺寸、T5 `coincident`/`concentric`、T6a 距离+角度倒角、T6b 方向线阵、T8 `plan_file` 与 T7 诊断措辞；公开工具 107→108。Creo 12.4.0.0 实机取得回执（组合法兰 job `f85ddda1…` 体积 770.185802 / 上界 770.185796 mm³、保存重载通过；倒角、线阵、尺寸、选择器与装配约束各有成功与拒绝用例）；T6c 区域切除、T7 弧端点与两阶段形状误差、`parallel`/`distance`、多约束求解与装配保存重载、Creo 10 与 WorkBuddy 黑盒未验。已随 [0.25.0 发布记录](validation/RELEASE-0.25.0.md)发布。本卡最初以 DEV-089 登记，合入时与 0.24.1 已归档的 DEV-089 冲突，改用 DEV-090；新增本卡后当前行数 186（BUG 83 / FEAT 64 / DEV 39）。

2026-11-13（0.24.1 启动参数与无图形批）：[BUG-125](work-items/BUG-125.md) 新增 `creo_startup_args`，参数经 `parametric.exe` 传给 `xtop.exe`；[BUG-126](work-items/BUG-126.md) 无图形会话中 `ProWindowActivate` 失败只记录 `window_activate_code`，不再判建模失败；[BUG-127](work-items/BUG-127.md) `creo_worker_launch` 三段配置与 `-4` 时经 Explorer 隐藏复核一次 worker；[BUG-128](work-items/BUG-128.md) `toolkit_hint` 区分 `-4`/`-38` 与退出码 20；[DEV-089](work-items/DEV-089.md) 安装文档补编译工具链实物预检与 Creo 13.4 编译层实测。五项无保留范围，按台账规则直接归档至[完成档案](BACKLOG_COMPLETED.md#已完成事项)，主台账表行仍 **185**（BUG 83 / FEAT 64 / DEV 38）；编号新增 BUG-125—128、DEV-089。本机 Creo 12.4.0.0 GUI 与 `-g:no_graphics` 会话各完成一次板件建模（job `3e57c202…` 29332.6105317228 vs 29332.61056745 mm³、job `907995ee…` 12475.327397219 vs 12475.3274122872 mm³，保存重载 verified），`direct`/`desktop` 两路径均 `toolkit_code=0`。全量 3570 项单测 3567 通过；`unit.test_inspection_only_admission` 3 项在本机因 `.tmp` 下 `runner.log` 被占用（`WinError 32`）失败，未含本版改动的基线同样复现，属本机环境问题。随 **0.24.1** 发布，四附件与 sidecar 远端核对见[发布记录](validation/RELEASE-0.24.1.md)，未测范围见[证据](validation/STARTUP-HEADLESS-2026-11-13.md)。

2026-11-13 [DEV-088](work-items/DEV-088.md)：明确开发 AI 自主承担参照取样、取树、单变量对照、引用重绑与重建/独立验收，不让维护者代做技术判断；离线核验、四情境只读试用和终审通过，移入[完成档案](BACKLOG_COMPLETED.md)。保留当次实机确认与缺口报告，本次未编译或真实取样。

2026-11-13 [DEV-087](work-items/DEV-087.md)：为不熟悉机械/Creo 的软件维护者补白话变更说明，按目标、因果、前后行为、独立预期与未证明范围汇报；两例历史说明、独立只读试用/局部复验及终审通过，移入[完成档案](BACKLOG_COMPLETED.md)。只改资料，保留其它任务现场；未编译或实机。

2026-11-13 [DEV-086](work-items/DEV-086.md)：参考后台 Java 建模案例，按本项目契约原创补充设计意图、实际几何/坐标、分层验收、源快照及原生文件依赖交付指导；skill/链接/台账检查与独立试用/终审通过，无保留范围，移入[完成档案](BACKLOG_COMPLETED.md)。未复制上游代码/模型/教材，未编译或实机；保留其它任务工作区改动。

2026-11-13（0.23.2 球鼻艏反馈批）：归档下载目录 `反馈包-球鼻艏-20261112` 全部 30 个文件到 [feedback-0.23.2-2026-11-12](validation/feedback-0.23.2-2026-11-12/MAPPING.md)（SHA256 与包内 `MANIFEST-SHA256.txt` 逐条比对通过），并建立[分批计划](superpowers/plans/2026-11-13-feedback-0232-bulb-loft.md)；新增 [BUG-121](work-items/BUG-121.md)、[BUG-122](work-items/BUG-122.md)、[BUG-123](work-items/BUG-123.md)、[BUG-124](work-items/BUG-124.md)、[FEAT-067](work-items/FEAT-067.md)，表行 180→**186**（BUG 79→83 / FEAT 63→64 / DEV 38→39，含同日登记的 DEV-088）。A 批离线交付：只读型计划自动按只读准入并为写计划失败补动作提示（BUG-121）、按同一 worker 实测签名在提交前拒绝 `surface_loft`（BUG-122）、计划级 `bbox_mm` 断言（FEAT-067；`surface_area_mm2` 于同日补齐并取得两态实机回执）。模板 XML（BUG-123）的 B1 导出、B2 原生 loader、B3 双路线一致性已于同日全部完成并在 Creo 12.4 实机验收：`tools/test_loft_template.py --live` 11 项全 PASS（手写树 `ea2ac599…` 1600.0 mm² vs 模板 `d590b87b…` 1600.0 mm²，相对差 0.0；负例 `49a9b065…` `TEMPLATE_SHAPE_MISMATCH`、`6fb40ac1…` `TEMPLATE_TREE_LOAD_FAILED` 均未留特征）；STEP/IGES 导入（BUG-124）离线实现完成（schema/计划准入/原生 `ProIntfimportModelWithOptionsMdlnameCreate` 建 part/19 项单测），门禁已于同日后续删除并在 12.4 实机两轮导入中验收（STEP `c725cca7…` 440.0 mm²、IGES `11823392…` 1540.0 mm²，均保存重载通过，详见 BUG-124 行）。A 批同日补 12.4 实机回执（`build/live_acceptance_20261113T160310` 14 项全 PASS：只读导出记 `readonly_source`、bbox 与面积断言各两态、同一模型连续两次放样不误拒；更早 `...T150422` 10 项同结论）；B 批在用户当次确认下连接 Creo 12.4 建模。本批已随 0.24.0 发布（[RELEASE-0.24.0](validation/RELEASE-0.24.0.md)），四附件与两个 sidecar 远端核对通过；`bridge.py build` exit 0，全量单测 3548 项通过。

2026-11-12 [DEV-085](work-items/DEV-085.md)：完成外部 Creo skill 评估，按本机 12.4 SDK 独立补充对象/遍历/装配引用/字符串/多实体/辅助函数专题与按需路由；离线核验、独立试用和终审通过，移入[完成档案](BACKLOG_COMPLETED.md)。未复制上游原文或代码，未编译、实机或发布。

2026-11-12 [DEV-084](work-items/DEV-084.md)：完成中文 TOOLKIT 开发指南、项目 skill 与入口；离线查证、文档核验及独立只读试用/终审通过，无保留范围，移入[完成档案](BACKLOG_COMPLETED.md)。本批仅本地开发资料，未编译、未连接 Creo、未合入 main 或发布。

2026-11-13（0.23.0 反馈批）：归档下载目录 `0.23.0` 四份原件到 [feedback-0.23.0-2026-11-12](validation/feedback-0.23.0-2026-11-12/MAPPING.md)。[DEV-083](work-items/DEV-083.md) 门禁补强：逐 ID 状态归一化、主台账列精确比对、工作卡 `分类：` 粗体比对、活动交付行全表扫描、可选「差异说明」列；发布说明/发布记录/POSTCHECK 增加本地相对链接存在性检查，并修正 0.23.0/0.23.1 两处断链。[BUG-120](work-items/BUG-120.md)：Creo 10 `surface_loft` 创建后 `ProFeatureElemtreeExtract=-18`，本轮交付 `SURFACE_LOFT_EXTRACT_UNSUPPORTED` 诊断、`feature_incomplete`/`kernel_evidence` 回执与 `kernel_completion` 只披露能力字段；模板 XML/导入未排期。表行 179→**180**（BUG 79 / FEAT 63 / DEV 38）。随 **0.23.2** 交付。

2026-11-12（0.22.0 反馈批）：归档下载目录 `0.22.0` 两份反馈。[BUG-119](work-items/BUG-119.md)：已有实体的模型上 `surface_loft` 因模型级 `has_solid` 被误判为创建实体而回滚，改为比较操作前后的实体状态、带材料实体数与体积增量，回执新增前后快照字段。表行 178→**179**（BUG 78 / FEAT 63 / DEV 38）。Creo 12.4.0.0 实机（用户当次授权）：`tools/test_surface_loft_existing_solid.py --live` 8 项全 PASS（job `76d69c9c…`，体积 60000→60000 mm³、材料体 1→1、面积 5026.548245743668 mm²、开放 quilt、保存重载 verified）；`tools/test_surface_loft_planes.py --live` 13 项全 PASS（YZ@X=0/50 为 6283.185307179587 mm²、XZ@Y=0/40 为 5026.548245743668 mm²）；`tools/test_surface_loft_guides.py --live` 全 PASS，门禁改动未回归既有放样。发布流程新增机器门禁（[DEV-083](work-items/DEV-083.md)）：`package.py` 与 `check_release_assets.py` 对 0.23.1 起拒绝过期或含占位词的包内 POSTCHECK/发布记录，`tools/check_release_records.py` 供预检；9 项门禁单测通过。随 **0.23.1** 发布：`main` 提交 `3d250ac`、附注标签对象 `fbd6a56`、Release id `442581848`，四附件经 `--tag v0.23.1` 核对通过；源码包解压后 `Ran 3443 tests ... OK (skipped=6)`。

2026-11-12（0.21.0 反馈批）：归档下载目录 `0.21.0` 三份原件（[manifest](validation/feedback-0.21.0-2026-11-11/manifest.json)、[MAPPING](validation/feedback-0.21.0-2026-11-11/MAPPING.md)）。P1 门禁修复归 [DEV-082](work-items/DEV-082.md)：`surface_loft`/`surface_boundary_fill` 从「是否有 `Probbl.h`」改为 `MECHDOG_HAS_BNBLN_TREE`（`ProElemId.h` 的五个元素 ID），worker 与能力文案同步。新增 [FEAT-066](work-items/FEAT-066.md)：`sketch` 接受 `b_spline`（degree/control_points/knots/weights），映射 `Pro2dBSplinedef` 精确复现 NURBS。表行 177→**178**（BUG 77 / FEAT 63 / DEV 38）。P3-4 更正 `RELEASE-0.20.0.md` 的「不触及 native」措辞。用户当次授权后在 Creo 12.4 实机验收：`tools/test_b_spline.py --live` 20 项全 PASS（控制点回读偏差 2.6e-31 mm、两截面面积 1058.017278 mm² 对齐独立 de Boor oracle 1058.017814 mm²、保存重载一致），`tools/test_surface_loft_guides.py --live` 全 PASS。证据 [feat066-b-spline-2026-11-12](validation/feat066-b-spline-2026-11-12/EVIDENCE.md)。已随 **0.23.0** 发布（提交 `0cfd429`，标签 `v0.23.0`，[Release](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.23.0)，四附件核对通过）。

2026-11-08：[DEV-076](work-items/DEV-076.md)在当前分支合入本地v0.18.4并修三件反馈。标签导入时实际表行为166（原文167偏大1）；新增本卡后实际为167，不是沿用错误数字。该句为DEV-076时点，尚未合main或发布。

2026-11-08：本分支合并已发布的 [v0.19.0](validation/RELEASE-0.19.0.md)（DEV-074 曲面与整链批），保留 DEV-076/DEV-077 与另一 AI 的工作树改动；本分支自身仍未合 main、未发布。

2026-11-08：[DEV-077](work-items/DEV-077.md)对比下载目录0.18.2的四份反馈，归档原件、回填RELEASING逐ID表与POSTCHECK v0.18.2四附件数据、补台账计数门禁及两项离线诊断修复；新增本卡后当前表行为168。未完成项见[接手清单](development/DEV-077-HANDOFF.md)。同样未合main或发布。

2026-11-08：DEV-076/DEV-077 的 0.19.1 子项已合入 main 并发布 [v0.19.1](validation/RELEASE-0.19.1.md)：worker 构建身份/`surface_loft` 动态准入、overlap 预算/覆盖诊断、trim 结果句柄与连续 trim、`rotation_tolerance`、`get_job` 300 s、`known_limitations`/`plan_examples`；公开工具仍 107。R01—R08 剩余项与未测范围见[DEV-077-HANDOFF](development/DEV-077-HANDOFF.md)。

2026-11-08：[DEV-079](work-items/DEV-079.md)归档下载目录0.19.0的三份Creo 10反馈并完成离线补漏：quilt_merge公开描述、曲率默认摘要/`include_samples`、surface_group结构化失败回执、`profile.method`与POSTCHECK旧句；新增本卡后当前表行为170。随 0.19.2 发布（提交`df8e178`，[Release](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.19.2)），四附件核对 exit 0；Creo 10原生能力与钣金余项见[对照表](validation/feedback-0.19.0-2026-11-08/MAPPING.md)。

2026-11-08：[DEV-080](work-items/DEV-080.md)接手上述三份报告复核后仍未闭环的H01—H09及未编号缺口；首批离线收口为手写TU头门控契约测试、COMPATIBILITY缺头降级说明、台账计数自检进CI；新增本卡后当前表行为171。开发分支`codex/DEV-080-feedback-0190-followup`，未合main、未发布；原生/实机项按依赖留卡。

2026-11-10（0.19.3 反馈批）：归档下载目录 `0.19.3` 四份原件（[manifest](validation/feedback-0.19.3-2026-11-10/manifest.json)、[MAPPING](validation/feedback-0.19.3-2026-11-10/MAPPING.md)）并建立[分批计划](superpowers/plans/2026-11-10-feedback-0193.md)；新增 [BUG-116](work-items/BUG-116.md)、[BUG-117](work-items/BUG-117.md)、[FEAT-065](work-items/FEAT-065.md)、[DEV-082](work-items/DEV-082.md)、[DEV-083](work-items/DEV-083.md)，表行 172→**177**（BUG 77 / FEAT 62 / DEV 38）。A 批离线交付：draft 中性面示例与两形式语义、原生 `failed_reference` 与候选数、`feature_state` targets 可读拒绝与重提提示、`-36` 多会话恢复文案、`surface_boundary_fill` 缺头门控与跨 TU 符号契约测试、POSTCHECK `## v0.20.0` 段与发布记录措辞更正。本批未连 Creo、未做故障注入、未重发版本；`bridge.py build` 成功，`-DMECHDOG_HAS_PROBBL_HEADER=0` 聚合语法检查 EXIT=0，实机与 Creo 10 SDK 整包编译未验。

2026-11-10（0.19.3 反馈批 B）：[FEAT-033](work-items/FEAT-033.md) 交付受控作业预算——`creo_execute_plan(timeout_seconds)` 60—7200、默认保持服务配置，job 回执与 `request.json` 冻结生效值与来源（`timeout_source=job|server`），native 子进程与看门狗 `expected_lifetime_seconds()` 同用该值，超时回执点名实际预算；[BUG-115](work-items/BUG-115.md) 只补诊断（`ProFeatureGeomitemVisit` 失败带 ProError 与「引用原始 target / quilt 几何 ID」替代方式）；[FEAT-039](work-items/FEAT-039.md) `project_curve` 两段创建失败分别指名步骤 1/2。分类调整：FEAT-033 由「待规划」移入「部分交付，剩余待规划」（自动公式与到期动作仍待规划），计数 待规划 43→42、部分交付剩余待规划 2→3，总数仍 177。本批未连 Creo；`bridge.py build` 成功，新增 `tests/unit/test_execute_plan_budget.py` 16 项通过，实机与 WorkBuddy 未验。同日续：[FEAT-018](work-items/FEAT-018.md) 交付只读 `completion_review`（五档 verdict + signals + 建议动作，固定不授权重放/改 revision），新增 `tests/unit/test_recovery_completion_review.py` 11 项；[FEAT-039](work-items/FEAT-039.md) 的 `quilt_merge` 拒绝回执补 target/tool id、面积与接触提示；[FEAT-065](work-items/FEAT-065.md) 完成 SDK 常量核对并拆 M1（同方向多截面，复用 `surface_loft` 的 1DIR 骨架）/M2（导线+任意正交平面，需实机元素树实验）。

2026-11-11：用户当次确认可用 Creo 测试后实施 [FEAT-065](work-items/FEAT-065.md) M1（同方向 2—32 截面 straight）：`SurfaceLoftOp.sections` 放宽到 32、原生按序解析全部截面并拒绝重复、回执加 `section_count`、能力与参考文案同步、新增 `tools/test_surface_loft_multisection.py`；离线 PASS，`tools/dev_check.py --work-item FEAT-065` 为 `success=true`、`Ran 3306 tests`、无新增回归。实机**未验收**：Creo 12.4 进程在跑（`parametric`/`xtop` 08:12 启动）但无窗口，协调器停在 `waiting_for_connection`，worker 探测 `toolkit_code=-4`（找不到已注册会话，非 `-36`），`nmsd` 监听 127.0.0.1:1239；按规则未结束/重启 Creo、未清锁。分类调整：FEAT-065 由「待规划」移入「部分交付，剩余待规划」，计数 待规划 42→41、部分交付剩余待规划 3→4，总数仍 177。

2026-11-11（FEAT-065 M1 实机验收）：用户重启 Creo 后协调器 10:46:22 到 `ready`（首次尝试因 Creo 无窗口/未注册会话返回 `-4`，非 `-36`，未结束或重启 Creo、未清锁）。`tools/test_surface_loft_multisection.py --live --confirm-session-usable` 30 项全 PASS：三截面 `job bd976c4c…`（模型 `f16d2075…`，revision 1）面积 2101.2524427513217 mm²、开放 quilt、`section_count=3`、无实体、保存重载后 id 与面积一致；thicken `job f40d0a73…`（revision 2）体积 4202.507981502071 mm³ = 实测面积×2；两截面回归 `job 7c6c80a4…`（模型 `52d39f1c…`）800.0 mm²、`piecewise_ruled=true`。据实测把 `interpolation` 扩为 `straight|smooth`（3 截面以上强制 smooth，straight 在提交前拒绝），回执新增 `section_count`/`piecewise_ruled`，能力 `limits` 写入实测数值。全量 `tools/dev_check.py --work-item FEAT-065` 为 `success=true`、`Ran 3307 tests`、无新增回归；报告 `build/surface_loft_multisection/20261111-104718.json`。M2 与 Creo 9/10 仍未验。

2026-11-11（0.21.1 交付）：[BUG-118](work-items/BUG-118.md) 修复 compact 预算裁剪丢曲面放样测量值——`OUTCOME_OPERATION_KEYS`（面积/闭合/计数/曲线与夸特 ID 等标量）并入保护集合，大块 `profile`/`surface_group`/`native_section` 仍可裁、`RESPONSE_BUDGET` 32 KiB 上限不变；`tools/test_surface_loft_guides.py` 的 3 截面 + 2 导线用例由 2 项 FAIL 转为全 PASS（job `2a2ee086…`，1599.9999999999995 mm²、单张开放 quilt、保存重载 verified），同批回填 0.21.0 的 3 截面复跑与发布记录。发布结果：`main` 提交 `8622f1b`（`origin/main` 同值），附注标签 `v0.21.1`（`f2ffc75`），[Release v0.21.1](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.21.1) 非 draft 非 prerelease，四附件逐个上传，`tools\check_release_assets.py --tag v0.21.1` exit 0 且两个 sidecar 与对应 ZIP 摘要一致；源码包解压后全量单测 `Ran 3315 tests ... OK (skipped=5)`。BUG-118 直接归入[完成档案](BACKLOG_COMPLETED.md)，未占用活跃表行，计数仍 177（BUG 77 / FEAT 62 / DEV 38）。未测：其他可能被整体剥掉的 op 类型、保护标量后的极端预算压测、Creo 9/10 与 WorkBuddy。

2026-11-11（FEAT-065 M3/M4 登记）：用户确认本轮范围后，[FEAT-065](work-items/FEAT-065.md) 登记 M3（`surface_loft` 截面/导线接受已有曲线、边与首末收敛点）与 M4（边界相切/曲率条件），并在开发分支 `codex/FEAT-065-m3-m4-surface-loft` 建立[计划](superpowers/plans/2026-11-11-feat065-m3-m4-surface-loft.md)（T0 文档对账、T1 M3、T2a M4 离线候选由子 agent 实施，T2b 参照树取证与 T3 实机须用户当次确认）。分类调整：FEAT-065 由「部分交付，剩余待规划」移入「开发中」，计数 部分交付剩余待规划 4→3、开发中 7→8，总数仍 177。登记时未连 Creo、未编译执行器、未合 main、未发布。

2026-11-11（FEAT-065 计划 T0 文档对账）：逐分节统计表行，发现 [FEAT-033](work-items/FEAT-033.md) 的「当前状态」为「部分交付，剩余待规划」，行却仍在「待规划」分节（2026-11-10 B 批已按该移动调整计数，表行未随之移动），致「部分交付，剩余待规划」分节只有 2 行、「待规划」分节 42 行。现把该行移入「部分交付，剩余待规划」分节；分类表数字不变（部分交付剩余待规划 3、待规划 41），九个分类与各分节行数逐类一致，总数仍 177（BUG 77 / FEAT 62 / DEV 38）。同次按 [FEAT-065](work-items/FEAT-065.md) M1/M2（0.21.0）更正 FEAT-009 行的多截面口径，该行仍留「待规划」分节。只改文档，未连 Creo、未改代码。

2026-11-11（FEAT-065 M3/M4 实机验收）：用户当次授权后，在本机已运行的 Creo 12.4.0.0 上完成实机验收（未结束或重启 Creo、未清锁、未做故障注入）：M3 输入验收驱动实机 40 项全 PASS；M4 相切用试值法取证（23 组，未建参照件，临时实验钩子未提交），测得相切为 `TAN_COND_TYPE` 2 加 `STRETCH`（首 -1、末 +1）、`TNC_BNDRY` 下标 0/1 分别为首/末截面；最终代码由新驱动 `tools/test_surface_loft_continuity.py` 复核，实机 59 项全 PASS，两条接缝 G1 0.0°。证据见 [T2b](validation/feat065-t2b-tangency-2026-11-11/EVIDENCE.md) 与 FEAT-065 工作卡。未合 main、未发布；计数不变，仍 177。

2026-11-11（发布 0.22.0）：[FEAT-065](work-items/FEAT-065.md) M3/M4 连同 `open_edge_records` 按 MINOR 发布（[版本说明](RELEASE_NOTES_0.22.0.md)、[发布记录](validation/RELEASE-0.22.0.md)）：`surface_loft` 的截面与导线接受已有曲线和 quilt 边、首末截面可用收敛点，新增 `boundary_conditions` 的边来源 `tangent`（`TAN_COND_TYPE` 2、`STRETCH` 首 -1/末 +1，接缝 G1 0.0°），`creo_measure_surface_group` 回执列出开放边 ID；公开工具仍 107。发布前在用户当次授权下重启了未注册名字服务器的 Creo 会话（原会话 `toolkit_code=-4`、未提交几何），随后在最终代码上复跑旧驱动：M1 离线 9 + 实机 21、M2 离线 12 + 实机 22、两截面 22 项、五爪整瓶 63 项全 PASS；`test_multi_quilt_group.py` 44/45，唯一 FAIL 是自 0.19.0 起过时的「拒绝且无 job_id」断言（原生错误文本与 0.18.4 证据逐字相同，非本版回归，未改测试语义）。离线 `dev_check` `success=true`、3413 项 0 失败；源码包解压后 `Ran 3413 tests ... OK (skipped=6)`。FEAT-065 由「开发中」移入「待规划」（剩余未排期），开发中 8→7、待规划 41→42，总数仍 177。

2026-11-11（0.22.0 发布结果）：`main` = `origin/main` = `2de2fa8d4e48a8ea0dbadb6c7c4cd7058513f280`（`ea753be..2de2fa8`），附注标签 `v0.22.0`（对象 `e2e33bd1`）指向该提交，[Release v0.22.0](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.22.0)（id `441943346`，非草稿非预发布，`published_at=2026-11-11T16:35:24Z`）；四附件源码包 9 636 010 字节 `5db68fe9…af3ab`、种子包 493 442 字节 `9fe456f2…6e7743` 及两个 sidecar，`tools\check_release_assets.py --tag v0.22.0` exit 0。历史标签 `v0.22` 与 `docs/RELEASE_NOTES_0.22.md` 未改动。

2026-11-10：用户当次确认可发布 `main` 新版本并选定 MINOR 后，[DEV-081](work-items/DEV-081.md) B 批四项连同 C1 契约冻结与 BUG-001 规则修订按 0.20.0 发布（[版本说明](RELEASE_NOTES_0.20.0.md)、[发布记录](validation/RELEASE-0.20.0.md)）：B1/F01 seed 兼容性前置预检与无 callback 路线说明、B2/F11 零去料切除结构化几何回执、B3/F06 compact 阶段进度与日志体积字段、B4/F08 选择性切除作用域公开 `scope` 参数与 `scope_applied` 特征树回读，均在 Creo 12.4.0.0 + 匹配 SDK 实机验收。B4 实机：两实体零件只切 body 52（面数 6→8），body 90 面数与包围盒不变，总体积 39214.6018 mm³ = 40000 − 250π，保存重载通过，未知 body id 失败回滚且 revision 不前进。公开工具仍 107，新增参数不新增工具，按 MINOR 递增。未完成项：B5/F09 着色预览与 B6/F10 锥台未实现，C 批 WorkBuddy 黑盒未执行，Creo 9/10 未复测，B4 的回读不匹配路径、装配内切除、三体以上与 compact 32 KiB 预算未验。计数仍 172（BUG 75 / FEAT 61 / DEV 36）。发布结果：`main` = `origin/main` = `2d7b498cd793a3f4693a561df6ae0df8f809d0f7`，annotated 标签 `v0.20.0`（`3f4ed82`）指向该提交，Release <https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.20.0>（id `RE_kwDOU_ueTM4aPLew`，非草稿非预发布，2026-11-10T09:56:06Z）；四附件源码包 9 398 084 字节 `896e03ff…c83d`、种子包 493 442 字节 `6cde6888…0697` 及两个 sidecar，`check_release_assets.py --tag v0.20.0` exit 0；源码包解压后全量单测 `Ran 3263 tests ... OK (skipped=5)`。
2026-11-09：按用户决定修订本机实机测试放行条件，[BUG-001/FEAT-018 工作卡](work-items/BUG-001-FEAT-018-RECOVERY.md)追加「用户明确确认后即可用 Creo 进行实机测试」，不再以卡死根因核对/事前会话可操作判定为阻断前置；根因未定、历史失败与恢复原件仍逐字节保留，安全底线（不擅自结束Creo/清锁或unknown保护、故障注入需单独授权）不变，确认按次生效。当前规则见 [AGENTS.md](../AGENTS.md) 与 [DEVELOPMENT.md](DEVELOPMENT.md)。本条为规则修订，不新增ID、不改计数（仍172），未合main、未发布；本轮未据此执行任何 Creo 实机测试。

2026-11-09：[DEV-081](work-items/DEV-081.md)归档第四份0.19.0反馈（护卫舰重建，报告P1—P11映射F01—F11），建立[MAPPING](validation/feedback-0.19.0-frigate-2026-11-08/MAPPING.md)与[离线批次实施计划](superpowers/plans/2026-11-09-feedback0190-frigate-offline.md)；A批离线六项（F02/F03/F07/F04回执/F11文档契约/F05限制说明）已交付并逐任务独立审查，统一dev_check通过。同日补[B/C批子计划](superpowers/plans/2026-11-09-feedback0190-frigate-bc-batches.md)与 WorkBuddy 黑盒提示词，实机/黑盒仍未执行；[DEV-080](work-items/DEV-080.md)首批离线收口与台账一并提交。新增本卡后当前表行为172；本批不改公开工具签名、未连Creo、未编译原生、未合main、未发布。

2026-11-09：上述 12 个开发分支提交连同版本元数据合入 `main`，按 PATCH 发布 [v0.19.3](validation/RELEASE-0.19.3.md)（[版本说明](RELEASE_NOTES_0.19.3.md)，公开工具仍 107）：DEV-081 A 批离线六项与 B/C 批规划、DEV-080 首批离线收口、BUG-001 实机放行规则修订及台账/证据同步。本批未连 Creo、未编译原生、未执行 WorkBuddy 黑盒；B1—B6 原生/实机与 C0—C5 黑盒仍开放。标签指向合入后的 `main` 提交，四附件与两个 `.sha256` sidecar 由该提交源码生成，发布后运行 `tools\check_release_assets.py --tag v0.19.3` 核对。计数仍 172（BUG 75 / FEAT 61 / DEV 36）。发布结果：`main` 提交 `096e86a`（`origin/main` 同值），附注标签对象 `61d1d2b`，[Release v0.19.3](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.19.3) 已发布（非 draft），四附件逐个上传，`tools\check_release_assets.py --tag v0.19.3` exit 0 且两个 sidecar 与对应 ZIP 摘要一致。

建立：2026-10-13；最近复核：2026-11-13（0.23.2 发布，[BUG-120](work-items/BUG-120.md) Creo 10 提取诊断与 [DEV-083](work-items/DEV-083.md) 状态/链接门禁补强）。本文件是唯一当前台账，按“开发入口 → 本表 ID → 工作卡当前摘要 → 相关源码”读取，历史证据按需打开。当前源码版本以 [version.py](../version.py) 为准；逐版交付记录见 [版本说明目录](../README.md) 与 `docs/validation/RELEASE-*.md`，不在本表重复回填。

DEV-073 以 `1cf9d3f` 为基点整理台账，随后并入 0.18.0 发布提交（[RELEASE-0.18.0](validation/RELEASE-0.18.0.md)）。0.18.0 已发布的结论以该发布记录与远端 Release 核对为准。DEV-074 的 0.18.3 子项交付以 [0.18.3 发布记录](validation/RELEASE-0.18.3.md)为准，0.18.4 子项以 [0.18.4 发布记录](validation/RELEASE-0.18.4.md)为准，0.19.0 子项以 [0.19.0 发布记录](validation/RELEASE-0.19.0.md)为准；两版发布状态来源和空白字段勘误以[统一POSTCHECK](development/RELEASE-POSTCHECK-2026-11-07.md)及其所链新勘误为准。

## 使用与计数

每个 ID 仅一行，保留优先级、当前状态、剩余工作和工作卡入口。目标版本统一表示剩余范围的安排，已交付子项版本/日期保留在工作卡；未分配的新工作不继承旧已发布目标。无独立卡的存量 ID 链接至完成档案的原登记，本轮不批量补卡。

诊断交付不等于根因修复；部分交付不关整卡；缺其他版本证据不自动判未修。观察项等自然新现场，不制造故障。已完成且无保留范围的行移入 [完成档案](BACKLOG_COMPLETED.md#2026-11-07dev-073-归档与历史进展)。原进展/证据保留日期，不再回填第二份待办。小修复沿用卡与证据，复杂跨模块任务才另建完整计划。

当前唯一 ID **192**（BUG **86**、FEAT **66**、DEV **40**）；2026-11-07整理时移入完成档案23项（含DEV-073、DEV-075），该句为历史时点，归档项不计入当前行数。DEV-077起运行 `python tools/check_backlog_counts.py` 自检声明行、表行与分类表三方计数，不一致exit 1；该脚本只校验计数，不替代逐ID人工核对。

| 当前分类 | 唯一 ID 数 |
| --- | --- |
| 仍需修复 | 6 |
| 待复现/待核实 | 33 |
| 已有修复但待验收 | 30 |
| 观察中 | 3 |
| 其它 agent 处理范围 | 20 |
| 开发中 | 7 |
| 部分交付，剩余待验收 | 42 |
| 部分交付，剩余待规划 | 7 |
| 待规划 | 44 |

BUG 分类是互斥主分类；“其它 agent”行仍写明已完成子项与真实缺口，勿重复派工。

## 仍需修复

| ID / 工作卡 | 优先级 | 当前状态 | 目标版本 | 简短剩余工作 / 依赖 |
| --- | --- | --- | --- | --- |
| [BUG-017](work-items/BUG-017.md) | P1 | 仍需修复 | 未排期 | 取得外部最小输入及 Creo 9 原生失败码，定位并修复或明确支持边界；现有修复仅覆盖子项，原案/规则未闭环。 |
| [BUG-034](work-items/BUG-034.md) | P1 | 仍需修复 | 未排期 | 定位种子生产版本及原生加载失败，决定可追溯重生方案；依赖：需 Creo 9 SDK/许可与种子来源。 |
| [BUG-036](work-items/BUG-036.md) | P1 | 仍需修复 | 未排期 | 核对实际约束、求解调用与 transform，修正写侧或给出明确拒绝；现有修复仅覆盖子项，原案/规则未闭环。 |
| [BUG-130](work-items/BUG-130.md) | P1 | 已修复（bulb 偏差 0.0899mm 达标；旧 14m 0.1115mm 未达标） | 0.27.0（偏差子项）；旧 14m 余项下个版本 | 约14m复杂球鼻艏 `export(stl)` 两次worker `0xC0000005`，整件剖分及外层计数返回成功后退出、STL均0字节；旧同尺度球鼻艏197118片/48.85MB成功，不能仅归因尺度。2026-11-17 离线：`tools/diagnose_stl_export.py`、`STL_*` 阶段日志与防护、`native/stl_file_check.h`/`native/stl_export.h`/`native/stl_mesh_check.h`、23+19 项 native 用例。旧路径只读实机定位 `n_facets=201551` 配 `facets=null`，安全失败且源件不变；官方路径小件成功，旧 14m 同质量 600 秒未完成。重启后恢复基线，逐面导出并做 SDK 法向对齐、0.001mm 焊点与边界环质心补洞、1e-9mm 精确邻接绕序修复：`bulb_bulged` 404,652 片/82,166,002 字节、旧 14m 197,722 片/40,068,497 字节，均 succeeded、源件 SHA/revision 不变；焊接后边界边 0、非流形边 0、零面积片 0，有符号体积与原生差 0.0030%/0.0172%，包络一致；trimesh 独立复核两件 `is_watertight=true`、`is_winding_consistent=true`、`euler_number=2`。默认路径已切换为逐面，官方路径保留 `MECHDOG_STL_OFFICIAL_FILE=1` 诊断。抽样偏差实测（`MECHDOG_STL_DEVIATION=1`，每 500 片取质心/边中点投影回原生面，顶点自检 ≤0.004mm）：bulb 平均 0.0367mm、p99 0.1378mm、最大 0.1581mm；旧 14m 平均 0.0814mm、p99 0.3002mm、最大 0.3086mm，**0.1mm 目标未达成**。逐面片数回执定位根因：bulb 在 0.05 与 0.005mm 弦高下大面均为 ~204,000 片（0.005 时 203,988/204,043/1,761），单面片数上限约 20.4 万；同几何小件（未到上限）0.05→0.001mm 片数 328→1,488，证明弦高参数本身有效、不是会话缓存。Task 6 已完成：`creo_export_model(format="stl", stl_options={"chord_height_mm":…,"angle_control":…})`，仅 STL 允许，未知键/布尔/NaN/Inf/越界提交前拒绝，缺省保持 0.05/0.1，回执保留 `requested`/`passed` 并新增逐面 `surface_facets`；9 项单测通过。剩余：装配、Creo 9/10 与其他质量入口未测；受单面上限约束，逐面路径无法把大面细化到 0.1mm 以内。计划见 [bug130-stl-export](superpowers/plans/2026-11-16-bug130-stl-export.md)。 |
| [BUG-131](work-items/BUG-131.md) | P1 | 仍需修复（取消/收尾/看门狗已实机；挂死根因未验） | 0.27.0（作业控制子项）；挂死根因未排期 | 23组件带配合总装作业 `1ce57484…` 在 `hom_1` 选择器解析挂死 60 分钟，同输入 2 组件探针 9.4 秒结构化失败；装配 `unknown_outcome` 后 reconcile 曾全不可用。已离线交付进度观测、`creo_cancel_job`（公开工具 108→109）、worker 日志停滞看门狗与 `revision==0` 新装配出口。2026-11-17 本机 Creo 12.4 临时件实机：worker 启动前取消 `cancelled`/`geometry_may_have_changed=false`，启动后取消 `unknown_outcome`/`true` 并终止 pid，两种均经 `abandon_new` 收尾；当次授权下 1 秒预算 + 500 圆孔重计划触发看门狗，`stall_watchdog` 记录 budget/silent/log_bytes/termination 并收尾。修复空 owner 误判与 stall_watchdog 未投影；`test_job_control` 19 项、投影 1 项。`revision==0` 新装配实机未复现；挂死根因仍需 Creo 10 栈/轨迹。 |
| [BUG-132](work-items/BUG-132.md) | P1 | 仍需修复（本机 Creo 12.4 已验报错分型与 coaxial insert；Creo 10/Arm7 未验） | 0.27.0（选择器子项）；Creo 10/Arm7 未排期 | native 圆柱面拆成两半（base 198/200、hom 57/59、96/98、224/226），TXT 整圆柱锚点无法唯一命中；报错把「消歧点落在端面平面」写成「add radius_mm」。已离线交付：零/多/类型不符三种报错分型（逐项列 `id (plane|cylinder)`，说明 `radius_mm` 非类型过滤器）、组装侧选择器缺 `assembly_component` 的准入预检、仅 `insert/concentric` 可用的显式 `coaxial:"any"`（多个圆柱命中取最小 id，默认唯一性不放宽），两个测试文件 39 项通过。2026-11-17 本机 Creo 12.4：R27.5 通孔拆半 102/103，三种报错分型实机通过并 `rolled_back`；默认 insert 拒绝并列出 102/103，`coaxial:"any"` insert+mate `committed`、`underconstrained=false`、轴共线，显式保存重载 5→6。Arm7 原半圆柱与 Creo 10 未验。 |

<a id="输入或规则待核实"></a>

## 待复现/待核实

| ID / 工作卡 | 优先级 | 当前状态 | 目标版本 | 简短剩余工作 / 依赖 |
| --- | --- | --- | --- | --- |
| [BUG-129](work-items/BUG-129.md) | P1 | 部分交付，剩余待验收 | 0.27.0（宽度映射文档子项）；Arm2 未排期 | 已加宽度方向断言、回执方向/原生质心与冲突拒绝；实机 YZ 140×290×1.5 宽向 `[0,0,1]`、bbox/质心符合、期望 `[1,0,0]` 被拒，见实机验收。0.26.0 补：独立工具 `creo_sheetmetal_base_flange` 已补方向断言参数（离线）。2026-11-17 离线收口：REFERENCE_SYNTAX 明确 XY→+Y、XZ→+Z、YZ→+Z 的 width 映射，docstring 同步“只断言不旋转”；`width_axis` 控制另立 FEAT，未在本卡静默实现。剩余：Arm2 原模型/placement 契约、Creo 12.4/10 实机复测。 |
| [FEAT-069](work-items/FEAT-069.md) | P2 | 部分交付，剩余待验收 | 0.27.0（区域适配层子项）；原生选区未排期 | 已交付 `region_selection` 契约：三套原始签名、frame `(1.5,v,-u)` 校验、无序/反向等价、重复/歧义/零命中拒绝，`region_index_hint` 不参与。0.26.0 复核真实 TXT 三签名解析与唯一匹配通过；新增 `ExtrudeOp.region` + 派生草图适配（准入前展开、实体原样复制、`region_adaptation` 回执，离线 24 项），源草图须为坐标草图且只支持简单闭环。原生选区、实机去料与 Creo 10 未验。 |
| [BUG-004](BACKLOG_COMPLETED.md#legacy-bug-004) | P1 | 待复现/待核实 | 未排期 | 核对对象句柄、种子身份、直线/平滑/三截面编辑和重载；依赖：需可用 Creo 12 会话与原始失败输入。 |
| [BUG-011](BACKLOG_COMPLETED.md#legacy-bug-011) | P1 | 待复现/待核实 | 未排期 | 取得状态查询与提交时间线，标明快照时间及实时性；依赖：需真实异常通道现场；禁止主动制造。 |
| [BUG-012](BACKLOG_COMPLETED.md#legacy-bug-012) | P1 | 待复现/待核实 | 未排期 | 区分未尝试/成功/失败/未知；核对新件无检查点和旧字段兼容；依赖：需失败样例与当前回执对照。 |
| [BUG-014](work-items/BUG-014.md) | P1 | 待复现/待核实 | 未排期 | counts=null 与后续查询有值的时点/来源差异及恢复失败路径仍待核对。 |
| [BUG-015](BACKLOG_COMPLETED.md#legacy-bug-015) | P2 | 待复现/待核实 | 未排期 | 以真实 body ID 做干净件/组合件保存重载对照，定位保存阶段；依赖：t30_probe 模型、原生返回与 Creo 会话。 |
| [BUG-016](BACKLOG_COMPLETED.md#legacy-bug-016) | P2 | 待复现/待核实 | 未排期 | 核对 side、工具面与切除语义，做双侧几何、体积及重载对照；依赖：原报告操作输入及 Creo 可用会话。 |
| [BUG-018](BACKLOG_COMPLETED.md#legacy-bug-018) | P2 | 待复现/待核实 | 未排期 | 逐输入结果契约已实施；历史 effect/status 矛盾需按当前返回核对，关联 T02/T13。 |
| [BUG-031](work-items/BUG-031.md) | P1 | 待复现/待核实 | 未排期 | 先建并查询唯一 x=45 平面，再与显式 ID/标签对照；依赖：需 Creo 几何对照。 |
| [BUG-035](work-items/BUG-035.md) | P1 | 待复现/待核实 | 未排期 | 补 shell+孔夹具，对照轴阵列与树依赖、材料体积；依赖：缺完整原模型/leader 历史与 Creo 实机。 |
| [BUG-037](work-items/BUG-037.md) | P1 | 待复现/待核实 | 未排期 | 测尺寸类型×引用数量及端点矩阵；依赖：缺完整草图请求与 Creo 9/12 对照。 |
| [BUG-039](work-items/BUG-039.md) | P2 | 待复现/待核实 | 未排期 | 与 extrude 对照原生 body ID、材料、体积、重载；依赖：曲面来源、厚度、侧及原 job/model。 |
| [BUG-041](work-items/BUG-041.md) | P2 | 待复现/待核实 | 未排期 | 先定普通约束非零 offset 契约，再加准入拒绝或显式转换，验证面距及保存值；依赖：原始约束输入/回读，或构造最小对照的 Creo 会话。 |
| [BUG-048](work-items/BUG-048.md) | P2 | 待复现/待核实 | 未排期 | 补等价特征序列并隔离镜像、顺序、变换和壳引用，取得原生诊断；依赖：原模型、引用、job；可用 Creo 会话。 |
| [BUG-049](work-items/BUG-049.md) | P1 | 待复现/待核实 | 未排期 | 原件取得后同件 gap/snapped 对照，确认多环支持边界；依赖：缺 gear10.json/sketch_entities.json。 |
| [BUG-052](work-items/BUG-052.md) | P2 | 待复现/待核实 | 未排期 | 以已知几何查询 Toolkit 返回语义，再设计兼容的 geometry_type 字段；依赖：平面/圆柱等原生夹具与 Creo 查询。 |
| [BUG-053](work-items/BUG-053.md) | P1 | 待复现/待核实 | 未排期 | 同一快照分段计时及调用计数后再选优化；依赖：缺大模型样本与阶段日志。 |
| [BUG-058](work-items/BUG-058.md) | P1 | 待复现/待核实 | 未排期 | 只在自然现场采集进程、窗口和通道时间线；依赖：需外部 Creo 9 无主窗口现场。 |
| [BUG-060](work-items/BUG-060.md) | P2 | 待复现/待核实 | 未排期 | 核对 schema/resolve 接受的引用类型，明确报错或扩展支持，验证重载；依赖：原始 S6 输入、固定面选择规则与 Creo 会话。 |
| [BUG-061](work-items/BUG-061.md) | P2 | 待复现/待核实 | 未排期 | 与 BUG-031 联查解析路径；明确接受或拒绝并给出 datum_plane 替代；依赖：用户契约决定与 Creo 几何对照。 |
| [BUG-063](work-items/BUG-063.md) | P1 | 待复现/待核实 | 未排期 | 取得外部轴引用形式/原模型并对照修复后 BUG-084；依赖：缺外部 Creo 10 原案。 |
| [BUG-065](work-items/BUG-065.md) | P2 | 待复现/待核实 | 未排期 | 保留 Creo 10 原案待复现；斜交与单平面回归依关联矩阵；依赖：外部原始模型与 Creo 10 环境。 |
| [BUG-066](work-items/BUG-066.md) | P2 | 待复现/待核实 | 未排期 | 取原 Part1/Part2、同作业请求及图像；实机逐图复核失真路径；依赖：原模型、preview.jpg、同作业 JSON。 |
| [BUG-075](work-items/BUG-075.md) | P2 | 待复现/待核实 | 未排期 | 下次自然出现时收集 worker 日志和时序，辨别探针异常/连接竞争；依赖：自然复发时原始探针日志。 |
| [BUG-078](work-items/BUG-078.md) | P1 | 待复现/待核实 | 未排期 | 偶发编辑 -1 未复现；三旧现场待选择 restore_baseline；依赖：现场日志/操作者。 |
| [BUG-081](work-items/BUG-081.md) | P1 | 待复现/待核实 | 未排期 | 自然现场验证 MCP 拒绝时序后决定 alive=None 规则；依赖：缺同型残留 worker/外部 Creo 9 现场。 |
| [BUG-085](work-items/BUG-085.md) | P1 | 待复现/待核实 | 未排期 | 自然事故时采集 nmsd 身份、worker 与源码指纹；依赖：缺原始时序和受控现场。 |
| [BUG-091](work-items/BUG-091.md) | P1 | 待复现/待核实 | 未排期 | 自然现场核对分层事实与外部时间线；依赖：缺真实断连/挂起现场。 |
| [BUG-102](work-items/BUG-102.md) | P1 | 待复现/待核实 | 未排期 | 取得报告方原 surface 69/中性面引用并做单变量对照；依赖：缺外部 Creo 10 原夹具/错误树。 |
| [BUG-106](work-items/BUG-106.md) | P2 | 部分交付（文案+裁定）；实机链路待验 | 0.27.0（离线裁定）；实机复测未排期 | 文案已修；2026-11-17 离线裁定不纳入 `adopt_session_copy`（一致性判定/身份改写/审计边界未冻结，现有两步文案已覆盖可恢复路径），反向断言保持 0 命中。只剩真实同名外部模型的 save/erase 两步链路实机复测。 |
| [BUG-108](work-items/BUG-108.md) | P1 | 待复现/待核实 | 未排期 | 在原 Creo 10 现场取得可复现平移及 accepted_rigid 实例，判断原点固定是否消除位移；现有修复仅覆盖子项，原案/规则未闭环。 |
| [BUG-109](work-items/BUG-109.md) | P1 | 待复现/待核实 | 未排期 | 自然现场取得子阶段时间线以定位阻塞；依赖：缺 Creo 9 真实停滞的 native.log/request.json。 |

## 已有修复但待验收

| ID / 工作卡 | 优先级 | 当前状态 | 目标版本 | 简短剩余工作 / 依赖 |
| --- | --- | --- | --- | --- |
| [DEV-078](work-items/DEV-078.md) | P2 | 离线完成；实机待样件 | 未排期 | 四边双方向填充、独立角释放/quilt成形、多段flange全部门禁已在 2026-11-08 离线交付并冻结，3031单测与SDK12.4编译通过；2026-11-17 复核无离线剩余。剩余全是真实样件/实机：Offset/PunchDie、格栅实测、保存重载/回滚、Creo9/10、非mm、WorkBuddy。 |
| [DEV-076](work-items/DEV-076.md) | P1 | 已有修复但待验收 | 未排期 | H13 worker构建身份/动态准入、H15 overlap预算/覆盖诊断、H16 trim结果句柄与连续trim已在Creo12.4实机通过；H14交线诊断、H17 Creo10直创原件、H18 Creo10同载荷、H19旧原件仍缺；Creo9/10与远端余项见接手H10—H19。 |
| [BUG-010](BACKLOG_COMPLETED.md#legacy-bug-010) | P1 | 已有修复但待验收 | 未排期 | 视图 scale=2 已有成功证据；位置更新、图纸保存重载/revision 仍未验。 |
| [BUG-013](work-items/BUG-013.md) | P1 | 已有修复但待验收 | 未排期 | 摘要/分页已有；模型查询精确32KiB及单项超限未验，不能复用 capabilities 结论。 |
| [BUG-019](work-items/BUG-019.md) | P2 | 已有修复但待验收 | 未排期 | 引用语法主线已验；计划/三入口公开终验仍缺，先核真实请求和部署。 |
| [BUG-028](work-items/BUG-028.md) | P2 | 已有修复但待验收 | 未排期 | 计划入口整数/字符串/混合草图引用的建模/重载待验，校验通过不等于成功。 |
| [BUG-029](work-items/BUG-029.md) | P1 | 已有修复但待验收 | 未排期 | 重排主矩阵及 no-op 已验；原模型重建/复杂多特征树仍待验证。 |
| [BUG-030](work-items/BUG-030.md) | P1 | 已有修复但待验收 | 未排期 | 尺寸编辑主线已验；原报告失败例与受影响回归仍需原件/实机。 |
| [BUG-040](work-items/BUG-040.md) | P2 | 已有修复但待验收 | 未排期 | 补扫掠后状态变化、compact/full、异常查询；保留非活动记录；依赖：原始 sweep job/native JSON；受控 Creo 会话。 |
| [BUG-047](work-items/BUG-047.md) | P1 | 已有修复但待验收 | 未排期 | 两方向折边已验；其它边/串连 flip 及回滚后合法折边还需矩阵。 |
| [BUG-057](work-items/BUG-057.md) | P1 | 已有修复但待验收 | 未排期 | 统一锁及本机三状态60轮已过；双进程200轮与 Win10/Python3.13 原环境待验。 |
| [BUG-062](work-items/BUG-062.md) | P1 | 已有修复但待验收 | 未排期 | centerline 核心两入口已验；保存重载全矩阵及其它构型按原卡保留。 |
| [BUG-072](work-items/BUG-072.md) | P2 | 已有修复但待验收 | 未排期 | 非毫米保护本机已验；公开复核待补，继续毫米准入与原件字节保护。 |
| [BUG-074](work-items/BUG-074.md) | P1 | 已有修复但待验收 | 未排期 | 历史身份停止证明已修；Windows 跨启动四动作与公开验收未齐，同次启动/未知仍拒绝。 |
| [BUG-076](work-items/BUG-076.md) | P1 | 已有修复但待验收 | 未排期 | 膨胀诊断/详情引用已修，阻断修复归 BUG-077；本卡真实零件全链路/公开复核仍待。 |
| [BUG-079](work-items/BUG-079.md) | P1 | 已有修复但待验收 | 未排期 | 就地改弧半径已修；非主平面/外部完整编辑矩阵仍未验。 |
| [BUG-080](work-items/BUG-080.md) | P1 | 已有修复但待验收 | 未排期 | 单位/变换本机实机及 A/B 已过；公开 WorkBuddy 第三轮仍缺，不代外部环境。 |
| [BUG-082](work-items/BUG-082.md) | P1 | 已有修复但待验收 | 未排期 | 主修复/外部 Creo 9 编辑已过；非主平面 autodim、贴轴基线及失败 revision 未齐。 |
| [BUG-083](work-items/BUG-083.md) | P2 | 已有修复但待验收 | 未排期 | Python 非法轴准入已修；原生 validate_revolve_axis 分支与外部原环境未验。 |
| [BUG-090](work-items/BUG-090.md) | P1 | 已有修复但待验收 | 未排期 | 厚度函数门控/实读回退已修；Creo 10 定向编译与运行待原环境，保持开放。 |
| [BUG-094](work-items/BUG-094.md) | P1 | 已有修复但待验收 | 未排期 | 本机已验，待原负责人交付裁定；−Z 扩展及外部原请求未验证；依赖：交付裁定；外部原请求/环境仅用于原案核对，不作全项目发布门槛。 |
| [BUG-098](work-items/BUG-098.md) | P1 | 已有修复但待验收 | 未排期 | 三点面阻塞已修并实机8/8；约束引用逐条核对仍未验证，保留数量校验安全边界。 |
| [BUG-101](work-items/BUG-101.md) | P1 | 已有修复但待验收 | 未排期 | 补圆弧端点支持并用 gear10 原案验证；依赖：缺 gear10.json 和外部 Creo 10 对照。 |
| [BUG-105](work-items/BUG-105.md) | P1 | 已有修复但待验收 | 未排期 | 回滚成功保持 ready 已验；派发前零变更及 ack_no_mutation 恢复失败态仍未实机。 |
| [BUG-107](work-items/BUG-107.md) | P1 | 已有修复但待验收 | 未排期 | 生成器门控已发布；本批DEV-076补手写surface_loft的Probbl.h门控与缺头实际编译回归。Creo9/10完整SDK/运行时未验，禁止用编译代替几何通过。 |
| [BUG-110](work-items/BUG-110.md) | P1 | 已有修复但待验收 | 未排期 | ack_failure 已实现；11/07 仍 guard_only，零件/装配成功确认分支未触发，待健康失败态夹具。 |
| [BUG-114](work-items/BUG-114.md) | P1 | 已有修复但待验收 | 未排期 | 新件清理/重建已验；新装配失败清理与终态作用域仍需实机，不放宽组件保护。 |
| [BUG-116](work-items/BUG-116.md) | P1 | 已有修复但待验收 | 未排期 | 0.19.3反馈P1/P5：draft 中性面示例改几何平面形式并说明两种解析语义，原生失败带 `failed_reference` 与候选数/ID；实机文案与建模效果未验。 |
| [BUG-117](work-items/BUG-117.md) | P2 | 已有修复但待验收 | 未排期 | 0.19.3反馈P4：targets 对象形式改单条可读拒绝并给合法示例，依赖列表加重提提示；自动基准面合并开关未设计与实现。 |
| [BUG-119](work-items/BUG-119.md) | P1 | 已有修复但待验收 | 0.23.1（已交付子项） | 0.22.0反馈P2：已有实体的模型上 `surface_loft` 不再因模型级 `has_solid` 回滚，改为前后实体/材料体/体积增量判定；Creo 12.4.0.0 实机通过。Creo 9/10 运行期、非毫米单位与 WorkBuddy 黑盒未验。 |

## 观察中

| ID / 工作卡 | 优先级 | 当前状态 | 目标版本 | 简短剩余工作 / 依赖 |
| --- | --- | --- | --- | --- |
| [BUG-005](work-items/BUG-005.md) | P1 | 观察中 | 未排期 | 新现场再查；依赖：新现场。 |
| [BUG-021](work-items/BUG-021.md) | P1 | 观察中 | 未排期 | 朋友新反馈再查；依赖：新现场。 |
| [BUG-088](work-items/BUG-088.md) | P2 | 观察中 | 未排期 | Creo 10 原案再查；依赖：原始日志。 |

## 其它 agent 处理范围

| ID / 工作卡 | 优先级 | 当前状态 | 目标版本 | 简短剩余工作 / 依赖 |
| --- | --- | --- | --- | --- |
| [BUG-003](BACKLOG_COMPLETED.md#legacy-bug-003) | P1 | 其它 agent 处理范围 | 未排期 | 与 FEAT-010 及反馈批对账；依赖：实机/原件。 |
| [BUG-032](work-items/BUG-032.md) | P1 | 其它 agent 处理范围 | 未排期 | green/white 面距、外部差异；依赖：外部环境。 |
| [BUG-045](work-items/BUG-045.md) | P2 | 其它 agent 处理范围 | 未排期 | 内核阈值扫描、外部 -2；依赖：健康会话/原报文。 |
| [BUG-046](work-items/BUG-046.md) | P1 | 其它 agent 处理范围 | 未排期 | revolve 与一体增料路线；依赖：原生方案。 |
| [BUG-050](work-items/BUG-050.md) | P1 | 其它 agent 处理范围 | 未排期 | 原切线闭环/53 mm 混合轮廓；依赖：原输入。 |
| [BUG-051](work-items/BUG-051.md) | P1 | 其它 agent 处理范围 | 未排期 | 完整原案与 coordinates 对照；依赖：原输入/日志。 |
| [BUG-064](work-items/BUG-064.md) | P1 | 其它 agent 处理范围 | 未排期 | surface 引用、无第二参照、外部原案；依赖：原件/实机。 |
| [BUG-084](work-items/BUG-084.md) | P1 | 其它 agent 处理范围 | 未排期 | 三引用等价与外部原案；依赖：原件/实机。 |
| [BUG-095](work-items/BUG-095.md) | P2 | 其它 agent 处理范围 | 未排期 | 本机已验，待原负责人交付裁定；报告方同面/同模型仍缺 request.json；依赖：request.json。 |
| [BUG-103](work-items/BUG-103.md) | P1 | 其它 agent 处理范围 | 未排期 | 四壁矩阵、UI 对照、外部差异；依赖：Creo 10 环境。 |
| [BUG-113](work-items/BUG-113.md) | P1 | 其它 agent 处理范围 | 未排期 | 外部 Backup/回滚原案；依赖：MCP/job/native/检查点。 |
| [BUG-115](work-items/BUG-115.md) | P2 | 其它 agent 处理范围（已交付 0.18.4 H12 回执复验子项） | 0.18.4（H12 子项已交付）；剩余未排期 | 原生 -4 根因、其它组合；依赖：原生机制。0.19.3 B 批只补诊断：`ProFeatureGeomitemVisit` 失败时回执带 ProError 数值、标签与「引用原始 target 或用 quilt 几何 ID」的替代方式，未改解析语义。 |
| [DEV-054](work-items/DEV-054.md) | P2 | 其它 agent 处理范围 | 未排期 | 原负责人仍有本地维护记录未提交；分支/归档与发布状态核对由其继续，本批只对账。 |
| [DEV-067](work-items/DEV-067.md) | P2 | 其它 agent 处理范围 | 未排期 | A01/A03/B01/D02 已进入本地集成，A02 已交付；协调原负责人验收/发布，其它组未全实现。 |
| [DEV-069](work-items/DEV-069.md) | P1 | 其它 agent 处理范围 | 未排期 | chatgpt/0.17.1 反馈归原批负责人；保真、钣金增料/角部、原现场与发布后核对未闭环。 |
| [DEV-072](work-items/DEV-072.md) | P1 | 其它 agent 处理范围 | 未排期 | 代码及组合编译已有；原生诊断实机/保存重载、真实附件下载与 0.17.4 发布核对归原负责人。 |
| [FEAT-035](work-items/FEAT-035.md) | P2 | 其它 agent 处理范围 | 未排期 | 标准孔实现已进入本地集成；孔表/深度和扩展原生矩阵由原负责人收口。 |
| [FEAT-057](work-items/FEAT-057.md) | P2 | 其它 agent 处理范围（0.18.1 已交付密度/单位/缺失原因契约，离线） | 0.18.1（已发布）；剩余未排期 | 质量属性已随 0.18.0 集成；0.18.1 补 `mass_unavailable_reason` 回执契约与单位口径（离线，24 项回归）。主惯量、装配 occurrence 汇总、真实材料密度与保存重载仍由原负责人收口。 |
| [FEAT-059](work-items/FEAT-059.md) | P2 | 其它 agent 处理范围（已交付 0.18.0 事务日志底座子项） | 未排期（剩余范围） | 事务日志底座随 0.18.0 集成；原生骨架创建、受管身份/依赖、完整多模型事务未实现，未排期。 |
| [FEAT-063](work-items/FEAT-063.md) | P2 | 其它 agent 处理范围 | 未排期 | 只读 box_frame 规划器软件完成并进入本地集成；模板原生/保存重载仍未验。 |

## 开发中

| ID / 工作卡 | 优先级 | 当前状态 | 目标版本 | 简短剩余工作 / 依赖 |
| --- | --- | --- | --- | --- |
| [DEV-002](work-items/DEV-002.md) | P2 | 开发中 | 未排期 | 第三批包化离线已交付，T5 实机待验；服务/启动/桥接后续分批，不关整项。 |
| [DEV-030](work-items/DEV-030.md) | P1 | 开发中 | 未排期 | 推进 G2 底板/编辑、G3 履带/性能、G4 阵列；已放宽三键不重复调查。 |
| [FEAT-010](work-items/FEAT-010.md) | P2 | 开发中 | 未排期 | Right ±Z 已验；倾斜 frame、保真/原53mm输入、编辑重载和投影驱动仍开放。 |
| [DEV-077](work-items/DEV-077.md) | P1 | R01—R04 已随 0.19.2 交付；实机/黑盒/远端余项待接手 | 0.19.2 | 0.18.2四份反馈对比归档、RELEASING/POSTCHECK回填、台账计数门禁、质量属性诊断与阶段计时回退；R01可配rotation_tolerance、R02质量属性提示/get_job 300s/known_limitations/plan_examples已在0.19.1交付；0.19.2新增草图closure_tolerance/snap_endpoints/偏差断言、mirror feature引用与回执、session_health降级策略、quilt_merge消耗回执；余项见DEV-077-HANDOFF R01—R08。 |
| [DEV-079](work-items/DEV-079.md) | P1 | 离线子项已随 0.19.2 交付；Creo 10/钣金/黑盒待接手 | 0.19.2 | 0.19.0三份Creo 10反馈归档与对照；quilt_merge描述同步、曲率默认摘要/`include_samples`、surface_group结构化失败回执、`profile.method`、POSTCHECK旧句已修；`state_reason`与裸名导入等0.19.1已修项不重复；H01—H09（Probbl.h替代、开放弧trim、残留quilt、原生截面面积、大作业compact、连续顶边选边、entities_file、native_bundle、负origin resize）待实机。 |
| [DEV-080](work-items/DEV-080.md) | P1 | 首批离线收口已随 0.19.3 交付；原生/实机余项待接手 | 0.19.3 | 接手0.19.0三份报告复核后仍未闭环的H01—H09及未编号缺口；首批交付手写TU头门控契约测试、COMPATIBILITY缺头降级说明、计数自检进CI；原生解耦/等价元素树、开放弧trim、残留quilt、原生截面面积、大作业compact、连续顶边选边、entities_file、native_bundle、负origin resize待Creo10 SDK或实机；解压单测发布前阻断与verify_stages优先留后续。 |
| [DEV-082](work-items/DEV-082.md) | P1 | 开发中 | 未排期 | 0.19.3反馈P1-1/P1-2 的跨TU符号门控已交付；0.21.0反馈P1 把 `surface_loft`/`surface_boundary_fill` 从 `__has_include(<Probbl.h>)` 改为 `MECHDOG_HAS_BNBLN_TREE`（`ProElemId.h` 五个 `PRO_E_BNBLN_*`），worker/能力文案同步，随 0.23.0 发布，Creo 12.4 实机放样回归全 PASS。H01抽 `element_tree_json.h`、单一真值源、真实Creo10 SDK整包编译与运行期元素树再生仍开放。 |

## 部分交付，剩余待验收

| ID / 工作卡 | 优先级 | 当前状态 | 目标版本 | 简短剩余工作 / 依赖 |
| --- | --- | --- | --- | --- |
| [BUG-121](work-items/BUG-121.md) | P2 | 部分交付，剩余待验收 | 0.24.0（子项）；剩余未排期 | 只读型计划（`export`/`dump_tree`/`mass_properties`/`surface_group_measure`/`surface_curvature`/`udf_inspect`）在 Python 侧自动按只读准入并记 `readonly_source`，不再被 GUI 保存造成的基线漂移挡住；写计划的 `model_reconciliation_required` 失败消息追加 `creo_reconcile_model` 动作指引，原生原文保留在 `native_message`。离线 11 项单测通过；Creo 12.4 实机多轮导出均成功（最新 `...T160310` 作业 `7b7ec1450490427598a2dbe72b99941c`，`...T150422`/`...T145133` 同结论），`job.json` 记 `readonly=true`/`readonly_source=inspection_only_plan`；GUI 保存造成的漂移与 Creo 10 未验。 |
| [BUG-122](work-items/BUG-122.md) | P1 | 部分交付，剩余待验收 | 0.27.0（准入接线修复）；Creo 10 未验 | 2026-11-17离线修复：提交使用同worker实测观测的身份副本，与能力披露一致；真实parser/观测落盘/读取/submit回归通过，同worker已知-18在lock/job前拒绝，跨worker及supported/unknown不误拒。模板XML仍需Extract，不再作为免抽取建议。Creo10第二次拒绝无空壳、WorkBuddy黑盒待验；未来panel按路线准入仍随BUG-120推进。保护修复不等于成型。 |
| [FEAT-067](work-items/FEAT-067.md) | P2 | 部分交付，剩余待验收 | 0.24.0（子项）；剩余未排期 | `assertions.bbox_mm{min,max,tolerance_mm}` 与 `assertions.surface_area_mm2{surface_area_tolerance_mm2}` 两条计划级断言已实现（bbox 按 inspection 的每实体 bbox 求并集；面积按 `ProSolidSurfaceVisit` 逐面求和后平方换算 mm²；两者都在未知单位时失败而非猜测），离线 23 项单测与 `bridge.py build` 通过；Creo 12.4 实机通过与失败两种回执两轮均已验证（`build/live_acceptance_20261113T150422` 作业 `841d50bb8ea54135bb2106cb80a61c4c` 通过；`99e8a458cab3424ebb5d920a026f7841` 报 `Bounding box assertion failed on Z: measured [0.000000, 15.000000] expected [0.000000, 10.000000]`，模型 revision 未变）；`surface_area_mm2` 于 12.4 实机两态通过（`...T160310` 作业 `c7c20fd3544b453fb8731900b8fb68c3` 以 4800 mm² 通过、`a759523eac444d4eb9914c0d8aa186fc` 报 `measured 5600.000000 mm2 expected 4800.000000 mm2`，revision 未变）；未知单位模型、空面与单面失败路径未验。 |
| [BUG-124](work-items/BUG-124.md) | P2 | 部分交付，剩余待验收 | 0.24.0（子项）；剩余未排期 | `import_geometry`（STEP/IGES → 独立新 part）离线实现完成：`ImportGeometryOp` schema（绝对路径、扩展名与 format 一致、双摘要校验）、计划级准入（唯一操作 + 无 model_id + 非只读 + part）、`native/import_geometry.cpp`（`ProIntfimportModelWithOptionsMdlnameCreate` + `PRO_IMPORTREP_MASTER`、执行前重算摘要、失败码原样透出、`quilt_count/area_mm2/closure` 未测即 null）、新建模型分支改为导入建 part；Creo 12.4 实机两次导入全 PASS（STEP 作业 `c725cca785d44cd6b382c2b0f14ef13f` 440.0 mm² 闭合单面组、IGES 作业 `11823392b60747d093659464030e7122` 1540.0 mm² 六面组，均保存重载验证），门禁已删除并登记 `geometry_import` 能力家族。剩余：Creo 10、纯曲面（非实体）样本、英寸模型（会被毫米校验回滚）未验。 |
| [DEV-027](work-items/DEV-027.md) | P2 | 部分交付，剩余待验收 | 未排期 | 真实世代回收、二进制可复现性及副本外部改动/登记不一致分支待验。 |
| [DEV-044](work-items/DEV-044.md) | P1 | 部分交付，剩余待验收 | 未排期 | 0.4.7 五组已有后续证据；保留 DEV-027 等整计划关联余项，避免按旧末段重复安排迁移。 |
| [DEV-046](work-items/DEV-046.md) | P1 | 部分交付，剩余待验收 | 未排期 | 第二批矩阵实机已验；第三批约束/结果比对、源件更新/嵌套及 DEV-027 余项保留。 |
| [DEV-051](work-items/DEV-051.md) | P1 | 部分交付，剩余待验收 | 未排期 | 历史离线批已交付；四壁后续、嵌套回导、原件缺项及公开预算契约按子卡对账。 |
| [DEV-052](work-items/DEV-052.md) | P1 | 部分交付，剩余待验收 | 未排期 | N 批已交付；曲面/角部、缺原件及会话调查按子卡接续；092/093 已补证，不再列未修。 |
| [DEV-053](work-items/DEV-053.md) | P1 | 部分交付，剩余待验收 | 未排期 | 反馈批部分交付；P07/P08/P11、P13/P16 及缺原件范围按卡保留，沿原 ID 接续。 |
| [DEV-065](work-items/DEV-065.md) | P1 | 部分交付，剩余待验收 | 未排期 | 诊断批已交付；真实停滞、刚体平移放行与 ack_failure 目标分支仍开放；BUG-111 已定因。 |
| [DEV-070](work-items/DEV-070.md) | P2 | 部分交付，剩余待验收 | 未排期 | 四附件校验及 API 回退已写；真实远端回退和旧附件/摘要冲突外置核对待原负责人完成。 |
| [DEV-071](work-items/DEV-071.md) | P1 | 部分交付，剩余待验收 | 未排期 | 0.17.3 离线修复已合主干；原生阶段码/miter 回执实机观察待补，53mm 根因归 BUG-050/051。 |
| [DEV-083](work-items/DEV-083.md) | P1 | 部分交付，剩余待验收 | 未排期 | 0.23.1/0.23.2 记录/状态/链接门禁已交付；0.25.0 续项已随 0.26.0 交付（部分子项）：交付快照与ID完备性、交付版本/实际Release列、差异说明收窄、完成档案覆盖、发布前后证据与前版基线、审定TXT白名单；专项单测通过，未实机。 |
| [DEV-074](work-items/DEV-074.md) | P1 | 已交付 0.18.3/0.18.4/0.19.0 子项；Creo 9/10 未排期 | 0.19.0（子项已交付） | 0.19.0 交付 H03 `creo_quilt_merge` 公开（两片 400→800 mm²）、H08 `creo_surface_round` 与 `creo_measure_surface_curvature` 实机、H10 五爪整瓶整链 63 项检查；H05 钣金附着增料、H07 独立 quilt 偏置、钣金成形类与任意非平面 fill 为不可用或未取证，门禁保持；仍开放：百叶/格栅/凸台/铰链/耳、格栅 cut 定因、Creo 9/10 与 WorkBuddy。 |
| [FEAT-004](work-items/FEAT-004.md) | P2 | 部分交付，剩余待验收 | 未排期 | rebase 后 18/18 实机已补；装配/骨架/族表尺寸、分类和同计划先后语义仍未验。 |
| [FEAT-005](BACKLOG_COMPLETED.md#legacy-feat-005) | P2 | 部分交付，剩余待验收 | 未排期 | 过期 revision 错误上下文已实现；公开 stdio 验收未记录，继续保持入队前拒绝。 |
| [FEAT-006](work-items/FEAT-006.md) | P2 | 部分交付，剩余待验收 | 未排期 | 接管/收养主线已验；卡内既有剩余范围继续保留，异常所有权不以健康夹具替代。 |
| [FEAT-007](work-items/FEAT-007.md) | P2 | 部分交付，剩余待验收 | 未排期 | 长轮询已实现且实机六项通过；真实长任务/stdin 取消与公开进度细分仍开放。 |
| [FEAT-008](work-items/FEAT-008.md) | P2 | 部分交付，剩余待验收 | 未排期 | entity_ids/中心线计数及重建配套已验；其余首批范围与真多中心线原件仍缺。 |
| [FEAT-012](work-items/FEAT-012.md) | P2 | 部分交付，剩余待验收 | 未排期 | 矩阵放置已验；显式源件更新/嵌套及内核精度扫描待补，阈值不改。 |
| [FEAT-014](work-items/FEAT-014.md) | P2 | 已交付 0.18.4/0.19.0 反证子项（附着增料与成形类均不可用，门禁保持）；其余未排期 | 0.19.0（反证子项已交付） | 四壁基础/origin/选边已有；附着增料经 Creo 12.4 反证不可用（直接 add −1、union 吞并钣金体）；成形类 corner relief/草图成形 create 失败或再生失败，hem/jog 无 API，格栅 cut 未取证；连续多边折边、格栅孔、凸台/铰链/耳未排期。 |
| [FEAT-018](work-items/FEAT-018.md) | P1 | 部分交付，剩余待验收 | 未排期 | 补四动作的 revision、凭证/过期、幂等、owner、再次中断与后续编辑矩阵。0.19.3 B 批新增只读 `completion_review`（五档 verdict + signals，明确不授权重放/改 revision）；恢复状态机与令牌未改。 |
| [FEAT-020](work-items/FEAT-020.md) | P2 | 部分交付，剩余待验收 | 未排期 | 更新预算/force 已实现；真实断网/限流及失败期间继续建模待验。 |
| [FEAT-022](work-items/FEAT-022.md) | P2 | 部分交付，剩余待验收 | 未排期 | 真实连接器升级前后核对路径、启动身份和工具版本；本地部署指纹已实现。 |
| [FEAT-023](work-items/FEAT-023.md) | P2 | 部分交付，剩余待验收 | 未排期 | 剩余 jobs 日志、复杂请求/union 错误体量及规范化回执实机；capabilities 分页已闭环。 |
| [FEAT-029](work-items/FEAT-029.md) | P1 | 部分交付，剩余待验收 | 未排期 | 剩余跨代兼容升级/回退、多目录与公开验收，自动注册/签名另评估。 |
| [FEAT-030](work-items/FEAT-030.md) | P2 | 部分交付，剩余待验收 | 未排期 | 15+2 种子本机矩阵已验；生产版本可追溯与 Creo 9 加载/重生仍缺环境和来源。 |
| [FEAT-031](work-items/FEAT-031.md) | P2 | 部分交付，剩余待验收 | 未排期 | 两件装配导出/隔离回导已验；嵌套、外部引用与跨机重建边界仍开放。 |
| [FEAT-036](work-items/FEAT-036.md) | P2 | 部分交付，剩余待验收 | 未排期 | delete/suppress/resume 主线已验；组/阵列头随动仍未闭环。 |
| [FEAT-039](work-items/FEAT-039.md) | P1 | 已交付 0.13.0/0.14.0/0.15.0/0.18.3/0.18.4/0.19.0 子项；H15/H16 已补；多截面/offset/fill/交线未排期 | 0.19.0（子项已交付） | 0.19.0 交付 H03 quilt merge 公开（两片 400→800 mm²、可继续加厚）、H10 五爪整瓶整链（闭合壳 7858.298125 mm²、加厚与 solidify）；H15 overlap预算/覆盖诊断与H16 trim结果句柄/连续trim已在Creo12.4实机通过，H14真实交线诊断、H17 Creo10直创原件、H18 Creo10同载荷仍缺；H07 独立偏置与任意非平面 fill 仍不可用（门禁保持）；多截面/边界混合与 trim 偏置语义未排期。0.19.3 B 批：`project_curve` 两段创建失败时分别指名为「步骤 1 扫描面」/「步骤 2 INTERSECT」，不再只给 -1；`quilt_merge` 拒绝回执带 target/tool quilt id、目标与合计面积、JOIN 接触要求与共面相邻提示；Creo 10 差异仍未定因。 |
| [FEAT-042](work-items/FEAT-042.md) | P1 | 部分交付，剩余待验收 | 未排期 | 接管、同模型并发编辑、真实再生失败及钣金语义仍需证据；通道 busy 不代替。 |
| [FEAT-043](work-items/FEAT-043.md) | P2 | 部分交付，剩余待验收 | 未排期 | 会话枚举主线已验；unknown、其它类型及真实并发枚举待补。 |
| [FEAT-044](work-items/FEAT-044.md) | P1 | 部分交付，剩余待验收 | 未排期 | 原 asm_mx.asm.16、显示失败、unknown 和真实并发的打开链路仍需现场。 |
| [FEAT-045](work-items/FEAT-045.md) | P2 | 部分交付，剩余待验收 | 未排期 | 只读装配检查主线已验；受限场景/外部原环境与公开黑盒保留。 |
| [FEAT-046](work-items/FEAT-046.md) | P1 | 部分交付，剩余待验收 | 未排期 | erase 主线已有外部证据；本机矩阵、阻断分支与公开黑盒仍未齐。 |
| [FEAT-047](work-items/FEAT-047.md) | P1 | 部分交付，剩余待验收 | 未排期 | health 正常/异常分页主线已验；外部异常数据还原及原始响应字节核对按卡保留。 |
| [FEAT-048](work-items/FEAT-048.md) | P1 | 部分交付，剩余待验收 | 未排期 | 按路径/批量收养已有实机；准入分支泛化及卡内保留项待补，不重做首批。 |
| [FEAT-051](work-items/FEAT-051.md) | P2 | 部分交付，剩余待验收 | 未排期 | requested/effective_flip 与 draft_failure 当前代码已有；外部 -1 定因、单位实机矩阵及回执补证仍开放。 |
| [FEAT-052](work-items/FEAT-052.md) | P2 | 部分交付，剩余待验收 | 未排期 | 分族上色主线已实机通过；真实 busy 并发与其余卡内矩阵未验，random/标签键归 FEAT-056。 |
| [FEAT-053](work-items/FEAT-053.md) | P2 | 部分交付，剩余待验收 | 未排期 | 三点定面与斜面草图已验；约束引用逐条核对未验证，关联 BUG-098 保留。 |
| [FEAT-058](work-items/FEAT-058.md) | P2 | 已交付 0.12.0/0.15.0/0.16.1/0.17.0/0.18.3 子项；坐标换参/扩展 frame 未排期 | 0.18.3（子项已交付） | H01 非零 `origin` 大跨度 resize 已修复（Creo 12.4 实机 14/14）；坐标换参、板厚回执新诊断、扩展 frame 与非矩形截面留原批未排期。 |

## 部分交付，剩余待规划

| ID / 工作卡 | 优先级 | 当前状态 | 目标版本 | 简短剩余工作 / 依赖 |
| --- | --- | --- | --- | --- |
| [DEV-091](work-items/DEV-091.md) | P1 | 部分交付，剩余待验收 | 未排期 | 四原件归档、源码对照与分批计划已完成；R/M1/A0/A1/G1 已实现，原生构建成功，M1/A0/A1 实机通过并保存重载。A2（61条）与 G1 原生选区仍待输入/查证，Arm2 完整装配未逐条对照。 |
| [BUG-123](work-items/BUG-123.md) | P1 | 部分交付，剩余待规划 | 0.24.0（子项）；剩余未排期 | B1/B2/B3 均已交付（2026-11-13，Creo 12.4 实机）：`tools/test_loft_template.py --live` 11 项全 PASS——手写树作业 `ea2ac599…`（1600.0 mm²）与模板 XML 作业 `d590b87b…`（`tree_source=template_xml`、`create_code=0`、`extract_code=0`、`feature_incomplete=false`、1600.0 mm²）相对差 0.0；负例 `TEMPLATE_SHAPE_MISMATCH`（作业 `49a9b065…`）与 `TEMPLATE_TREE_LOAD_FAILED`（作业 `6fb40ac1…`）均未留下特征。模板已随源码包发行（`template_library_files()` 按 manifest 校验 bytes/sha256，10 项打包测试）。剩余：Creo 10 解析与创建后 `ProFeatureElemtreeExtract` 未复测（模板只换输入树，`-18` 不因此消失）、仅 3 截面 + 3 导线一种形态。 |
| [FEAT-027](BACKLOG_COMPLETED.md#legacy-feat-027) | P3 | 部分交付，剩余待规划 | 未排期 | 墓碑与旧别名拒绝已交付；显式释放/重绑定接口和跨版本历史核对待规划。 |
| [DEV-066](work-items/DEV-066.md) | P2 | 部分交付，剩余待规划 | 未排期 | 0.18.2已交付来源降级子项；当前分支8def1e4已补齐其余Git读取、报告字段、负例捕获和runtime日志取消跟踪，未发布增量及H08—H09见DEV-075-HANDOFF。 |
| [FEAT-033](work-items/FEAT-033.md) | P1 | 部分交付，剩余待规划 | 未排期（0.19.3 B 批 opt-in 已交付） | small/large 基准已有；`execute_plan(timeout_seconds)` 受控覆盖（60—7200，默认=服务配置）与 job 回执 `timeout_seconds`/`timeout_source`、看门狗按作业预算判定已交付；自动预算公式、阶段耗时公开契约与到期动作仍待规划，不以取消保存重载缩时。 |
| [FEAT-066](work-items/FEAT-066.md) | P1 | 部分交付，剩余待规划 | 0.23.0（已交付子项） | `b_spline` 精确 NURBS 实体随 0.23.0 发布，Creo 12.4 实机控制点回读偏差 2.6e-31 mm、两截面面积 1058.017278 mm² 对齐独立 de Boor oracle、保存重载一致，`surface_loft` 回归 PASS。剩余 `closed`、`dimensioning="coordinates"`、页面编辑未排期；Creo 10 运行期未验。 |
| [BUG-120](work-items/BUG-120.md) | P1 | 部分交付，原生后端待授权实施 | 0.23.2（诊断子项）；D1/D4.3/D4.4离线部分未定版 | T1-C原件、取消及非平面作用已取证。D1路线契约/按路线准入/panel profile库、D4.3阶段预算看门狗接线、D4.4跨模型会话guard已离线实现（3918单测通过）；原生后端未编译未连接Creo，协议4 ABI2与票据、真实曲线引用、可靠结束观测、几何保存重载、目标机验收与分发待做；本版guard无MCP侧退役动作，需人工核实后删`panel_session_guard.json`。 |

<a id="未来能力候选"></a>
<a id="当前优先功能"></a>

## 待规划

| ID / 工作卡 | 优先级 | 当前状态 | 目标版本 | 简短剩余工作 / 依赖 |
| --- | --- | --- | --- | --- |
| [DEV-090](work-items/DEV-090.md) | P1 | 部分交付，剩余待验收 | 0.27.0（G2 实机子项）；其余未排期 | 0.25.0 已交付T1/T2/T3组合首壁/T4/T5/T6a/T6b/T8与T7诊断措辞；新反馈的方向偏差、锚点与选区分别归BUG-129、FEAT-068/069（签名已补，完整草图/API未核）。本卡续多约束求解/保存重载、parallel/distance、T7实测及黑盒，见DEV-091计划；G2 已实机验证（2026-11-17 本机 Creo 12.4：R5 圆弧 `107.3015`→G2 `80.0793 mm³`，R30 `3862.8331`→`2883.2442 mm³`，四条均 `committed` 且保存重载通过，G2 表面非圆柱、相对圆弧少 25.37%，排除静默退化），`RoundOp` 增可选 `curvature_continuous`；曲率连续性未测，Arm7 实体边与 Creo10/9 未验，Creo10不外推。 |
| [FEAT-068](work-items/FEAT-068.md) | P1 | 部分交付，剩余待验收 | 未排期 | 已接通单点直边、圆边（含角度过滤）、装配选择器与解析后平面/圆柱校验；实机直边/圆边圆角、coincident+concentric 与保存重载通过。倒角邻面、61条可解性与多约束组合仍待验收。 |
| [FEAT-065](work-items/FEAT-065.md) | P1 | 已交付 0.21.0（M1/M2）、0.22.0（M3/M4）与 0.23.1（补充）子项；剩余未排期 | 未排期 | 已发布：2—32 截面、2—8 条第二方向导线、截面/导线接受已有曲线与边、首末收敛点、边来源首/末截面的 `tangent`，quilt 边 ID 由 `creo_measure_surface_group` 的 `open_edge_records` 给出；0.23.1 起已有实体模型不再误拒 `surface_loft`（BUG-119），YZ@X 与 XZ@Y 正交平面截面实机通过。2026-11-16 原始球鼻艏在 Creo 12.4 完成独立实体：精确导线+末端收敛点放样、镜像、后端盖、缝合与实体化均保存重载 true；1活动材料体、体积54405151075.317024 mm³，未接船体，单独quilt体积查询-62及重叠扫描未完如实保留，见卡。剩余：`curvature`/`normal`/导线边界无实测依据仍拒绝；非平面相邻面与两端朝向不同的相切未测；`ADV_VIA_CRV`；`boundary_conditions` 不在 compact 保护集合内；Creo 9/10 与 WorkBuddy 黑盒。见 [0.22.0 发布记录](validation/RELEASE-0.22.0.md) 与 [0.23.1 发布记录](validation/RELEASE-0.23.1.md)。 |
| [DEV-003](BACKLOG_COMPLETED.md#legacy-dev-003) | P2 | 待规划 | 未排期 | 整理 C++ 的执行上下文、模块接口和资源由谁创建、释放，再用受影响的 SDK 构建并运行原生测试。 |
| [DEV-004](BACKLOG_COMPLETED.md#legacy-dev-004) | P2 | 待规划 | 未排期 | 在 DEV-003 完成后，让各模块可以独立编译，并整理原生测试目录。检查构建缓存、安装、保存重载和失败回滚。 |
| [DEV-005](BACKLOG_COMPLETED.md#legacy-dev-005) | P2 | 待规划 | 未排期 | 按工具和参数用法记录本机哪些测过、哪些没测，并注明真实环境，同步安装和能力说明。其他环境收到具体反馈再补；不要求双版本验收，也不能拿“82 工具测过”的汇总代替每种用法的兼容性测试。 |
| [DEV-006](BACKLOG_COMPLETED.md#legacy-dev-006) | P2 | 待规划 | 未排期 | 按工具分支补成功/非法输入、真并发与保存重载；需对应 SDK/种子/UDF 环境，黑盒单列。 |
| [DEV-007](BACKLOG_COMPLETED.md#legacy-dev-007) | P2 | 待规划 | 未排期 | 复用 DEV-006 的发布回归清单，按环境记录；模拟/本地直调不代替公开 MCP。 |
| [DEV-008](BACKLOG_COMPLETED.md#legacy-dev-008) | P3 | 待规划 | 未排期 | 查清旧清单第 5/6/7/9 项分别来自哪里、现在归哪个任务，补上对照关系。来源是 NEXT_STEPS_025 的“完善建议 5”。 |
| [DEV-009](BACKLOG_COMPLETED.md#legacy-dev-009) | P2 | 待规划 | 未排期 | 按模块分别整理代码格式，每批完成后做回归检查，不自动增加历史问题的豁免项。2026-10-14 的历史统计为 67 条 Ruff 问题、36 个 Python 和 14 个 C++ 文件，见历史记录。 |
| [DEV-031](work-items/DEV-031.md) | P2 | 待规划 | 未排期 | 先澄清履带TXT的相位、闭合、近似与容差，再分步安排63站/90凸台、性能和恢复；报告−1.46%偏差仍未满足±1%，本条不直接建模。 |
| [DEV-056](work-items/DEV-056.md) | P2 | 待规划 | 未排期 | job/驱动统一记录 worker SHA256 与 build stamp；已有 service/loader 指纹不重复开发。 |
| [DEV-057](work-items/DEV-057.md) | P3 | 待规划 | 未排期 | 原 BCG 输入仍缺；凹圆棱替代例已验，补原案及超薄几何规则裁定。 |
| [DEV-058](work-items/DEV-058.md) | P3 | 待规划 | 未排期 | WorkBuddy 提示词需按当前契约更新，公开 MCP 黑盒尚未执行；不以开发者证据替代。 |
| [DEV-059](work-items/DEV-059.md) | P3 | 待规划 | 未排期 | 核实旧 22 项环境 errors 是否仍存在；余下统计校验与计划状态规范，历史清理已完成。 |
| [DEV-063](work-items/DEV-063.md) | P3 | 待规划 | 未排期 | compact erase 摘要和预览矩阵 false 的说明待补；full 字段不裁剪。 |
| [DEV-081](work-items/DEV-081.md) | P1 | B1/B2/B3/B4 已随 0.20.0 实机验收交付；B5/B6 与 C 批黑盒待做 | 0.20.0 | 第四份0.19.0反馈（护卫舰）F01—F11；A批F02圆弧闭合误拒/F03半径上限/F07更新提示/F04 connect −4回执/F11平面语义文档/F05限制说明已离线交付，六个提交与统一dev_check证据见[MAPPING第五节](validation/feedback-0.19.0-frigate-2026-11-08/MAPPING.md)；A批仅「离线已交付、实机未验」，计划见[离线批次计划](superpowers/plans/2026-11-09-feedback0190-frigate-offline.md)；B1—B6原生/实机与C0—C5黑盒拆项、前置条件见[B/C批子计划](superpowers/plans/2026-11-09-feedback0190-frigate-bc-batches.md)，[WorkBuddy提示词](validation/feedback-0.19.0-frigate-2026-11-08/workbuddy-blackbox-prompt.md)仅阶段0/1可试、建模与并发留卡，未连Creo未做黑盒。 |
| [FEAT-001](work-items/FEAT-001.md) | P1 | 待规划 | 未排期 | 启动/重连/多会话状态检测及普通 retry、损坏通道恢复完整验收仍开放。 |
| [FEAT-002](BACKLOG_COMPLETED.md#legacy-feat-002) | P2 | 待规划 | 未排期 | 遇到 DLL 提示等需要人工处理的情况时，说明正在等什么。测试等待超时后，任务上下文是否保留、相关模块能否清理。 |
| [FEAT-003](BACKLOG_COMPLETED.md#legacy-feat-003) | P2 | 待规划 | 未排期 | 支持并测试带单位的关系式，例如 `8[mm]`。确认它能真实驱动尺寸、带动相关参数变化，并保留用户对单位的检查设置。 |
| [FEAT-009](work-items/FEAT-009.md) | P2 | 已交付 0.18.3 子项；动态准入已补；多截面/导线已由 FEAT-065 M1/M2 随 0.21.0 交付；闭合/连续性/非平面未排期 | 0.18.3（子项已交付） | 两截面直纹曲面放样 `creo_surface_loft` 在Creo12.4已实机验收（quilt 800 mm²、trim 两侧各 400、2 mm 加厚 1600 mm³）；H13 worker构建身份/动态准入与提交前拒绝已实现并在Creo12.4核验，Creo10缺Probbl.h实机与完整放样路线仍未验。2026-11-11 更正：多截面已由 [FEAT-065](work-items/FEAT-065.md) M1/M2 随 0.21.0 发布并在 Creo 12.4 实机验收——2—32 截面（两截面 straight 直纹，3 截面以上必须 smooth）、可选 2—8 条第二方向导线；闭合曲面、相切/曲率连续性、非平行/扭转/任意正交平面截面、圆弧截面、端点收敛仍不公开或未测，Creo 9/10 未验。 |
| [FEAT-011](BACKLOG_COMPLETED.md#legacy-feat-011) | P2 | 待规划 | 未排期 | 增加复合轨迹、可变截面和螺旋扫掠，分别明确范围并测试。 |
| [FEAT-013](BACKLOG_COMPLETED.md#legacy-feat-013) | P2 | 待规划 | 未排期 | 增加剖视、局部放大、装配图和 BOM（物料清单），逐项检查模型变化后图纸能否同步更新。 |
| [FEAT-015](BACKLOG_COMPLETED.md#legacy-feat-015) | P3 | 待规划 | 未排期 | 评估模具、NC 加工和仿真能力，先选一个最小场景做完整流程，暂不承诺支持全部模块。 |
| [FEAT-016](BACKLOG_COMPLETED.md#legacy-feat-016) | P2 | 待规划 | 未排期 | 增加翼型凸度和 NACA 四位数系列，检查能否通过原生参数编辑，并验证实际几何。 |
| [FEAT-017](BACKLOG_COMPLETED.md#legacy-feat-017) | P2 | 待规划 | 未排期 | 分别复现并测试布尔、曲面和拔模中尚未测过的用法，再决定扩大哪些支持范围。 |
| [FEAT-021](BACKLOG_COMPLETED.md#legacy-feat-021) | P1 | 待规划 | 未排期 | 设计受控取消任务，先说明 queued、running、unknown_outcome 各能否取消，再检查执行器和模型状态。不能安全中断时说明原因。取消后要检查最终状态、保存点、revision、锁和下一次任务是否正常；不能把杀 worker 或清 pending_job 当作取消成功。与未知结果恢复分别验收，任务状态名称不表示当前已有排队能力。 |
| [FEAT-024](BACKLOG_COMPLETED.md#legacy-feat-024) | P3 | 待规划 | 未排期 | lookup_constants 没找到结果时，说明没有匹配，并提示可用前缀。测试不存在的前缀、空条件、合法前缀及旧返回规则；保留正常命中的行为。当前按体验改进处理，不直接把空字典认定为缺陷。 |
| [FEAT-025](BACKLOG_COMPLETED.md#legacy-feat-025) | P2 | 待规划 | 未排期 | 评估 creo_loft 在回调未就绪时，能否用 2～6 截面种子完成部分操作。先说明支持哪些截面和模式、怎样保留模型身份，再检查已有特征、编辑、revision、保存重载和失败恢复。种子能新建零件，不代表能追加到已有零件；不自动加载 DLL 或改变策略，也不预先承诺实现成本低。 |
| [FEAT-026](BACKLOG_COMPLETED.md#legacy-feat-026) | P3 | 待规划 | 未排期 | 提供 create_feature_tree 能运行的最小 dict 示例，说明 dump XML 能否转换或导入。先让示例建模、参数、几何和重载通过，非法树能指出问题元素，再评估导出后重新导入。无效示例失败不能证明工具不可用。 |
| [FEAT-028](BACKLOG_COMPLETED.md#legacy-feat-028) | P3 | 待规划 | 未排期 | 评估一次性 create_plate 的注册/后续编辑范围；不能把无 model_id 产物当受管源件。 |
| [FEAT-032](work-items/FEAT-032.md) | P2 | 待规划 | 未排期 | 评估原生沿曲线阵列：先简单平面，再闭环弧长、相位、切向、种子计数和跳站，最后履带63站与多特征；多次切除不算原生阵列验收。 |
| [FEAT-037](work-items/FEAT-037.md) | P3 | 待规划 | 未排期 | 先补参数误写的最小输入，再明确模型/特征参数目标与同名规则，评估少量建议；不自动猜改，验证关系、revision及重载。 |
| [FEAT-038](BACKLOG_COMPLETED.md#legacy-feat-038) | P2 | 待规划 | 未排期 | 提供不建立 Toolkit 连接的安装自检路径：校验部署产物与配置一致性（常量表、执行器与源码指纹、种子哈希与清单、protk/loader 注册文件），让按约束停止 Toolkit 连接的受限环境也能确认安装正确性，不必冒卡死风险连 Creo。先确定自检覆盖哪些项、怎样判定"一致"，以及自检通过与实机就绪的关系（自检通过不等于通道可用）。来源见Creo 10 反馈，关联 FEAT-022。 |
| [FEAT-040](work-items/FEAT-040.md) | P2 | 待规划 | 未排期 | 核对SDK后评估变半径表与收尾控制，补真实冲突边/可行半径诊断；恒定半径行为及回滚保持，与 FEAT-039 联动。 |
| [FEAT-041](work-items/FEAT-041.md) | P3 | 待规划 | 未排期 | 评估可选输出目录与预览/导出视角、正交投影；保持默认行为，输出目录不开放任意写路径。 |
| [FEAT-049](work-items/FEAT-049.md) | P1 | 待规划 | 未排期 | 显式目标参考约束克隆；核现有六类回放，不重复实现；完整快照/映射尚未交付。 |
| [FEAT-050](work-items/FEAT-050.md) | P2 | 待规划 | 未排期 | 冻结基准和显式映射后比对组件集、位姿、约束、包络/体积，缺数据标未验证。 |
| [FEAT-054](work-items/FEAT-054.md) | P2 | 待规划 | 未排期 | 待裁定四带几何偏差与求解路线，再推进全叶片/轮毂阵列；缺原始四带输入。 |
| [FEAT-055](work-items/FEAT-055.md) | P2 | 已交付 0.18.4/0.19.0 子项（H08 曲面边圆角与数值曲率/G1 已公开并实机）；其余未排期 | 0.19.0（H08 子项已交付）；剩余未排期 | `creo_surface_round` 与 `creo_measure_surface_curvature` 已公开，公开工具 107；edge-chain、变半径/过渡、斑马/曲率梳图像无 API；重拟曲面操作链、merge/放样及原生查询补证未排期。 |
| [FEAT-060](work-items/FEAT-060.md) | P2 | 待规划 | 未排期 | 骨架驱动首壁参数；依赖 FEAT-059 真实骨架，先冻结日志/依赖闭包与 revision 契约。 |
| [FEAT-061](work-items/FEAT-061.md) | P2 | 待规划 | 未排期 | 单层受管装配配置切换/抑制恢复；保留身份、约束和位姿，尚未实施。 |
| [FEAT-062](work-items/FEAT-062.md) | P2 | 待规划 | 未排期 | 独立零件 rename/derive；统一名称冲突、身份与检查点恢复，尚未实施。 |
| [FEAT-064](work-items/FEAT-064.md) | P3 | 待规划 | 未排期 | 受管世代清理 inspect/apply；冻结证据/幂等与引用保护后实施，不自动删除。 |

## 历史资料

<a id="workbuddy-030-全量实测问题映射"></a>

[完成档案与来源索引](BACKLOG_COMPLETED.md)、[开发规则](DEVELOPMENT.md)。历史版本说明和 docs/validation 原件保持路径；日期交接快照不承担当前待办维护。
