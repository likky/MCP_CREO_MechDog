# MCP_CREO_MechDog 0.44.0 版本说明

2026-11-24 发布范围为 MINOR，公开工具数 111。本版汇集 [DEV-100](work-items/DEV-100.md) 与 [DEV-101](work-items/DEV-101.md) 首批本机 Creo 10 实机验收交付：

- **钣金法兰材料侧、宽向与附着复核**：[BUG-186](work-items/BUG-186.md) 新增 `sheetmetal_flange.flip_thickness` 分别控制伸展侧与板厚侧（四象限实测通过）；[FEAT-084](work-items/FEAT-084.md) 让 `sheetmetal_base_flange` 接受字典平面与厚度侧，Arm2 钣金毛坯包络 `(-10,-2,-2)–(10,8,12)`、体积 `850.19 mm³`、内外弯 R0.7366/R2.7366 通过保存重载；[FEAT-089](work-items/FEAT-089.md) 实测确认 `SheetmetalFlangeOp` 连续两段附着已有壁自由端与方向控制已覆盖需求。
- **STL 导出预算与阶段进度**：[BUG-130](work-items/BUG-130.md) 独立导出新增 `timeout_seconds` 单次硬预算，默认逐面导出通过 `native_progress.sub_stage` 披露 6 个网格阶段。
- **边选择器面过滤与唯一最近消歧**：[FEAT-085](work-items/FEAT-085.md) 新增 `on_face={"kind":"surface","id":N}` 与 `ambiguity="nearest"`（等距候选仍拒绝），并支持 compact 回读 `geometry_selector_resolution`。
- **草图闭合焊合、开放端定位、显式 v 轴与构造圆**：[DEV-100](work-items/DEV-100.md) 把 `closure_tolerance_mm` 接入 `snap_endpoints` 并支持多缝开放链焊合，原生失败回执与报错列出按距离升序的 `open_end_samples` / `Nearest open ends:`；[BUG-187](work-items/BUG-187.md) 新增 `PlaneOp.flip` 与 `SketchOp.plane.v_axis`（同时给 `u_axis`/`v_axis` 时按叉积 `u_axis × v_axis` 确定法线）；[BUG-188](work-items/BUG-188.md) 让 `dimensioning="coordinates"` 放行 `PRO_2D_CONSTR_CIRCLE` 并标记 `construction=true`。
- **旋转两点式坐标轴与弧度入口**：`RevolveOp` 与 `creo_revolve` 支持 `axis={"kind":"sketch_points","start_mm":[u1,v1],"end_mm":[u2,v2]}`（及简写 `{start_mm,end_mm}`）与 `angle_rad` 弧度入口，`(360, 360.001]` 度受控收敛至 `360.0°` 并回执 `angle_clamped_from_deg`。
- **装配 packaged 放置与调用/诊断体验**：[FEAT-088](work-items/FEAT-088.md) 新增 `assemble_component.placement="packaged"`（保留变换、0 约束）并回读 `constraint_count`；[BUG-189](work-items/BUG-189.md) 在 MCP 调用边界按工具 schema 拒绝未知参数并附拼写建议；[BUG-190](work-items/BUG-190.md) 在失败作业 `creo_get_job` 顶层透传 `failed_operation_index`/`failed_stage`/`failure_phase`/`native_result_path`/`round_failure_summary`。

上一版本：0.43.2（`v0.43.2`，提交 `a6769c3cc2507e9bb69fc26651d45050e2d2d27a`）。

本版已在本机 Windows x64 / Python 3.12.10 / Creo 10.0.0.0（`release_numeric=42`）完成全部上述建模、装配、保存重载与失败回滚验收。Creo 9/12 实机、WorkBuddy 黑盒、两圆弧直接焊合以及 [FEAT-086](work-items/FEAT-086.md)/[FEAT-087](work-items/FEAT-087.md) 仍留后续版本。[验收与发布记录](validation/RELEASE-0.44.0.md)

## 附件

- `MCP_CREO_MechDog-0.44.0-source.zip`
- `MCP_CREO_MechDog-0.44.0-source.zip.sha256`
- `MCP_CREO_MechDog-0.44.0-seed-library.zip`
- `MCP_CREO_MechDog-0.44.0-seed-library.zip.sha256`

种子包 SHA256 为 `cfc72a788053ce067feb90021d6558a1c1db1f5f5002edcca341d779edc7a791`。源码包摘要记录在同名 sidecar 中。两份同名 sidecar 分别记录对应 ZIP 的实际 SHA256。[GitHub Release](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.44.0)
