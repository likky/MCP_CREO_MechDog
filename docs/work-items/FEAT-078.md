# FEAT-078：`creo_inspect_model` 新增总表面积、逐面面积、包围盒与合并拓扑计数

- 类型：功能
- 优先级：P1

分类：**已有修复但待验收**（0.41.0 已交付并完成本机 Creo 10.0.0.0 零件与装配实机验收；Creo 9/12 与 WorkBuddy 黑盒未验）

- 目标版本：0.41.0（MINOR）

来源：[0.39.0 原始反馈（Creo 9 全圆边选择器与面积查询）](../validation/feedback-0.39.0-2026-11-23/originals/creo9-full-circle-edge-selector-and-area-inspection.md) §3、§4。

## 实现内容

1. `native/generic.cpp`：
   - `inspection()` 为零件与装配统一输出 `total_surface_area_mm2`（取自 `ProSolidMassPropertyWithDensityGet` 的 `mp.surface_area` 按已确认单位换算）与 `bounding_box_mm`（`min`/`max`/`size`，取自 `ProSolidOutlineGet` 按已确认单位换算）。
   - `inspect_surface()` 逐面调用 `ProSurfaceAreaEval` 输出 `surfaces[].area_mm2`（单位未知或求值失败时为 `null`）。
2. `src/creo_mechdog/model_queries.py`：
   - `inspection_summary()` 透传 `total_surface_area_mm2` 与 `bounding_box_mm`，默认 `detail="compact"` 直接可读。
   - 新增只读 `merged_counts`（合并同轴拆半圆柱面与同圆拆半圆弧边）与 `counts_convention` 说明，保持既有 `counts` 语义不变。

## 验收证据（2026-11-24）

- 实机 `tools/test_feedback0390_edge_inspect.py`（报告 `build/feedback0390_edge_inspect.json`）：
  - `S1`（R20×40 圆柱零件 `34158c45e7b045f2b1d6b53ddcfd4c24`）：`total_surface_area_mm2 = 7539.822368615503`、逐面 `surfaces[].area_mm2` 求和 `7539.822368615503`（与解析值 `2π×20×40 + 2π×20²` 精确吻合）；`bounding_box_mm.size = [40.05, 40.0, 40.0]`；`merged_counts = {surfaces: 3, edges: 4, cylindrical_face_groups: 1, circular_edge_groups: 2}`。
  - `S4`（2 实例圆柱装配 `bb95aca5bdef4d40abfb1dd37d217fe2`）：`total_surface_area_mm2 = 14555.486 mm²`、`bounding_box_mm = {min: [-20,-20,0], max: [120,20,40], size: [140, 40, 40]}`。
- 单元测试：`tests/unit/test_feedback0390_fixes.py::Feat078InspectAreaBboxAndMergedCountsTests` 全部通过。
- 未验范围：Creo 9/12 与 WorkBuddy 黑盒。

## 2026-11-24 新反馈补充

0.43.1 报告 §8/§9 与 0.43.0 报告 N3：同一几何的 bbox 比源件大 0.004—0.006 mm；`bounding_box_mm.min[2]=-910.0` 与 964 条 `surfaces[].bbox` 并集 `-885.0` 差 25 mm。待办：注明 bbox 精度量级与来源，排查两套口径是否应分字段命名，并补“面数只比类型+半径分组、不比张数”的验收指引。来源见 [DEV-101](DEV-101.md)。
