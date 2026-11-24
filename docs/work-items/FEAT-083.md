# FEAT-083：`ExtrudeOp.region` 曲线感知 `interior_point_yz_mm` 内点选区

- 类型：功能
- 优先级：P3

分类：**已有修复但待验收**（0.43.0 已交付并完成本机 Creo 10.0.0.0 实机验收；Creo 9/12 与 WorkBuddy 黑盒未验）

- 目标版本：0.43.0（MINOR）

来源：[0.40.0 原始反馈（B 样条除料「零除料」与无法渲染剖面正视图）](../validation/feedback-0.40.0-2026-11-24-bspline-view/originals/bspline-cut-zero-removal-and-section-view.md) §5。

## 修复内容

1. **`SketchRegionSelector` 扩展**：`src/creo_mechdog/schema.py` 将 `signature_yz_mm` 改为可选，新增 `interior_point_yz_mm: [y, z]`（支持单独使用或与 `signature_yz_mm` 组合消歧，至少提供其一；严格拒绝布尔与非有限数）。
2. **曲线采样内点判定**：`src/creo_mechdog/sketch_regions.py` 对直线、圆弧（含 `dir`/`sweep_deg`）、多段线、样条与 B 样条（复用 `eval_bspline`）在全局 YZ 平面采样构建闭合环多边形，通过射线法筛选包含 `interior_point_yz_mm` 的最小面积闭合环，可无歧义区分共端点圆弧/样条子区域，零命中或等面积歧义时明确拒绝。

## 验收证据（2026-11-24）

- 实机 `tools/test_feedback0430_live.py`（报告 `build/feedback0430_live_report.json`，Creo 10.0.0.0 / release 42）：
  - `S3_region_interior_point_live`：含三次 B 样条分割的多区域 YZ 草图仅传 `interior_point_yz_mm=[15.0, 15.0]`（无 `signature_yz_mm`）切除上子区域（作业 `83001e94e636476eafc15d87133ca6fb`），体积 `3000.0 → 2199.997625 mm³`（去料 `800.002375 mm³` vs 解析 `800.0 mm³`），`saved_file_reloaded_and_verified=true`。
- 单元测试：`tests/unit/test_feedback0400_bspline_view.py::Feat083RegionInteriorPointTests` 全部通过（含共端点双圆弧月牙选区与 B 样条子区域）。
- 未验范围：Creo 9/12、原 Arm7 完整工程与 WorkBuddy 黑盒。
