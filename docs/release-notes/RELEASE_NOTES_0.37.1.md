# MCP_CREO_MechDog 0.37.1 版本说明

版本类型为 PATCH，公开工具数 111。本版收口 [BUG-151](../archive/work-items/BUG-151.md) 并完善验证工具链，不改建模核心与原生执行器。

上一版本：0.37.0（`v0.37.0`，提交 `5932e20d2eba2760325f666ed1ca5b4f9851df83`）。

- **冒烟脚本实机启动等待与全模式收口**。此前 `tools/test_mcp.py` 在实机模式下启动 `server.py` 后立即调用 `creo_session_status`，在协调器尚未离开 `building_worker` 时必然失败；现改为先通过 `tools/mcp_readiness.py` 等待 `creo_startup_status` 就绪，并显式打印异常回溯以防被 `TaskGroup` 遮蔽、自动创建输出目录、补齐 `cancelled` 终态与 `detail="full"` 分页 `result_entries` 兜底。[BUG-151](../archive/work-items/BUG-151.md)
- **离线门禁接入 `dev_check`**。`tools/test_mcp.py` 新增 `--offline` 模式（测试服务端隔离 `startup.start` 与 `updates.start` 副作用，不拉起 Creo、不触网，走真实 stdio 传输），并加入 `tools/dev_check.py` 的 `OFFLINE_ACCEPTANCE_SCRIPTS`（三项离线门禁全自动运行）。
- **清理其余验证脚本的分页与启动状态漂移**。在 `src/creo_mechdog/mcp_contract.py` 新增 `fetch_capabilities_section` / `call_capabilities_section` 与 `tool_count` 一致性检查；修复 9 个仍从 compact `creo_capabilities({})` 直接读取 `runtime`/`references`/`seed_library`/`tools` 的 `tools/` 脚本（`test_callback_modeling`、`test_creo_startup`、`test_direct_loft`、`test_failed_model_cleanup`、`test_model_reconciliation`、`test_reference_contract`、`test_startup_retry`、`test_toolkit_channel`、`test_toolkit_recovery`），并在 `tests/unit/test_mcp_contract.py` 增加静态护栏；同步把 `tools/mcp_readiness.py` 的活跃状态集合对齐 `creo_startup.ACTIVE`（补齐 `connecting` 与 `waiting_for_channel`）。
- **偶发等待放宽与反馈归档**。按 0.35.8 反馈 §3 将 `tests/unit/test_startup_reboot.py` 中 `test_two_controllers_share_one_recovery_archive_and_launch` 的 2 s 事件等待放宽至 10 s；逐字节归档 0.35.8 反馈原件至 [test-mcp-capabilities-drift.md](../validation/feedback-0.35.8-2026-11-22/originals/test-mcp-capabilities-drift.md)。

本机环境为 Windows x64 / Python 3.12.10 / Creo 10.0.0.0（`release_numeric=42`）。本版未改 `native/**`，实机完成 `tools/test_mcp.py` 全部模式（`--offline`、`--protocol-only`、默认、`--classic`、`--create --simple` 与 `--create` 两件零件均保存重载通过）及 `tools/test_reference_contract.py` 协议面复验。Creo 9/12 实机与 WorkBuddy 黑盒未验。详见[验收与发布记录](../validation/RELEASE-0.37.1.md)。

## 附件

- `MCP_CREO_MechDog-0.37.1-source.zip`
- `MCP_CREO_MechDog-0.37.1-source.zip.sha256`
- `MCP_CREO_MechDog-0.37.1-seed-library.zip`
- `MCP_CREO_MechDog-0.37.1-seed-library.zip.sha256`

种子包 SHA256 为 `69e9f82e20b25e1e37bd8b3c2e3de11d60fe7b088efbf551a1e244c2ac0b4d13`。源码包摘要记录在同名 sidecar 中，两份 sidecar 分别记录对应 ZIP 的实际 SHA256。[GitHub Release](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.37.1)
