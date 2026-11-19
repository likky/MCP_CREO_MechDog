# 0.28.0 发布记录

- 版本：`0.28.0`（MINOR，部分交付）
- 日期：2026-11-19
- 版本说明：[RELEASE_NOTES_0.28.0](../RELEASE_NOTES_0.28.0.md)
- 主台账：[BACKLOG](../BACKLOG.md) · 工作卡：[BUG-120](../work-items/BUG-120.md) · 交付快照：[0.28.0](../releases/0.28.0.json)
- 受测提交：本记录所在 `main` 提交（标签 `v0.28.0` 的对象与提交号只登记在 `main` 的[POSTCHECK](../development/RELEASE-POSTCHECK-2026-11-07.md) `## v0.28.0` 段）
- 与上一版本的关系：上一版本：0.27.0（`v0.27.0`，提交 `fc1efaefa68cda1c0b4d46849f18933c35050b64`），本版在其之上完成 BUG-120 的 Creo 10 resident_panel 路线、candidate-3 导线/点与两段式实体化，并同步发布资料

## 包内容对照（相对 0.27.0）

| 项 | 0.27.0 | 0.28.0 | 说明 |
| --- | --- | --- | --- |
| 公开工具 | 109 | 109 | 不变 |
| Creo 10 边界混合 | 元素树 `surface_loft` 受 `Extract=-18` 限制 | `creation_route="resident_panel"` 认证路线 | 面板选择、Done 括号与保存重载 |
| 第二方向/末端点 | 无 | candidate-3 导线/点与 11 位置上限 | 单特征“点+导线”仍再生失败 |
| 球鼻艏 | 无成型链路 | 两段式演示体镜像/合并/后盖/实体化 | 167543.67 mm³，轴对演示体 |
| WorkBuddy 黑盒 | 未做 | 面板链与实体化链两轮通过 | 6283.1853 mm³ |
| 种子库 | 9 个种子 | 9 个种子 | `compatible_server_version=0.28.0` |

## 验证

- 环境：Windows x64、Python 3.12.10、Creo 10.0.0.0 / `release_numeric=42` 与匹配 Toolkit SDK、MSVC x64。
- 离线：`tools/dev_check.py --work-item BUG-120` 通过，`lint_findings=0`、`unformatted_files=0`；全量单测 **4040 项通过（6 跳过）**；`bridge.py build` 退出码 0。
- 原生规则：`tools/test_panel_references.py`（`all rules hold`）与 `tools/test_panel_selection_state.py`（`protocol 4 rules hold`）通过。
- 实机（本机 Creo 10，用户当次授权）：
  - 2 截面 + 2 导线 `ce906e56…`（800.0 mm²）、+3 导线 `72aa7604…`（828.9745 mm²、4 边 120 mm）、2 截面 + 单点 `0bbcdae1…`（1301.2531 mm²、3 条开放边且点处无开放边界）、7 曲线 + 点 `034066fc…`（2643.27 mm²）、7 曲线 + 3 导线 `38cac400…`（2400.0 mm²、4 边 200 mm）。
  - 两段式球鼻艏：面板 `1292c88b…`（7/7）、`7a032a4e…`（3/3），合并/镜像/合并/后盖/合并/实体化 `2ae66ecf…`、`b799ba92…`、`a05b0533…`、`ea02d10a…`、`29c3f217…`、`36abbbe0…`；rev 9、体积 167543.67 mm³、质心 `(25.0002,0,0)`、零自由边、保存重载 true。
  - 11 位置“7 曲线 + 点 + 3 导线”与 10 位置“7 曲线 + 点 + 2 导线”：选择全成功、`codes` 全 0，Done 后 Creo 报“特征重新生成失败”，作业 `072544a6…`、`429c04ff…`、`47a4b069…` 在看门狗超时后 `unknown_outcome`；这是本版明确披露的边界。
- WorkBuddy 黑盒：面板链 `wb_te_panel`（`602b6ddb…`，rev 0→7）与实体化链 `wb_te_solid`（`de0ad937…`，rev 1→13，6283.1853 mm³）通过；闭合壳 4 面、bbox Y ±10.0208、密度不可读等偏差已记录。
- 文档与门禁：`tools/check_release_records.py --version 0.28.0` 通过；`tools/package.py` 的四附件门禁与发布记录门禁通过。

## 逐 ID 状态核对

成员：本版交付 1 个 ID，部分交付。

| ID / 工作卡 | 技术状态 | 交付版本 | 剩余范围 | 卡首页 | 主台账 | 差异说明 | 版本说明 | 开发入口 | 实际 Release |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [BUG-120](../work-items/BUG-120.md) | 部分交付 0.28.0（认证面板路线、candidate-3 导线/点、两段式实体与 WorkBuddy 黑盒已交付；11 位置点+导线未通过） | 0.28.0 | 11 位置“点+导线”单特征再生失败、真实船体剖面/非圆截面映射、Creo 9 运行期、`geometry_check` 回执缺口 | 部分交付 0.28.0 | 部分交付，面板/T-D/T-E 已通过；11 位置点+导线未通过 | — | 已列入 | 已列入 | v0.28.0 |

## 未纳入本版

- 11 位置“7 曲线 + 点 + 3 导线”的单特征几何；共享顶点/顶点的替代构造。
- 真实球鼻艏的非圆截面、真实导线拼合与最终船体外形。
- Creo 9 运行期与其他 Creo 版本；密度/质量与真实 UI 观察。
- 公开认证范围内的 guides/点/boundary_conditions/template 拒绝行为未由黑盒构造请求实测。

## 发布核对

本版发布四个附件（逐个列出，不使用通配）：

- `MCP_CREO_MechDog-0.28.0-source.zip`
- `MCP_CREO_MechDog-0.28.0-source.zip.sha256`（源码包摘要记录在同名 sidecar 中，一行 `<64 位 SHA256>  文件名`）
- `MCP_CREO_MechDog-0.28.0-seed-library.zip`
- `MCP_CREO_MechDog-0.28.0-seed-library.zip.sha256`（种子包摘要同样在 sidecar 中）

- 种子包 SHA256：`dfac1ec5b62a0a926d0debf1efaf77ab13cf627ee0c6318ff6993be5201aacf9`（24 个文件、9 个种子，与 `docs/seed_package.json` 一致，重建一次摘要不变）。
- 源码包：由本版合入 `main` 的提交源码构建，`tools/package.py` 的四附件门禁与发布记录门禁均通过；字节数与 SHA256 见同名 sidecar，不写入包内。
- Release：<https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.28.0>。
- 发布后核对：发布后执行，当前未验证；实际列表、标签指向、附件摘要与 `main` 提交只追加到[POSTCHECK](../development/RELEASE-POSTCHECK-2026-11-07.md) `## v0.28.0` 段，冻结包内副本不回写。
- 本版原生修改 `native/blend_sync.cpp`、`native/panel_protocol.h`、`native/panel_references.h`、`native/panel_references_sdk.h`、`native/panel_run.h`、`native/panel_selection_state.h`，升级后必须重编译 worker 并重启 MCP 连接器。

## 相对上一正式包核对（上一版本：0.27.0）

| 项目 | 上一版 | 本版 | 结论 / 注册影响 |
| --- | --- | --- | --- |
| native/third_party 原字节（含 json.hpp、第三方许可） | 未改 | 未改 | 无 |
| 回调指纹（sha256-repo-lf-v1） | `83ad907d…` | `83ad907d…` | 未变 |
| loader DLL SHA256 | `edceae2e…` | `edceae2e…` | 未变 |
| callback DLL SHA256 | 0.27.0 构建 | `3c80bf15…`（本版面板载荷） | 需重新部署并确认 `callback_status=ready` |
| worker SHA256 | 0.27.0 构建 | 本版重编译（`bridge.py build`） | 必须重编译 worker |
| protk.dat / 注册表路径 | `build/blend_callback_protk.dat` | 同路径 | 无需迁移 |
| 实际注册影响（未变 / 需重新注册 / 需迁移 / 需重启） | — | — | 需重新部署 panel 载荷、重编译 worker 并重启 Creo |
