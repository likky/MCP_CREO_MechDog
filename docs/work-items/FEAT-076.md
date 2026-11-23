# FEAT-076：边选择器支持 `feature` 标签过滤、`creo_inspect_model` 支持 `near` 空间近邻查询与圆角选择器文档同步

- 类型：功能
- 优先级：P1

分类：**已有修复但待验收**（0.39.0 已交付并完成本机 Creo 10.0.0.0 实机验收；原始 6428 边实机件、Creo 9/12 与 WorkBuddy 黑盒未验）

- 目标版本：0.39.0（MINOR）

来源：[0.36.0 反馈原件 §五（问题 D）](../validation/feedback-0.36.0-2026-11-23/originals/upgrade-session-and-recovery-deadlock.md)。关联 [BUG-155](BUG-155.md)。

## 实现变更

- `src/creo_mechdog/geometry_selectors.py` 与 `native/generic.cpp`：开放 `target="edge"` 模型空间 `feature` 标签过滤；原生按 `ProFeatureGeomitemVisit(&owner, PRO_EDGE, ...)` 与相邻面 `ProFeatureGeomitemVisit(&owner, PRO_SURFACE, ...)` 的并集限定候选边（完整覆盖特征自身边与切除交线边）。
- `src/creo_mechdog/model_queries.py`、`generic_bridge.py`、`server.py`：为 `creo_inspect_model` 新增可选参数 `near: list[float] | None`（`[x, y, z]` mm，适用于 `detail="full"` 且 `section` 为 `"edges"` 或 `"surfaces"`）与 `max_distance_mm: float | None`，按精确 3D 线段/圆弧/面距离升序返回最近 `limit` 条并附加 `distance_mm` 与 `near_filter` 统计。
- `server.py`：`creo_round` 与 `creo_chamfer` 的 `references` 字段说明同步补齐 `geometry_selector(target="edge", point_mm=..., feature=...)` 写法。

## 验收证据（2026-11-23）

- 环境：Windows x64 / Python 3.12.10 / Creo 10.0.0.0（`release_numeric=42`），执行器 `build/creo_worker.exe` SHA256 `e1f4a3782146cb969264ded0a32185760dd2e0173dd36d3417e57c785257b321`。
- 实机 `tools/test_feedback0360_recovery_preview_edges.py --live --confirm-session-usable`（`F076_near_edge_query_and_feature_scoped_round`，报告 SHA256 `cd0e12d248374ac68dc409784b375ed677d85fb254709b6ee548695ba1a0c083`）：
  - `creo_inspect_model(detail="full", section="edges", near=[30, 30, 20], limit=5)` 一次定位边 `101`（`distance_mm=0.0`，从 24 条边按距离升序返回）。
  - `round(size=2.0)` 使用 `geometry_selector(target="edge", point_mm=[30, 30, 20], feature="top_boss", tolerance_mm=0.5)`（作业 `f2840203…`）成功，体积 `52000.0 → 51982.83180179726 mm³`（解析 `51982.831853071795`），`saved_file_reloaded_and_verified=true`。
- 单元测试：`tests/unit/test_feedback0360_fixes.py::Feat076EdgeSelectorAndNearQueryTests` 3/3 通过（含 6428 边合成快照单次 `near` 查询与圆弧距离精度校验）。
- 未验范围：原始 6428 边 M113 P05 零件实机、Creo 9/12 与 WorkBuddy 黑盒。
