# MCP_CREO_MechDog 0.37.0 版本说明

版本类型为 MINOR，公开工具仍 111。本版交付 0.35.5 反馈的 P0 批次，覆盖边选择器类型、嵌套装配、看门狗与装配恢复、预算披露、多半径弧准入、B 样条坐标尺寸与同圆重复边。

上一版本：0.36.1（`v0.36.1`，提交 `a9bf80d3036e597258af917f80cffd1f7ca51220`）。

- **边选择器按类型解析**。几何选择器命中边后写入并保留 `target="edge"`，`resolve()` 用 `ProEdgeInit`/`ProSurfaceInit` 校验 id 与目标类型，失败时给出 target、id 和返回码，不再把边 id 当曲面初始化后只报 `-23`。[BUG-155](work-items/BUG-155.md)
- **嵌套装配源**。`creo_assemble_component` 接受受管装配作为源；子装配与零件一样走 `ProMdlnameCopy` 隔离快照，自身文件、组件与 revision 不被移动，回执披露 `source_model_type`、`source_snapshot` 与 `component_count`。三级装配与保存重载已实机验证。[BUG-156](work-items/BUG-156.md)
- **看门狗观察 native.log**。停滞看门狗同时读取 `worker.log` 与 `native.log`，任一增长即刷新进度，并在停滞证据中记录两者字节数与增长来源，长任务不再因 `worker.log` 为空被误杀。[BUG-157](work-items/BUG-157.md)
- **装配基线恢复**。`creo_reconcile_model` 允许保存过的装配使用 `restore_baseline`/`accept_saved`/`accept_live`；`restore_baseline` 默认走 `verify_mode="identity"`，只核对名称、类型、毫米单位、特征数与体积并明确 `full_inspection_verified=false`；装配依赖须位于模型输出目录或受管 `models` 根，`recovery_phase_seconds` 默认 300 s（30–900）。[BUG-157](work-items/BUG-157.md)
- **作业预算披露**。提交回执、`creo_get_job` 运行态与 compact 投影同时给出 `job_timeout_seconds`/`timeout_source`、`stall_watchdog_seconds`/`stall_watchdog_source` 和观察文件 `worker.log`、`native.log`；停滞预算独立于作业预算。[BUG-158](work-items/BUG-158.md)
- **多半径弧准入（部分交付）**。间隙不超过 1e-6 mm 的弧-弧接点视为已接合，不再误报 `arc_inconsistent`；类别列表被截断时用完整列表的 `near_tolerance_max_gap_mm` 与 `near_tolerance_arc_only` 放行坐标草图。40 段圆弧轮廓已通过 Python 准入，但本机内核仍拒绝拉伸，共享顶点问题转 [BUG-165](work-items/BUG-165.md)，本版不承诺该轮廓可拉伸。[BUG-159](work-items/BUG-159.md)
- **B 样条坐标尺寸与面积空值**。坐标尺寸模式接受精确 `b_spline`（次数、节点、控制点、可选权重），原生创建并校验几何；存在未支持实体时 `material_area_mm2` 返回 `null`，并给出 `area_status="unavailable_unsupported_entities"`、原因与实体列表，不再伪造 0。4 条三次闭合 B 样条已实机通过并保存重载。[BUG-160](work-items/BUG-160.md)
- **同圆重复边拒绝**。圆角/倒角在创建特征前解析每个边引用，按圆心与半径（1e-6 mm）识别同一整圆的多个引用，明确列出 id、圆心、半径并建议保留最小 id，不再出现无信息的 status 6。[BUG-161](work-items/BUG-161.md)

本机验收环境为 Windows x64 / Creo 12.4.0.0（`release_numeric=42`，安装目录 `D:\Program Files\PTC\Creo 10.0.0.0`）/ 匹配 Toolkit。四组实机脚本 `tools/test_feedback0355_selector_round.py`、`tools/test_feedback0355_nested_assembly.py`、`tools/test_feedback0355_assembly_recovery.py`、`tools/test_feedback0355_sketch_profiles.py` 均通过，保存重载核验为 true（40 段圆弧内核拒绝按边界记录）。未验：Creo 9 与 Creo 10 现场、原始报告模型（垫板 116/174、40 段输入、6428 边零件、269 组件装配）、曲面选择器回归与外部 WorkBuddy 黑盒。详见[验收与发布记录](validation/RELEASE-0.37.0.md)。

升级提示：本版改动原生执行器，升级后需重新运行 `setup.ps1` 或 `python bridge.py build`；种子包清单的 `compatible_server_version` 已改为 0.37.0，0.36.x 服务会拒绝该种子包。

## 附件

- `MCP_CREO_MechDog-0.37.0-source.zip`
- `MCP_CREO_MechDog-0.37.0-source.zip.sha256`
- `MCP_CREO_MechDog-0.37.0-seed-library.zip`
- `MCP_CREO_MechDog-0.37.0-seed-library.zip.sha256`

种子包 SHA256 为 `0fe2c5fb197fedfa917843d189a9ba533b3b514af10cbf6324939d0bd33dc67b`。源码包摘要记录在同名 sidecar 中，两份 sidecar 分别记录对应 ZIP 的实际 SHA256。[GitHub Release](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.37.0)
