# MCP_CREO_MechDog 0.35.4 版本说明

版本类型：PATCH。承接 0.35.3。

上一版本：0.35.3（`v0.35.3`，提交 `0fa005dc44ac65c9d118e37e1bf9b58b87474486`）。

## 亮点

- **旋转矩阵准入按实机内核边界收紧**：[BUG-133](work-items/BUG-133.md) 在 Creo 10.0.0.0 / release 42 上补做精度阶梯与扰动扫描。残差 `4.5e-10`、`7.664e-9`、`4.7552320081578614e-8` 的 9/8/7 位小数矩阵可放置并保存重载；`2.241e-7`、`4.890e-7`、`1.1294880000178864e-6` 均被 `ProAsmcompAssemble` 与 `ProAsmcompPositionSet` 以 `-2` 拒绝。因此 `rotation_tolerance` 的缺省值和上限都改为 `1e-7`，Python 与原生同值。
- **六位小数矩阵提前拒绝**：显式容差现在只能收紧，不能把上限抬到 `1e-7` 以上。六位小数矩阵在 `validate_operations`/原生入口即失败，报错给出实际残差并说明内核在 `1e-7` 以上返回 `-2`，不再建议用更大容差“救回”。
- **矩阵仍原样回显**：不自动转置、不正交化、不修改输入；`1e-9` 继续只用于 `strict`/`near_orthonormal` 分类，不参与准入。

## 变更总览

- `src/creo_mechdog/rotation_admission.py`：`ADMISSION_TOLERANCE` 与 `MAX_ADMISSION_TOLERANCE` 改为 `1e-7`，默认文本、上限报错与精度建议同步。
- `native/assembly_pose.h`：`assembly_admission_tolerance()`、`assembly_max_admission_tolerance()`、默认文本与拒绝文案同步为 `1e-7`。
- `src/creo_mechdog/schema.py`、`src/creo_mechdog/capabilities.py`、`server.py`：字段说明与报错同步，不再承诺显式大容差可放行非正交矩阵。
- 回归：`tests/unit/test_rotation_admission.py`、`test_assembly_matrix_poses.py`、`test_assembly_pose.py`、`test_assembly_matrix_rollback.py`、`test_failed_operation_context.py` 与 `tests/native/test_assembly_pose.cpp` 改为新边界；I032（`2.24085e-7`）改为拒绝，七位小数矩阵保持通过。
- 文档：[BUG-133](work-items/BUG-133.md)、[FEAT-012](work-items/FEAT-012.md)、[REFERENCE_SYNTAX](REFERENCE_SYNTAX.md) 与主台账同步当前契约。
- 版本元数据同步：`version.py`、`README.md` 标题/当前版/徽章、两份种子清单与 `docs/seed_package.json`；公开工具仍 110。

## 交付项

| 项 | 摘要 |
| --- | --- |
| [BUG-133](work-items/BUG-133.md) | 旋转矩阵准入收紧为实机 `1e-7` 边界；六位小数矩阵提交前拒绝，七位小数及更精确矩阵原样通过。 |

## 已知限制（如实记录）

- 该边界只在 Creo 10.0.0.0 / release 42 上做了实机测量；Creo 12.4、Creo 9 与其他安装未复测。
- 此前依赖 `1e-5`/`1e-3` 放行六位小数矩阵的调用现在会在提交前失败，应改用精确正交矩阵或从角度重建。
- 本版未重复 WorkBuddy 黑盒验收。

## 附件与摘要

Release 发布后见 `https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.35.4`。

四个附件（源码包摘要记录在同名 sidecar 中，一行 `<64 位 SHA256>  文件名`）：

- `MCP_CREO_MechDog-0.35.4-source.zip`
- `MCP_CREO_MechDog-0.35.4-source.zip.sha256`
- `MCP_CREO_MechDog-0.35.4-seed-library.zip`
- `MCP_CREO_MechDog-0.35.4-seed-library.zip.sha256`

- 种子包 SHA256：`ba556e79d80f18268c38d9b5044ac15a07afa6cc676153dd8e310cc9c9aec325`（24 个文件、9 个种子，两次构建摘要一致，与 `docs/seed_package.json` 一致）。
- 源码包：由本版发布提交的源码构建；字节数与 SHA256 见同名 sidecar，不写入包内。

## 未验

- Creo 12.4 与 Creo 9（本机环境为 Creo 10.0.0.0 / release 42）。
- WorkBuddy 黑盒验收。
- 发布后未重复执行 Creo 实机与 WorkBuddy 黑盒，实机范围以发布前记录为准。
