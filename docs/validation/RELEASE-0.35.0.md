# 发布记录 v0.35.0（0.35.0，2026-11-21）

- 版本：`0.35.0`（MINOR 部分交付）。
- 发布提交：合入 `main` 后由该提交源码构建（提交号发布后回填）。
- 上一版本：0.34.0（`v0.34.0`，提交 `bbd81cdbaa92f7acdc1988d574dfdab832e01bed`）。
- 交付快照：[releases/0.35.0.json](../releases/0.35.0.json)。
- 版本说明：[RELEASE_NOTES_0.35.0.md](../RELEASE_NOTES_0.35.0.md)。
- Release：`https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.35.0`（发布后执行，当前未验证）。
- 发布流程：[RELEASING.md](../development/RELEASING.md)；附件核对留存在 [RELEASE-POSTCHECK-2026-11-07.md](../development/RELEASE-POSTCHECK-2026-11-07.md) 的 `## v0.35.0` 段。

## 逐 ID 状态核对

台账以 [BACKLOG.md](../BACKLOG.md) 与 `docs/releases/0.35.0.json`（frozen 交付集）为准；工作卡状态只读首页 `分类：` 行的粗体词。本批六项随 v0.35.0 交付，均保留已记录的未测范围（跨作业/mirror/trim 标签、其他参考面组合、真实缓存与僵尸现场、崩溃根因、零候选原生接入）。

| ID | 技术状态 | 交付版本 | 实际 Release | 卡首页 | 主台账 | 差异说明 |
| --- | --- | --- | --- | --- | --- | --- |
| [BUG-140](../work-items/BUG-140.md) | 部分交付 0.35.0，剩余待验收 | 0.35.0 | v0.35.0 | 部分交付 0.35.0，剩余待验收 | 部分交付 0.35.0，剩余待验收 | — |
| [BUG-141](../work-items/BUG-141.md) | 部分交付 0.35.0，剩余待验收 | 0.35.0 | v0.35.0 | 部分交付 0.35.0，剩余待验收 | 部分交付 0.35.0，剩余待验收 | — |
| [BUG-142](../work-items/BUG-142.md) | 部分交付 0.35.0，剩余待验收 | 0.35.0 | v0.35.0 | 部分交付 0.35.0，剩余待验收 | 部分交付 0.35.0，剩余待验收 | — |
| [BUG-143](../work-items/BUG-143.md) | 部分交付 0.35.0，剩余待验收 | 0.35.0 | v0.35.0 | 部分交付 0.35.0，剩余待验收 | 部分交付 0.35.0，剩余待验收 | — |
| [FEAT-071](../work-items/FEAT-071.md) | 部分交付 0.35.0，剩余待验收 | 0.35.0 | v0.35.0 | 部分交付 0.35.0，剩余待验收 | 部分交付 0.35.0，剩余待验收 | — |
| [DEV-098](../work-items/DEV-098.md) | 部分交付 0.35.0，剩余待验收 | 0.35.0 | v0.35.0 | 部分交付 0.35.0，剩余待验收 | 部分交付 0.35.0，剩余待验收 | — |

## 发布前核对

- 源码身份：分支 `codex/feedback-0330-startup-surfaces`，基于 `main` `0a1e91f1f9dbe481cc1859778a58f7bf629f4ce0`，合入前 `dirty=true`（未提交）；版本以 [version.py](../../version.py) 为准，`README.md` 标题/当前版/徽章、`docs/seed_manifest.json` 与 `seed_library/seed_manifest.json` 的 `compatible_server_version` 同步为 0.35.0，公开工具仍 110。
- Ruff：`ruff check` 与 `ruff format --check` 通过（不含 `docs/validation/` 历史原件与第三方/生成文件）。
- 单元测试：`tools/dev_check.py` 跑全量，`build/unit_test_report.json` `success=true`，全量 unittest 4286 项通过、失败 0、异常 0、跳过 6；跳过项为环境限制（符号链接权限、MSVC x64 独立 helper 环境、归档证据缺失）。
- 原生构建：`.\.venv\Scripts\python.exe bridge.py build` 编译变更后的 `native/quilt_query.h`、`native/surfaces.cpp`、`native/worker.cpp`、`native/result_delivery.h`、`native/generic.cpp`，exit 0 → `build\creo_worker.exe`。
- 发布记录门禁：`tools\check_release_records.py --version 0.35.0` 须 exit 0；`tools\check_backlog_counts.py` 须 `consistent: true`（当前 208 项：BUG 95 / FEAT 68 / DEV 45）。
- 资产门禁（DEV-097）：Release 正文须列出四个附件名、声明摘要在同名 sidecar，且正文任一 SHA256 与真实 sidecar 摘要一致（发布后核对）。

## 实机验收摘要（本机 Creo 10.0.0.0 / release 42，2026-11-19 常设授权）

- **BUG-143（同计划标签引用）**：模型 `fb38fca6ca654971b0536034a72d9c0f`，作业 `bcc2c0d5802d4cdfbb5bc99f2c410da9`；`status=succeeded`、`saved_file_reloaded_and_verified=true`；两次 `quilt_merge` 回执 `quilt_id=result_quilt_id=71`；`solidify` 以 `{kind:"quilt_feature","label":"merge_closed_result"}` 提交，`target_quilt_id=71`、`volume_after_mm3=785.3981633974481`（=π·5²·10）；`surface_fill` 回执 `quilt_id` 95/114。
- **BUG-143（失败语义）**：fill 标签被 `solidify` 引用时解析成功，仅因 quilt 开放按 `ProQuiltVolumeEval=-18, quilt_is_open` 拒绝（作业 `975f8b2ce81b4079b68485b66eeeb718`），不再报 `-4`。
- **BUG-143 回归**：`tools/test_surface_chain.py --case solidify --live` 全项通过（run `20261121-022012-337500`），显式 `{kind:"quilt",id:N}` 路径未回归。
- **FEAT-071**：`tools/test_chamfer_angle.py --live` 4/4 通过；`d1=2,d2=5` → 前侧面 2.0 mm、顶面 5.0 mm（作业 `186b2b1a…`）；`d1=5,d2=2` → 前侧面 5.0 mm、顶面 2.0 mm（作业 `3948c49d…`）；两次去除体积均为 250 mm³、保存重载 true；距离+角度两例回归通过。
- **BUG-142**：实机复现 `0xC0000409`（作业 `0e5ea74cb55146979679d6b59f6e779b`，`PHASE=disconnect`，仅 0 字节临时结果）；修复交付顺序后，失败路径作业 `975f8b2c…` 的 `native_result.json` 存在、`delivery_complete=true`、`rollback_succeeded=false`、无残留 `.tmp`。崩溃栈 Cookie 根因未定位。
- **BUG-140/141**：离线回归；10 依赖指纹探针 0.415647 s/1024 候选 → 1.8 µs/0 次 legacy 调用；退出条目 `uncertain` 由 True 变 False。未连接实机构造真实僵尸或冷缓存计时。

## 附件与摘要

源码包摘要记录在同名 sidecar 中，一行 `<64 位 SHA256>  文件名`。四个附件：

- `MCP_CREO_MechDog-0.35.0-source.zip`
- `MCP_CREO_MechDog-0.35.0-source.zip.sha256`
- `MCP_CREO_MechDog-0.35.0-seed-library.zip`
- `MCP_CREO_MechDog-0.35.0-seed-library.zip.sha256`

- 种子包 SHA256：`8f7c1645d7a324f674de6f486bd83aca0f4ad99e5abd50177843fedc6352f02d`（24 个文件、9 个种子，两次构建摘要一致，与 `docs/seed_package.json` 一致）。
- 源码包：由本版合入 `main` 的提交源码构建；字节数与 SHA256 见同名 sidecar，不写入包内文件。

## 未验

- Creo 12.4 与 Creo 9（本机为 Creo 10.0.0.0 / release 42）。
- WorkBuddy 黑盒验收；BUG-143 跨作业标签、mirror 标签与 trim 标签链；FEAT-071 其他参考面组合与曲面边。
- BUG-140/141 真实缓存计时与真实僵尸进程现场；BUG-142 栈 Cookie 根因；DEV-098 零候选最近边原生接入。
- 发布后未重复执行 Creo 实机与 WorkBuddy 黑盒，实机范围以发布前记录为准。

## 发布后核对

- 发布后执行，当前未验证；结果追加到 [POSTCHECK `## v0.35.0`](../development/RELEASE-POSTCHECK-2026-11-07.md) 段，不重打已冻结附件。
