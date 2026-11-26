# 0.33.0 发布记录

- 版本：`0.33.0`（MINOR，部分交付）
- 日期：2026-11-20
- 版本说明：[release-notes/RELEASE_NOTES_0.33.0](../release-notes/RELEASE_NOTES_0.33.0.md)
- 主台账：[BACKLOG](../BACKLOG.md) · 工作卡：[BUG-134](../work-items/BUG-134.md) · [BUG-135](../work-items/BUG-135.md) · [BUG-136](../work-items/BUG-136.md) · [DEV-095](../work-items/DEV-095.md) · [DEV-096](../work-items/DEV-096.md) · 交付快照：[0.33.0](../releases/0.33.0.json)
- 受测提交：`613cc4bc3424ce066fb255d5781aa157b23f35a3`（`main`），标签对象 `629f5db8acc9c09bb68f2bd4486d751a1d45cbca` 指向该提交
- 与上一版本的关系：上一版本：0.32.0（`v0.32.0`，提交 `539a6b0145d84a9c15e538df6601d9538ecfd035`），本版在其之上交付 0.31.1 反馈批的面板 -8 修复、元素树完成旁路、装配约束类型文案、面板可信度披露与发布记录门禁交叉校验

## 包内容对照（相对 0.32.0）

| 项 | 0.32.0 | 0.33.0 | 说明 |
| --- | --- | --- | --- |
| 公开工具 | 109 | 109 | 不变 |
| `resident_panel` 开面板 | `ProMdlCurrentGet` 恒 -8 时失败 | 优先用 `ProMdlInit` 的 board，并先 `ProMdlDisplay` 前置 | 回执写 `panel_preopen` 码值 |
| 面板回执 | 无模型名 | 面板块带 `model_name` | 与作业目标模型一致 |
| `creo_surface_loft` | 提取 -18 无条件回滚 | 可选 `accept_unverified_completion` 保留并如实检查 | 默认 `false`，旧计划字节不变 |
| 元素树回执 | 只报失败码 | 另加三次补全尝试与 `completion_verified_by` | 失败仍回滚 |
| 装配约束文案 | `mate_offset` 被当圆柱面要求 | 按 `mate`/`align` 平面、`insert` 圆柱、`csys` 跳过 | 写实际类型 |
| 面板准入 | 只拒绝 | 额外披露 `unverified_bindings=["payload_sha256"]` | 只披露不拒绝 |
| 发布记录门禁 | 只查 `previous_release_commit` 形状 | 与“上一版本”行提交号及标签三方交叉 | 无 `.git` 时跳过标签核对 |
| 种子库 | 9 个种子 | 9 个种子 | `compatible_server_version=0.33.0` |
| 原生/worker/loader | 0.32.0 构建 | 本版有原生改动 | 需重新编译 |

## 验证

- 环境：Windows x64、Python 3.12.14、MSVC x64 构建工具、本机 **Creo 10.0.0.0 / `release_numeric=42`** 与匹配 Toolkit SDK（此前文档写的 12.4 有误；Creo 12.4 未安装、未复测）。
- 离线：`python bridge.py build` exit 0；全量单测通过（6 项跳过）；`ruff check` 与 `ruff format --check` 通过。
- 实机（按 2026-11-19 常设授权执行；未删除或改写用户模型与历史证据）：
  - 面板作业 `7bb73fa98a764818843e85c2e9220b3a`（`acc_panel_20261120g`，rev 1）`succeeded`、保存重载 true；`ProMdlCurrentGet` 及显示/窗口前置码全为 0，无 -8；quilt 60 / feature 54、单面、面积 1052.4223235864151 mm²、`geometry_check.verified=true`。
  - 元素树旁路作业 `21535fea4d0f408bb74c2a0ccc08a99d` 在 Creo 10 上以 `SURFACE_LOFT_ACCEPT_INCOMPLETE` 失败并清理新模型（`absence_verified=true`）；该宿主无法补全几何，只能走 resident_panel。
  - `tools\test_t09_assembly_replay.py --live`（`build/t09_assembly_replay_20261120.json`）六类约束全部通过；圆柱面 `mate_offset`（`7e748410…`）、平面 `insert`（`d7ddf3cb…`）按类型被拒，`csys`（`54ab2895…`）成功且保存重载 true。
  - `host_release.release_numeric=42` 在健康度重写后保留；面板准入 `unverified_bindings=["payload_sha256"]`（认证 `3c80bf15…` 对部署 `41ad8198…`），作业仍成功。
- 发布资料：`tools/check_release_records.py --version 0.33.0` 与 `tools/package.py` 的四附件/发布记录门禁在打包时执行。
- 证据：`docs/work-items/BUG-134.md`、`BUG-135.md`、`BUG-136.md`、`DEV-095.md` 内逐项记录，运行报告保留在忽略的 `build/`。

## 逐 ID 状态核对

成员：本版交付 5 个 ID，均为部分交付（软件层与主场景实机完成；Creo 12.4 及其余路径未验）。

| ID / 工作卡 | 技术状态 | 交付版本 | 剩余范围 | 卡首页 | 主台账 | 差异说明 | 版本说明 | 开发入口 | 实际 Release |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [BUG-134](../work-items/BUG-134.md) | 部分交付 0.33.0（本机 Creo 10 面板主场景通过，无 -8，几何与保存重载通过） | 0.33.0 | Creo 12.4 复测、`PANEL_MODEL_UNAVAILABLE` 失败构造、WorkBuddy 黑盒 | 部分交付 0.33.0（本机 Creo 10 面板主场景通过；Creo 12.4 与失败路径未验） | 已有修复但待验收 | — | 已列入 | 已列入 | v0.33.0 |
| [BUG-135](../work-items/BUG-135.md) | 部分交付 0.33.0（旁路已可控并如实失败；Creo 10 内核无法补全） | 0.33.0 | Creo 12.4 成功路径、Creo 9、WorkBuddy 黑盒 | 部分交付 0.33.0（旁路已可控；Creo 12.4 成功路径未验） | 已有修复但待验收 | — | 已列入 | 已列入 | v0.33.0 |
| [BUG-136](../work-items/BUG-136.md) | 部分交付 0.33.0（本机 Creo 10 六类约束实机通过，文案按类型） | 0.33.0 | Creo 12.4、Arm7 原模型 60 条配合全量、WorkBuddy 黑盒 | 部分交付 0.33.0（六类约束实机通过；Creo 12.4 与 Arm7 原模型未验） | 已有修复但待验收 | — | 已列入 | 已列入 | v0.33.0 |
| [DEV-095](../work-items/DEV-095.md) | 部分交付 0.33.0（`host_release` 与 `payload_sha256` 披露本机 Creo 10 实测） | 0.33.0 | Creo 12.4、认证 payload 与运行中 DLL 的实时绑定证明 | 部分交付 0.33.0（披露本机 Creo 10 实测；Creo 12.4 未验） | 已有修复但待验收 | — | 已列入 | 已列入 | v0.33.0 |
| [DEV-096](../work-items/DEV-096.md) | 部分交付 0.33.0（交叉校验与标签核对已实施，本版发布记录实跑通过） | 0.33.0 | 负例复核与历史发布记录回归 | 部分交付 0.33.0（交叉校验已实施；负例与历史记录回归未验） | 已有修复但待验收 | — | 已列入 | 已列入 | v0.33.0 |

## 未纳入本版

- Creo 12.4 与 Creo 9 的实机复测；`PANEL_MODEL_UNAVAILABLE` 失败路径（未构造 board 为空的夹具）。
- 元素树路线在 Creo 10 上的“保留件再生”——该宿主内核拒绝补全几何，本版只证明旁路可控且失败会清理。
- `unverified_bindings` 只证明披露生效；认证 payload 与运行中 DLL 的实时绑定证明未做。
- Arm7 原模型 60 条配合全量、WorkBuddy 黑盒、非 mm 单位。

## 发布核对

本版发布四个附件（逐个列出，不使用通配）：

- `MCP_CREO_MechDog-0.33.0-source.zip`
- `MCP_CREO_MechDog-0.33.0-source.zip.sha256`（源码包摘要记录在同名 sidecar 中，一行 `<64 位 SHA256>  文件名`）
- `MCP_CREO_MechDog-0.33.0-seed-library.zip`
- `MCP_CREO_MechDog-0.33.0-seed-library.zip.sha256`（种子包摘要同样在 sidecar 中）

- 种子包 SHA256：`d53682cc02d3089490977fcac06afea65113e9369b72f7df4c26bd756215cda7`（24 个文件、9 个种子，两次构建摘要一致，与 `docs/seed_package.json` 一致）。
- 源码包：由本版合入 `main` 的提交源码构建；字节数与 SHA256 见同名 sidecar，不写入包内。
- Release：`https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.33.0`（2026-11-20 12:38Z 发布，非 draft、非 prerelease；`tools\check_release_assets.py --tag v0.33.0` → exit 0，四附件齐全且两个 sidecar 与对应 ZIP 摘要一致，逐项摘要见 `main` 的 POSTCHECK `## v0.33.0` 段）。
