# 0.31.1 发布记录

- 版本：`0.31.1`（PATCH，工程规则）
- 日期：2026-11-19
- 版本说明：[release-notes/RELEASE_NOTES_0.31.1](../release-notes/RELEASE_NOTES_0.31.1.md)
- 主台账：[BACKLOG](../BACKLOG.md) · 完成档案：[BACKLOG_COMPLETED](../BACKLOG_COMPLETED.md) · 工作卡：[DEV-093](../archive/work-items/DEV-093.md) · 交付快照：[0.31.1](../releases/0.31.1.json)
- 与上一版本的关系：上一版本 0.31.0（`v0.31.0`，提交 `daadbe71869ae4b394a9298970a8d9ec6608bc91`）；本版在其之上只改实机联调规则与版本元数据

## 包内容对照（相对 0.31.0）

| 项 | 0.31.0 | 0.31.1 | 说明 |
| --- | --- | --- | --- |
| 公开工具 | 109 | 109 | 不变 |
| Python/原生源码 | BUG-120 交付版 | 未改 | 无代码或原生改动 |
| `AGENTS.md` 实机规则 | 2026-11-09 按次确认 | 2026-11-19 常设授权 | 启动/重启/结束进程/清锁/GUI 操作无需逐次确认 |
| 数据边界 | 不可改写用户模型与历史证据 | 不变 | 已发布产物也不可改写 |
| 种子库 | 9 个种子 | 9 个种子 | `compatible_server_version=0.31.1` |

## 验证

- 本次仅改 `AGENTS.md` 与版本文档，未改 Python/原生源码；不涉及 Creo 实机验收项。
- 全量 unittest：4078 项通过（6 跳过），见本节“离线结果”。
- `tools/check_release_records.py --version 0.31.1` 与 `tools/package.py` 的发布门禁通过。

## 逐 ID 状态核对

成员：本版交付 1 个工程条目，已归档 [DEV-093](../archive/work-items/DEV-093.md)。

| ID / 工作卡 | 技术状态 | 交付版本 | 剩余范围 | 卡首页 | 主台账 | 差异说明 | 版本说明 | 开发入口 | 实际 Release |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [DEV-093](../archive/work-items/DEV-093.md) | 已完成（0.31.1 交付） | 0.31.1 | 无 | 已完成（0.31.1 交付） | 已完成（0.31.1 交付） | — | 已列入 | 已列入 | v0.31.1 |

## 未纳入本版

- 任务 5 接缝 G1 仍为历史基线（最大 6.28°，判据 0.5°），不在本版范围。
- WorkBuddy 黑盒与本机之外的 Creo 版本不因规则变更重新验证。

## 发布核对

本版发布四个附件（逐个列出，不使用通配）：

- `MCP_CREO_MechDog-0.31.1-source.zip`
- `MCP_CREO_MechDog-0.31.1-source.zip.sha256`（源码包摘要记录在同名 sidecar 中，一行 `<64 位 SHA256>  文件名`）
- `MCP_CREO_MechDog-0.31.1-seed-library.zip`
- `MCP_CREO_MechDog-0.31.1-seed-library.zip.sha256`（种子包摘要同样在 sidecar 中）

- 种子包 SHA256：`ca5a61b5fb45cae7b73c19d1cff9017a2158728ad3fa94171005ea94a15b5b48`（24 个文件、9 个种子，两次构建摘要一致，与 `docs/seed_package.json` 一致）。
- 源码包：由本版合入 `main` 的提交源码构建；SHA256 `6eea649b3b1564d7fe47576f0b162747c6ca28cbc890607f2077aec6ed7fd18d`（11 114 799 字节、2167 个文件，摘要记录在同名 sidecar 中）。
- Release：<https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.31.1>（已发布，非 draft、非 prerelease，target `main`；id `451362319`，`published_at=2026-11-19T13:10:16Z`）。
- 发布后核对（2026-11-19 21:11 +08:00 / 13:11Z）：gh 下载四附件后 `tools\check_release_assets.py --tag v0.31.1 --version 0.31.1 --dir` → exit 0，「four assets present; both sidecars match」；附件列表与摘要见 POSTCHECK `## v0.31.1` 段。冻结包内副本仍为打包时点措辞（`remote_verification=pending`），不回写、不重发已发布附件。

## 相对上一正式包核对（上一版本：0.31.0）

| 项目 | 上一版 | 本版 | 结论 / 注册影响 |
| --- | --- | --- | --- |
| native/third_party 原字节 | 未改 | 未改 | 无 |
| Python/原生执行器与回调载荷 | 0.31.0 构建 | 未改 | 无需重编译或重新部署回调 |
| `AGENTS.md` | 按次确认 | 常设授权 | 只影响开发流程，不影响注册 |
| protk.dat / 注册表路径 | `build/blend_callback_protk.dat` | 同路径 | 无需迁移 |
| 实际注册影响（未变 / 需重新注册 / 需迁移 / 需重启） | — | — | 未变 |

## 离线结果

- 2026-11-19：全量 unittest **4078 项通过（6 跳过）**；`tools/dev_check.py --skip-unit` 通过（Ruff 0.17.0、clang-format 23.1.3）。
- `tools/check_backlog_counts.py` 一致（194/87/66/41）；`tools/check_release_records.py --version 0.31.1` 通过。
- 本版未改 Python/原生源码，未重新编译执行器或部署回调。
