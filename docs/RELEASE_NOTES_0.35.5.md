# MCP_CREO_MechDog 0.35.5 版本说明

版本类型：PATCH。承接 0.35.4。

上一版本：0.35.4（`v0.35.4`，提交 `29f9ed277d6436d9a0c6de4d4a1168fd51942444`）。

## 亮点

- **打包单测不再跨轮次污染**：[BUG-144](work-items/BUG-144.md) 让 `tools/test_unit.py` 在运行前原子写 `build/unit_test_run.json`，记录本轮 `run_id`、PID、版本与源码身份；结束后原子置 `completed`/`interrupted`，报告带同一 `run_id`。自 0.35.5 起，发布记录若声明“全部单测通过”，`release_integrity` 要求状态与报告共同满足 `completed`、版本、`run_id`、两侧源码指纹等于当前受测源与 `tests_run>0`；更早版本保持仅检查 `success=true`，历史记录逐字节不变。
- **门禁前移到任何产物之前**：`tools/package.py` 新增 `--source-root` 与 `--unit-report`，发布记录检查在写 ZIP、sidecar 与 stage 之前执行；测试用临时 checkout 副本覆盖显式输出、默认输出与 `stage` 三条路径，并验证缺证据、失败证据、既有输出与非空 stage 都会在零产物状态下拒绝。
- **README 工具数不再硬编码**：[DEV-099](work-items/DEV-099.md) 把特性段的固定“109 个公开工具”改为引用 `creo_capabilities` 返回的 `tool_count`，并保留隐藏工具说明。
- **真实 disconnect 阻塞实机闭环**：[BUG-142](work-items/BUG-142.md) 增加默认关闭的 `MECHDOG_TEST_DISCONNECT_DELAY_MS` 钩子，在预断开 checkpoint 之后、`ProEngineerDisconnect` 之前休眠。本机 Creo 10 实机在延迟窗口内 `SIGTERM` 结束 worker，作业转 `unknown_outcome`，预发布 `native_result.json` 保持 `delivery_complete=false`，模型 `revision=0` 且 `pending_job` 保留；对照作业随后 `succeeded`，会话仍可用。

## 变更总览

- 新增 `src/creo_mechdog/unit_evidence.py`：运行状态、原子写、`O_EXCL` 运行锁与死 PID 接管、源码身份。
- `src/creo_mechdog/unit_report.py`、`tools/test_unit.py`：报告带 `run_id`，运行状态与报告同批原子发布。
- `src/creo_mechdog/release_integrity.py`：新增 `UNIT_EVIDENCE_ENFORCED_FROM=(0,35,5)` 与状态/报告一致性检查。
- `tools/package.py`：新增 `--source-root`、`--unit-report`，发布记录门禁前移。
- 测试：新增 `tests/unit/test_unit_evidence.py`；`tests/unit/test_release_integrity.py` 的 `SeedPackagingGateTests` 改为在隔离副本打包。
- `native/result_delivery.h`、`tests/native/test_bug142_result_delivery.cpp`、`tests/unit/test_bug142_result_delivery.py`：断开延迟钩子与回归。
- 文档：README 特性段、工作卡、主台账与完成档案同步；版本元数据为 `version.py`、`README.md` 标题/当前版/徽章、两份种子清单与 `docs/seed_package.json`。公开工具仍 110。

## 交付项

| 项 | 摘要 |
| --- | --- |
| [BUG-144](work-items/BUG-144.md) | 打包单测绑定本轮 `run_id` 与源码指纹；三条打包路径隔离，门禁先于产物。 |
| [DEV-099](work-items/DEV-099.md) | README 工具数改引 `creo_capabilities.tool_count`；两条离线检查 exit 0、实测 110。 |
| [BUG-142](work-items/BUG-142.md) | 断开延迟钩子；本机 Creo 10 实机核验被中断的 disconnect 保留 `unknown_outcome` 与预发布事实。 |

## 已知限制（如实记录）

- BUG-142 的断开阻塞只在 Creo 10.0.0.0 / release 42 实机核验；其他 Creo 版本与 WorkBuddy 黑盒未测。
- BUG-144 的严格证据门禁自 0.35.5 起生效；外部反馈环境（Windows 10 / Python 3.13 / Creo 9 SDK）未复跑。
- 本版未新增公开工具，接口与 0.35.4 兼容。

## 附件与摘要

Release 发布后见 `https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.35.5`。

四个附件（源码包摘要记录在同名 sidecar 中，一行 `<64 位 SHA256>  文件名`）：

- `MCP_CREO_MechDog-0.35.5-source.zip`
- `MCP_CREO_MechDog-0.35.5-source.zip.sha256`
- `MCP_CREO_MechDog-0.35.5-seed-library.zip`
- `MCP_CREO_MechDog-0.35.5-seed-library.zip.sha256`

- 种子包 SHA256：`fa98100e05aae1573322ad89d6f19b0192c63e008557168a4150bce358456405`（24 个文件、9 个种子，两次构建摘要一致，与 `docs/seed_package.json` 一致）。
- 源码包：由本版发布提交的源码构建；字节数与 SHA256 见同名 sidecar，不写入包内。

## 未验

- Creo 12.4 与 Creo 9（本机环境为 Creo 10.0.0.0 / release 42）。
- WorkBuddy 黑盒验收。
- 外部反馈环境（Windows 10 / Python 3.13 / Creo 9 SDK）复跑。
