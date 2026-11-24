# MCP_CREO_MechDog 0.43.0 版本说明

版本类型为 MINOR，公开工具数 111。本版基于 0.40.0 外部反馈（B 样条除料零除料/静默少切与无法渲染 YZ 剖面正视图；注：原报告 §4 G2 圆角曲率验证已由 0.42.0 [FEAT-081](work-items/FEAT-081.md) 交付）交付 [BUG-183](work-items/BUG-183.md)、[FEAT-082](work-items/FEAT-082.md)、[BUG-184](work-items/BUG-184.md)、[FEAT-083](work-items/FEAT-083.md) 与 [BUG-185](work-items/BUG-185.md)，并逐字节归档反馈原件至 [SOURCE_MANIFEST.json](validation/feedback-0.40.0-2026-11-24-bspline-view/SOURCE_MANIFEST.json)。

上一版本：0.42.0（`v0.42.0`，提交 `be2d634629f21247de1548992fdcc27fc9ea9db4`）。

- **B 样条除料求解截面面积（`solved_section_area_mm2`）、除料风险提示与对称切除体积核验**。原生 `section_profile_summary` 使用 `ProSectionEntityEval` 采样已求解 `ProSection` 闭合环并计算 `solved_section_area_mm2`，随草图 `native_section`、零去料 `cut_geometry_context` 与成功拉伸切除回执一并发布；闭合 B 样条草图回执新增 advisory `b_spline_cut_risk`；`cut_volume_check` 扩展支持 `blind` 与 `symmetric` 切除，并在 `profile.material_area_mm2` 为 `null` 时自动回落至 `solved_section_area_mm2`（标注 `area_source="native_solved_section"` 与 `b_spline_cut_risk=true`）。[BUG-183](work-items/BUG-183.md)
- **JPEG 导出全正交视图（`right`/`left`/`back`/`bottom`）与自定义 3×3 `view_matrix`**。`JpegOptions.view` 扩展至 `isometric | front | back | top | bottom | left | right`（`right` 沿 -X 正视 YZ 平面），并新增可选 3×3 右手正交旋转矩阵 `view_matrix`（行向量约定 `v_screen = v_model * M`）支持任意基准面或自定义视角渲染。[FEAT-082](work-items/FEAT-082.md)
- **草图 `geometry_deviation` 逐点位移向量、`compact` 超阈可见性与 `autodim` 容差文档**。`geometry_deviation.sample` 为发生位移的实体补齐最大位移点角色 `point`、目标坐标 `requested_mm`、实测坐标 `actual_mm` 与位移向量 `delta_mm`；`compact` 投影保留 `warning_threshold_mm`/`enforced`/`tolerance_source` 并在 `exceeds_warning=true` 时附前 5 条 `displaced_sample`；`creo_create_sketch` 与 `creo_update_sketch_geometry` 的 `geometry_tolerance_mm` schema 说明明确标注在 `coordinates` 与 `autodim` 均作硬拒绝执行。[BUG-184](work-items/BUG-184.md)
- **`ExtrudeOp.region` 曲线感知 `interior_point_yz_mm` 内点选区**。`SketchRegionSelector` 将 `signature_yz_mm` 改为可选并新增 `interior_point_yz_mm: [y, z]`，采样直线、圆弧与 B 样条构建全局 YZ 闭合环多边形并选取包含该内点的最小面积环，可直接区分共端点圆弧/样条子区域或与签名联用消歧。[FEAT-083](work-items/FEAT-083.md)
- **`creo_get_job` 参数前置条件说明与报错指引**。为 `detail`、`section`、`cursor`、`sections` 补齐输入 schema 描述（明确 `section`/`cursor` 要求 `detail="full"`、`sections` 要求 `detail="compact"`），并完善 `bridge.get_job` 拒绝文案。[BUG-185](work-items/BUG-185.md)

本机环境为 Windows x64 / Python 3.12.10 / Creo 10.0.0.0（`release_numeric=42`）。本版通过 `bridge.py build` 编译验证，完成 `tools/test_feedback0430_live.py` 3/3 实机场景验收（含三次 B 样条 10×10 闭合草图 `solved_section_area_mm2=100.0` 与 3 mm 对称切除 `299.9997 mm³`/`cut_volume_check` 及空切 `cut_geometry_context.solved_section_area_mm2=100.0`、3 mm YZ 薄板 `right`/`left`/`front`/`custom_matrix` 四视角渲染均 `view_matrix_matches=true`、多区域 B 样条 YZ 草图仅用 `interior_point_yz_mm=[15.0,15.0]` 切除 `800.0024 mm³`），建模场景均保存重载通过。Creo 9/12、原 Arm7 完整工程与 WorkBuddy 黑盒未验。详见[验收与发布记录](validation/RELEASE-0.43.0.md)。

## 附件

- `MCP_CREO_MechDog-0.43.0-source.zip`
- `MCP_CREO_MechDog-0.43.0-source.zip.sha256`
- `MCP_CREO_MechDog-0.43.0-seed-library.zip`
- `MCP_CREO_MechDog-0.43.0-seed-library.zip.sha256`

种子包 SHA256 为 `b8b8408f614088ce1c3c67a12ea55fefe5dfe4fe19c2297e2024e2e3f0ebcc2f`。源码包摘要记录在同名 sidecar 中，两份 sidecar 分别记录对应 ZIP 的实际 SHA256。[GitHub Release](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.43.0)
