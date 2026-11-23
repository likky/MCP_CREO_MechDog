# 发布记录 v0.37.1

日期为 2026-11-23，版本类型为 PATCH，公开工具仍 111。

上一版本：0.37.0（`v0.37.0`，提交 `5932e20d2eba2760325f666ed1ca5b4f9851df83`）。

## 验收范围

本版收口 [BUG-151](../work-items/BUG-151.md) 并归档 0.35.8 外部反馈原件 [test-mcp-capabilities-drift.md](feedback-0.35.8-2026-11-22/originals/test-mcp-capabilities-drift.md)（SHA256 `5944044677c36c089f182590881ee9710de44144390c57a7dd298e17698732ee`）：

- `tools/test_mcp.py`：实机模式在调用 `creo_session_status` 前通过 `wait_for_startup` 等待启动就绪（修复 0.36.1 未验实机时必然撞 `building_worker` 失败的问题）；新增 `--offline` 模式（内部 `--serve-offline` 隔离 `startup.start` 与 `updates.start` 副作用，不拉起 Creo、不触网，走真实 stdio）；显式打印异常回溯防止被 `TaskGroup` 遮蔽；自动创建报告输出目录；补齐 `cancelled` 终态与 `detail="full"` 分页 `result_entries` 兜底；核对 `tool_count` 与 `enabled_tool_count` 一致。
- `tools/dev_check.py`：将 `("test_mcp", ["tools/test_mcp.py", "--offline"])` 纳入 `OFFLINE_ACCEPTANCE_SCRIPTS`，每次 `dev_check` 均自动执行三项离线 stdio 验收。
- `tools/mcp_readiness.py`：活跃状态集合改为直接引用 `creo_startup.ACTIVE`（补齐 `connecting` 与 `waiting_for_channel`）。
- `src/creo_mechdog/mcp_contract.py` 与 9 个 `tools/` 脚本：新增 `fetch_capabilities_section` / `call_capabilities_section` 与 `tool_count` 校验，清理 `test_callback_modeling`、`test_creo_startup`、`test_direct_loft`、`test_failed_model_cleanup`、`test_model_reconciliation`、`test_reference_contract`、`test_startup_retry`、`test_toolkit_channel`、`test_toolkit_recovery` 中仍从 compact `creo_capabilities({})` 读取 `runtime`/`references`/`seed_library`/`tools` 的代码；`tests/unit/test_mcp_contract.py` 新增静态扫描护栏。
- `tests/unit/test_startup_reboot.py`：按 0.35.8 反馈 §3 将 `test_two_controllers_share_one_recovery_archive_and_launch` 的 2 s 等待放宽至 10 s。

未改 `native/**`，未改任何 MCP 工具签名或建模契约，公开工具仍 111 个。

## 环境与实机证据

- Windows x64 / Python 3.12.10 / Creo 10.0.0.0（`release_numeric=42`，安装目录 `D:\Program Files\PTC\Creo 10.0.0.0`）与匹配 Toolkit SDK（复用既有 `build/creo_worker.exe`，本版无原生源码变动）。
- 重启此前无窗口且返回 `-4` 的旧 Creo 会话前确认无残留 `creo_worker`；启动新会话后 `bridge.session_status()` 返回 `connected=true`、`toolkit_code=0`、`release_numeric=42`。
- `tools/test_mcp.py --offline`：exit 0，`tool_count=111`、`capability_contract_verified=true`、`capability_pages=2`（`build/mcp_offline_test.json`）。
- `tools/test_mcp.py --protocol-only`：exit 0，`tool_count=111`、`capability_contract_verified=true`、`capability_pages=2`。
- `tools/test_mcp.py`（默认实机）与 `tools/test_mcp.py --classic`：均 exit 0，`tool_count=111`、`capability_contract_verified=true`、`capability_pages=2`、`session_connected=true`（`build/mcp_protocol_test.json`）。
- `tools/test_mcp.py --create --simple`（42×30×6 平板）：exit 0，job `55adbac97065439890cda876df55f58e`，`status=succeeded`，体积 `7560` mm³（解析 `42×30×6=7560`），`extrude=1`，`saved_file_reloaded_and_verified=true`，`delivery_complete=true`，`disconnect_code=0`，PRT SHA256 `27a4f45d13dfc024556159030cedd6688febc8f76b4c92e59c3f3283cd57f81a`（`build/mcp_simple_test.json`）。
- `tools/test_mcp.py --create`（100×70×12 R4 五孔平板）：exit 0，job `3390da54279149eaac721ee078bf586c`，`status=succeeded`，体积 `81535.5374853249` mm³（解析 `81535.5399670615`），`extrude=1`/`round=1`/`hole=5`，`saved_file_reloaded_and_verified=true`，`delivery_complete=true`，`disconnect_code=0`，PRT SHA256 `069293bf28d8a2b42c56095aec4b560e84442d62b93a680b55bb27e5a07f302b`（`build/mcp_integration_test.json`）。
- `tools/test_reference_contract.py`（协议模式）：exit 0，`success=true`、`protocol_verified=true`、`tool_count=111`。

## 种子包

`python tools/package_seeds.py --output build/release-0.37.1/MCP_CREO_MechDog-0.37.1-seed-library.zip --allow-record-mismatch` 首次构建得到摘要后回填 `docs/seed_package.json`；再用 `python tools/package_seeds.py --output build/release-0.37.1/confirm/MCP_CREO_MechDog-0.37.1-seed-library.zip` 重建确认，两次摘要一致：`69e9f82e20b25e1e37bd8b3c2e3de11d60fe7b088efbf551a1e244c2ac0b4d13`（24 个文件、9 个种子）。

## 单测证据

发布候选在 0.37.1 工作树上运行 `tools/test_unit.py`，全量 unittest 通过，0 失败、0 错误。具体 `run_id`、耗时与源码指纹取自本轮 `build/unit_test_report.json`（不随源码包分发）。

语言与格式检查以 `tools/dev_check.py --skip-unit --work-item BUG-151` 执行：`success=true`，lint 0、unformatted 0，离线验收 3/3 通过（`test_update_check`、`test_model_reconciliation`、`test_mcp`）。

## 未测范围

- Creo 9/12 实机未复验；本机无 Creo 9 SDK。
- 其余 8 个实机驱动脚本仅通过静态护栏、语法与 `dev_check` 验证，未逐一运行实机。
- WorkBuddy 外部黑盒验收未执行。

## 附件

- `MCP_CREO_MechDog-0.37.1-source.zip`
- `MCP_CREO_MechDog-0.37.1-source.zip.sha256`
- `MCP_CREO_MechDog-0.37.1-seed-library.zip`
- `MCP_CREO_MechDog-0.37.1-seed-library.zip.sha256`

种子包 SHA256 为 `69e9f82e20b25e1e37bd8b3c2e3de11d60fe7b088efbf551a1e244c2ac0b4d13`。源码包摘要记录在同名 sidecar 中，两份 sidecar 分别记录对应 ZIP 的实际 SHA256。

## 逐 ID 状态核对

| ID | 交付版本 | 实际 Release | 技术状态 | 卡首页 | 主台账 | 差异说明 |
| --- | --- | --- | --- | --- | --- | --- |
| [BUG-151](../work-items/BUG-151.md) | 0.37.1 | v0.37.1 | 已完成 | 已完成（0.36.1 协议契约修复；0.37.1 补齐实机启动等待、离线门禁、全模式实机验收与其余脚本分页漂移清理） | 已完成（0.36.1 协议契约修复；0.37.1 实机与全链路收口） | 0.36.1 与 0.37.1 合并收口；Creo 9/12 与 WorkBuddy 未测 |

## 远端核对

发布后执行，当前未验证。[GitHub Release](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.37.1) 附件字节、摘要与环境侧发布通道发布后补记于本节与[发布后核对](../development/RELEASE-POSTCHECK-2026-11-07.md)。
