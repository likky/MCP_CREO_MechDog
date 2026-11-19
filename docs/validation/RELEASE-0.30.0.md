# 0.30.0 发布记录

- 版本：`0.30.0`（MINOR，部分交付）
- 日期：2026-11-19
- 版本说明：[RELEASE_NOTES_0.30.0](../RELEASE_NOTES_0.30.0.md)
- 主台账：[BACKLOG](../BACKLOG.md) · 工作卡：[DEV-092](../work-items/DEV-092.md) · [BUG-133](../work-items/BUG-133.md) · [FEAT-012](../work-items/FEAT-012.md) · 交付快照：[0.30.0](../releases/0.30.0.json)
- 受测提交：本记录所在开发分支的提交（标签 `v0.30.0` 的对象与提交号只在合入 `main` 后登记到 `main` 的[POSTCHECK](../development/RELEASE-POSTCHECK-2026-11-07.md) `## v0.30.0` 段）
- 与上一版本的关系：上一版本 0.29.0（`v0.29.0`，提交 `e0ae9767ab7867ee89a3b756ecd62b77b00ef3b0`），本版在其之上统一装配位姿容差与矩阵约定、补齐约束组边界与失败诊断

## 包内容对照（相对 0.29.0）

| 项 | 0.29.0 | 0.30.0 | 说明 |
| --- | --- | --- | --- |
| 公开工具 | 109 | 109 | 不变 |
| `rotation_tolerance` | Python 接受任意正有限值，原生固定 `1e-6` | 两层同一有效值，默认 `1e-6`、上限 `1e-3` | 契约收紧，超限拒绝 |
| 矩阵约定 | 只接受行向量写法 | 可选 `rotation_convention="row"\|"column"` | 列输入只转置一次 |
| 装配回执 | `rotation_convention`（解算变换） | 另加 `input_rotation_convention`、`rotation_tolerance` | 请求与解算分开 |
| 约束失败诊断 | 只有操作级 `stage` 与原始错误 | 另加 `failed_constraint_index`/`failed_constraint_type`/`constraint_stage`/`constraint_reason` | 整组求解失败索引为空 |
| 种子库 | 9 个种子 | 9 个种子 | `compatible_server_version=0.30.0` |
| 原生/worker/loader | 0.29.0 构建 | 本版有原生改动 | 需重新编译 |

## 验证

- 环境：Windows x64、Python 3.12.14、MSVC x64 构建工具、本机 Creo 12.4.0.0 / 匹配 Toolkit SDK（仅编译，未启动或连接 Creo）。
- 失败回归先行：修改前 `tools/test_assembly_pose.py` 运行退出 `3221226505`（原生固定 `1e-6` 拒绝 28° 六位小数矩阵），Python 专项 2 failures + 1 error；修复后 harness `build_exit_code=0`、`success=true`。
- 合并 `origin/main` 0.29.0 后：`python bridge.py build` exit 0；`tools/test_assembly_pose.py` `success=true`；`tools/dev_check.py --work-item DEV-092` `success=true`，全量单测 **4065 项通过（0 跳过、0 失败）**，`lint_findings=0`、`unformatted_files=0`（C++ 67、Python 549 个文件）。
- 发布资料：`tools/check_release_records.py --version 0.30.0` 通过；`tools/package.py` 的四附件门禁在打包时执行。
- 证据：`docs/validation/feedback-creo13-assembly-2026-11-19/IMPLEMENTATION-2026-11-19.md`（含 SDK 433 头文件逐项 SHA256、修改前后结果与未测范围）。

## 逐 ID 状态核对

成员：本版交付 3 个 ID，均为部分交付（软件层完成、实机未验收）。

| ID / 工作卡 | 技术状态 | 交付版本 | 剩余范围 | 卡首页 | 主台账 | 差异说明 | 版本说明 | 开发入口 | 实际 Release |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [BUG-133](../work-items/BUG-133.md) | 部分交付 0.30.0（软件层已修复，待实机验收） | 0.30.0 | 产品执行器实机放置与测量、Creo 内核是否接受 `1e-5` 精度、保存重载与失败回滚 | 部分交付 0.30.0（软件层已修复，待实机验收） | 部分交付 0.30.0（软件层已修复，待实机验收） | — | 已列入 | 已列入 | v0.30.0 |
| [FEAT-012](../work-items/FEAT-012.md) | 部分交付 0.30.0，剩余待验收 | 0.30.0 | 列约定与容差的 Creo 实机放置/回执复读；源件更新、嵌套子装配未做 | 部分交付 0.30.0，剩余待验收 | 部分交付 0.30.0，剩余待验收 | — | 已列入 | 已列入 | v0.30.0 |
| [DEV-092](../work-items/DEV-092.md) | 部分交付 0.30.0（T0/T1/T2/T4 软件层完成；T3 查证；T5 待输入） | 0.30.0 | T3 逐实例 `bbox_world_mm`/逐面面积实现与实机测量；T5 原始输入（说明书 8.2/8.5、9 件模型、22 条引用）与实机回放 | 部分交付 0.30.0（T0/T1/T2/T4 软件层完成；T3 查证；T5 待输入） | 部分交付 0.30.0（T0/T1/T2/T4 软件层完成；T3 查证；T5 待输入） | — | 已列入 | 已列入 | v0.30.0 |

## 未纳入本版

- 逐实例 `bbox_world_mm`、`bbox_status` 与逐面 `area_mm2` 字段（T3 只做 SDK 语义查证）。
- 22 条原样回放、固定快照与配合语义、`parallel`/轴点 `distance` 的正向依据（T5 缺原始输入）。
- Creo 实机放置、约束求解、保存重载、revision 与回滚。
- WorkBuddy 黑盒；Creo 9/10 运行期与其他版本。

## 发布核对

本版发布四个附件（逐个列出，不使用通配）：

- `MCP_CREO_MechDog-0.30.0-source.zip`
- `MCP_CREO_MechDog-0.30.0-source.zip.sha256`（源码包摘要记录在同名 sidecar 中，一行 `<64 位 SHA256>  文件名`）
- `MCP_CREO_MechDog-0.30.0-seed-library.zip`
- `MCP_CREO_MechDog-0.30.0-seed-library.zip.sha256`（种子包摘要同样在 sidecar 中）

- 种子包 SHA256：`e210ee229590a474c5fc22c5d81a0d39448f09055b55011671e6eac7177c2c13`（24 个文件、9 个种子，与 `docs/seed_package.json` 一致）。
- 源码包：由本版合入 `main` 的提交源码构建；字节数与 SHA256 见同名 sidecar，不写入包内。
- Release：<https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.30.0>（已发布，非 draft、非 prerelease，target `main`）。
- 发布后核对（2026-11-19 13:20 +08:00 / 05:20Z）：`tools\check_release_assets.py --tag v0.30.0` → exit 0，「v0.30.0: four assets downloaded and verified; both sidecars match」；实际列表、标签指向与附件摘意见 POSTCHECK `## v0.30.0` 段。冻结包内副本仍为打包时点措辞（`remote_verification=pending`），不回写、不重发已发布附件。
- 源码包 SHA256：`a52fa49d5d1c089485fddd7997487ac4cb292a84ad8ecc5df907fbf86cf46e67`（11 110 422 字节、2169 个文件；摘要记录在同名 sidecar 中）。
- 已冻结的源码包内记录仍是 `pending`，本段的 `verified` 与远端结果只存在于 `main`。`docs/releases/0.30.0.json` 的 `remote_verification` 为 `pending`。发布后须执行 `tools\check_release_assets.py --tag v0.30.0`（四个附件齐全、两个 sidecar 与对应 ZIP 摘要一致）并把结果追加到 POSTCHECK。

## 相对上一正式包核对（上一版本：0.29.0）

| 项目 | 上一版 | 本版 | 结论 / 注册影响 |
| --- | --- | --- | --- |
| native/third_party 原字节（含 json.hpp、第三方许可） | 未改 | 未改 | 无 |
| `native/assembly_pose.h`、`native/advanced.cpp`、`native/generic.cpp` | 0.29.0 | 已改 | worker 需重编译 |
| 回调指纹（sha256-repo-lf-v1） | `83ad907d…` | 未改面板载荷 | 无 |
| loader DLL / callback DLL | 0.29.0 构建 | 由本版源码重建 | 需按 `bridge.py build` 重新部署 |
| protk.dat / 注册表路径 | `build/blend_callback_protk.dat` | 同路径 | 无需迁移 |
| 实际注册影响（未变 / 需重新注册 / 需迁移 / 需重启） | — | — | 需重编译并重启 MCP 连接器、换种子包 |
