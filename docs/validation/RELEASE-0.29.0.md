# 0.29.0 发布记录

- 版本：`0.29.0`（MINOR，部分交付）
- 日期：2026-11-19
- 版本说明：[RELEASE_NOTES_0.29.0](../RELEASE_NOTES_0.29.0.md)
- 主台账：[BACKLOG](../BACKLOG.md) · 工作卡：[BUG-120](../work-items/BUG-120.md) · 交付快照：[0.29.0](../releases/0.29.0.json)
- 受测提交：本记录所在 `main` 提交（标签 `v0.29.0` 的对象与提交号只登记在 `main` 的[POSTCHECK](../development/RELEASE-POSTCHECK-2026-11-07.md) `## v0.29.0` 段）
- 与上一版本的关系：上一版本：0.28.0（`v0.28.0`，提交 `e1ea2da3a6c62602855ce5d7fde3f5407e1dcfe4`），本版在其之上把 candidate-3 升为公开认证 profile、扩展 resident_panel 的公开输入范围并补准入前置拒绝

## 包内容对照（相对 0.28.0）

| 项 | 0.28.0 | 0.29.0 | 说明 |
| --- | --- | --- | --- |
| 公开工具 | 109 | 109 | 不变 |
| 认证 profile | `creo10-bbl-candidate-2` | `creo10-bbl-candidate-3` | candidate-3 是超集，candidate-2 保留独立认证 |
| 第一方向 | 2—8 条开放曲线 | 2—8 条曲线或首/末单点 | 点最多一个，只在首/末 |
| 第二方向 | 不公开 | 可选 2—8 条导线 | 最多 11 个位置 |
| 点 + 导线单特征 | 再生失败 | 仍再生失败 | 认证明确排除，使用两段式 |
| 无第二方向槽时的带导线请求 | 进入 worker 后 `PANEL_COMMAND_MISSING`、`unknown_outcome` + guard | 提交前拒绝，0 作业 | 准入修复 |
| 种子库 | 9 个种子 | 9 个种子 | `compatible_server_version=0.29.0` |
| 原生/worker/loader | 0.28.0 构建 | 未改 | 无需重编译 |

## 验证

- 环境：Windows x64、Python 3.12.10；实机证据来自本机 Creo 10.0.0.0 / `release_numeric=42` 与匹配 Toolkit SDK（0.28.0 期间，用户当次授权）。
- 离线：全量单测 **4045 项通过（6 项跳过）**；`ruff check` 与 `ruff format --check` 通过；`tools/dev_check.py --work-item BUG-120` 通过。
- 原生规则：`tools/test_panel_references.py`（`all rules hold`）通过；本版没有原生源码改动。
- 实机：本版未新增实机操作；认证记录 `creo10-bbl-2026-11-19.json` 绑定 2+2（`ce906e56…`，800.0 mm²）、2+3（`72aa7604…`，828.9745 mm²）、2+末端点（`0bbcdae1…`，1301.2531 mm²）、7+3（`38cac400…`，2400.0 mm²）与两段式球鼻艏实体（`1292c88b…`/`7a032a4e…`，167543.67 mm³），保存重载均为 true。
- 文档与门禁：`tools/check_release_records.py --version 0.29.0` 通过；`tools/package.py` 的四附件门禁与发布记录门禁通过。
- 源码包解压：包内 `test_panel_profiles`、`test_surface_loft_panel_admission`、`test_release_integrity` 共 115 项通过（缺少仓库验收原件时跳过 1 项）；全量包内单测受无 `.git`/`.venv`/`build` 限制，不作为本版结论。

## 逐 ID 状态核对

成员：本版交付 1 个 ID，部分交付。

| ID / 工作卡 | 技术状态 | 交付版本 | 剩余范围 | 卡首页 | 主台账 | 差异说明 | 版本说明 | 开发入口 | 实际 Release |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [BUG-120](../work-items/BUG-120.md) | 部分交付 0.29.0（candidate-3 已认证：导线/末端点/11 位置与准入前置拒绝；单特征点+导线仍不可再生） | 0.29.0 | 11 位置“点+导线”单特征再生失败、真实船体剖面/非圆截面映射、Creo 9 运行期、`geometry_check` 回执缺口、新 profile 的 WorkBuddy 黑盒 | 部分交付 0.29.0 | 部分交付，candidate-3 已认证；11 位置点+导线未通过 | — | 已列入 | 已列入 | v0.29.0 |

## 未纳入本版

- 11 位置“7 曲线 + 点 + 3 导线”的单特征几何；共享顶点的替代构造。
- 真实球鼻艏的非圆截面、真实导线拼合与最终船体外形。
- 用新认证 profile 重跑的 WorkBuddy 黑盒。
- Creo 9 运行期与其他 Creo 版本；密度/质量与真实 UI 观察。

## 发布核对

本版发布四个附件（逐个列出，不使用通配）：

- `MCP_CREO_MechDog-0.29.0-source.zip`
- `MCP_CREO_MechDog-0.29.0-source.zip.sha256`（源码包摘要记录在同名 sidecar 中，一行 `<64 位 SHA256>  文件名`）
- `MCP_CREO_MechDog-0.29.0-seed-library.zip`
- `MCP_CREO_MechDog-0.29.0-seed-library.zip.sha256`（种子包摘要同样在 sidecar 中）

- 种子包 SHA256：`cd3a5d5ec11928670f9e35aa6cdc2deb06314ce94ab9b7d8df5825af34ae8db3`（24 个文件、9 个种子，与 `docs/seed_package.json` 一致，重建一次摘要不变）。
- 源码包：由本版合入 `main` 的提交源码构建，`tools/package.py` 的四附件门禁与发布记录门禁均通过；字节数与 SHA256 见同名 sidecar，不写入包内。
- Release：<https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.29.0>。
- 发布后核对：发布后执行，当前未验证；`docs/releases/0.29.0.json` 的 `remote_verification` 在打包时为 `pending`，远端列表、标签指向与附件摘要只追加到 `main` 的 [POSTCHECK](../development/RELEASE-POSTCHECK-2026-11-07.md) `## v0.29.0` 段。
- 本版没有原生源码改动；`native/`、worker、loader 与面板载荷与 0.28.0 相同，升级只需更新源码、重启 MCP 连接器并换用新种子包。

## 相对上一正式包核对（上一版本：0.28.0）

| 项目 | 上一版 | 本版 | 结论 / 注册影响 |
| --- | --- | --- | --- |
| native/third_party 原字节（含 json.hpp、第三方许可） | 未改 | 未改 | 无 |
| 回调指纹（sha256-repo-lf-v1） | `83ad907d…` | `83ad907d…` | 未变 |
| loader DLL SHA256 | `edceae2e…` | `edceae2e…` | 未变 |
| callback DLL SHA256 | `3c80bf15…` | `3c80bf15…` | 未变 |
| worker SHA256 | 0.28.0 构建 | 同 0.28.0 | 无需重编译 |
| protk.dat / 注册表路径 | `build/blend_callback_protk.dat` | 同路径 | 无需迁移 |
| 实际注册影响（未变 / 需重新注册 / 需迁移 / 需重启） | — | — | 无需重新部署；只需重启 MCP 连接器并换种子包 |
