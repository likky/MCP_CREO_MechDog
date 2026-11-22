# 发布记录 v0.35.6

日期：2026-11-22
版本：0.35.6（PATCH）
上一版本：0.35.5（`v0.35.5`，提交 `91642489e708f1c2ac7ee3fa1ff6f8565a53851b`）。
本次发布提交：见 `v0.35.6` 标签指向（本记录随该提交冻结；实际提交号与 Release id 由发布后的 POSTCHECK 回填）。

## 范围

- [FEAT-057](../work-items/FEAT-057.md)：装配质量属性（体积/面积/几何重心/质量重心、只读 occurrence 扫描、有效平均密度标记）。
- [FEAT-073](../work-items/FEAT-073.md)：`creo_get_mass_properties_batch`，公开工具 110→111。
- [FEAT-072](../work-items/FEAT-072.md)：`session_candidates` 与进程内 `session_id` 选定。
- [BUG-143](../work-items/BUG-143.md)：固体特征镜像挂死根因与创建前拒绝全部 feature 引用。
- [BUG-145](../work-items/BUG-145.md)：桌面 worker 的 Unicode 路径与清理异常。
- [BUG-146](../work-items/BUG-146.md)：`launched_by`、`stalled_recovery`、`abandon_stalled_recovery`。
- [BUG-147](../work-items/BUG-147.md)：材质密度失败的调用名/返回码/显式密度用法。
- [BUG-148](../work-items/BUG-148.md)：单个与多个开放轮廓的曲面拉伸诊断。
- 交接自 0.35.5 的实机批次（0.35.0 反馈 T03—T10）；`main` 上 BUG-142/BUG-144/DEV-098/DEV-099 已随 0.35.5 交付并归档，本版不重复认领。

## 验收

- 环境：Windows x64 build 26200、Python 3.12.10、MSVC 19.29、Creo 10.0.0.0 / release 42（实机部分）。源码为本次发布提交，`dirty=false`，受测指纹与 `run_id` 见 `build/unit_test_report.json`、`build/unit_test_run.json`。
- 单元测试（本轮 `tools/test_unit.py`，报告落在 `build/unit_test_report.json`，运行状态在 `build/unit_test_run.json`）：全量 unittest 通过，`tests_run=4368`、`failures=0`、`errors=0`、`skipped=6`（跳过项均为本机环境不具备：MSVC 独立 helper 2 项、归档作业缺失 2 项、符号链接权限 2 项）。
- 开发检查：`tools/dev_check.py --skip-unit --work-item FEAT-073`（及 FEAT-057、BUG-144 记录在计划的定向运行）Ruff 0 发现、0 文件待格式化，两项独立离线 stdio 验收通过，`success=true`。
- 原生构建：`bridge.py build` exit 0，产物 `build/creo_worker.exe`；本轮未改动原生接口签名，装配质量属性与镜像拒绝已在 Creo 10 SDK 下编译通过。
- 实机（Creo 10.0.0.0 / release 42，证据留在 `build/live_t08_assembly_mass.py`、`build/live_t10_batch_mass.py`、`build/live_t10a_full_batch.py`、`build/live_t10a_timeout_followup.py` 的运行记录中）：
  - FEAT-057 12/12：装配体积 `2199.9999999999986` mm³、面积 `1679.9999999999998` mm²、几何重心 `[22.72727272727273, 2.727272727272727, 2.3636363636363638]`；`component_scan` 3 个活动实例、0 缺材料、0 未解析、`complete=true`；材料密度查询 `-1` 时 `mass:null`/`material_query_failed`；`density_g_cm3=7.85` 得 `17.26999999999999` g，体积/面积/重心不变。
  - FEAT-073 15/15 + 11/11：两件一次批量 `succeeded=2`、`elapsed=16.172 s`；16 项满批 `16/16`、`elapsed=131.188 s`（预算 180 s）、单项目均 8.199 s；并发批量的被拒方首项 `toolkit_busy`、`blocking_job_id` 可查回 `succeeded`；预算 14 s 时首项成功、第二项 `error_kind=timeout`、第三项 `skipped/time_budget_exhausted`，被判超时的作业随后 3.06 s 自行 `succeeded`（体积 700 mm³）。
  - FEAT-072：单会话无选择 `toolkit_code=0`、错误 ID `not_found_or_unreadable` 且不回落；双 Creo 现场 `toolkit_code=-36`、`selection_required`，关闭多余会话后无需重启恢复 `connected=true`。
  - BUG-143：实体镜像两次挂死（330 s / 240 s，`ProArrayAlloc(…ProFeatureCreateOptions…)=0`，随后 `toolkit_code=-38`）；修复后 feature 引用在提交阶段被拒（`feature_job=null`、会话 `toolkit_code=0`），`{kind:"part"}` 路线 `succeeded`、体积 `4000.0000000000005` mm³、保存重载 true。
  - BUG-146：`waiting_for_channel` + runner 已退出的真实残留 `stalled_recovery.proven=true`（basis=`runner_exited`）→ `abandon_stalled_recovery` → `restore_baseline` `succeeded`，`pending_job`/`recovery_pending` 均 null。
  - BUG-148：两开放轮廓报 `-1` 并给出拆分指引（0 闭合、2 轮廓、4 开放端），单开放轮廓 `quilts=1`/`has_solid=false`，闭合对照成功。
- 发布记录门禁：`tools/check_release_records.py --version 0.35.6` exit 0；`tools/package.py` 的发布记录门禁（含本轮 `run_id`/源码指纹证据）在写 ZIP、sidecar、stage 之前执行并通过。
- 源码包解压独立验收：打包后执行，当前未验证。计划在 `%TEMP%\mc-0356-extract` 解压 `MCP_CREO_MechDog-0.35.6-source.zip`，用独立 venv（`pip install -e .` 与 `-r requirements.txt`）运行 `tools/test_unit.py`，并把项数、跳过、解压受测指纹与差异项追加到 `main` 的统一 POSTCHECK；包内记录不预填该轮结果。

## 种子库

- 名称：`MCP_CREO_MechDog-0.35.6-seed-library.zip`；sidecar `MCP_CREO_MechDog-0.35.6-seed-library.zip.sha256`。
- 内容：24 个文件、9 个种子；`compatible_server_version=0.35.6`。
- SHA256：`32ea2d0324e329f46bce7ac9dd41bd3086e2b7f151b1227e035038f0b1bd81fe`，两次构建摘要一致，与 `docs/seed_package.json` 一致。

## 源码包

- 名称：`MCP_CREO_MechDog-0.35.6-source.zip`；sidecar `MCP_CREO_MechDog-0.35.6-source.zip.sha256`（一行 `<64 位 SHA256>  文件名`）。
- 由本版发布提交的源码构建；源码包摘要见同名 sidecar（一行 `<64 位 SHA256>  文件名`），不写入包内文件。打包器拒绝放松的文件集、非空 stage 与既有输出；`stage` 与两个 ZIP 在同一目录生成后逐个核对。

## 逐 ID 状态核对

| ID | 交付版本 | 实际 Release | 技术状态 | 卡首页 | 主台账 | 差异说明 |
| --- | --- | --- | --- | --- | --- | --- |
| [FEAT-057](../work-items/FEAT-057.md) | 0.35.6 | v0.35.6 | 部分交付 0.35.6 子项 | 部分交付 0.35.6 子项 | 部分交付 0.35.6 子项（装配路径与扫描证据）；缺材料/抑制/嵌套与混合密度真实质量、主惯量未排期 | 无 |
| [FEAT-073](../work-items/FEAT-073.md) | 0.35.6 | v0.35.6 | 已交付 0.35.6 | 已交付 0.35.6 | 已交付 0.35.6 | 无 |
| [FEAT-072](../work-items/FEAT-072.md) | 0.35.6 | v0.35.6 | 部分交付 0.35.6 | 部分交付 0.35.6 | 部分交付 0.35.6；真实 ID A→A 与 Creo 9/12 未排期 | 无 |
| [BUG-143](../work-items/BUG-143.md) | 0.35.6 | v0.35.6 | 部分交付 0.35.6 子项 | 部分交付 0.35.6 子项 | 部分交付 0.35.6 子项；闭合锥面 trim 与其他非圆柱形态未排期 | 无 |
| [BUG-145](../work-items/BUG-145.md) | 0.35.6 | v0.35.6 | 已有修复但待验收 | 已有修复但待验收 | 已有修复但待验收 | 无 |
| [BUG-146](../work-items/BUG-146.md) | 0.35.6 | v0.35.6 | 已有修复但待验收 | 已有修复但待验收 | 已有修复但待验收 | 无 |
| [BUG-147](../work-items/BUG-147.md) | 0.35.6 | v0.35.6 | 已有诊断待材质实测 | 已有诊断待材质实测 | 已有诊断待材质实测 | 无 |
| [BUG-148](../work-items/BUG-148.md) | 0.35.6 | v0.35.6 | 已有修复但待验收 | 已有修复但待验收 | 已有修复但待验收 | 无 |

## 发布后远端核对

- 发布后执行，当前未验证。核对方式：`tools\check_release_assets.py --tag v0.35.6`，并把真实附件列表、API digest、本地实算 SHA256 与 sidecar 比对结果追加到 `main` 的统一 POSTCHECK。
- Release 地址（发布后）：`https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.35.6`。

## 未验

- 缺材料组件、抑制装配组件、嵌套子装配、混合密度真实质量与主惯量。
- 批量查询的完整 120 s 超时窗口（仅离线覆盖）。
- Creo 12.4 与 Creo 9（本机仅 Creo 10.0.0.0 / release 42）。
- WorkBuddy 黑盒验收与外部反馈环境（Windows 10 / Python 3.13 / Creo 9 SDK）复跑。
- 客户端退出遗留只读 pending job 的清理路径（建议另立 BUG-149，未纳入本版）。
