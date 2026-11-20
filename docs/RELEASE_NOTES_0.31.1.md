# MCP_CREO_MechDog 0.31.1

一句话：把本机实机操作从“每次确认”改为常设授权——评估、启动、重启、卡死恢复和界面操作可以直接做，同时保留数据与已发布产物不可改写的边界。

- 类型：PATCH（工程规则/文档变更，无代码与原生改动）
- 日期：2026-11-19
- 公开工具：**109 个**（不变）
- 上一版本：0.31.0
- 主台账：[BACKLOG](BACKLOG.md) · 发布记录：[RELEASE-0.31.1](validation/RELEASE-0.31.1.md)

## 变更内容

- `AGENTS.md` 的实机联调补充改为 **2026-11-19 常设授权**：无需逐次征求确认，即可新建 Toolkit 连接、启动或重启 Creo 与 nmsd、结束卡死或异常的 Creo/worker 进程、确认后清理残留 `toolkit.lock` 与 unknown 保护状态、编译执行器、建模、GUI 界面操作（含坐标点击与计算机使用）以及几何/保存重载验收。
- 授权自动适用于后续会话，不再按次或按范围重新确认；`docs/DEVELOPMENT.md` 引用的“实机确认制”表述同步改为“实机常设授权”。
- 数据边界保持不变：不得删除或改写用户模型、历史证据与已发布产物；清理锁或结束进程前先确认无残留 worker，并在证据中记录原因。
- Toolkit 单通道、busy 立即拒绝、revision 保护、保存重载核验等既有边界不变；开发者单测与 WorkBuddy 黑盒仍分开记录。

## 行为变化与升级注意

1. 这是规则变更，服务行为、工具数量、种子内容与回调载荷均未改；升级不需要重新编译执行器或重新部署回调。
2. 种子库 `compatible_server_version` 同步为 `0.31.1`，与 0.31.0 的种子包不通用。
3. 本次改动不涉及 `resident_panel`、`surface_loft` 或回执字段。

## 验证

- 本次只改 `AGENTS.md` 与版本文档，未改 Python/原生源码；全量 unittest 与 `tools/dev_check.py --skip-unit` 结果见发布记录。
- 无 Creo 实机验收项（规则/文档变更）。

## 仍未验（本版不声称）

- 任务 5 接缝 G1 仍为历史基线（最大 6.28°，判据 0.5°），未在本版重测。
- WorkBuddy 黑盒未重跑；Creo 10 release 42 之外版本不外推。

## 源码包与校验

本版发布四个附件（逐个列出，不使用通配）：

- `MCP_CREO_MechDog-0.31.1-source.zip`
- `MCP_CREO_MechDog-0.31.1-source.zip.sha256`（源码包摘要记录在同名 sidecar 中，一行 `<64 位 SHA256>  文件名`）
- `MCP_CREO_MechDog-0.31.1-seed-library.zip`
- `MCP_CREO_MechDog-0.31.1-seed-library.zip.sha256`（种子包摘要同样在 sidecar 中）

- 种子包：24 个文件、9 个种子，SHA256 `ca5a61b5fb45cae7b73c19d1cff9017a2158728ad3fa94171005ea94a15b5b48`，两次构建摘要一致，与 `docs/seed_package.json` 一致。
- Release：发布后执行，当前未验证；当前 `docs/releases/0.31.1.json` 的 `remote_verification` 为 `pending`。
