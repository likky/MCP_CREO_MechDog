# MCP_CREO_MechDog 0.40.0 版本说明

版本类型为 MINOR，公开工具数 111。本版基于 0.35.8 外部反馈（倾斜基准面草图、验证挂起与恢复硬限）交付 [BUG-171](work-items/BUG-171.md)、[BUG-172](work-items/BUG-172.md)、[BUG-173](work-items/BUG-173.md) 与 [BUG-174](work-items/BUG-174.md)，并逐字节归档三份反馈原件至 [SOURCE_MANIFEST.json](validation/feedback-0.35.8-2026-11-23-hang-recovery/SOURCE_MANIFEST.json)。

上一版本：0.39.0（`v0.39.0`，提交 `7518f0fa2b60287319d2e78e26f1385c9b9ee34b`）。

- **恢复阶段超时结果落盘、`restore_baseline` 双巡检去重、1800 s 预算上限与终态恢复指引**。① 原生恢复截止定时器触发 `ExitProcess(31)` 前除 `native_checkpoint.json` 外同步写出最小 `native_result.json`（`completion_stage="recovery_phase_timeout"`、`delivery_complete=false`、`phase_budget_seconds` 与明确下一步指引），Python 侧保留 `unknown_outcome` 保护并在报错中直接输出 `recovery_phase_timeout (<N> s)`；② `reconcile_native` 在 `restore_baseline(verify_mode="full")` 中复用已重载再生并校验通过的 `before` 快照，消除此前无 save/reload 间隔的第二次重复 `inspection()`；③ `creo_reconcile_model(budget_seconds)` 与原生钳位上限扩至 **1800 s**，自适应下限同时按 `edges`（`120 + edges // 15`）、`features`（`120 + features // 2`）与 `surfaces`（`120 + surfaces // 4`）取最大下限；④ 当 `recovery_pending` 指向已终态（`unknown_outcome`/`failed`/`aborted`/`cancelled`）的恢复作业时，inspect 的 `recovery_wait` 返回 `state="terminal_unconfirmed"`，直接提示调用 `restore_baseline` 或 `abandon_unknown_recovery`，不再建议轮询已终态的 `creo_get_job`。[BUG-171](work-items/BUG-171.md)
- **消除单次作业 10+ 次冗余全量 `inspection()` 与逐半边 `fflush()` 刷盘开销**。`native/generic.cpp` 新增轻量查询助手 `find_default_csys_id()`、`collect_datum_planes_quiet()`、`model_has_solid()`、`active_body_count()` 与 `check_model_health()`，替换 `resolve({kind:"default_csys"})`、`resolve({kind:"datum_plane"})`、`body_options()`、`extrude_or_revolve()` 与常规操作尾部的冗余全量 `inspection()`（6 步 B045 作业全量巡检由 15+ 次降至 3 次）；热循环改用 `check_quiet(code, op, item_id)`（仅在错误时打印并刷盘），每 100 个特征/面输出 `INSPECT_PROGRESS`，巡检完成输出 `INSPECT_SUMMARY`，并设置 `INSPECT_MAX_FEATURES`/`INSPECT_MAX_SURFACES`/`INSPECT_MAX_HALF_EDGES` 迭代上限。[BUG-172](work-items/BUG-172.md)
- **单轴倾斜三点基准面草图自动创建正交辅助锚定面与 `ProSectionSolve` 错误精准归因**。① 在创建未完成草图特征前检查模型是否已有同时垂直于 `frame.n` 与 `orient_normal` 的基准面；主平面 XY/XZ/YZ 天然满足（零额外特征），而在缺失第二正交投影锚点的单轴倾斜三点基准面（如 B045/B047/B104/B105）上，自动创建并复用 1 个过草图轮廓形心的正交辅助锚定平面（`SKETCH_ANCHOR_HELPER=1`），基准面投影按正交等级分层（`tier0`→`tier1`→`tier2`）；② 草图回执与失败暂存新增 `section_references`（`anchor_count`、`reference_incomplete`、`helper_anchor_created`、`origin_pin_u`/`v`/`available`），`coordinates` 模式解算失败同时报告 `ProSectionSolve` 与救援 `ProSectionAutodim` 返回码，不再误报为单纯 `AutodimensionSketch` 失败。[BUG-173](work-items/BUG-173.md)
- **`creo_execute_plan` 内联 `chamfer_type` 保留、盲切 `cut_volume_check` 低去料告警、Runner 脱离披露与语法文档更新**。① `dump_plan_operations()` 保留 `ChamferOp` 上显式传入的 `chamfer_type`（修复内联提交 `d1_d2`/`distance_angle` 倒角在 `general.submit()` 二次校验时被误拒）；② 盲切拉伸（`extrude mode="cut"`、`depth_type="blind"`）回执新增 `cut_volume_check`（实际去料低于解析棱柱体积 `profile_area_mm2 * effective_depth_mm` 的 5% 时标记 `low_removal_warning=true`）；③ 新增 `bridge.spawn_detached_runner()`，Windows 下优先尝试 `CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP | CREATE_BREAKAWAY_FROM_JOB`（遇 `WinError 5` 回退）并在回执中披露 `runner_detached_from_job` 与 `runner_lifecycle_note`；④ `docs/REFERENCE_SYNTAX.md` 补充坐标尺寸共享顶点/共坐标轴跳过、斜基准面自动正交锚定面与盲切去料比例诊断说明。[BUG-174](work-items/BUG-174.md)

本机环境为 Windows x64 / Python 3.12.10 / Creo 10.0.0.0（`release_numeric=42`）。本版通过 `bridge.py build` 编译验证，完成 `tools/test_feedback0358_hang_recovery_sketch.py` 4/4 实机场景验收（基体与三点斜基准面创建、无手工锚定面下 B045 三块斜隔板草图+拉伸 9.094 s 完成且全量巡检仅 3 次/逐边日志 0 行、内联 `d1_d2` 倒角与擦边低去料盲切告警、`restore_baseline` 单次 `full` 巡检与 1800 s `identity` 恢复，全部几何精确匹配并保存重载通过）。外部原始 474 特征 `frigate_v4` / 53 特征 `carrier_v2` 本地模型文件、宿主禁止 breakaway 的客户端强制退出实机现场、Creo 9/12 与 WorkBuddy 黑盒未验。详见[验收与发布记录](validation/RELEASE-0.40.0.md)。

## 附件

- `MCP_CREO_MechDog-0.40.0-source.zip`
- `MCP_CREO_MechDog-0.40.0-source.zip.sha256`
- `MCP_CREO_MechDog-0.40.0-seed-library.zip`
- `MCP_CREO_MechDog-0.40.0-seed-library.zip.sha256`

种子包 SHA256 为 `507bd0019650dd397046b1ed2cfb735a4f840a4174487b45dab55e536e8db77f`。源码包摘要记录在同名 sidecar 中，两份 sidecar 分别记录对应 ZIP 的实际 SHA256。[GitHub Release](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.40.0)
