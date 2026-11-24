# 发布记录 v0.42.0

日期为 2026-11-24，版本类型为 MINOR，公开工具仍 111。

上一版本：0.41.0（`v0.41.0`，提交 `93003cc40ddf3087a4dc2d74200909abe7c63776`）。

## 验收范围

本版交付 [BUG-179](../work-items/BUG-179.md)、[BUG-180](../work-items/BUG-180.md)、[FEAT-080](../work-items/FEAT-080.md)、[BUG-181](../work-items/BUG-181.md)、[FEAT-081](../work-items/FEAT-081.md) 与 [BUG-182](../work-items/BUG-182.md)，逐字节归档 0.40.0 两份外部反馈原件至 [SOURCE_MANIFEST.json](feedback-0.40.0-2026-11-24/SOURCE_MANIFEST.json)（[frigate-chamfer-tangent-chain-and-round-diagnostics.md](feedback-0.40.0-2026-11-24/originals/frigate-chamfer-tangent-chain-and-round-diagnostics.md) SHA256 `02e0149e78d92b6f9311e60da338e5d52e8195201b22c9bd84502183cfa92019`、[arm7-region-cut-g2-verification-and-mated-assembly.md](feedback-0.40.0-2026-11-24/originals/arm7-region-cut-g2-verification-and-mated-assembly.md) SHA256 `0689eb6e7a937fd7afa04c308590ccfcfb2b86b2a96bedab84c5dc4fade10347`）：

- `src/creo_mechdog/schema.py`、`native/generic.cpp`、`src/creo_mechdog/compact_sections.py`（[BUG-179](../work-items/BUG-179.md)）：`ChamferOp` 新增 `propagate: "single" | "chain"`，倒角回执新增 `created_surface_count`、`created_surface_area_mm2` 与 `chamfered_edge_length_mm`，`chamfer_type` 补注 `exclude=True` 与 `dump_plan_operations()` 说明。
- `native/generic.cpp`、`src/creo_mechdog/compact_sections.py`（[BUG-180](../work-items/BUG-180.md)）：单/多边 `round`/`chamfer` 失败采集 `ProFeatureStatusGet` 与 `round_failure.edge_diagnostics`；`round` 成功回执补齐有符号 `volume_delta_mm3` 与 `round_kind`。
- `src/creo_mechdog/schema.py`、`server.py`、`native/generic.cpp`、`src/creo_mechdog/model_queries.py`、`src/creo_mechdog/query_client.py`（[FEAT-080](../work-items/FEAT-080.md)）：`ShellOp`/`creo_shell` 新增精确 `body_id` 单实体抽壳、`MirrorOp` 补充三条替代路径、`creo_inspect_model` 分页顶层新增 `total_count` 与 `page_count`。
- `src/creo_mechdog/sketch_region_split.py`、`src/creo_mechdog/sketch_regions.py`（[BUG-181](../work-items/BUG-181.md)）：`ExtrudeOp.region` 新增曲线交点分割、精确 Boehm B 样条细分与零命中 `closest_loop` 诊断。
- `native/generic.cpp`、`src/creo_mechdog/compact_sections.py`（[FEAT-081](../work-items/FEAT-081.md)）：G2 圆角新增几何级 `g2_verification` 曲率连续性验证。
- `native/geometry_selectors.cpp`、`native/generic.cpp`（[BUG-182](../work-items/BUG-182.md)）：装配面/边选择器零命中每条候选新增 `suggested_reference`、报错直出最近候选、`assembly` 空间标注 `nearest_coordinate_space="component"` 与 `assembly_origin_mm`/`assembly_normal`。

## 环境与实机证据

- Windows x64 / Python 3.12.10 / Creo 10.0.0.0（`release_numeric=42`，安装目录 `D:\Program Files\PTC\Creo 10.0.0.0`）与匹配 Toolkit SDK；`bridge.py build` 编译 `build/creo_worker.exe` 成功。
- `tools/test_feedback0400_live.py`（报告 `build/feedback0400_live_report.json`）：**5/5 通过**：
  - `S1_chamfer_propagate`：`single`（作业 `4583c49860ce44dbb4bf52c0841eb6ba`）实测 `chamfered_edge_length_mm=97.141428`（精确吻合 $90+\sqrt{51}$）、`delta=-423.0002 mm³`；`chain`（作业 `b41e73cdc12e4fed891057efe97d3dfc`）实测 `chamfered_edge_length_mm=155.707963`（精确吻合 $90+10\pi/2+50$）、`delta=-693.6174 mm³`，均 `saved_file_reloaded_and_verified=true`。
  - `S2_round_g2_concave_failure`：G2 R10 凸圆角（作业 `41527cfd9703406b816798e7bb5caf6e`）`round_kind="convex"`、`g2_verification={native_conic_type:3, native_conic_value:0.5, sampled_edges:2, sampled_points:6, max_tangent_angle_deg:0.0, max_curvature_gap_inv_mm:0.0, tolerance_inv_mm:0.002, verdict:"pass"}`；凹边 R5 圆角（作业 `61fde9e665a14ed68b70365c07bde157`）`round_kind="concave"`、`volume_delta_mm3=+429.203377 mm³`；单边 R999 失败（作业 `ffe9223d341142ac8882bd48c4f6f6fd`）输出 `round_failure.edge_diagnostics`（edge 161、length 70 mm、dihedral 90°、两相邻平面 69/63 与两端点邻边统计）并干净回滚。
  - `S3_shell_body_id_inspect_total`：两实体零件仅对 `body_b_id=90` 抽壳 2 mm（作业 `f3b5f71a2a814bba9f0269554cbfb358`），实测体积 `78751.99999999999 mm³` vs 解析值 `78752.0 mm³`（另一实体 `64000.0 mm³` 零改动），`saved_file_reloaded_and_verified=true`；分页返回 `total_count=24`、`page_count=5`。
  - `S4_region_cut_bspline_split`：含两条相交三次 B 样条与外框直线的 YZ 草图经 `ExtrudeOp.region` 切除指定子区域（作业 `48afea02f1bf476c8d9883e15313f10a`），体积 `3000.0 → 2699.9999999999995 mm³`（去料 `300.00000000000045 mm³`），`saved_file_reloaded_and_verified=true`。
  - `S5_assembly_selector_suggested_ref`：偏移 `[100,0,0]` 的装配板触发 0.254 mm 零命中（作业 `277b1320f6eb4409bc84df6fb8e1c652`），返回 `requested_coordinate_space="assembly"`、`nearest_coordinate_space="component"`、`origin_mm=[0,0,10]`、`assembly_origin_mm=[100,0,10]`、`suggested_reference={"kind":"surface","id":58}` 及报错中的 `Closest candidate: {kind:'surface',id:58}`，干净回滚。

## 种子包

`python tools/package_seeds.py --output build/release-0.42.0/MCP_CREO_MechDog-0.42.0-seed-library.zip --allow-record-mismatch` 首次构建得到摘要后回填 `docs/seed_package.json`；再用 `python tools/package_seeds.py --output build/release-0.42.0/confirm/MCP_CREO_MechDog-0.42.0-seed-library.zip` 重建确认，两次摘要一致：`23ba2e8f0f7599360a9f4ff3cc13c4ab8378335a905de9966f3171a1b975b4f3`（24 个文件、9 个种子）。

## 单测证据

发布候选在 0.42.0 工作树上运行 `tools/dev_check.py --work-item BUG-179`，全量 unittest 待运行并回填。

## 未测范围

- Creo 9/12、原护卫舰 `frigate_v4` / 原 Arm7 完整工程、60 条配合全量装配与 WorkBuddy 外部黑盒验收未执行。

## 附件

- `MCP_CREO_MechDog-0.42.0-source.zip`
- `MCP_CREO_MechDog-0.42.0-source.zip.sha256`
- `MCP_CREO_MechDog-0.42.0-seed-library.zip`
- `MCP_CREO_MechDog-0.42.0-seed-library.zip.sha256`

种子包 SHA256 为 `23ba2e8f0f7599360a9f4ff3cc13c4ab8378335a905de9966f3171a1b975b4f3`。源码包摘要记录在同名 sidecar 中，两份 sidecar 分别记录对应 ZIP 的实际 SHA256。

## 逐 ID 状态核对

| ID | 交付版本 | 实际 Release | 技术状态 | 卡首页 | 主台账 | 差异说明 |
| --- | --- | --- | --- | --- | --- | --- |
| [BUG-179](../work-items/BUG-179.md) | 0.42.0 | v0.42.0 | 已有修复但待验收 | 已有修复但待验收（0.42.0 已交付并完成本机 Creo 10.0.0.0 实机验收；Creo 9/12 与 WorkBuddy 黑盒未验） | 已有修复但待验收 | 剩 Creo 9/12、WorkBuddy 黑盒 |
| [BUG-180](../work-items/BUG-180.md) | 0.42.0 | v0.42.0 | 已有修复但待验收 | 已有修复但待验收（0.42.0 已交付并完成本机 Creo 10.0.0.0 实机验收；Creo 9/12 与 WorkBuddy 黑盒未验） | 已有修复但待验收 | 剩 Creo 9/12、WorkBuddy 黑盒 |
| [FEAT-080](../work-items/FEAT-080.md) | 0.42.0 | v0.42.0 | 已有修复但待验收 | 已有修复但待验收（0.42.0 已交付并完成本机 Creo 10.0.0.0 实机验收；Creo 9/12 与 WorkBuddy 黑盒未验） | 已有修复但待验收 | 剩 Creo 9/12、WorkBuddy 黑盒 |
| [BUG-181](../work-items/BUG-181.md) | 0.42.0 | v0.42.0 | 已有修复但待验收 | 已有修复但待验收（0.42.0 已交付并完成本机 Creo 10.0.0.0 实机验收；Creo 9/12 与 WorkBuddy 黑盒未验） | 已有修复但待验收 | 剩 Creo 9/12、原 Arm7 工程、WorkBuddy 黑盒 |
| [FEAT-081](../work-items/FEAT-081.md) | 0.42.0 | v0.42.0 | 已有修复但待验收 | 已有修复但待验收（0.42.0 已交付并完成本机 Creo 10.0.0.0 实机验收；Creo 9/12 与 WorkBuddy 黑盒未验） | 已有修复但待验收 | 剩 Creo 9/12、非解析面 G2、WorkBuddy 黑盒 |
| [BUG-182](../work-items/BUG-182.md) | 0.42.0 | v0.42.0 | 已有修复但待验收 | 已有修复但待验收（0.42.0 已交付并完成本机 Creo 10.0.0.0 实机验收；Creo 9/12 与 WorkBuddy 黑盒未验） | 已有修复但待验收 | 剩 Creo 9/12、全量 60 配合装配、WorkBuddy 黑盒 |

## 远端核对

发布后执行，当前未验证。
