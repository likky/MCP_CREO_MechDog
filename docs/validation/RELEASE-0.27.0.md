# 0.27.0 发布记录

- 版本：`0.27.0`（MINOR，部分交付）
- 日期：2026-11-17
- 版本说明：[RELEASE_NOTES_0.27.0](../RELEASE_NOTES_0.27.0.md)
- 主台账：[BACKLOG](../BACKLOG.md)
- 工作卡：[BUG-130](../work-items/BUG-130.md)、[BUG-131](../work-items/BUG-131.md)
- 受测提交：本记录所在 `main` 提交（标签 `v0.27.0` 的对象与提交号只登记在 `main` 的[POSTCHECK](../development/RELEASE-POSTCHECK-2026-11-07.md) `## v0.27.0` 段）
- 与上一版本的关系：上一版本：0.26.0（`v0.26.0`，提交 `13609bc5a2889d02ab04e0b62364ca99c29dca02`），本版在其之上合入 0.26.0 反馈与球鼻艏 STL 导出的已完成部分

## 包内容对照（相对 0.26.0）

| 项 | 0.26.0 | 0.27.0 | 说明 |
| --- | --- | --- | --- |
| 公开工具 | 108 | 109 | 新增 `creo_cancel_job` |
| STL 导出 | 单一导出路径，大件崩溃或超时 | 默认逐面导出、参数域细化与 `stl_options` | `bulb_bulged` 偏差 0.0899mm；旧 14m 未达标 |
| 作业控制 | 无取消、无停滞看门狗 | `creo_cancel_job`、`stall_watchdog`、`abandon_new` | 取消不承诺回滚 |
| 圆柱面拆半 | 只能唯一命中 | `coaxial:"any"` 与三类报错分型 | 仅 insert/concentric |
| 区域切除 | 仅签名契约 | `ExtrudeOp.region` 派生草图适配层 | 原生选区未开放 |
| 放样准入 | 裸 worker 身份 | 同 worker 实测身份合并 | 不改变 supported/unknown 放行 |
| 圆角 | G2 仅静态查证 | `curvature_continuous` + 本机实机 | 曲率连续性未测量 |
| 种子库 | 9 个种子 | 9 个种子 | `compatible_server_version=0.27.0` |

## 验证

- 环境：Windows x64、Python 3.12、Creo 12.4.0.0 与匹配 Toolkit SDK、MSVC x64。
- 离线：`tools/dev_check.py` 单测 3810 项通过（0 失败/0 错误/0 跳过，650 秒）、`lint_findings=0`、`unformatted_files=0`；`bridge.py build` 退出码 0。
- 原生单测：`tests/native/test_stl_export.cpp` 24 项、`test_stl_file_check.cpp` 11 项、`test_stl_mesh_check.cpp` 12 项。
- 文档与门禁：`tools/check_release_records.py --version 0.27.0` 通过；`tools/check_backlog_counts.py` 一致；`tools/package.py` 的四附件门禁与发布记录门禁通过。
- 实机（本机 Creo 12.4.0.0，用户当次授权）：
  - BUG-130：`bulb_bulged` job `cde4566fc9134d05a59d656cda7b2970` 737,984 片、150,658,502 字节、194 秒，最大偏差 0.0899mm/p99 0.0584/平均 0.0125，trimesh 闭合与绕序一致；旧 14m 默认预算 job `dd659d80790a43f19035229ccb8b86e6` 0.1559mm、50 万顶点 job `40197280d83245418896fc8f18ef585a` 0.1115mm。
  - BUG-131：取消与看门狗实机，`test_job_control` 19 项、投影 1 项通过。
  - BUG-132：R27.5 通孔 102/103 默认拒绝，`coaxial:"any"` insert+mate `committed`、`underconstrained=false`，保存重载 5→6。
  - DEV-090：R5/R30 G2 四条用例 `committed` 且保存重载，R5 去除 `107.3015→80.0793 mm³`。
  - BUG-020：STEP 导出 `.stp` 8622 字节、`ISO-10303-21`，诊断摘录移入 `output/diagnostics/`，保存重载 true。
- 未测：旧 14m 0.1mm 精度、装配/Creo 9/10 STL、BUG-131 挂死根因、BUG-132 的 Arm7/Creo 10、原生选区、Creo 10 放样复测与 WorkBuddy 黑盒。

## 逐 ID 状态核对

成员：本版交付 8 个 ID，均为部分交付或技术结论；BUG-020 无独立工作卡、已移入完成档案，不列入本表。剩余范围写在各自工作卡首页。

| ID / 工作卡 | 技术状态 | 交付版本 | 剩余范围 | 卡首页 | 主台账 | 差异说明 | 版本说明 | 开发入口 | 实际 Release |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [BUG-106](../work-items/BUG-106.md) | 部分交付（文案+裁定）；实机链路待验 | 0.27.0 | 真实同名外部模型的 save/erase 两步链路实机复测 | 部分交付（文案+离线裁定）；实机链路待验 | 部分交付（文案+裁定）；实机链路待验 | 卡首页措辞更细，状态类同为部分交付 | 已列入 | 已列入 | v0.27.0 |
| [BUG-122](../work-items/BUG-122.md) | 部分交付，剩余待验收 | 0.27.0 | Creo 10 第二次提交无空壳、WorkBuddy 黑盒、panel 路线准入 | 部分交付 | 部分交付，剩余待验收 | 卡首页粗体词为简写，状态类相同 | 已列入 | 已列入 | v0.27.0 |
| [BUG-129](../work-items/BUG-129.md) | 部分交付，剩余待验收 | 0.27.0 | Arm2 原模型与 placement 契约、Creo 12.4/10 实机复测 | 部分交付，剩余待验收 | 部分交付，剩余待验收 | 无 | 已列入 | 已列入 | v0.27.0 |
| [BUG-130](../work-items/BUG-130.md) | 已修复（bulb 偏差 0.0899mm 达标；旧 14m 0.1115mm 未达标） | 0.27.0 | 旧 14m 0.1mm 精度、ASCII 写出优化、装配与 Creo 9/10、默认预算 | 已修复（bulb 偏差 0.0899mm 达标；旧 14m 0.1115mm 未达标） | 已修复（bulb 偏差 0.0899mm 达标；旧 14m 0.1115mm 未达标） | 无 | 已列入 | 已列入 | v0.27.0 |
| [BUG-131](../work-items/BUG-131.md) | 仍需修复（取消/收尾/看门狗已实机；挂死根因未验） | 0.27.0 | 23 组件挂死根因、`revision==0` 新装配实机复现 | 仍需修复（取消/收尾/看门狗已实机；挂死根因未验） | 仍需修复（取消/收尾/看门狗已实机；挂死根因未验） | 无 | 已列入 | 已列入 | v0.27.0 |
| [BUG-132](../work-items/BUG-132.md) | 仍需修复（本机 Creo 12.4 已验报错分型与 coaxial insert；Creo 10/Arm7 未验） | 0.27.0 | Arm7 原半圆柱、Creo 10 对照 | 仍需修复（本机 Creo 12.4 已验报错分型与 coaxial insert；Creo 10/Arm7 未验） | 仍需修复（本机 Creo 12.4 已验报错分型与 coaxial insert；Creo 10/Arm7 未验） | 无 | 已列入 | 已列入 | v0.27.0 |
| [FEAT-069](../work-items/FEAT-069.md) | 部分交付，剩余待验收 | 0.27.0 | 原生选区创建、实机去料、Creo 10 | 部分交付，剩余待验收 | 部分交付，剩余待验收 | 无 | 已列入 | 已列入 | v0.27.0 |
| [DEV-090](../work-items/DEV-090.md) | 部分交付，剩余待验收 | 0.27.0 | 多约束求解/保存重载、`parallel`/`distance`、T7 实测、Arm7 实体边与 Creo 10 | 部分交付，剩余待验收 | 部分交付，剩余待验收 | 无 | 已列入 | 已列入 | v0.27.0 |

## 未纳入本版

- 旧 14m 球鼻艏的 0.1mm 偏差目标：默认与加大预算均未达成，转入下个版本。
- 装配件与 Creo 9/10 的 STL 导出、官方文件路径同质量完成性。
- BUG-131 的 23 组件挂死根因与 `revision==0` 新装配实机。
- BUG-132 的 Arm7 原半圆柱与 Creo 10 对照。
- FEAT-069 的原生选区创建与实机去料。
- WorkBuddy 黑盒、非 mm 单位与其它 Creo 版本。

## 发布核对

本版发布四个附件（逐个列出，不使用通配）：

- `MCP_CREO_MechDog-0.27.0-source.zip`
- `MCP_CREO_MechDog-0.27.0-source.zip.sha256`（源码包摘要记录在同名 sidecar 中，一行 `<64 位 SHA256>  文件名`）
- `MCP_CREO_MechDog-0.27.0-seed-library.zip`
- `MCP_CREO_MechDog-0.27.0-seed-library.zip.sha256`（种子包摘要同样在 sidecar 中）

- 种子包 SHA256：`72cdd8053298981b7fc9ac6665bb66033b9f91daacd4194d3360d2bc0389b36f`（24 个文件、9 个种子，与 `docs/seed_package.json` 一致，重建一次摘要不变）。
- 源码包：由本版合入 `main` 的提交源码构建，`tools/package.py` 的四附件门禁与发布记录门禁均通过；字节数与 SHA256 见同名 sidecar，不写入包内。
- Release：<https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.27.0>。
- 发布后核对：已执行，实际列表、标签指向、附件摘要与 `main` 提交见[POSTCHECK](../development/RELEASE-POSTCHECK-2026-11-07.md) `## v0.27.0` 段；冻结包内副本仍为打包时点措辞，不回写、不重发已发布附件。
- 本版原生修改 `native/generic.cpp`、`native/stl_export.h`、`native/geometry_selectors.cpp`、`native/advanced.cpp`，升级后必须重编译 worker 并重启 MCP 连接器。

## 相对上一正式包核对（上一版本：0.26.0）

| 项目 | 上一版 | 本版 | 结论 / 注册影响 |
| --- | --- | --- | --- |
| native/third_party 原字节（含 json.hpp、第三方许可） | 未改 | 未改 | 无 |
| 回调指纹（sha256-repo-lf-v1） | 未改 | 未改 | 无 |
| loader DLL SHA256 | 未改 | 未改 | 无 |
| callback DLL SHA256 | 未改 | 未改 | 无 |
| worker SHA256 | 0.26.0 构建 | 本版修改四个原生源文件并新增 `stl_export.h` | 必须重新编译 worker（`bridge.py build`） |
| protk.dat / 注册表路径 | 未改 | 未改 | 无需重新注册 |
| 实际注册影响（未变 / 需重新注册 / 需迁移 / 需重启） | — | — | 仅需重编译并重启 MCP 连接器 |
