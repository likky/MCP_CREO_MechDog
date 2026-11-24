# 发布记录 v0.43.0

日期为 2026-11-24，版本类型为 MINOR，公开工具仍 111。

上一版本：0.42.0（`v0.42.0`，提交 `be2d634629f21247de1548992fdcc27fc9ea9db4`）。

## 验收范围

本版交付 [BUG-183](../work-items/BUG-183.md)、[FEAT-082](../work-items/FEAT-082.md)、[BUG-184](../work-items/BUG-184.md)、[FEAT-083](../work-items/FEAT-083.md) 与 [BUG-185](../work-items/BUG-185.md)，逐字节归档 0.40.0 外部反馈原件至 [SOURCE_MANIFEST.json](feedback-0.40.0-2026-11-24-bspline-view/SOURCE_MANIFEST.json)（[bspline-cut-zero-removal-and-section-view.md](feedback-0.40.0-2026-11-24-bspline-view/originals/bspline-cut-zero-removal-and-section-view.md) SHA256 `ca5008894c14c4e7311cc8a855b1d0f4065fc200bb6c7dc002a3ee2da7ac862b`；注：原报告 §4 G2 圆角曲率验证已由 0.42.0 [FEAT-081](../work-items/FEAT-081.md) 交付）：

- `native/generic.cpp`、`src/creo_mechdog/cut_geometry_context.py`、`src/creo_mechdog/operation_results.py`、`src/creo_mechdog/compact_sections.py`（[BUG-183](../work-items/BUG-183.md)）：原生 `section_profile_summary` 用 `ProSectionEntityEval` 计算 `solved_section_area_mm2` 并随草图 `native_section`、零去料 `cut_geometry_context` 与成功拉伸切除回执发布；闭合 B 样条草图附 advisory `b_spline_cut_risk`；`cut_volume_check` 扩展支持 `blind`/`symmetric` 并回落至 `solved_section_area_mm2`。
- `src/creo_mechdog/schema.py`、`server.py`、`native/generic.cpp`（[FEAT-082](../work-items/FEAT-082.md)）：`JpegOptions` 支持全正交视图 `right`/`left`/`back`/`bottom`（`right` 沿 -X 正视 YZ 平面）与自定义 3×3 右手正交 `view_matrix`。
- `native/sketch_coordinates.cpp`、`src/creo_mechdog/geometry_deviation.py`、`src/creo_mechdog/operation_results.py`、`server.py`（[BUG-184](../work-items/BUG-184.md)）：草图 `geometry_deviation.sample` 补最大位移点 `point`/`requested_mm`/`actual_mm`/`delta_mm`；`compact` 投影超阈保留前 5 条 `displaced_sample`；明确 `geometry_tolerance_mm` 在 `autodim` 下同样硬拒绝。
- `src/creo_mechdog/schema.py`、`src/creo_mechdog/sketch_regions.py`（[FEAT-083](../work-items/FEAT-083.md)）：`ExtrudeOp.region` 新增曲线感知 `interior_point_yz_mm` 内点选区（采样直线、圆弧与 B 样条，无需顶点对签名即可区分共端点曲线子区域）。
- `server.py`、`bridge.py`（[BUG-185](../work-items/BUG-185.md)）：`creo_get_job` 参数 schema 标明 `section`/`cursor` 要求 `detail="full"`、`sections` 要求 `detail="compact"` 并完善报错指引。

## 环境与实机证据

- Windows x64 / Python 3.12.10 / Creo 10.0.0.0（`release_numeric=42`，安装目录 `D:\Program Files\PTC\Creo 10.0.0.0`）与匹配 Toolkit SDK；`bridge.py build` 编译 `build/creo_worker.exe` 成功。
- `tools/test_feedback0430_live.py`（报告 `build/feedback0430_live_report.json`）：**3/3 通过**：
  - `S1_bspline_solved_area_and_cut_check`：含三次 B 样条的 10×10 YZ 闭合草图 `solved_section_area_mm2=100.0`、附 `b_spline_cut_risk`；3 mm 对称切除（作业 `0d0b1e8cbac34f3491a423f409948235`）`cut_volume_check` 返回 `area_source="native_solved_section"`、`expected_prism_volume_mm3=300.0`、`actual_removed_mm3=299.999708`、`b_spline_cut_risk=true`，`saved_file_reloaded_and_verified=true`；空切失败（作业 `a49100a33f724f40aacb258c14dc583a`）`cut_geometry_context.solved_section_area_mm2=100.0`。
  - `S2_jpeg_orthographic_and_matrix`：3 mm 厚 60×40 mm YZ 薄板渲染 `right`（作业 `857a5d6fd3094303a166b10eee321236`，20,877 字节，视觉确认呈完整 60×40 轮廓）、`left`（`e8b942d5f6574f27a8f4b76c38838dff`）、`front`（`ed6dad6e9ce04c41a29b0f5d00ac3d0a`）与 45° 自定义 `view_matrix`（`24e16910e62e4f658cd0ee1ea812f65f`），全部 `view_matrix_matches=true`。
  - `S3_region_interior_point_live`：含三次 B 样条分割的多区域 YZ 草图仅传 `interior_point_yz_mm=[15.0, 15.0]` 切除上子区域（作业 `83001e94e636476eafc15d87133ca6fb`），体积 `3000.0 → 2199.997625 mm³`（去料 `800.002375 mm³` vs 解析 `800.0 mm³`），`saved_file_reloaded_and_verified=true`。

## 种子包

`python tools/package_seeds.py --output build/release-0.43.0/MCP_CREO_MechDog-0.43.0-seed-library.zip --allow-record-mismatch` 首次构建得到摘要后回填 `docs/seed_package.json`；再用 `python tools/package_seeds.py --output build/release-0.43.0/confirm/MCP_CREO_MechDog-0.43.0-seed-library.zip` 重建确认，两次摘要一致：`b8b8408f614088ce1c3c67a12ea55fefe5dfe4fe19c2297e2024e2e3f0ebcc2f`（24 个文件、9 个种子）。

## 单测证据

将在干净的 0.43.0 发布候选提交上运行 `tools/dev_check.py --work-item BUG-183` 并回填本段。

## 未测范围

- Creo 9/12、原 Arm7 完整工程与 `a7_s5` 吸附实机复现、装配体多视角 JPEG 与 WorkBuddy 外部黑盒验收未执行。

## 附件

- `MCP_CREO_MechDog-0.43.0-source.zip`
- `MCP_CREO_MechDog-0.43.0-source.zip.sha256`
- `MCP_CREO_MechDog-0.43.0-seed-library.zip`
- `MCP_CREO_MechDog-0.43.0-seed-library.zip.sha256`

种子包 SHA256 为 `b8b8408f614088ce1c3c67a12ea55fefe5dfe4fe19c2297e2024e2e3f0ebcc2f`。源码包摘要记录在同名 sidecar 中，两份 sidecar 分别记录对应 ZIP 的实际 SHA256。

## 逐 ID 状态核对

| ID | 交付版本 | 实际 Release | 技术状态 | 卡首页 | 主台账 | 差异说明 |
| --- | --- | --- | --- | --- | --- | --- |
| [BUG-183](../work-items/BUG-183.md) | 0.43.0 | v0.43.0 | 已有修复但待验收 | 已有修复但待验收（0.43.0 已交付并完成本机 Creo 10.0.0.0 实机验收；Creo 9/12 与 WorkBuddy 黑盒未验） | 已有修复但待验收 | 剩 Creo 9/12、原 Arm7 工程、WorkBuddy 黑盒 |
| [FEAT-082](../work-items/FEAT-082.md) | 0.43.0 | v0.43.0 | 已有修复但待验收 | 已有修复但待验收（0.43.0 已交付并完成本机 Creo 10.0.0.0 实机验收；Creo 9/12 与 WorkBuddy 黑盒未验） | 已有修复但待验收 | 剩 Creo 9/12、装配多视角、WorkBuddy 黑盒 |
| [BUG-184](../work-items/BUG-184.md) | 0.43.0 | v0.43.0 | 已有修复但待验收 | 已有修复但待验收（0.43.0 已交付并通过单元测试与原生构建；Creo 9/12 与 WorkBuddy 黑盒未验） | 已有修复但待验收 | 剩原 Arm7 `a7_s5` 实机复现、Creo 9/12、WorkBuddy 黑盒 |
| [FEAT-083](../work-items/FEAT-083.md) | 0.43.0 | v0.43.0 | 已有修复但待验收 | 已有修复但待验收（0.43.0 已交付并完成本机 Creo 10.0.0.0 实机验收；Creo 9/12 与 WorkBuddy 黑盒未验） | 已有修复但待验收 | 剩 Creo 9/12、原 Arm7 工程、WorkBuddy 黑盒 |
| [BUG-185](../work-items/BUG-185.md) | 0.43.0 | v0.43.0 | 已有修复但待验收 | 已有修复但待验收（0.43.0 已交付并通过单元测试与离线 stdio 契约检查；WorkBuddy 黑盒未验） | 已有修复但待验收 | 剩 WorkBuddy 黑盒 |

## 远端核对

发布后执行 `python -X utf8 tools/check_release_assets.py --tag v0.43.0` 核对并回填本段。
