# FEAT-078：`creo_inspect_model` 新增总表面积、逐面面积、包围盒与合并拓扑计数

- 类型：功能
- 优先级：P1

分类：**部分交付，剩余待验收**。0.45.0 交付实体面包围盒修正。外部原计划、Creo 9/12 与 WorkBuddy 待验。 [0.45.0 回归与发布记录](../validation/RELEASE-0.45.0.md)

- 已交付版本为原功能 0.41.0 和包围盒修正 0.45.0。

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

## 2026-11-25 实体包围盒修正

来源为 0.44.0 / Creo 10.0.0.0 反馈 P2。切齿草图超出 R41 盘体、贯穿槽刀具越出 5 mm 厚度、67° 回转壳轮廓包络偏大。用临时模型重建单个齿槽、双向贯穿槽和八段截面的 67° 回转壳，按输入几何独立计算有符号极值。附加用例覆盖倾斜实例、嵌套实例和远离实体的独立曲面。

### 方法与公开回执

- `ProSolidOutlineGet` 读再生轮廓。逐实体 `ProSolidBodyOutlineGet` 在槽和齿槽上可排除刀具超界，但回转壳仍报告 X −84.264 至 −9.035 mm。排除曲线后调用 `ProSolidOutlineCompute` 可还原槽和壳，却把 R41 圆盘的 X 极值算成 ±40.919 mm。候选对照见 `build/feat078_outline_probe.json`。
- 新实现只遍历活动、非构造实体的面，用 `ProSurfaceTessellationGet` 采样修剪后的面。装配用 `ProAsmcomppathTrfGet` 的实例至根装配变换，在根坐标系取采样点极值，再统一用 mm 报告。源字段为 `solid_face_tessellation`，`bounding_box_status` 披露 0.001 mm 目标弦高和测量状态。这个参数是网格请求值，实测误差按算例报告。[PTC 面三角化 API](https://support.ptc.com/help/creo_toolkit/protoolkit_pma/r13/usascii/creo_toolkit/api/dita/4073.html)
- 无实体时 `bounding_box_mm=null`，状态为 `no_solid`。发生未解析实例、不完整三角化、识别到装配级切除或超出计算预算时返回 `unavailable` 及原因。旧保存快照的原生轮廓仍可在 `legacy_regeneration_outline_mm` 查询，新保存快照和实时刷新采用实体面口径。逐面、逐实体的旧 `bbox` 字段保留原单位和原语义。

### Creo 10 对照结果

| 夹具 | 旧轮廓 | 新实体面范围 | 独立期望 |
| --- | --- | --- | --- |
| R41 单齿槽 | Y 上限 41.250000 | 40.987804 | 40.987803 |
| 5 mm 厚板双向贯穿槽 | Z −0.5 至 5.5 | 0 至 5 | 0 至 5 |
| 67° 回转壳 | X −84.263782 至 −9.035144 | −60.369999 至 −45.345814 | −60.370000 至 −45.345815 |
| 30°/37° 倾斜圆盘装配 | X −42.131862 至 67.636400 | −27.099722 至 52.604259 | −27.099786 至 52.604324 |

倾斜装配对照中最大绝对误差为 0.000466 mm。全部解析对照中最大误差为 0.001236 mm。含远置独立曲面的实体零件及装配样本均符合实体解析范围。纯曲面零件返回 `no_solid`。

Windows x64 / Python 3.12.10 / Creo 10.0.0.0（release 42）及匹配 SDK。基点 `10fab183d4906d46a1f661700b4e4e09757876e3`，dirty=true。构建命令 `.\.venv\Scripts\python.exe bridge.py build`。测量版 worker 源码指纹 `61f56db893ac32c5d50bc0bfe93c948e23c25e61c858b05e78116998d2f7855f`，二进制 SHA256 `3e54c1773f0e0bc0b2bd6d5a80f0b57e0a12c5f6978a20ebba4c459a5d42ee34`。

- 修复前 `.\.venv\Scripts\python.exe tools/test_solid_bounding_box.py --baseline --output build/feat078_solid_bbox_baseline.json`。报告 SHA256 `580ba04d9eca59383f86af038f72ff1a48f8345221b0e198dc67283e06e30cf7`。
- 修复后 `.\.venv\Scripts\python.exe tools/test_solid_bounding_box.py` 完成 19 个作业，14 个写作业均确认保存重载。报告 `build/feat078_solid_bbox.json`，SHA256 `fce20b8aebf9c0b19f185450288fed5e32fee9f5b0b27b70bb6f04decd87efb4`。齿槽、贯穿槽、回转壳、直接旋转装配及嵌套旋转装配在保存重载后均重新进行只读测量，分别与该次保存的盒一致。装配保存作业 `a319c0f345d3499cbf9751ae2fa1794c`、`6ac94c5cd58045809c0e419f3025af4d`。
- 复查基线旧贯穿槽的历史快照，compact 和 full 均在 `legacy_regeneration_outline_mm` 返回原先的 Z −0.5 至 5.5 mm，当前 `bounding_box_mm` 为空。实体面测量报告来自新作业。
- `.\.venv\Scripts\python.exe tools/dev_check.py --work-item FEAT-078` 通过语言检查、三项离线验收及全量单元测试（4527 项，7 项跳过）。报告留存于 `build/feat078-development-check.json`，受检源码指纹 `48cb473ce960d6230b27341cd8242a7ae7d97c74ed0609e171b6ed383a31dec2`。

未测范围为外部报告的完整模型与计划、Creo 9/12、WorkBuddy 黑盒、混合单位装配、装配级切除和网格不完整或达到预算上限的实机路径。
