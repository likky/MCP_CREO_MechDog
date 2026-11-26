# MCP_CREO_MechDog 0.34.0 版本说明

版本类型：MINOR 部分交付。承接 0.33.0。

上一版本：0.33.0（`v0.33.0`，提交 `613cc4bc3424ce066fb255d5781aa157b23f35a3`）。

## 亮点

- **BUG-120 实体化链路收官**：[FEAT-070](../work-items/FEAT-070.md) 新增公开工具 `creo_redefine_solidify_body`，可对实体化（patch/solidify）特征重定义 `PRO_E_BODY_USE`/`PRO_E_BODY_SELECT`，以 `strategy=new` 重建失效主体参照、解除 `BOW_BULB_SOLID`（feature 250）在失败态把主体 251 选作自身参照的自锁；本机 Creo 10 / release 42 实机成功，体积与 BUG-120 基线完全一致、保存重载通过。公开工具 109 → 110。
- **发布口径可证**：[DEV-097](../archive/work-items/DEV-097.md) 为 ≥0.34.0 增加 Release 正文自证门禁——正文必须列出四个附件名、声明摘要在同名 sidecar，且正文中出现的任一 SHA256 必须与真实 sidecar 摘要一致；历史版本（<0.34.0）祖父化不误报。
- **全量单测口径真实**：[BUG-137](../archive/work-items/BUG-137.md) 修复 `tests/unit/test_inspection_only_admission.py` 因未隔离 `subprocess.Popen` 导致的 3 个 teardown errors（`runner.log` WinError 32），并要求发布记录对全量单测结果的表述必须由 `success=true` 的 `build/unit_test_report.json` 支撑。
- **验收脚本不再硬编码工具数**：[BUG-138](../archive/work-items/BUG-138.md) 去除 `tools/test_update_check.py` / `tools/test_model_reconciliation.py` 的硬编码 82/84，改以 `creo_capabilities` 为准；`tools/dev_check.py` 新增离线验收门禁，`docs/UPDATE_CHECK.md` 同步。
- **启动协调器韧性**：[BUG-139](../work-items/BUG-139.md) 探测超时可配、成功探测在循环外落地、连接阶段有 `connecting` 相位、总预算可配且分段、准入支持 recent-connected 降级或 `force_ready`、`worker_build_identity` 增加 `observed_at`/`env_fingerprint` 并清除陈旧失败字段、拒绝文案附最后 `toolkit_code`；本机 Creo 10 冷启动走到 `ready`。

## 变更总览

- 新增公开工具 `creo_redefine_solidify_body`（`server.py`、`src/creo_mechdog/schema.py` 的 `RedefineSolidifyBodyOp`、`capabilities.py` 登记），公开工具 109 → 110。
- `native/generic.cpp`：新增 `generic_redefine_solidify_body` 及 `feat070_*` 辅助；`ProFeatureWithoptionsRedefine` 调用分配选项数组与错误列表，避免空指针崩溃与 Creo 模态对话框阻塞消息循环。
- `src/creo_mechdog/release_integrity.py`：`validate_release_body`（DEV-097）、`_unit_test_claim_problems`（BUG-137）；`tools/check_release_assets.py --body-file` 与 `release_download.fetch_release_body`。
- `creo_startup.py`、`bridge.py`：启动协调器韧性七项（BUG-139）；`config.example.json` 暴露新增可配项。
- `docs/`：`BACKLOG.md` 五项状态更新；新增 `work-items/{BUG-137,BUG-138,BUG-139,DEV-097,FEAT-070}.md` 实现与证据；`releases/0.34.0.json` 交付快照；`development/RELEASE-POSTCHECK-2026-11-07.md` 增 `## v0.34.0` 段。
- 版本元数据同步：`version.py`、`README.md` 标题/当前版/徽章（110 工具）、`docs/seed_package.json`、`seed_library/seed_manifest.json`、`docs/seed_manifest.json` 的 `compatible_server_version` 与种子包名/摘要。

## 交付项

| 项 | 摘要 |
| --- | --- |
| [FEAT-070](../work-items/FEAT-070.md) | 实体化重定义重建失效主体参照；`strategy=new` 打破 BUG-120 自锁，本机 Creo 10 实机体积 55087038135.823044 mm³ 与基线一致、保存重载通过；失败路径回滚干净。公开工具 109→110。 |
| [BUG-137](../archive/work-items/BUG-137.md) | 隔离 `subprocess.Popen` 消除全量单测 teardown WinError 32；发布口径门禁要求 `success=true` 报告。 |
| [BUG-138](../archive/work-items/BUG-138.md) | 去硬编码工具数 82/84，改以 `creo_capabilities` 为准；`dev_check` 离线验收门禁；修复 `native/surface_loft.cpp` 存量格式回归。 |
| [BUG-139](../work-items/BUG-139.md) | 启动协调器韧性七项；本机 Creo 10 冷启动走到 `ready`。 |
| [DEV-097](../archive/work-items/DEV-097.md) | Release 正文自证门禁（四附件名 + sidecar 指引 + 摘要比对，≥0.34.0 强制，历史版本祖父化）。 |

## 已知限制（如实记录）

- FEAT-070 `strategy=existing` 在 BUG-120 该几何上触发 Creo 10 / release 42 内核 `dig_err`：经 `resolve({"kind":"body"})` 取默认主体再 `ProSelectionToReference` 时 Creo 内部回溯弹出模态对话框，worker 阻塞，看门狗在 `native_timeout_seconds=180` 后结束进程。`strategy=new` 是可靠的自锁解除路径；`strategy=existing` 的该几何不稳定待后续抑制 UI 或换用其他主体解析方式时跟进。
- BUG-139 的 `force_ready` 降级路径与失败路径文案未在本机 Creo 10 构造实机夹具复现（由 26 项单测覆盖）。

## 附件与摘要

Release：`https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.34.0`。

四个附件（源码包摘要记录在同名 sidecar 中，一行 `<64 位 SHA256>  文件名`）：

- `MCP_CREO_MechDog-0.34.0-source.zip`
- `MCP_CREO_MechDog-0.34.0-source.zip.sha256`
- `MCP_CREO_MechDog-0.34.0-seed-library.zip`
- `MCP_CREO_MechDog-0.34.0-seed-library.zip.sha256`

- 种子包 SHA256：`b3bfcab0ad754cb087019fda0f763fd020fa98ac23f38475e3189179df971343`（24 个文件、9 个种子，两次构建摘要一致，与 `docs/seed_package.json` 一致）。
- 源码包：由本版合入 `main` 的提交源码构建；字节数与 SHA256 见同名 sidecar，不写入包内。

## 未验

- Creo 12.4 与 Creo 9（本机环境为 Creo 10.0.0.0 / release 42）。
- WorkBuddy 黑盒验收。
- FEAT-070 `strategy=existing` 在该几何的稳定性、真实船体非圆剖面。
- 发布后未重复执行 Creo 实机与 WorkBuddy 黑盒，实机范围以发布前记录为准；远端附件核对发布后执行，当前未验证。
