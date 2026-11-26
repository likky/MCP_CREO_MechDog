# MCP_CREO_MechDog 0.42.0 版本说明

版本类型为 MINOR，公开工具数 111。本版基于 0.40.0 两份外部反馈（护卫舰倒角延伸/圆角失败无诊断/抽壳单实体/分页计数；Arm7 区域切除零命中/G2 曲率几何验证/装配面选择器零命中）交付 [BUG-179](../work-items/BUG-179.md)、[BUG-180](../work-items/BUG-180.md)、[FEAT-080](../work-items/FEAT-080.md)、[BUG-181](../work-items/BUG-181.md)、[FEAT-081](../work-items/FEAT-081.md) 与 [BUG-182](../work-items/BUG-182.md)，并逐字节归档两份反馈原件至 [SOURCE_MANIFEST.json](../validation/feedback-0.40.0-2026-11-24/SOURCE_MANIFEST.json)。

上一版本：0.41.0（`v0.41.0`，提交 `93003cc40ddf3087a4dc2d74200909abe7c63776`）。

- **`chamfer` 传播模式、实测倒角长度/面积回执与 `chamfer_type` 文档说明**。Creo 10 实测确认 `PRO_CURVCOLL_ADD_ONE_INSTR` 仅选单边（但开放/相切端受 Creo 默认过渡线性延伸至相邻面退出点），显式追加 `PRO_CURVCOLL_ADD_TANGENT_INSTR` 则沿整条切向链传播。`ChamferOp` 新增可选 `propagate: "single" | "chain"`（默认 `"single"` 维持既有行为）；成功回执新增 `created_surface_count`、`created_surface_area_mm2` 与 `chamfered_edge_length_mm`；`ChamferOp.chamfer_type` 补注 `exclude=True` 与 `dump_plan_operations()` 说明。[BUG-179](../work-items/BUG-179.md)
- **`round`/`chamfer` 单/多边失败几何层诊断与 `round` 凹凸加去料回执**。无论单边还是多边失败，`generic_round` 均采集 `ProFeatureStatusGet` 与 `round_failure.edge_diagnostics`（边长、相邻面 ID/类型/面积/中点法向、中点二面角、两端点邻边数量/最短邻边长度与相切邻边 ID）；`round` 成功回执补齐有符号 `volume_delta_mm3` 与 `round_kind`（`"convex"` / `"concave"` / `"neutral"` / `"unknown"`）。[BUG-180](../work-items/BUG-180.md)
- **`ShellOp` 按实体 `body_id` 限定抽壳、`MirrorOp` 替代指引与 `creo_inspect_model` 分页总数**。`ShellOp` 与 `creo_shell` 新增可选精确 `body_id`（支持负数初始体如 `-5778` 及正数新建体），原生经 `require_scopable_body` 校验后按指定实体写入 `PRO_E_BODY_SELECT` 并返回 `body_id`；`MirrorOp` 拒绝特征引用时补充整件/面组/镜像重建三条替代方案；`creo_inspect_model` 分页响应顶层新增 `total_count` 与 `page_count`（保留 `returned_count` 向后兼容）。[FEAT-080](../work-items/FEAT-080.md)
- **Arm7 `ExtrudeOp.region` 交点分割、精确 Boehm B 样条细分与差异诊断**。新增 `src/creo_mechdog/sketch_region_split.py`，对直线、圆弧与 clamped B 样条做两两求交、T 型端点求交与高斯-牛顿精化，并在内部交点处通过精确 Boehm 节点插入分割 B 样条；无内部交点时保持源实体不变；零命中报错附带 `closest_loop=`、`max_endpoint_diff_mm=` 与 `detected_loops=`。[BUG-181](../work-items/BUG-181.md)
- **G2 曲率连续圆角几何级曲率验证（`g2_verification`）**。请求 `curvature_continuous=true` 时，原生读回 `PRO_E_RNDCH_CONIC_TYPE`/`PRO_E_RNDCH_CONIC_VALUE`，并沿圆角面与相邻支撑面的共享相切边界边调用 `ProEdgeXyzdataEval`、`ProSurfaceParamEval` 与 `ProSurfaceXyzdataEval` 计算第一、第二基本形式下的法向夹角与跨边界法曲率差，输出结构化 `g2_verification`（`verdict: "pass" | "fail" | "unsupported"`）。[FEAT-081](../work-items/FEAT-081.md)
- **装配面/边选择器零命中可执行修复建议与坐标空间语义澄清**。`nearest_surfaces`/`nearest_edges` 每条候选新增可直接复制的 `suggested_reference`，零命中报错直出最近候选；`requested_coordinate_space="assembly"` 时标注 `nearest_coordinate_space="component"` 并补充 `assembly_origin_mm` 与 `assembly_normal`/`assembly_axis`。[BUG-182](../work-items/BUG-182.md)

本机环境为 Windows x64 / Python 3.12.10 / Creo 10.0.0.0（`release_numeric=42`）。本版通过 `bridge.py build` 编译验证，完成 `tools/test_feedback0400_live.py` 5/5 实机场景验收（`chamfer` `single` 97.14 mm vs `chain` 155.71 mm、G2 R10 圆角 `max_curvature_gap_inv_mm=0.0`/`verdict="pass"`、凹边圆角 `round_kind="concave"` `+429.20 mm³`、单边圆角超限 `round_failure.edge_diagnostics`、两实体零件按 `body_id` 仅抽体 B 精确 `78752.0 mm³`、相交三次 B 样条 YZ 草图 `ExtrudeOp.region` 精确切除 `300.0 mm³`、装配偏移板 `coordinate_space="assembly"` 零命中输出 `suggested_reference` 与 `assembly_origin_mm`），所有建模场景均保存重载通过。Creo 9/12、原护卫舰/Arm7 完整工程与 WorkBuddy 黑盒未验。详见[验收与发布记录](../validation/RELEASE-0.42.0.md)。

## 附件

- `MCP_CREO_MechDog-0.42.0-source.zip`
- `MCP_CREO_MechDog-0.42.0-source.zip.sha256`
- `MCP_CREO_MechDog-0.42.0-seed-library.zip`
- `MCP_CREO_MechDog-0.42.0-seed-library.zip.sha256`

种子包 SHA256 为 `23ba2e8f0f7599360a9f4ff3cc13c4ab8378335a905de9966f3171a1b975b4f3`。源码包摘要记录在同名 sidecar 中，两份 sidecar 分别记录对应 ZIP 的实际 SHA256。[GitHub Release](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.42.0)
