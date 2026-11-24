# FEAT-081：G2 曲率连续圆角几何级曲率验证（`g2_verification`）

- 类型：功能
- 优先级：P2

分类：**已有修复但待验收**（0.42.0 已交付并完成本机 Creo 10.0.0.0 实机验收；Creo 9/12 与 WorkBuddy 黑盒未验）

- 目标版本：0.42.0（MINOR）

来源：[0.40.0 原始反馈（Arm7 区域切除仍零命中、G2 仍无几何级验证、全量 60 条配合仍在 arm2_1 零命中）](../validation/feedback-0.40.0-2026-11-24/originals/arm7-region-cut-g2-verification-and-mated-assembly.md) §5。

## 修复内容

1. `native/generic.cpp` 新增 `measure_g2_round_verification`：当 `RoundOp` 请求 `curvature_continuous=true` 时，读回特征树 `PRO_E_RNDCH_CONIC_TYPE` 与 `PRO_E_RNDCH_CONIC_VALUE`，并沿新建圆角面与相邻支撑面的共享相切边界边，通过 `ProEdgeXyzdataEval`、`ProSurfaceParamEval` 与 `ProSurfaceXyzdataEval` 计算第一、第二基本形式下的跨边界法向夹角（`max_tangent_angle_deg`）与法曲率差（`max_curvature_gap_inv_mm`，单位 $\text{mm}^{-1}$），输出 `g2_verification`（`verdict: "pass" | "fail" | "unsupported"`）。
2. 将 `g2_verification` 纳入 `src/creo_mechdog/compact_sections.py` 白名单。

## 验收证据（2026-11-24）

- 实机 `tools/test_feedback0400_live.py`（报告 `build/feedback0400_live_report.json`，Creo 10.0.0.0 / release 42）：
  - `S2` G2 R10 圆角（作业 `41527cfd9703406b816798e7bb5caf6e`）：`native_conic_type=3`、`native_conic_value=0.5`、`sampled_edges=2`、`sampled_points=6`、`max_tangent_angle_deg=0.0`、`max_curvature_gap_inv_mm=0.0`、`tolerance_inv_mm=0.002`、`verdict="pass"`，保存重载通过。
- 单元测试：`tests/unit/test_feedback0400_fixes.py::Bug179ChamferTests` 全部通过。
- 未验范围：Creo 9/12、非解析曲面 G2 圆角与 WorkBuddy 黑盒。
