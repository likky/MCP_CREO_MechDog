# 0.26.0 发布记录

- 版本：`0.26.0`（MINOR，部分交付）
- 日期：2026-11-16
- 版本说明：[RELEASE_NOTES_0.26.0](../RELEASE_NOTES_0.26.0.md)
- 主台账：[BACKLOG](../BACKLOG.md)
- 工作卡：[DEV-091](../work-items/DEV-091.md)
- 受测提交：本记录所在 `main` 提交（标签 `v0.26.0` 的对象与提交号只登记在 `main` 的[POSTCHECK](../development/RELEASE-POSTCHECK-2026-11-07.md) `## v0.26.0` 段）
- 与上一版本的关系：上一版本：0.25.0（`v0.25.0`，提交 `38bee48692d67d7f962d21ad713abbaa821c2fa7`），本版在其之上合入 0.25.0 四份反馈的已完成部分

## 包内容对照（相对 0.25.0）

| 项 | 0.25.0 | 0.26.0 | 说明 |
| --- | --- | --- | --- |
| 公开工具 | 108 | 108 | 无新增工具 |
| 首壁方向 | 只回执 frame/envelope | 新增 `expected_width_direction_world`、`width_direction_tolerance_deg` 与方向冲突拒绝 | 回执增 `width_direction_world`、`width_expected`、`center_of_mass_mm` |
| 边选择器 | `endpoints_mm`、`center_mm`/`radius_mm`/`axis` | 增加单独 `point_mm` 与圆边 `point_mm` 角度过滤 | 圆边多段拆分可唯一命中 |
| 面选择器 | 按点/轴/半径/中心 | `points_mm` 必须落在面片包围盒内 | 同轴圆柱/大平面拆分的多命中被消除 |
| 装配约束 | `coincident`/`concentric` 只收面 ID | 接受 `geometry_selector`，`concentric` 必须 `radius_mm` | 原生解析后复核真实平面/圆柱 |
| 区域签名 | 无 | 新增 `region_selection` 解析与唯一匹配 | 未接 `ExtrudeOp`，能力不开放 |
| 发布门禁 | 状态/链接/记录门禁 | 交付快照、逐 ID 交付列、完成档案、发布前后证据、审定 TXT | 只前向适用，不回改旧包 |
| 种子库 | 9 个种子 | 9 个种子 | `compatible_server_version=0.26.0` |

## 验证

- 环境：Windows x64、Python 3.12、Creo 12.4.0.0（`release_numeric=44`）与匹配 Toolkit SDK、MSVC x64。
- 离线：`tools/dev_check.py` 全量单测通过、`lint_findings=0`、`unformatted_files=0`；`bridge.py build` 退出码 0。
- 文档与门禁：`tools/check_release_records.py --version 0.26.0` 通过；`tools/check_backlog_counts.py` 一致；`tools/package.py` 的四附件门禁与发布记录门禁通过。
- 实机：M1 方向断言与拒绝、A0 单点直边/圆边、A1 装配选择器，逐项回执见[实机验收](../development/LIVE-ACCEPTANCE-0250-2026-11-16.md)；三次用例均保存重载通过。
- 未测：A2 的 61 条约束、Arm2 完整装配逐条对照、61 条边锚点、G1 区域切除、G2 实机、Creo 10/9 与 WorkBuddy 黑盒。

## 逐 ID 状态核对

成员：本版交付 6 个 ID，均为部分交付；剩余范围写在各自工作卡首页，并集中登记在[交接文档](../development/HANDOFF-0250-2026-11-16.md)。

| ID / 工作卡 | 技术状态 | 交付版本 | 剩余范围 | 卡首页 | 主台账 | 差异说明 | 版本说明 | 开发入口 | 实际 Release |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [DEV-083](../work-items/DEV-083.md) | 部分交付，剩余待验收 | 0.26.0 | 0.25.0 反馈续项未实机；历史包不回改 | 部分交付，剩余待验收 | 部分交付，剩余待验收 | 无 | 已列入 | 已列入 | v0.26.0 |
| [DEV-090](../work-items/DEV-090.md) | 部分交付，剩余待验收 | 0.26.0 | G2 仅静态查证；多约束、`parallel`/`distance`、T7 实测未做 | 部分交付，剩余待验收 | 部分交付，剩余待验收 | 无 | 已列入 | 已列入 | v0.26.0 |
| [DEV-091](../work-items/DEV-091.md) | 部分交付，剩余待验收 | 0.26.0 | A2、Arm2 完整装配、G1 原生选区未验 | 部分交付，剩余待验收 | 部分交付，剩余待验收 | 无 | 已列入 | 已列入 | v0.26.0 |
| [BUG-129](../work-items/BUG-129.md) | 部分交付，剩余待验收 | 0.26.0 | Arm2 完整装配逐条对照与 placement 契约未做 | 部分交付，剩余待验收 | 部分交付，剩余待验收 | 无 | 已列入 | 已列入 | v0.26.0 |
| [FEAT-068](../work-items/FEAT-068.md) | 部分交付，剩余待验收 | 0.26.0 | `Hom n7/n8` 倒角邻面与 61 条边锚点未验 | 部分交付，剩余待验收 | 部分交付，剩余待验收 | 无 | 已列入 | 已列入 | v0.26.0 |
| [FEAT-069](../work-items/FEAT-069.md) | 部分交付，剩余待验收 | 0.26.0 | 原生选区创建、切除输出侧与保存重开未证 | 部分交付，剩余待验收 | 部分交付，剩余待验收 | 无 | 已列入 | 已列入 | v0.26.0 |

## 未纳入本版

- A2 的 61 条 `[B-MATE]`：缺增强版 TXT 与测试机 `creo_plans_v0250`，不近似、不补造。
- Arm2 完整装配与 61 条边锚点批量验收：只有独立 YZ 首壁与合成边/面用例。
- G1 区域切除：原生“选中已有区域”的接口未找到。
- G2 圆角：`PRO_ROUND_CURV_CONTINUOUS` 的元素表未定义，未做单变量实机对照。

## 发布核对

本版发布四个附件（逐个列出，不使用通配）：

- `MCP_CREO_MechDog-0.26.0-source.zip`
- `MCP_CREO_MechDog-0.26.0-source.zip.sha256`（源码包摘要记录在同名 sidecar 中，一行 `<64 位 SHA256>  文件名`）
- `MCP_CREO_MechDog-0.26.0-seed-library.zip`
- `MCP_CREO_MechDog-0.26.0-seed-library.zip.sha256`（种子包摘要同样在 sidecar 中）

- 种子包 SHA256：`b16328fa2f114dcd3f5f520645e63a68752c9a3e1dd049f5a7f778fedd899d5c`（24 个文件、9 个种子，与 `docs/seed_package.json` 一致，重建一次摘要不变）。
- 源码包：由本版合入 `main` 的提交源码构建，`tools/package.py` 的四附件门禁与发布记录门禁均通过；字节数与 SHA256 见同名 sidecar，不写入包内。
- Release：<https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.26.0>。
- 发布后核对：发布后执行，当前未验证。冻结快照的 `remote_verification` 为 `pending`；实际 Release id、发布时间、标签对象与四附件摘要只追加到 `main` 的[POSTCHECK](../development/RELEASE-POSTCHECK-2026-11-07.md)，不改写已冻结包。
- 本版原生修改 `native/base_flange.cpp`、`native/geometry_selectors.cpp`、`native/advanced.cpp`、`native/generic.cpp`，升级后必须重编译 worker 并重启 MCP 连接器。

## 相对上一正式包核对（上一版本：0.25.0）

| 项目 | 上一版 | 本版 | 结论 / 注册影响 |
| --- | --- | --- | --- |
| native/third_party 原字节（含 json.hpp、第三方许可） | 未改 | 未改 | 无 |
| 回调指纹（sha256-repo-lf-v1） | 未改 | 未改 | 无 |
| loader DLL SHA256 | 未改 | 未改 | 无 |
| callback DLL SHA256 | 未改 | 未改 | 无 |
| worker SHA256 | 0.25.0 构建 | 本版修改四个原生源文件 | 必须重新编译 worker（`bridge.py build`） |
| protk.dat / 注册表路径 | 未改 | 未改 | 无需重新注册 |
| 实际注册影响（未变 / 需重新注册 / 需迁移 / 需重启） | — | — | 仅需重编译并重启 MCP 连接器 |
