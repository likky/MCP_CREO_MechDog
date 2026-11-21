# 发布记录 v0.35.1（0.35.1，2026-11-21）

- 版本：`0.35.1`（PATCH）。
- 发布提交：合入 `main` 后由该提交源码构建（提交号发布后回填）。
- 上一版本：0.35.0（`v0.35.0`，提交 `4e42e1d4b7e801894ab296271398e9bd1bb83012`）。
- 交付快照：[releases/0.35.1.json](../releases/0.35.1.json)。
- 版本说明：[RELEASE_NOTES_0.35.1.md](../RELEASE_NOTES_0.35.1.md)。
- Release：`https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.35.1`。
- 发布流程：[RELEASING.md](../development/RELEASING.md)；附件核对留存在 [RELEASE-POSTCHECK-2026-11-07.md](../development/RELEASE-POSTCHECK-2026-11-07.md) 的 `## v0.35.1` 段。

## 逐 ID 状态核对

台账以 [BACKLOG.md](../BACKLOG.md) 与 `docs/releases/0.35.1.json`（frozen 交付集）为准；工作卡状态只读首页 `分类：` 行的粗体词。本批两项随 v0.35.1 交付，均保留已记录的未测范围（0.32.0 原始模型、真实 disconnect 阻塞、其他选择器形态与其他 Creo 版本）。

| ID | 技术状态 | 交付版本 | 实际 Release | 卡首页 | 主台账 | 差异说明 |
| --- | --- | --- | --- | --- | --- | --- |
| [BUG-142](../work-items/BUG-142.md) | 部分交付 0.35.1，剩余待验收 | 0.35.1 | v0.35.1 | 部分交付 0.35.1，剩余待验收 | 部分交付 0.35.1，剩余待验收 | — |
| [DEV-098](../work-items/DEV-098.md) | 部分交付 0.35.1，剩余待验收 | 0.35.1 | v0.35.1 | 部分交付 0.35.1，剩余待验收 | 部分交付 0.35.1，剩余待验收 | — |

## 发布前核对

- 源码身份：分支 `codex/dev098-nearest-bug142-root`（提交 `3dcbd39`），以 `--ff-only` 合入 `main`；合入后本版元数据与发布记录在同一主干提交中提交。版本以 [version.py](../../version.py) 为准，`README.md` 标题/当前版/徽章、`docs/seed_manifest.json` 与 `seed_library/seed_manifest.json` 的 `compatible_server_version` 同步为 0.35.1，公开工具仍 110。
- Ruff：`ruff check` 与 `ruff format --check` 通过（不含 `docs/validation/` 历史原件与第三方/生成文件）。
- 单元测试：`tools/dev_check.py` 全量 4293 项通过、失败 0、异常 0、跳过 6；`build/unit_test_report.json` `success=true`。跳过项为环境限制（符号链接权限、MSVC x64 独立 helper 环境、归档证据缺失）。
- 原生构建：`.\.venv\Scripts\python.exe bridge.py build` 编译变更后的 `native/geometry_selectors.cpp` 与 `native/worker.cpp`，exit 0 → `build\creo_worker.exe`；构建指纹含 `NATIVE_BUILD_FLAGS /utf-8-v1`，旧缓存不复用。
- 发布记录门禁：`tools\check_release_records.py --version 0.35.1` 须 exit 0；`tools\check_backlog_counts.py` 须 `consistent: true`。
- 资产门禁（DEV-097）：Release 正文须列出四个附件名、声明摘要在同名 sidecar，且正文任一 SHA256 与真实 sidecar 摘要一致（发布后核对）。

## 实机与原生证据摘要（本机 Creo 10.0.0.0 / release 42）

- **BUG-142 受控复现**：`tests/native/test_bug142_result_delivery.cpp` 的 `strict_dump_crash` 在非法 UTF-8 上调用严格 `dump(2)`，退出码 `0xC0000409`，留下 0 字节 `strict_result.json`；`invalid_utf8` 走替换 handler 后正常发布（失败码 30）、`delivery_complete=true`、无残留 `.tmp`；`invalid_utf8_complete` 保持成功投影。定向 11 项、组合回归 35 项通过。
- **BUG-142 字节对照**：修复前 `build\creo_worker.exe` 中弯破折号字节为 `E2 80 3F`（非法 UTF-8），加入 `/utf-8` 强制重编译后为 `E2 80 94`；对应实机崩溃作业 `0e5ea74cb55146979679d6b59f6e779b` 的 `native.log` 原始字节亦为 `… \xe2\x80?its label …`。
- **DEV-098 实机探针**：模型 `357fdb93e9544160aaac4b14f7599e12`，建面作业 `f8b1ea376ee74dffb19aab88f4d33d39` `succeeded`；零匹配拒绝作业 `16332c209fe247cc9e0c0396441aaae9` `failed`，回执 `candidate_count=12`、`matched_ids=[]`、`form=endpoints`、`coordinate_space=model`，`nearest_edges` 为 ids 54/55/56/59/60、`error_mm=100.0`；操作键包含 `geometry_selector_diagnostic`，最近候选未被选中。
- **原生冒烟**：`tools/probe_bug143.py` 作业 `bea2d8d6…` `succeeded`、`saved_file_reloaded_and_verified=true`，确认重建后的 worker 正常完成建模与保存重载。

## 附件与摘要

源码包摘要记录在同名 sidecar 中，一行 `<64 位 SHA256>  文件名`。四个附件：

- `MCP_CREO_MechDog-0.35.1-source.zip`
- `MCP_CREO_MechDog-0.35.1-source.zip.sha256`
- `MCP_CREO_MechDog-0.35.1-seed-library.zip`
- `MCP_CREO_MechDog-0.35.1-seed-library.zip.sha256`

- 种子包 SHA256：`ad1d62bfc15e2dd45b1118464df75d19ee3635a871b179e9eaa590ae8b5c0ed4`（24 个文件、9 个种子，两次构建摘要一致，与 `docs/seed_package.json` 一致）。
- 源码包：由本版合入 `main` 的提交源码构建；字节数与 SHA256 见同名 sidecar，不写入包内文件。

## 未验

- Creo 12.4 与 Creo 9（本机为 Creo 10.0.0.0 / release 42）。
- WorkBuddy 黑盒验收；DEV-098 的面/圆边轴/装配坐标选择器形态。
- BUG-142 的 0.32.0 原始模型与真实 disconnect 阻塞现场；替换 handler 之外的非法字节来源未穷举。
- 发布后未重复执行 Creo 实机与 WorkBuddy 黑盒，实机范围以发布前记录为准。

## 发布后核对

发布后执行，当前未验证。发布后以 `tools\check_release_assets.py --tag v0.35.1` 核对远端四个附件、两个 sidecar 与 Release 正文自证，并把实际列表、标签指向、字节数与 SHA256 追加到 `main` 的 POSTCHECK `## v0.35.1` 段；冻结包内快照不回写。
