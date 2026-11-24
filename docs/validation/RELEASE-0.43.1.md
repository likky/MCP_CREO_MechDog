# 发布记录 v0.43.1

日期为 2026-11-24，版本类型为 PATCH，公开工具仍 111。

上一版本：0.43.0（`v0.43.0`，提交 `fc64e3bcb7956d68f0b167f0e0f22c5f987f5831`）。

## 验收范围

本版阶段交付 [BUG-017](../work-items/BUG-017.md)：

- `native/surfaces.cpp`、`native/generic.cpp`、`src/creo_mechdog/operation_results.py`、`src/creo_mechdog/compact_sections.py`、`tests/unit/test_bug017_rib_diagnostics.py`（[BUG-017](../work-items/BUG-017.md)）：`generic_rib` 逐阶段记录 `create_code`/`create_element_errors`/`feature_id`/`extract_code`/`matrlside_set_code`/`redefine_code`/`redefine_element_errors`/`status_code`/`feature_status`/`geometry_visit_code`/`geometry_item_count`（`rib_diagnostics` 回执与 `RIB_DIAG` 日志），并在“API 返回 0 但 `status != PRO_FEAT_ACTIVE`”路径写入 `last_feature_error_report`（`failed_stage="rib_regeneration"`）；`native/generic.cpp` 在 `catch (const std::exception &)` 同步发布顶层 `report["feature_errors"]`；`operation_results.py` 与 `compact_sections.py` 透传 `rib_diagnostics`。
- `tools/test_direct_loft.py`、`docs/work-items/BUG-017.md`、`.gitattributes`、`.gitignore`（[BUG-017](../work-items/BUG-017.md)）：修复 `Probe.job` 对当前 `creo_get_job(detail="full")` 与 `inspection_summary` 的回读兼容；登记用户提供的 Creo 9/10 参考头文件（受 `export-ignore` 排除不入公开源码包）并逐行核对 `ProRib.h`/`ProBodyOpts.h`/`ProStdSection.h` 与 `ProElemId.h`/`ProFeatType.h`/`ProFeatForm.h`/`ProFeature.h`（完全一致）。

## 环境与实机证据

- Windows x64 / Python 3.12.10 / Creo 10.0.0.0（`release_numeric=42`，安装目录 `D:\Program Files\PTC\Creo 10.0.0.0`）与匹配 Toolkit SDK；`bridge.py build` 编译 `build/creo_worker.exe` 成功。
- `tools/test_p1_modeling.py --cases ribs,negative_geometry,unavailable_and_nonintersecting --output build/bug017_rib.json`：**17/17 作业通过（`success=true`）**：
  - 4 组正例（`rib_False_symmetric` `1e670783a13b4d60b09f9aa673ec98a7`、`rib_True_symmetric` `5475122e25d546fe8a897d02fd728519`、`rib_False_positive` `fe78a3826c4f4c1db8d6518ee4551b6e`、`rib_False_negative` `e1c9bb80e3ed4c11bc39fa4dde6d2b8b`）：原生 `PRO_FEAT_RIB`（type 920、`feature_status=0`、`geometry_item_count=38`），体积 `54000.0 → 55250.0 mm³`（与独立解析增量 `+1250.0 mm³` 一致），revision `1→2`，`saved_file_reloaded_and_verified=true`。
  - 负例与回滚：`closed_rib`（`b5b8799f1fb34bf19a60d7593d6dfa75`）在 `precheck_closed_profile` 拒绝并回滚；`nonintersecting_rib`（`ca3bf9989178457d888a74bf3776b99e`）回执精确输出 `feature_id=86`、`feature_status=6`、`geometry_item_count=0`、`create_code=0`、`redefine_code=0`、`failed_stage="rib_regeneration"` 及顶层/操作级 `feature_errors`，回滚至 `24000.0 mm³`、revision 不变、无残留特征。
- 单变量对照与 Creo 9 历史夹具复现（`build/bug017_experiments.json`）：导出成功特征 XML 树 `feature_139.xml`（job `245ccb2f0ebc43e8b84235119658ace8`）；验证外表面 `YZ offset=0` 上 `symmetric`/`positive` 失败而向内 `negative` 成功（`55250.0 mm³`）；重构 0.3.2/0.3.0 夹具在 Creo 10 上复现相同的 `ProFeatureWithoptionsCreate=0`、`created_feature_id=84`、`CompleteFeature=0`、`status=6` 签名并全部回滚。

## 种子包

`python tools/package_seeds.py --output build/release-0.43.1/MCP_CREO_MechDog-0.43.1-seed-library.zip --allow-record-mismatch` 首次构建得到摘要后回填 `docs/seed_package.json`；再用 `python tools/package_seeds.py --output build/release-0.43.1/confirm/MCP_CREO_MechDog-0.43.1-seed-library.zip` 重建确认，两次摘要一致：`ced6a484eea05be3472f3ddb1d7b59cf83d615c4908bff63086e57948c2fda41`（24 个文件、9 个种子）。

## 单测证据

发布候选在 0.43.1 工作树上运行 `tools/test_unit.py`，全量 unittest 通过，0 失败、0 错误。下列数字取自本轮 `build/unit_test_report.json`，该报告不随源码包分发。

本轮 `run_id=99162369b7b94bc1ac49fb457c188309`，执行 4,495 项，0 失败、0 错误、6 跳过，耗时 351.72 s，报告 `version=0.43.1`、`status=completed`、`success=true`。受测提交 `37411b7c63446bb0631573e31d5689027496c3e1`（分支 `codex/BUG-017-rib-diagnostics`，`dirty=false`），源码指纹 `ef842bb463f09265ba07752b48170d5badee9e25bdf5e6f13c08eb7f831b4c84`，统计 682 个受 Git 跟踪的 `.py` 与原生头/源文件。后续回填本段文档不改动任何受跟踪 `.py` 或原生文件，源码指纹保持不变。跳过项为 Windows 符号链接权限、MSVC 独立辅助程序环境与未随仓库保存的历史作业证据，均不涉及本版改动。

语言与格式检查以 `tools/dev_check.py --work-item BUG-017` 执行：`success=true`，lint 0、unformatted 0（596 个 Python、69 个 C++），离线验收 3/3 通过（`test_update_check`、`test_model_reconciliation`、`test_mcp`）。

## 未测范围

- Creo 9.0.0.0（`release_numeric=41`）运行时实测、Creo 9 界面 Profile Rib 对照、单阶段创建在 Creo 9 的实测，以及 WorkBuddy 外部黑盒验收均未执行；BUG-017 原案保持“仍需修复”。

## 附件

- `MCP_CREO_MechDog-0.43.1-source.zip`
- `MCP_CREO_MechDog-0.43.1-source.zip.sha256`
- `MCP_CREO_MechDog-0.43.1-seed-library.zip`
- `MCP_CREO_MechDog-0.43.1-seed-library.zip.sha256`

种子包 SHA256 为 `ced6a484eea05be3472f3ddb1d7b59cf83d615c4908bff63086e57948c2fda41`。源码包摘要记录在同名 sidecar 中，两份 sidecar 分别记录对应 ZIP 的实际 SHA256。

## 逐 ID 状态核对

| ID | 交付版本 | 实际 Release | 技术状态 | 卡首页 | 主台账 | 差异说明 |
| --- | --- | --- | --- | --- | --- | --- |
| [BUG-017](../work-items/BUG-017.md) | 0.43.1 | v0.43.1 | 仍需修复 | 仍需修复（本机阶段交付完成，Creo 9 原案保留待验） | 仍需修复 | 剩 Creo 9.0.0.0 同环境合法用例/界面对照与 WorkBuddy 黑盒 |

## 远端核对

已发布并核对（2026-11-24）。Release id `456550695`（非 draft、非 prerelease），创建于 `2026-11-24T09:37:56Z`、发布于 `2026-11-24T09:38:12Z`；附注标签 `v0.43.1`（对象 `0d9156ab6b2100735f2cd91c41507496ddef11f9`）指向 `f8a07c0513a0abbf7b1e30ca454cb9a1ed4215a0`（本版合入提交），远端 `refs/heads/main` 在核对时指向同一提交。`python -X utf8 tools/check_release_assets.py --tag v0.43.1` 返回 `v0.43.1: four assets downloaded and verified; both sidecars match; release body self-proof verified`（exit 0），四个附件与两份 sidecar 摘要及远端 API digest 一致：源码包 `85f8584d9199681db6d1f5c3998118716c0f7c6ebb072767df2c832d8466104f`（12,133,140 字节，sidecar `18fc27a36d8a9843058173769be66f738625d80795cea4712113a2a451393af4`），种子包 `ced6a484eea05be3472f3ddb1d7b59cf83d615c4908bff63086e57948c2fda41`（493,442 字节，sidecar `833a44b3e1216ac77b5e91abae930104fd69766874145118fd77d2f70fc12c6f`）。附件字节、摘要与环境侧发布通道见 [GitHub Release](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.43.1) 和[发布后核对](../development/RELEASE-POSTCHECK-2026-11-07.md)。
