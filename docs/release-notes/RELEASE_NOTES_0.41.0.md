# MCP_CREO_MechDog 0.41.0 版本说明

版本类型为 MINOR，公开工具数 111。本版基于 0.39.0 两份外部反馈（BUG-170 单测固定 0.3 s deadline 随机失败；Creo 9 全圆边选择器阻断、面积/包围盒缺口与草图/装配可用性）交付 [BUG-175](../work-items/BUG-175.md)、[BUG-176](../work-items/BUG-176.md)、[FEAT-078](../work-items/FEAT-078.md)、[FEAT-079](../work-items/FEAT-079.md)、[BUG-177](../work-items/BUG-177.md) 与 [BUG-178](../work-items/BUG-178.md)，并逐字节归档两份反馈原件至 [SOURCE_MANIFEST.json](../validation/feedback-0.39.0-2026-11-23/SOURCE_MANIFEST.json)。

上一版本：0.40.0（`v0.40.0`，提交 `9b7bdaa84675fef364972240a8f3d7c7677e2361`）。

- **修复 BUG-170 单测固定 0.3 s 墙钟 deadline 导致的随机失败**。`tests/unit/test_feedback0360_fixes.py::Bug170StaleSessionAndForceNewTests::test_drive_stale_session_without_and_with_force_new_session` 改用可控假时钟（mock `creo_startup.time.monotonic` 与 `coord1._stop.wait`），保证 preparation 与首次 `-4` 探测完成后才越过 deadline，50/50 连续确定性通过。[BUG-175](../work-items/BUG-175.md)
- **整圆棱边选择器 `full_circle:true`、接缝/极值 `point_mm` 自动消歧与单点选圆弧**。① 圆形边选择器（`center_mm` + `radius_mm` + 可选 `axis`）新增布尔选项 `full_circle: true`，仅当命中多段弧同属同一物理整圆时确定性取最小边 ID（`round`/`chamfer` 沿整圆传播）；② 圆形边选择器携带 `point_mm` 且点落于两段半圆弧公共接缝/象限极值点时，自动确定性取最小边 ID 并披露 `seam_point_resolved=true`；③ 仅传 `point_mm` 的单点边选择器同时支持有限直边与圆弧边。[BUG-176](../work-items/BUG-176.md)
- **`creo_inspect_model` 新增总表面积、逐面面积、包围盒与合并拓扑计数**。原生 `inspection()` 为零件与装配统一输出 `total_surface_area_mm2`（取自 `ProSolidMassPropertyWithDensityGet`）与 `bounding_box_mm`（`min`/`max`/`size`，取自 `ProSolidOutlineGet`），`inspect_surface()` 逐面调用 `ProSurfaceAreaEval` 输出 `surfaces[].area_mm2`；Python `inspection_summary()` 透传总表面积与包围盒，并新增 `merged_counts`（合并同轴拆半圆柱面与同圆拆半圆弧边）与 `counts_convention` 说明，既有 `counts` 语义不变。[FEAT-078](../work-items/FEAT-078.md)
- **多引用 `round` / `chamfer` 失败自动逐集定位**。当多集（>1）圆角或倒角创建/再生失败时，原生先清理失败特征再在安全上限（前 20 集）内逐集探测并清理探针，失败回执与异常消息明确指出 `failed_reference_index`、`failed_reference` 与 `round_failure.failed_indices`，并保持完整事务回滚。[FEAT-079](../work-items/FEAT-079.md)
- **草图优弧 `sweep_deg`、`spline` 数值面积、`coordinates` 偏差样本与基准面文档**。① `Arc` 支持有符号张角 `sweep_deg`（`0 < |sweep_deg| < 360`）直接表达 >180° 优弧；② `profile_diagnostics.py` 对 `spline` 进行平滑 Catmull-Rom 采样使闭合剖面返回数值 `material_area_mm2`（保留 `b_spline`/`ellipse` 为 `unsupported_entities`）；③ `coordinates` 超差拒绝附带 `shifted_sample`；④ `creo_create_sketch`、`creo_extrude` 与 `docs/REFERENCE_SYNTAX.md` 补全 `XY`/`XZ`/`YZ` 基准面 `(u,v)` 与法线对照表（标注 `XZ` 法线为 `-Y`）。[BUG-177](../work-items/BUG-177.md)
- **`feature_state` 依赖展开与建议目标、`component_changes` 浮点噪声过滤与 `creo_execute_plan` 空操作指引**。① `FeatureStateOp` 新增可选 `include_dependencies: bool = False`，开启后自动纳入非系统必需受影响依赖并记录 `auto_included_dependencies`，默认 `false` 缺依赖时给出可复制 `suggested_targets`；② `component_changes.py` 引入 `1e-12` 变换矩阵容差消除无关既有组件误报 `moved`；③ `creo_execute_plan` 空操作返回明确指引（如 `creo_new_assembly`）。[BUG-178](../work-items/BUG-178.md)

本机环境为 Windows x64 / Python 3.12.10 / Creo 10.0.0.0（`release_numeric=42`）。本版通过 `bridge.py build` 编译验证，完成 `tools/test_feedback0390_edge_inspect.py` 4/4 实机场景验收（整圆 `full_circle` 圆角、极值接缝点倒角、单点选圆弧倒角、零件与装配表面积/包围盒/合并计数精确吻合、多集倒角失败定位索引 1 与回滚、270° 优弧 `sweep_deg`、`feature_state include_dependencies=true` 自动展开依赖删除与保存重载、装配新增第 3 实例零误报 `moved`）。Creo 9.0.0.0 原始发动机零件、Creo 12 与 WorkBuddy 黑盒未验。详见[验收与发布记录](../validation/RELEASE-0.41.0.md)。

## 附件

- `MCP_CREO_MechDog-0.41.0-source.zip`
- `MCP_CREO_MechDog-0.41.0-source.zip.sha256`
- `MCP_CREO_MechDog-0.41.0-seed-library.zip`
- `MCP_CREO_MechDog-0.41.0-seed-library.zip.sha256`

种子包 SHA256 为 `af563439edba0e1682f03ea78c1d9459d9bbd872bbcc1b59adcf27b95415df09`。源码包摘要记录在同名 sidecar 中，两份 sidecar 分别记录对应 ZIP 的实际 SHA256。[GitHub Release](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.41.0)
