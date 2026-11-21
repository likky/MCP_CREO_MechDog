# 发布记录 v0.35.5

日期：2026-11-21
版本：0.35.5（PATCH）
上一版本：0.35.4（`v0.35.4`，提交 `29f9ed277d6436d9a0c6de4d4a1168fd51942444`）。
本次发布提交：`main` 上由 annotated 标签 `v0.35.5` 指向的提交（提交号以 `git rev-parse v0.35.5^{}` 为准）。

## 范围

- [BUG-144](../work-items/BUG-144.md)：打包单测绑定本轮证据，门禁前移到任何产物之前。
- [DEV-099](../work-items/DEV-099.md)：README 工具数改引 `creo_capabilities.tool_count`。
- [BUG-142](../work-items/BUG-142.md)：断开延迟钩子，实机核验被中断的 disconnect 保留 `unknown_outcome` 与预发布事实。
- 公开工具仍 110，无接口删除或重命名。

## 验收

- 环境：Windows x64、Python 3.12.10、Creo 10.0.0.0 / release 42（仅 BUG-142 实机）；源码提交 `5b32ef7` 之上的本轮改动，dirty 状态与源码指纹见 `build/development_check.json`、`build/unit_test_report.json`。
- BUG-144 修复前复现：在 detached worktree（`5b32ef7`）写入陈旧失败报告后运行旧版显式输出打包用例，FAIL / exit 1；stderr 显示打包被发布记录门禁拒绝，原因指向旧代码读取到的 `build/unit_test_report.json` 为 `success=False`（原文见 `build/bug144_repro_old_failure.txt`）。
- BUG-144 修复后：`tests/unit/test_unit_evidence.py` 全部通过；`SeedPackagingGateTests` 在临时 checkout 副本上覆盖显式输出、默认输出与 `stage` 三条正例，并验证缺证据、失败证据、既有输出、非空 stage 在零产物状态下拒绝。
- DEV-099：`tools/test_update_check.py --network-failure` exit 0（`{"success": true, "tool_count": 110, ...}`）；`tools/test_model_reconciliation.py --offline` exit 0。
- BUG-142：本机 Creo 10 作业 `9a73ad5e6a50466c8b4c2d3fdf6fc583` 在延迟窗口内写出预发布 `native_result.json`（`delivery_complete=false`、`before_disconnect`、`success=true`、`saved_file_reloaded_and_verified=true`），`SIGTERM` 后作业 `unknown_outcome`、模型 `revision=0` 且 `pending_job` 保留、无残留 `.tmp`；对照作业 `8d84a22553f14c5583338b7330cd1959` `succeeded`。原生 `delay` 模式与 `tests.unit.test_bug142_result_delivery` 12 项通过。
- 原生构建：`bridge.py build` exit 0，产物 `build/creo_worker.exe`。
- 发布记录门禁：`tools/check_release_records.py --version 0.35.5` exit 0；`tools/package.py` 的发布记录门禁在写 ZIP、sidecar、stage 之前执行并通过。
- 单元测试（本轮 `tools/test_unit.py`）：全量 unittest 通过，`tests_run=4319`、`failures=0`、`errors=0`、`skipped=6`（跳过项均为本机环境不具备：MSVC 独立 helper 2 项、归档作业缺失 2 项、符号链接权限 2 项）；`run_id` 与源码指纹同时记录在 `build/unit_test_report.json` 与 `build/unit_test_run.json`，打包器要求两者一致。
- 源码包解压独立验收：把 `MCP_CREO_MechDog-0.35.5-source.zip` 解压到 `build\extract-0.35.5`，用独立 venv（仅按 `requirements.lock.txt` 安装依赖并 editable 安装解压副本）运行 `python -m unittest discover -s tests`，结果 `Ran 4311 tests`、`errors=3`、`skipped=14`。3 项失败均为解压环境限制：2 项因包内不含本机 `config.json`（`bridge.config()` 严格校验），1 项因解压路径较长触发 Windows MAX_PATH（`intent-*.tmp` 写入返回 ENOENT）；同一源码在主检出环境 4319 项全通过。

## 种子库

- 名称：`MCP_CREO_MechDog-0.35.5-seed-library.zip`；sidecar `MCP_CREO_MechDog-0.35.5-seed-library.zip.sha256`。
- 内容：24 个文件、9 个种子；`compatible_server_version=0.35.5`。
- SHA256：`fa98100e05aae1573322ad89d6f19b0192c63e008557168a4150bce358456405`，两次构建摘要一致，与 `docs/seed_package.json` 一致。

## 源码包

- 名称：`MCP_CREO_MechDog-0.35.5-source.zip`；sidecar `MCP_CREO_MechDog-0.35.5-source.zip.sha256`（一行 `<64 位 SHA256>  文件名`）。
- 由本版发布提交的源码构建；字节数与 SHA256 见同名 sidecar，不写入包内文件；打包器拒绝放松的文件集、非空 stage 与既有输出。

## 逐 ID 状态核对

| ID | 交付版本 | 实际 Release | 技术状态 | 卡首页 | 主台账 | 差异说明 |
| --- | --- | --- | --- | --- | --- | --- |
| [BUG-144](../work-items/BUG-144.md) | 0.35.5 | v0.35.5 | 已完成（0.35.5 交付） | 已完成（0.35.5 交付） | 已完成（0.35.5 交付） | 无 |
| [DEV-099](../work-items/DEV-099.md) | 0.35.5 | v0.35.5 | 已完成（0.35.5 交付） | 已完成（0.35.5 交付） | 已完成（0.35.5 交付） | 无 |
| [BUG-142](../work-items/BUG-142.md) | 0.35.5 | v0.35.5 | 已完成（0.35.5 交付） | 已完成（0.35.5 交付） | 已完成（0.35.5 交付） | 无 |

## 发布后远端核对

- 发布后执行，当前未验证（`remote_verification=pending`）；发布后用 `tools/check_release_assets.py --tag v0.35.5` 核对，结果回填本段与 [POSTCHECK](../development/RELEASE-POSTCHECK-2026-11-07.md)。
- 四个附件：`MCP_CREO_MechDog-0.35.5-source.zip`、`MCP_CREO_MechDog-0.35.5-source.zip.sha256`、`MCP_CREO_MechDog-0.35.5-seed-library.zip`、`MCP_CREO_MechDog-0.35.5-seed-library.zip.sha256`。
- Release 地址：`https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.35.5`。
- 种子包 SHA256 `fa98100e05aae1573322ad89d6f19b0192c63e008557168a4150bce358456405`；源码包摘要见 sidecar。

## 未验

- Creo 12.4 与 Creo 9（本机仅 Creo 10.0.0.0 / release 42）。
- WorkBuddy 黑盒验收。
- 外部反馈环境（Windows 10 / Python 3.13 / Creo 9 SDK）复跑。
