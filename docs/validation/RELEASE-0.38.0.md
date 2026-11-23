# 发布记录 v0.38.0

日期为 2026-11-23，版本类型为 MINOR，公开工具仍 111。

上一版本：0.37.1（`v0.37.1`，提交 `87cade1e24c91140d97789516b2ff92b49518e86`）。

## 验收范围

本版交付 [BUG-169](../work-items/BUG-169.md) 与 [FEAT-075](../work-items/FEAT-075.md)，归档 0.35.8 外部反馈原件 [linear-pattern-leader-and-through-all-scope.md](feedback-0.35.8-2026-11-23/originals/linear-pattern-leader-and-through-all-scope.md)（SHA256 `cd93e2c16b4095e5af0d85b76fba5b0099df2613332142c067879d57178b668e`），并在 [BUG-150](../work-items/BUG-150.md) 补录外部 `frigate_v4` 验证结果：

- `native/generic.cpp`：`extrude_or_revolve()` 与 `execute_operation_body()` 为已 `remember(op, f)` 的特征操作回填 `feature_id`。
- `native/linear_pattern.cpp`：在 `ProPatternCreate` 前通过 `ProFeatureTypeGet` 与 `ProFeatureGeomitemVisit(..., PRO_SURFACE)`（含组头 `ProFeatureGroupGet` + `ProGroupFeaturesCollect` 汇总）校验 leader，拒绝草图/曲线/基准及零实体面 leader（`LINEAR_PATTERN_NON_SOLID_LEADER`）与别名/原生类型冲突（`LINEAR_PATTERN_LEADER_ALIAS_MISMATCH`）；成功与失败回执均携带 `leader_kind`、`leader_feature_type`、`leader_surface_count`、`leader_surface_query_code`。
- `src/creo_mechdog/schema.py` 与 `generic_bridge.py`：在提交准入阶段拒绝指向已知草图/基准别名的 `linear_pattern.leader`（建作业前返回 `LINEAR_PATTERN_NON_SOLID_LEADER`）。
- `src/creo_mechdog/operation_results.py` 与 `src/creo_mechdog/job_projection.py`：将 `feature_id` 及 `linear_pattern` leader/member 诊断键纳入 compact 保护集合与投影白名单，确保 `creo_get_job(detail="compact")` 同步可见。
- `src/creo_mechdog/f08_contract.py`、`src/creo_mechdog/capabilities.py`、`server.py`：开放 `extrude mode="cut"` 单实体 `scope` 与 `depth_type="through_all"` 组合（含 `positive`/`negative`/`symmetric` 与初始体 `-5778`），维持单目标、`new_body` 互斥、`scope_applied` 回读与 `non_target_bodies_unchanged` 校验。
- `src/creo_mechdog/profile_diagnostics.py` 与 `docs/REFERENCE_SYNTAX.md`：仅命中 `intersecting`/`tangent` 时不再建议改 `closure_tolerance_mm`；补齐拉伸切除交集语义与多闭合环边界说明。

## 环境与实机证据

- Windows x64 / Python 3.12.10 / Creo 10.0.0.0（`release_numeric=42`，安装目录 `D:\Program Files\PTC\Creo 10.0.0.0`）与匹配 Toolkit SDK；`bridge.py build` 编译 `build/creo_worker.exe` 成功（SHA256 `ec443506e5e91d93b99a08973a9bf37b4ab50130abcea6f88ec53a5613e9db9e`）。
- `tools/test_feedback0358_pattern_scope.py --live --confirm-session-usable`（报告 `build/feedback0358_pattern_scope.json`，SHA256 `ad8715c31aa8e2590475f99ed5c40e5587e580a45564dc002497e2b842a3f447`）：**8/8 通过**：
  - `B169_1_feature_id_and_cut_pattern`（模型 `34c1823a090040bf85130eef8f737744`，切除 `ec5ff5f1f6034ef5b2da25ca0aa7f22b`，阵列 `9095d57bea6e4461aa9b34f1a63ede4e`）：全量与 compact 均返回 `feature_id=87`（区别于草图 `78`）、`leader_id=87`、`leader_kind="cut"`、`leader_surface_count=12`、`member_count=3`，体积 `48000.0 → 45000.0 mm³`（解析 `45000.0`），`saved_file_reloaded_and_verified=true`。
  - `B169_2_sketch_alias_rejected_pre_submit`：`leader="slot_sk"` 建作业前拒绝 `LINEAR_PATTERN_NON_SOLID_LEADER`，revision `3 → 3`。
  - `B169_3_sketch_numeric_id_rejected_native`（作业 `95cfd7026eda43cfb3120d2e99244f8c`）：裸数字草图 ID `78` 原生失败 `LINEAR_PATTERN_NON_SOLID_LEADER`（`leader_kind="sketch_or_curve"`、`leader_surface_count=0`），回滚 revision `3 → 3`、体积保持 `45000.0 mm³`。
  - `B169_4_protrusion_and_feature_group_pattern`（模型 `b4c7ce60c0bc4d33855e6f503aec8bd1`）：凸台阵列 `bea46953f2aa42a3b54b147bd559d858`（`leader_kind="protrusion"`、`leader_surface_count=6`、`member_count=3`，`50400.0` vs 解析 `50400.0`）与特征组阵列 `34dea71d37f74827b7b3e30f23a6277b`（`leader_kind="feature_group"`、`leader_surface_count=12`、`member_count=2`，`49680.0` vs 解析 `49680.0`）均成功并保存重载通过。
  - `F075_1_two_body_positive_through_all_scope`（模型 `dbd649f8c9324f459b148044b7676a0f`，作业 `53d698c3f6d44abfa47225e646e6ff29`）：双体 `through_all` + `positive` + `scope=[52]`，`applied_body_ids=[52]`、`non_target_bodies_unchanged=true`、Body 92 面数/包络不变、体积 `144000.0 → 137716.8146928204 mm³`（解析 `137716.81469282042`），保存重载通过。
  - `F075_2_three_body_symmetric_through_all_scope`（模型 `18eb4265ff51478895adfce37d6dac11`，作业 `1413361eca854c1d8eff4a2a7ea7549a`）：三体 `through_all` + `symmetric` + `scope=[52]`，`applied_body_ids=[52]`、`non_target_bodies_unchanged=true`、非目标体 92/131 均未变、体积 `216000.0 → 209716.8146928204 mm³`（解析 `209716.81469282042`），保存重载通过。
  - `F075_3_initial_body_minus5778_symmetric_through_all`（模型 `2d6ed5675175466a943296241f5cb16a`，作业 `75ce428de3e84725b74bed5e9391abcf`）：放样基准初始体 `-5778` + `symmetric` + `through_all` + `scope=[-5778]`，`applied_body_ids=[-5778]`、`non_target_bodies_unchanged=true`、体积 `65716.8146928204 mm³`（解析 `65716.81469282041`），保存重载通过。
  - `F075_4_unknown_body_through_all_rollback`（作业 `e458ebb3ae9043b5bf52865d68fbffb8`）：`scope=[999999]` 返回 `F08_SCOPE_RESOLVE_FAILED` 并回滚，revision `2 → 2`、体积保持 `137716.8146928204 mm³`。
- `tools/test_linear_pattern.py --live --confirm-session-usable`（报告 `build/linear_pattern.json`，SHA256 `e47e4a1d760638df32c35c9149e7cb0b6283919eb60a42f56d32dca1aebbfdd7`）：**3/3 通过**（`A_translation`、`B_flip_reverses`、`C_unbound_direction_refused`）。

## 种子包

`python tools/package_seeds.py --output build/release-0.38.0/MCP_CREO_MechDog-0.38.0-seed-library.zip --allow-record-mismatch` 首次构建得到摘要后回填 `docs/seed_package.json`；再用 `python tools/package_seeds.py --output build/release-0.38.0/confirm/MCP_CREO_MechDog-0.38.0-seed-library.zip` 重建确认，两次摘要一致：`f01e832b9a8b7ea3eef7f845f53af3502c1b3656e1896a90ab02f76bb6a36223`（24 个文件、9 个种子）。

## 单测证据

发布候选在 0.38.0 工作树上运行 `tools/test_unit.py`，全量 unittest 通过，0 失败、0 错误。下列数字取自本轮 `build/unit_test_report.json`，该报告不随源码包分发。

本轮 `run_id=37e4484ce94e4bf391093a84901cb3d2`，执行 4,431 项，0 失败、0 错误、6 跳过，耗时 327.33 s，报告 `version=0.38.0`、`status=completed`、`success=true`。受测提交 `6d3828206eac8b10cd4cb8201dc259be3c2a6d6d`（分支 `codex/bug169-feat075-pattern-scope`，`dirty=false`），源码指纹 `6faa86295b8bea167b4337b32370993924646cdddd27798fc0f0125f2ce442d0`，统计 670 个受 Git 跟踪的 `.py` 与原生头/源文件。后续回填本段文档不改动任何受跟踪 `.py` 或原生文件，源码指纹保持不变。跳过项为 Windows 符号链接权限、MSVC 独立辅助程序环境与未随仓库保存的历史作业证据，均不涉及本版改动。

语言与格式检查以 `tools/dev_check.py --skip-unit --work-item BUG-169` 执行：`success=true`，lint 0、unformatted 0（584 个 Python、69 个 C++），离线验收 3/3 通过（`test_update_check`、`test_model_reconciliation`、`test_mcp`）。

## 未测范围

- 原案 B025（作业 `a8ca9a72…` → `66041948…` → `8e82f379…`）未附原始 `request.json`/`model.json`，同标签首次指向草图的外部现象未复现。
- Creo 9/12 实机未复验；本机无 Creo 9 SDK。
- WorkBuddy 外部黑盒验收未执行。

## 附件

- `MCP_CREO_MechDog-0.38.0-source.zip`
- `MCP_CREO_MechDog-0.38.0-source.zip.sha256`
- `MCP_CREO_MechDog-0.38.0-seed-library.zip`
- `MCP_CREO_MechDog-0.38.0-seed-library.zip.sha256`

种子包 SHA256 为 `f01e832b9a8b7ea3eef7f845f53af3502c1b3656e1896a90ab02f76bb6a36223`。源码包摘要记录在同名 sidecar 中，两份 sidecar 分别记录对应 ZIP 的实际 SHA256。

## 逐 ID 状态核对

| ID | 交付版本 | 实际 Release | 技术状态 | 卡首页 | 主台账 | 差异说明 |
| --- | --- | --- | --- | --- | --- | --- |
| [BUG-169](../work-items/BUG-169.md) | 0.38.0 | v0.38.0 | 已有修复但待验收 | 已有修复但待验收（0.38.0 交付并完成本机 Creo 10 4/4 + 回归 3/3 验收） | 已有修复但待验收 | 剩原案 B025 原始快照、Creo 9/12 与 WorkBuddy 黑盒 |
| [FEAT-075](../work-items/FEAT-075.md) | 0.38.0 | v0.38.0 | 已有修复但待验收 | 已有修复但待验收（0.38.0 交付并完成本机 Creo 10 4/4 验收，含 `-5778` 初始体） | 已有修复但待验收 | 剩 Creo 9/12 与 WorkBuddy 黑盒 |

## 远端核对

发布后执行，当前未验证。[GitHub Release](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.38.0)
