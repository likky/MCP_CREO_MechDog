# 发布记录 v0.41.0

日期为 2026-11-24，版本类型为 MINOR，公开工具仍 111。

上一版本：0.40.0（`v0.40.0`，提交 `9b7bdaa84675fef364972240a8f3d7c7677e2361`）。

## 验收范围

本版交付 [BUG-175](../work-items/BUG-175.md)、[BUG-176](../work-items/BUG-176.md)、[FEAT-078](../work-items/FEAT-078.md)、[FEAT-079](../work-items/FEAT-079.md)、[BUG-177](../work-items/BUG-177.md) 与 [BUG-178](../work-items/BUG-178.md)，逐字节归档 0.39.0 两份外部反馈原件至 [SOURCE_MANIFEST.json](feedback-0.39.0-2026-11-23/SOURCE_MANIFEST.json)（[bug170-unit-test-fixed-deadline-flaky.md](feedback-0.39.0-2026-11-23/originals/bug170-unit-test-fixed-deadline-flaky.md) SHA256 `8cdfbceae8b54ea73bfdd5a72c8e83fb4665408abde2355dc9c7a2552cc3e32e`、[creo9-full-circle-edge-selector-and-area-inspection.md](feedback-0.39.0-2026-11-23/originals/creo9-full-circle-edge-selector-and-area-inspection.md) SHA256 `174de538e660918071d21c4dfce2c7cbfb1f99c05ba24036c25ff455b8497560`）：

- `tests/unit/test_feedback0360_fixes.py`（[BUG-175](../work-items/BUG-175.md)）：BUG-170 单测改用可控假时钟消除 0.3 s 墙钟竞争（50/50 连续通过）。
- `src/creo_mechdog/geometry_selectors.py`、`native/geometry_selectors.cpp`（[BUG-176](../work-items/BUG-176.md)）：圆形边选择器新增 `full_circle: true`、接缝/极值 `point_mm` 自动消歧取最小边 ID、单点 `point_mm` 支持匹配圆弧边。
- `native/generic.cpp`、`src/creo_mechdog/model_queries.py`（[FEAT-078](../work-items/FEAT-078.md)）：`creo_inspect_model` 新增 `total_surface_area_mm2`、逐面 `surfaces[].area_mm2`、零件与装配 `bounding_box_mm`（`min`/`max`/`size`）、`merged_counts` 与 `counts_convention`。
- `native/generic.cpp`、`src/creo_mechdog/compact_sections.py`、`src/creo_mechdog/operation_results.py`（[FEAT-079](../work-items/FEAT-079.md)）：多集 `round`/`chamfer` 失败时逐集探测定位 `failed_reference_index`/`failed_reference`/`round_failure` 并保持回滚。
- `src/creo_mechdog/schema.py`、`src/creo_mechdog/profile_diagnostics.py`、`native/sketch_coordinates.cpp`、`server.py`、`docs/REFERENCE_SYNTAX.md`（[BUG-177](../work-items/BUG-177.md)）：`Arc` 支持有符号 `sweep_deg`、`spline` 数值面积、`coordinates` 超差附 `shifted_sample` 与 `XY`/`XZ`/`YZ` 基准面 `(u,v)`/法线对照表。
- `src/creo_mechdog/schema.py`、`src/creo_mechdog/feature_state.py`、`native/feature_state.cpp`、`src/creo_mechdog/component_changes.py`、`server.py`（[BUG-178](../work-items/BUG-178.md)）：`feature_state` 依赖展开 `include_dependencies` 与 `suggested_targets`、`component_changes` 1e-12 浮点容差、`creo_execute_plan` 空操作清晰报错。

## 环境与实机证据

- Windows x64 / Python 3.12.10 / Creo 10.0.0.0（`release_numeric=42`，安装目录 `D:\Program Files\PTC\Creo 10.0.0.0`）与匹配 Toolkit SDK；`bridge.py build` 编译 `build/creo_worker.exe` 成功。
- `tools/test_feedback0390_edge_inspect.py`（报告 `build/feedback0390_edge_inspect.json`）：**4/4 通过**：
  - `S1_full_circle_seam_point_arc_and_area_bbox`（模型 `34158c45e7b045f2b1d6b53ddcfd4c24`）：初始体积 `50265.482457 mm³`、`total_surface_area_mm2=7539.822369`（逐面求和一致）、`bounding_box_mm.size=[40.05,40.0,40.0]`、`merged_counts={surfaces:3, edges:4, cylindrical_face_groups:1, circular_edge_groups:2}`；`full_circle:true` R2 圆角体积 `50160.021 mm³`、极值接缝点 `[20,0,0]` D2 倒角体积 `49917.072 mm³`、单点 `[15,0,30]` D1.5 倒角（作业 `920574343ec847b2bfd9c79ee5fd603e`）体积 `21103.256 mm³`，均 `saved_file_reloaded_and_verified=true`。
  - `S2_multi_set_round_failure_localization`（作业 `3f6cc9016f464fc3a08eaaaf79485f85`）：2 集 D10 倒角精准定位 `failed_reference_index=1`、`round_failure.failed_indices=[1]`、`probed_count=2`，`rollback_succeeded=true`。
  - `S3_major_arc_sweep_and_feature_state_include_deps`：`sweep_deg=270` 优弧体积 `9424.777961 mm³`（解析 `9424.777961 mm³`）；`feature_state delete` 缺依赖返回 `suggested_targets=['sk_cut', 84]`，带 `include_dependencies=true`（作业 `f256c840bb8a42b3b10336fc482c967b`）自动纳入 `cut_top`（84）与两个伴随 `datum_plane`（76、85）并恢复体积至 `9424.777961 mm³`，`saved_file_reloaded_and_verified=true`。
  - `S4_assembly_area_bbox_and_component_changes`（装配 `bb95aca5bdef4d40abfb1dd37d217fe2`）：`total_surface_area_mm2=14555.486 mm²`、`bounding_box_mm.size=[140.0,40.0,40.0]`；新增第 3 实例 `c3` 后 `component_changes.changes` 仅含 `added`（零误报 `moved`），`saved_file_reloaded_and_verified=true`。

## 种子包

`python tools/package_seeds.py --output build/release-0.41.0/MCP_CREO_MechDog-0.41.0-seed-library.zip --allow-record-mismatch` 首次构建得到摘要后回填 `docs/seed_package.json`；再用 `python tools/package_seeds.py --output build/release-0.41.0/confirm/MCP_CREO_MechDog-0.41.0-seed-library.zip` 重建确认，两次摘要一致：`af563439edba0e1682f03ea78c1d9459d9bbd872bbcc1b59adcf27b95415df09`（24 个文件、9 个种子）。

## 单测证据

发布候选在 0.41.0 工作树上运行 `tools/test_unit.py`，全量 unittest 通过，0 失败、0 错误。下列数字取自本轮 `build/unit_test_report.json`，该报告不随源码包分发。

待本轮 `tools/test_unit.py` 完成后回填 `run_id`、总数与受测源码指纹。

## 未测范围

- Creo 9.0.0.0 原始直列四缸发动机 6 零件与 29 实例装配、Creo 12 与 WorkBuddy 外部黑盒验收未执行。
- 外部报告方在干净源码包中复测 BUG-175 待反馈。

## 附件

- `MCP_CREO_MechDog-0.41.0-source.zip`
- `MCP_CREO_MechDog-0.41.0-source.zip.sha256`
- `MCP_CREO_MechDog-0.41.0-seed-library.zip`
- `MCP_CREO_MechDog-0.41.0-seed-library.zip.sha256`

种子包 SHA256 为 `af563439edba0e1682f03ea78c1d9459d9bbd872bbcc1b59adcf27b95415df09`。源码包摘要记录在同名 sidecar 中，两份 sidecar 分别记录对应 ZIP 的实际 SHA256。

## 逐 ID 状态核对

| ID | 交付版本 | 实际 Release | 技术状态 | 卡首页 | 主台账 | 差异说明 |
| --- | --- | --- | --- | --- | --- | --- |
| [BUG-175](../work-items/BUG-175.md) | 0.41.0 | v0.41.0 | 已有修复但待验收 | 已有修复但待验收（0.41.0 已交付并完成 50/50 连续确定性验证；外部干净源码包复测待反馈） | 已有修复但待验收 | 剩外部干净源码包复测 |
| [BUG-176](../work-items/BUG-176.md) | 0.41.0 | v0.41.0 | 已有修复但待验收 | 已有修复但待验收（0.41.0 已交付并完成本机 Creo 10.0.0.0 实机验收；Creo 9 原始发动机零件与 WorkBuddy 黑盒未验） | 已有修复但待验收 | 剩 Creo 9 原始零件、Creo 12、WorkBuddy 黑盒 |
| [FEAT-078](../work-items/FEAT-078.md) | 0.41.0 | v0.41.0 | 已有修复但待验收 | 已有修复但待验收（0.41.0 已交付并完成本机 Creo 10.0.0.0 零件与装配实机验收；Creo 9/12 与 WorkBuddy 黑盒未验） | 已有修复但待验收 | 剩 Creo 9/12、WorkBuddy 黑盒 |
| [FEAT-079](../work-items/FEAT-079.md) | 0.41.0 | v0.41.0 | 已有修复但待验收 | 已有修复但待验收（0.41.0 已交付并完成本机 Creo 10.0.0.0 实机验收；Creo 9/12 与 WorkBuddy 黑盒未验） | 已有修复但待验收 | 剩 Creo 9/12、WorkBuddy 黑盒 |
| [BUG-177](../work-items/BUG-177.md) | 0.41.0 | v0.41.0 | 已有修复但待验收 | 已有修复但待验收（0.41.0 已交付并完成本机 Creo 10.0.0.0 实机验收；Creo 9/12 与 WorkBuddy 黑盒未验） | 已有修复但待验收 | 剩 Creo 9/12、WorkBuddy 黑盒 |
| [BUG-178](../work-items/BUG-178.md) | 0.41.0 | v0.41.0 | 已有修复但待验收 | 已有修复但待验收（0.41.0 已交付并完成本机 Creo 10.0.0.0 实机验收；Creo 9/12 与 WorkBuddy 黑盒未验） | 已有修复但待验收 | 剩 Creo 9/12、WorkBuddy 黑盒 |

## 远端核对

远端核对发布后执行，当前未验证。[GitHub Release](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.41.0)
