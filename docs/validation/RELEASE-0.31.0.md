# 0.31.0 发布记录

- 版本：`0.31.0`（MINOR，部分交付）
- 日期：2026-11-19
- 版本说明：[RELEASE_NOTES_0.31.0](../RELEASE_NOTES_0.31.0.md)
- 主台账：[BACKLOG](../BACKLOG.md) · 工作卡：[BUG-120](../work-items/BUG-120.md) · 交付快照：[0.31.0](../releases/0.31.0.json)
- 受测提交：本记录所在开发分支的提交（标签 `v0.31.0` 的对象与提交号只在合入 `main` 后登记到 `main` 的 [POSTCHECK](../development/RELEASE-POSTCHECK-2026-11-07.md) `## v0.31.0` 段）
- 与上一版本的关系：上一版本 0.30.0（`v0.30.0`，提交 `1c20f550571f15820dba6816f4efbab060197a4d`），本版在其之上补齐 BUG-120 的导线预检与建面回执，并把任务 5 接缝单独排期

## 包内容对照（相对 0.30.0）

| 项 | 0.30.0 | 0.31.0 | 说明 |
| --- | --- | --- | --- |
| 公开工具 | 109 | 109 | 不变 |
| `resident_panel` 截面/导线写法 | 接受裸标签字符串 | 必须 `{label, open_confirmed:true}` | 裸标签在建作业前拒绝 |
| 开面板前诊断 | 无 | 新增 `curve_fit_check`，7×3=21 对截面×导线 | 只报告，不新增拒绝规则 |
| 成功回执 | 面积/开闭 | 另加唯一新增面组关联与 `geometry_check.verified` 证据链 | `selection_record` 仍为 null |
| 种子库 | 9 个种子 | 9 个种子 | `compatible_server_version=0.31.0` |
| 原生/worker/loader | 0.30.0 构建 | 本版有原生改动（`panel_fit.h`/`panel_run.h`/`generic.cpp`） | 需重新编译并重新加载回调 |

## 验证

- 环境：Windows x64、Python 3.12、MSVC x64 构建工具、本机 Creo 10.0.0.0 / release 42 / 匹配 Toolkit SDK；实机按用户当次确认执行。
- 离线：`bridge.py build` exit 0；全量 unittest **4078 项通过（6 跳过）**；`tools/test_panel_fit.py` 通过；`tools/dev_check.py --skip-unit`（Ruff + clang-format）通过。
- 实机 B：作业 `9d854dd0…` → `66a65ab2…` → 面板放样 `744abfff…`，模型 `ceda66c1…`、rev 3、quilt 142/feature 136、面积 **46,555,189.24528535 mm²**、21/21 对 `crossing`、独立 4 条开放边 **11916.01893/11924.14083/4612.01158/2126.66969 mm**、`geometry_check.verified=true`、保存重载 true、PRT SHA256 `d186b587…`。
- 实机 C：在 B 的 PRT 副本上采用 `3dbf8e89…`，`9a3b1f50…`→`61f1430f…`→`660a10ee…`→`48d9e87c…`→`a2888e30…`→`e228c80f…`→`2a987299…`→`c41a497d…`；模型 `e56e5f26…`、rev 9、一个活动含材料实体、体积 **55,087,038,135.823044 mm³**、5 面/14 边/0 开放边、58 特征、保存重载 true、PRT SHA256 `22223de9…`。
- 构建身份：实机跑在 worker `9d353a47…` / source digest `058e8cdb…` / 面板载荷 `eba1b25b…` / loader `9e90d705…`；收尾把 `native/panel_fit.h` 加入 `bridge.callback_relatives` 后同源重建为 worker `39fafb98…` / 载荷 `5dc6b5a4…`（仅构建依赖清单变化，运行代码未变，未重跑 B/C）。
- 证据：`build/bug120_task4/`（`B_report.json`、`C_report.json` 与两份 PRT 副本）；完整日志保留在忽略的 `build/`。
- 发布资料：`tools/check_release_records.py --version 0.31.0` 通过；`tools/package.py` 的四附件门禁在打包时执行。

## 逐 ID 状态核对

成员：本版交付 1 个 ID，为部分交付（任务 1–4 已交付，任务 5 单独排期）。

| ID / 工作卡 | 技术状态 | 交付版本 | 剩余范围 | 卡首页 | 主台账 | 差异说明 | 版本说明 | 开发入口 | 实际 Release |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [BUG-120](../work-items/BUG-120.md) | 部分交付 0.31.0（任务 1–4 已交付，任务 5 接缝单独排期） | 0.31.0 | 任务 5 接缝 G1（当前最大 6.28°，未达 0.5° 判据）；真实船体非圆剖面、STL 与 WorkBuddy 黑盒 | 部分交付 0.31.0（任务 1–4 已交付，任务 5 接缝单独排期） | 部分交付 0.31.0（任务 1–4 已交付，任务 5 接缝单独排期） | — | 已列入 | 已列入 | v0.31.0 |

## 未纳入本版

- 任务 5 接缝 G1 光顺（当前 6.28°，按用户要求单独排期，不阻塞本批）。
- `selection_record` 载荷写入（本版仍为 null，几何证据改由 `curve_fit_check`/`geometry_check` 与保存重载测量提供）。
- 真实船体非圆剖面、STL 导出与自动加载回调。
- WorkBuddy 黑盒；Creo 10 release 42 之外版本。

## 发布核对

本版发布四个附件（逐个列出，不使用通配）：

- `MCP_CREO_MechDog-0.31.0-source.zip`
- `MCP_CREO_MechDog-0.31.0-source.zip.sha256`（源码包摘要记录在同名 sidecar 中，一行 `<64 位 SHA256>  文件名`）
- `MCP_CREO_MechDog-0.31.0-seed-library.zip`
- `MCP_CREO_MechDog-0.31.0-seed-library.zip.sha256`（种子包摘要同样在 sidecar 中）

- 种子包 SHA256：`fef385db303722c3279b9fc6525dc8fd06717b6d67f99d6128c587d04a2e8356`（24 个文件、9 个种子，两次构建摘要一致，与 `docs/seed_package.json` 一致）。
- 源码包：由本版合入 `main` 的提交源码构建；字节数与 SHA256 见同名 sidecar，不写入包内。
- Release：<https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.31.0>（发布后执行，当前未验证，非 draft 状态以发布后 POSTCHECK 为准）。
- 冻结包内记录仍为 `pending`；发布后须执行 `tools\check_release_assets.py --tag v0.31.0`（四个附件齐全、两个 sidecar 与对应 ZIP 摘要一致），并把结果追加到 `main` 的 POSTCHECK。

## 相对上一正式包核对（上一版本：0.30.0）

| 项目 | 上一版 | 本版 | 结论 / 注册影响 |
| --- | --- | --- | --- |
| native/third_party 原字节（含 json.hpp、第三方许可） | 未改 | 未改 | 无 |
| `native/panel_run.h`、`native/generic.cpp` | 0.30.0 | 已改；新增 `native/panel_fit.h` | worker 需重编译 |
| 回调指纹（sha256-repo-lf-v1） | `34311077…` | 因 `panel_fit.h` 列入依赖清单而重建（载荷 `5dc6b5a4…`） | 需重新部署回调 |
| loader DLL / callback DLL | 0.30.0 构建 | 由本版源码重建 | 需按 `bridge.py build` 重新部署 |
| protk.dat / 注册表路径 | `build/blend_callback_protk.dat` | 同路径 | 无需迁移 |
| 实际注册影响（未变 / 需重新注册 / 需迁移 / 需重启） | — | — | 需重编译、重启 MCP 连接器并重新加载回调、换种子包 |
