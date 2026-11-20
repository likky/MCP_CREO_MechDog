# 发布记录 v0.34.0（0.34.0，2026-11-21）

- 版本：`0.34.0`（MINOR 部分交付）。
- 发布提交：合入 `main` 后由该提交源码构建（提交号发布后回填）。
- 上一版本：0.33.0（`v0.33.0`，提交 `613cc4bc3424ce066fb255d5781aa157b23f35a3`）。
- 交付快照：[releases/0.34.0.json](../releases/0.34.0.json)。
- 版本说明：[RELEASE_NOTES_0.34.0.md](../RELEASE_NOTES_0.34.0.md)。
- Release：`https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.34.0`。
- 发布流程：[RELEASING.md](../development/RELEASING.md)；附件核对留存在 [RELEASE-POSTCHECK-2026-11-07.md](../development/RELEASE-POSTCHECK-2026-11-07.md) 的 `## v0.34.0` 段。

## 逐 ID 状态核对

台账以 [BACKLOG.md](../BACKLOG.md) 与 `docs/releases/0.34.0.json`（frozen 交付集）为准；工作卡状态只读首页 `分类：` 行的粗体词。本批五项均为 `部分交付 0.34.0`，与主台账逐字一致。

| ID | 交付版本 | 实际 Release | 卡首页 | 主台账 | 差异说明 |
| --- | --- | --- | --- | --- | --- |
| [BUG-137](../work-items/BUG-137.md) | 0.34.0 | v0.34.0 | 部分交付 0.34.0 | 部分交付 0.34.0 | — |
| [BUG-138](../work-items/BUG-138.md) | 0.34.0 | v0.34.0 | 部分交付 0.34.0 | 部分交付 0.34.0 | — |
| [BUG-139](../work-items/BUG-139.md) | 0.34.0 | v0.34.0 | 部分交付 0.34.0 | 部分交付 0.34.0 | — |
| [DEV-097](../work-items/DEV-097.md) | 0.34.0 | v0.34.0 | 部分交付 0.34.0 | 部分交付 0.34.0 | — |
| [FEAT-070](../work-items/FEAT-070.md) | 0.34.0 | v0.34.0 | 部分交付 0.34.0 | 部分交付 0.34.0 | — |

## 发布前核对

- 源码身份：分支 `codex/feedback-0311-0320-feat070`，基于 `main` `95852899d893f590c6ef37a3724ac669ca7c845e`，合入前 `dirty=true`（未提交）；版本以 [version.py](../../version.py) 为准，`README.md` 标题/当前版/徽章、`docs/seed_manifest.json` 与 `seed_library/seed_manifest.json` 的 `compatible_server_version` 同步为 0.34.0。
- Ruff：`ruff check` 与 `ruff format --check` 通过（不含 `docs/validation/` 历史原件与第三方/生成文件）。
- 单元测试：`tools\test_unit.py` 已跑全量，`build/unit_test_report.json` `success=true`，全量单测 4229 项通过。
- 单元测试明细：未通过 0、异常 0、跳过 6，耗时 341.4 秒；跳过项均为环境限制（目录/文件符号链接权限、MSVC x64 独立 helper 环境不可用、归档证据缺失），与源码无关。
- 原生构建：`.\.venv\Scripts\python.exe bridge.py build` 编译变更后的 `native/generic.cpp`，exit 0 → `build\creo_worker.exe`。
- 发布记录门禁：`tools\check_release_records.py --version 0.34.0` 须 exit 0；`tools\check_backlog_counts.py` 须 `consistent: true`（当前 205 项：BUG 93 / FEAT 67 / DEV 45）。
- 资产门禁（DEV-097，≥0.34.0 强制）：Release 正文须列出四个附件名、声明摘要在同名 sidecar，且正文任一 SHA256 与真实 sidecar 摘要一致。

## 实机验收摘要（本机 Creo 10.0.0.0 / release 42，2026-11-19 常设授权）

- **FEAT-070 `strategy=new` 成功**：模型 `51abe8c9c4264ee5b63df878aa2b861a`，作业 `973e4318b1f540dd9bf66541c4815174`；`status=succeeded`、`stage=verified`、`saved_file_reloaded_and_verified=true`；回执 `old_body` use=2(selected) ref_id=251 → `new_body` use=0(new)，`redefine_code=0`、`regenerate_code=0`、`feature_incomplete=false`；`body_counts_before objects=2 → after objects=3`；`volume_before = volume_after = 55087038135.823044 mm³`，与 BUG-120 基线完全一致；`native.log` 跑到 `BUILD_SUCCESS=1`/`DISCONNECT=0`/`result_delivery_complete`，无崩溃、无模态。
- **FEAT-070 失败路径**：模型 `1c1099e76241489c86db3313e2f8aef1`，作业 `f05c076d9b564c4f903f3d2371142fd6`，瞄准非实体化特征 1（基准 RIGHT）→ `status=failed`、`phase="locate_body_branch"`、`feature_incomplete=true`、`effect_status="rolled_back"`，消息 `FEAT070_NO_BODY_BRANCH: ... query_code=-4`；无崩溃、模型干净。
- **BUG-139 冷启动**：结束 xtop 与 nmsd、确认无残留 `creo_worker` 后清理 `toolkit.lock`，启动协调器从冷态走到 `ready`（不再在 `connected:true` 时误发 `timeout`），随后上述 FEAT-070 建模作业成功并保存重载。
- 已知限制：FEAT-070 `strategy=existing` 在该几何触发 Creo 10 / release 42 内核 `dig_err`（`resolve` 默认主体 → `ProSelectionToReference` 时 Creo 内部回溯模态，worker 阻塞至看门狗超时），记入 [FEAT-070 卡](../work-items/FEAT-070.md)；`strategy=new` 是可靠的自锁解除路径。

## 附件与摘要

源码包摘要记录在同名 sidecar 中，一行 `<64 位 SHA256>  文件名`。四个附件：

- `MCP_CREO_MechDog-0.34.0-source.zip`
- `MCP_CREO_MechDog-0.34.0-source.zip.sha256`
- `MCP_CREO_MechDog-0.34.0-seed-library.zip`
- `MCP_CREO_MechDog-0.34.0-seed-library.zip.sha256`

- 种子包 SHA256：`b3bfcab0ad754cb087019fda0f763fd020fa98ac23f38475e3189179df971343`（24 个文件、9 个种子，两次构建摘要一致，与 `docs/seed_package.json` 一致）。
- 源码包：由本版合入 `main` 的提交源码构建；字节数与 SHA256 见同名 sidecar，不写入包内文件。

## 未验

- Creo 12.4 与 Creo 9（本机为 Creo 10.0.0.0 / release 42）。
- WorkBuddy 黑盒验收；FEAT-070 `strategy=existing` 稳定性、真实船体非圆剖面。
- BUG-139 `force_ready` 降级路径与失败路径文案的本机 Creo 10 实机夹具（由 26 项单测覆盖）。
- 发布后未重复执行 Creo 实机与 WorkBuddy 黑盒，实机范围以发布前记录为准。

## 发布后核对

发布后执行，当前未验证。
