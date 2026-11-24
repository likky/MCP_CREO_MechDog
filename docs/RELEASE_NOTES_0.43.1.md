# MCP_CREO_MechDog 0.43.1 版本说明

版本类型为 PATCH，公开工具数 111。本版阶段交付 [BUG-017](work-items/BUG-017.md)：补齐开放剖面加强筋（`creo_rib` / `generic_rib`）逐阶段原生诊断与未激活再生失败回执，完成本机 Creo 10.0.0.0 正反对照与 Creo 9/10 `ProRib.h` 逐行核对，并修复历史实机脚本对当前 `creo_get_job(detail="full")` 结构的兼容。Creo 9.0.0.0 原案运行时实测仍保留待验。

上一版本：0.43.0（`v0.43.0`，提交 `fc64e3bcb7956d68f0b167f0e0f22c5f987f5831`）。

- **加强筋逐阶段原生诊断与未激活再生失败回执（`rib_diagnostics`、`RIB_DIAG`、`feature_errors`）**。`native/surfaces.cpp` 的 `generic_rib` 现分别记录 `ProFeatureWithoptionsCreate`、`ProFeatureElemtreeExtract`、`ProElementIntegerSet(PRO_E_STD_MATRLSIDE)`、`ProFeatureWithoptionsRedefine`、`ProFeatureStatusGet` 与 `ProFeatureGeomitemVisit` 的原始返回码、`ProErrorlist`、特征 ID、特征状态与几何项计数；在“API 均返回 0 但 `status != PRO_FEAT_ACTIVE`”路径填充 `last_feature_error_report`（`failed_stage="rib_regeneration"`、`api="ProFeatureStatusGet"`、`code=<status>`）并在错误文本附原始字段；`native/generic.cpp` 在 `catch (const std::exception &)` 同步发布顶层 `report["feature_errors"]`；`operation_results.py` 与 `compact_sections.py` 透传 `rib_diagnostics`。[BUG-017](work-items/BUG-017.md)
- **Creo 9/10 `ProRib.h` 核对与实机验收脚本兼容**。直接逐行比对用户提供的 Creo 9.0.0.0 与 Creo 10.0.0.0 参考头文件：`ProRib.h`、`ProBodyOpts.h`、`ProStdSection.h` 及 `ProElemId.h`/`ProFeatType.h`/`ProFeatForm.h`/`ProFeature.h` 中加强筋相关符号均完全一致，Creo 9 `ProRib.h` Note-6 同样要求先完整定义 `PRO_E_STD_SECTION` 再设置 `PRO_E_STD_MATRLSIDE`（参考目录已通过 `.gitattributes` `export-ignore` 排除出源码包）。修复 `tools/test_direct_loft.py` 中 `Probe.job` 对当前 `creo_get_job(detail="full")` 与 `inspection_summary` 的兼容，使 `tools/test_p1_modeling.py` 可端到端运行。[BUG-017](work-items/BUG-017.md)

本机环境为 Windows x64 / Python 3.12.10 / Creo 10.0.0.0（`release_numeric=42`）。本版通过 `bridge.py build` 编译验证，完成 `tools/test_p1_modeling.py --cases ribs,negative_geometry,unavailable_and_nonintersecting` 17/17 实机作业（4 组 L 形底座正例均为原生 `PRO_FEAT_RIB`、`feature_status=0`、`55250.0 mm³`、revision `1→2`、`saved_file_reloaded_and_verified=true`；闭合剖面与不相交剖面均准确归因并回滚至 `24000.0 mm³`），以及单变量外表面/材料侧对照与 Creo 9 历史夹具复现。Creo 9.0.0.0 运行时实测、Creo 9 界面 Profile Rib 对照与 WorkBuddy 黑盒未验。详见[验收与发布记录](validation/RELEASE-0.43.1.md)。

## 附件

- `MCP_CREO_MechDog-0.43.1-source.zip`
- `MCP_CREO_MechDog-0.43.1-source.zip.sha256`
- `MCP_CREO_MechDog-0.43.1-seed-library.zip`
- `MCP_CREO_MechDog-0.43.1-seed-library.zip.sha256`

种子包 SHA256 为 `ced6a484eea05be3472f3ddb1d7b59cf83d615c4908bff63086e57948c2fda41`。源码包摘要记录在同名 sidecar 中，两份 sidecar 分别记录对应 ZIP 的实际 SHA256。[GitHub Release](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.43.1)
