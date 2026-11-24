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

发布候选在 0.43.0 工作树上运行 `tools/test_unit.py`，全量 unittest 通过，0 失败、0 错误。下列数字取自本轮 `build/unit_test_report.json`，该报告不随源码包分发。

本轮 `run_id=a8242666aa154b65bf874d7eedf5c500`，执行 4,491 项，0 失败、0 错误、6 跳过，耗时 344.91 s，报告 `version=0.43.0`、`status=completed`、`success=true`。受测提交 `2a1ae671bf94818635cd0203f84853a118196959`（分支 `codex/feedback-0400-bspline-view-0430`，`dirty=false`），源码指纹 `c3ae6bcccd897ecfa2c6a4f5e175057b6a318cd3bf4995b459fe69e4ef7cb14b`，统计 681 个受 Git 跟踪的 `.py` 与原生头/源文件。后续回填本段文档不改动任何受跟踪 `.py` 或原生文件，源码指纹保持不变。跳过项为 Windows 符号链接权限、MSVC 独立辅助程序环境与未随仓库保存的历史作业证据，均不涉及本版改动。

语言与格式检查以 `tools/dev_check.py --work-item BUG-183` 执行：`success=true`，lint 0、unformatted 0（595 个 Python、69 个 C++），离线验收 3/3 通过（`test_update_check`、`test_model_reconciliation`、`test_mcp`）。

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

已发布并核对（2026-11-24）。Release id `456439582`（非 draft、非 prerelease），创建于 `2026-11-24T07:39:58Z`、发布于 `2026-11-24T07:41:46Z`；附注标签 `v0.43.0`（对象 `6df0d95e8a0585d7bc0388fd4686ef5eda6d4439`）指向 `fc64e3bcb7956d68f0b167f0e0f22c5f987f5831`（本版合入提交），远端 `refs/heads/main` 在核对时指向同一提交。`python -X utf8 tools/check_release_assets.py --tag v0.43.0` 返回 `v0.43.0: four assets downloaded and verified; both sidecars match; release body self-proof verified`（exit 0），四个附件与两份 sidecar 摘要及远端 API digest 一致：源码包 `d4f0e993a87c596550cef22cfd7ec5783c5f2432107455407282c9a39cc1e2f4`（12,117,567 字节，sidecar `bb7eafb1058ca9f40fde003515a67d9e4afa35396dcb43850b2a224c816cb70b`），种子包 `b8b8408f614088ce1c3c67a12ea55fefe5dfe4fe19c2297e2024e2e3f0ebcc2f`（493,442 字节，sidecar `07bab14b60c8d701473692e79c6ff92b1eba1044643f2f0dae5a629b44efd8bc`）。附件字节、摘要与环境侧发布通道见 [GitHub Release](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.43.0) 和[发布后核对](../development/RELEASE-POSTCHECK-2026-11-07.md)。
