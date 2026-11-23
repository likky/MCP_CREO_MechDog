# 发布记录 v0.37.0

日期为 2026-11-23，版本类型为 MINOR，公开工具仍 111。

上一版本：0.36.1（`v0.36.1`，提交 `a9bf80d3036e597258af917f80cffd1f7ca51220`）。

## 验收范围

本版交付 0.35.5 反馈的 P0 批次七项：

- [BUG-155](../work-items/BUG-155.md)：边选择器写入 `target="edge"`，`resolve()` 按目标类型校验 id 并给出显式错误。
- [BUG-156](../work-items/BUG-156.md)：装配可作为装配源，走 `ProMdlnameCopy` 隔离快照，回执披露源类型、快照与组件数。
- [BUG-157](../work-items/BUG-157.md)：看门狗同时观察 `worker.log` 与 `native.log`；装配开放 `restore_baseline` 并新增 `verify_mode="identity"`；依赖限制在模型输出目录或受管 `models` 根；`recovery_phase_seconds` 默认 300 s。
- [BUG-158](../work-items/BUG-158.md)：提交回执、运行态与 compact 投影同源披露作业预算、停滞预算、来源与观察文件。
- [BUG-159](../work-items/BUG-159.md)：间隙不超过 1e-6 mm 的弧-弧接点视为已接合；部分交付，内核拉伸拒绝转 [BUG-165](../work-items/BUG-165.md)。
- [BUG-160](../work-items/BUG-160.md)：坐标尺寸接受精确 B 样条；未支持实体存在时面积返回 `null` 并给出 `area_status` 与实体列表。
- [BUG-161](../work-items/BUG-161.md)：圆角/倒角在创建特征前拒绝同一整圆的重复边引用。

原生改动位于 `native/advanced.cpp`、`native/generic.cpp`、`native/geometry_selectors.cpp`、`native/sketch_coordinates.cpp`；其余为 Python 准入、恢复、回执与文档。公开工具数仍 111。

## 环境与原生构建

- Windows x64，Creo 12.4.0.0（`release_numeric=42`，安装目录 `D:\Program Files\PTC\Creo 10.0.0.0`）与匹配 Toolkit；Python 3.12。
- 基线提交 `9df2b36`，分支 `codex/feedback-0355-p0`（发布候选），运行时 dirty=true；实机报告记录当时的提交与源码指纹。
- `bridge.py build` 编译通过后运行四组实机脚本；保存重载核验使用 `saved_file_reloaded_and_verified=true`。

## 实机证据

四组报告均为本地运行产物，不随源码包分发：

- `build/feedback0355_selector_round/20261123T113336_4d09dea0/report.json`，SHA256 `8ea1401d2fd95414ef5d6176bcc47b2b96577cddf34643afedad5b968cfeecd0`：4/4 通过。`selector_edge`（job `e9e646901785439aace6273fc50a6f99`）与 `single_edge_id`（job `1e24a103ae5d47f8b0172d01707da5c5`）圆角成功、revision 2、保存重载 true；`duplicate_circle_ids`（job `3e74779e309f460caed9b3e77f0a4e54`）在建特征前拒绝 72/90 同圆引用，revision 保持 1。
- `build/feedback0355_nested/20261123T120626_cd08c54e/report.json`，SHA256 `f79ecbedf0740d26e70c7be4cfda7b99cf9e2eef7b327e9c272bc28d64bb02ae`：5/5 通过。`nested_assembly`（job `ab06fb11f8bd40f2bd6417edb5384aa5`）三级装配成功，回执 `source_model_type="assembly"`、`source_snapshot=true`、`component_count=2`，父装配体积 1499.9999999999993 mm³，源子装配 SHA256 前后一致且 revision 3→3；`budget_disclosure` 的回执与运行态均为 `timeout_seconds=600`、`stall_watchdog_seconds=600`、观察文件 `worker.log`/`native.log`。
- `build/feedback0355_recovery/20261123T135331_0e42b81f/report.json`，SHA256 `ffe7c7894decb285f35ea1b8e27bed1e3dc6fafe847591dbd67014bf57633b1b`：5/5 通过。60 次装配长任务取消后 `unknown_outcome`，inspect 给出 `restore_baseline.available=true`、`native_phase_seconds=300`、`outer_seconds=330`；apply（job `73d54f834a5c45cd86253733696ff9d7`）以 `verification="identity"` 恢复，`feature_count=6`、体积 499.9999999999999 mm³、`full_inspection_verified=false`、保存重载 true，磁盘 SHA 不变、组件数 1。
- `build/feedback0355_sketch/20261123T135114_933cab28/report.json`，SHA256 `4e78eedeb98bee24f1ee246c823317938bae734f31e059615c2dc28a4d184704`：2/2 通过。40 段圆弧 40 个接点间隙 1.7301e-8–1.1180e-7 mm，`admission_accepted=true`；内核仍以 `ProFeatureWithoptionsCreate=-1` 拒绝拉伸，按边界记录 `kernel_extrude="rejected"`、`follow_up="BUG-165"`，不伪造通过。4 条三次闭合 B 样条坐标草图成功、revision 1、保存重载 true，`analysis="partial"`、`material_area_mm2=null`、`area_status="unavailable_unsupported_entities"`、`unsupported_entities=["sp0","sp1","sp2","sp3"]`，原生 `closed_contours=1`、`open_ends=0`。

## 种子包

`python tools/package_seeds.py --output build/release-0.37.0/MCP_CREO_MechDog-0.37.0-seed-library.zip --allow-record-mismatch` 首次构建得到摘要后回填 `docs/seed_package.json`；再用 `python tools/package_seeds.py --output build/release-0.37.0/confirm/MCP_CREO_MechDog-0.37.0-seed-library.zip` 重建确认，两次摘要一致：`0fe2c5fb197fedfa917843d189a9ba533b3b514af10cbf6324939d0bd33dc67b`（24 个文件、9 个种子）。

## 单测证据

发布候选在 0.37.0 工作树上运行 `tools/test_unit.py`，全量 unittest 通过，0 失败、0 错误。下列数字取自本轮 `build/unit_test_report.json`，该报告不随源码包分发。

本轮 `run_id=c7e3a8b254924a8d8aeeb98ae3f5dba7`，执行 4,419 项，0 失败、0 错误、6 跳过，耗时 310.25 s，报告 `version=0.37.0`、`status=completed`、`success=true`。受测提交 `ea3b21bffe989eecdf101eb9314ec92d8a1db677`（分支 `codex/feedback-0355-p0`；运行时本版文档与 `version.py` 尚未提交，故 `dirty=true`），源码指纹 `a840e8cf58261a50e6e6e34802d1926242d7e49ba23287ef38b4c04d327279b6`，统计 669 个受 Git 跟踪的 `.py` 与原生头/源文件。跳过项为 Windows 符号链接权限、MSVC 独立辅助程序环境与未随仓库保存的历史作业证据，均不涉及本版改动。

语言与格式检查以 `tools/dev_check.py --skip-unit` 执行：`success=true`，lint 0、unformatted 0，离线验收 2/2 通过。

## 未测范围

- Creo 9 实机编译/建模未复验；本机无 Creo 9 SDK。Creo 10 现场本批未复验。
- 原报告模型未随附：垫板 116/174 原边、40 段原始输入、6428 边零件、269 组件装配均以等价模型验证同一代码路径。
- 曲面选择器回归、外部 WorkBuddy 黑盒、真实客户端长作业试探未执行。
- 40 段多半径圆弧的拉伸仍由内核拒绝，共享顶点工作转 BUG-165，本版不承诺该轮廓可拉伸。

## 附件

- `MCP_CREO_MechDog-0.37.0-source.zip`
- `MCP_CREO_MechDog-0.37.0-source.zip.sha256`
- `MCP_CREO_MechDog-0.37.0-seed-library.zip`
- `MCP_CREO_MechDog-0.37.0-seed-library.zip.sha256`

种子包 SHA256 为 `0fe2c5fb197fedfa917843d189a9ba533b3b514af10cbf6324939d0bd33dc67b`。源码包摘要记录在同名 sidecar 中，两份 sidecar 分别记录对应 ZIP 的实际 SHA256。

## 逐 ID 状态核对

| ID | 交付版本 | 实际 Release | 技术状态 | 卡首页 | 主台账 | 差异说明 |
| --- | --- | --- | --- | --- | --- | --- |
| [BUG-155](../work-items/BUG-155.md) | 0.37.0 | v0.37.0 | 已有修复但待验收 | 已有修复但待验收（0.37.0 已交付，剩余现场待验） | 已有修复但待验收 | 状态类别一致；曲面选择器回归与 Creo 9 待补 |
| [BUG-156](../work-items/BUG-156.md) | 0.37.0 | v0.37.0 | 已有修复但待验收 | 已有修复但待验收（0.37.0 已交付，剩余现场待验） | 已有修复但待验收 | 状态类别一致；原始 P05 与 Creo 9 待补 |
| [BUG-157](../work-items/BUG-157.md) | 0.37.0 | v0.37.0 | 已有修复但待验收 | 已有修复但待验收（0.37.0 已交付，剩余现场待验） | 已有修复但待验收 | 状态类别一致；6428 边与 269 组件现场待补 |
| [BUG-158](../work-items/BUG-158.md) | 0.37.0 | v0.37.0 | 已有修复但待验收 | 已有修复但待验收（0.37.0 已交付，剩余现场待验） | 已有修复但待验收 | 状态类别一致；真实长作业试探待补 |
| [BUG-159](../work-items/BUG-159.md) | 0.37.0 | v0.37.0 | 部分交付 0.37.0（Python 准入已修复；内核拉伸转 BUG-165） | 部分交付 0.37.0（Python 准入已修复；内核拉伸转 BUG-165） | 部分交付 0.37.0（Python 准入已修复；内核拉伸转 BUG-165） | 内核共享顶点转 BUG-165，本版不承诺拉伸 |
| [BUG-160](../work-items/BUG-160.md) | 0.37.0 | v0.37.0 | 已有修复但待验收 | 已有修复但待验收（0.37.0 已交付，剩余现场待验） | 已有修复但待验收 | 状态类别一致；原始模型与 Creo 9 待补 |
| [BUG-161](../work-items/BUG-161.md) | 0.37.0 | v0.37.0 | 已有修复但待验收 | 已有修复但待验收（0.37.0 已交付，剩余现场待验） | 已有修复但待验收 | 状态类别一致；原始垫板 116/174 待补 |

## 远端核对

已发布并核对（2026-11-23）。Release id `455171815`，创建于 2026-11-23T08:48:50Z；附注标签对象 `6180aed4c26c7722e6cbe3789a5d741505c81b8f` 指向 `5932e20d2eba2760325f666ed1ca5b4f9851df83`（本版合入提交），远端 `refs/heads/main` 与该提交一致。`tools/check_release_assets.py --tag v0.37.0` 返回 “four assets downloaded and verified; both sidecars match; release body self-proof verified”，四个附件与两份 sidecar 摘要一致：源码包 `94f0aa1683c0c4b32d4519669f3215b715d2cd85af40b7b6c135e0fb2ecf5ffc`，种子包 `0fe2c5fb197fedfa917843d189a9ba533b3b514af10cbf6324939d0bd33dc67b`。附件字节、摘要与环境侧发布通道见 [GitHub Release](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.37.0) 和[发布后核对](../development/RELEASE-POSTCHECK-2026-11-07.md)。
