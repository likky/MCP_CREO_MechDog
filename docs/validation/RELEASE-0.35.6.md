# 发布记录 v0.35.6

日期：2026-11-22
版本：0.35.6（PATCH）
上一版本：0.35.5（`v0.35.5`，提交 `91642489e708f1c2ac7ee3fa1ff6f8565a53851b`）。
本次发布提交：`13aa9e163da7569c548949de8c8c3b9b8bf3615a`（annotated 标签 `v0.35.6`；包内该行为打包时点措辞，提交号在此 `main` 版本回填）。

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
- 单元测试（本轮 `tools/test_unit.py`，报告落在 `build/unit_test_report.json`，运行状态在 `build/unit_test_run.json`）：全量 unittest 通过，`tests_run=4376`、`failures=0`、`errors=0`、`skipped=6`（跳过项均为本机环境不具备：MSVC 独立 helper 2 项、归档作业缺失 2 项、符号链接权限 2 项）。
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
- 源码包解压独立验收：`MCP_CREO_MechDog-0.35.6-source.zip` 解压到 `%TEMP%\mc-0356-extract`（2,273 个文件、无 `.git`、无本机 `config.json`），新建 venv 后 `pip install -e .` 与 `-r requirements.txt` 成功，运行 `tools/test_unit.py`：4,368 项、0 失败、0 错误、14 跳过，解压受测指纹 `96262512a5d847f927d31ecc08bff4fd7bd12ee470d06c6f2f7d3e9c3803ad91`（`commit`/`dirty` 为 null，`source_status=complete`）。较工作树 4,376 项少 8 项，全部转为跳过（本机编译器配置缺失 5、无 `config.json` 2、符号链接特权 1 等环境项）。

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

- 发布：Release id `454230616`，`https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.35.6`，非 draft、非 prerelease，`created_at=2026-11-22T05:40:56Z`、`published_at=2026-11-22T05:41:17Z`（13:41 +08:00），target `main`，正文 2,652 字符。
- 标签：附注标签 `v0.35.6` 指向 `13aa9e163da7569c548949de8c8c3b9b8bf3615a`，远端 `main` 同值（`919f575..13aa9e1`）。
- 核对命令：`tools\check_release_assets.py --tag v0.35.6` 首次尝试因本机 `gh release download` 30 s 超时与 GitHub API 直连 502 未取得远端结论；改用 `gh release download v0.35.6 --dir build\release-assets\v0.35.6-remote` 下载四附件后执行 `tools\check_release_assets.py --tag v0.35.6 --version 0.35.6 --dir build\release-assets\v0.35.6-remote --body-file build\release-assets\v0.35.6-body.md`，exit 0，输出 `local_verified: four assets present; both sidecars match (version 0.35.6); release body self-proof verified`。
- 远端 API digest、下载后本地实算与 sidecar 逐一致：源码包 `4cdd0bb47e1590c3424a2f4f8c911be3ba01687d4a7a6c9a286d48a582b9f041`（11,618,127 字节）、源码 sidecar `fcbd997b87b9188896ad0068771d0af18cb915f7099adce7efa9d425a1ed76da`（101 字节）、种子包 `32ea2d0324e329f46bce7ac9dd41bd3086e2b7f151b1227e035038f0b1bd81fe`（493,442 字节）、种子 sidecar `d8f54519d30cef2d827dc1b63ba29248e9a597f0c950235fd5751dff905e33b8`（107 字节）。
- 正文：`gh release view v0.35.6 --json body` 与本地 `--notes-file` 除末尾换行外逐字相同。

## 未验

- 缺材料组件、抑制装配组件、嵌套子装配、混合密度真实质量与主惯量。
- 批量查询的完整 120 s 超时窗口（仅离线覆盖）。
- Creo 12.4 与 Creo 9（本机仅 Creo 10.0.0.0 / release 42）。
- WorkBuddy 黑盒验收与外部反馈环境（Windows 10 / Python 3.13 / Creo 9 SDK）复跑。
- 客户端退出遗留只读 pending job 的清理路径（建议另立 BUG-149，未纳入本版）。
