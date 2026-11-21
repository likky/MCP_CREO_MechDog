# 发布记录 v0.35.2（0.35.2，2026-11-21）

- 版本：`0.35.2`（PATCH）。
- 发布提交：`HEAD`（打标签后在本段回填 40 位哈希；`v0.35.2` 标签指向同一提交）。
- 上一版本：0.35.1（`v0.35.1`，提交 `9b933cf5507322f7c8693ea6fd6ae74648866e5b`）。
- 交付快照：[releases/0.35.2.json](../releases/0.35.2.json)。
- 版本说明：[RELEASE_NOTES_0.35.2.md](../RELEASE_NOTES_0.35.2.md)。
- Release：`https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.35.2`。
- 发布流程：[RELEASING.md](../development/RELEASING.md)；附件核对留存在 [RELEASE-POSTCHECK-2026-11-07.md](../development/RELEASE-POSTCHECK-2026-11-07.md) 的 `## v0.35.2` 段。
- 远端核对：发布后执行，当前未验证。

## 逐 ID 状态核对

台账以 [BACKLOG.md](../BACKLOG.md) 与 `docs/releases/0.35.2.json`（frozen 交付集）为准；工作卡状态只读首页 `分类：` 行的粗体词。本批两项随 v0.35.2 交付，均保留已记录的未测范围（非圆柱组合、完整保存闭环、装配坐标实机、其他 Creo 版本）。

| ID | 技术状态 | 交付版本 | 实际 Release | 卡首页 | 主台账 | 差异说明 |
| --- | --- | --- | --- | --- | --- | --- |
| [BUG-143](../work-items/BUG-143.md) | 部分交付 0.35.2，剩余待验收 | 0.35.2 | v0.35.2 | 部分交付 0.35.2，剩余待验收 | 部分交付 0.35.2，剩余待验收 | — |
| [DEV-098](../work-items/DEV-098.md) | 部分交付 0.35.2，剩余待验收 | 0.35.2 | v0.35.2 | 部分交付 0.35.2，剩余待验收 | 部分交付 0.35.2，剩余待验收 | — |

## 发布前核对

- 源码身份：`main` 分支工作树提交；版本以 [version.py](../../version.py) 为准，`README.md` 标题/当前版/徽章、`docs/seed_manifest.json` 与 `seed_library/seed_manifest.json` 的 `compatible_server_version` 同步为 0.35.2，公开工具仍 110。
- Ruff：`ruff check` 与 `ruff format --check` 通过（不含 `docs/validation/` 历史原件与第三方/生成文件）。
- 单元测试：`tools/dev_check.py` 全量 4297 项通过、失败 0、异常 0、跳过 6；`build/unit_test_report.json` `success=true`。跳过项为环境限制（符号链接权限、MSVC x64 独立 helper 环境、归档证据缺失）。
- 原生构建：`.\.venv\Scripts\python.exe bridge.py build` 编译变更后的 `native/advanced.cpp`、`native/generic.cpp` 与 `native/geometry_selectors.cpp`，exit 0；构建指纹含 `NATIVE_BUILD_FLAGS /utf-8-v1`。
- 发布记录门禁：`tools\check_release_records.py --version 0.35.2` 须 exit 0；`tools\check_backlog_counts.py` 须 `consistent: true`。

## 实机与原生证据摘要（本机 Creo 10.0.0.0 / release 42）

- **BUG-143 镜像崩溃防护**：`build/probe_bug143_mirror_guard.py` 两次运行（模型 `1be27ae0aa3b44baadaf2465e393961b`/作业 `48555b187b254a79962e02e30cb5f625`，最终二进制下模型 `a89320a0ff1442c4a47ef6a0c1c5b138`/作业 `fcdf320e55824086a4cde5b9e9618fa5`）均返回 `must name a solid feature`，`session_alive_after_refusal=true`，随后巡检仍返回 1 个 quilt。
- **BUG-143 标签跨作业**：mirror 作业 `f8787149d0314713886b9fae301ccde6` 成功后，solidify 作业 `0b3d60a9f7854a91b0ead29f8666b9f8` 以 `{kind:"quilt_feature",label:"q_mirrored"}` 解析成功（`target_quilt_id=113`、6283.185307179587 mm³）；trim 作业 `d152928d95c5495f8d41af8c1fb94cfe` 面积 3141.5926535897934 → 1570.7963267786718 mm²、保留区 z 60…79.944；thicken 作业 `67ce2525a9774cb38936db18bda46237` 体积 1405.1862192991748 mm³。上述三例保存阶段命中 `ProMdlnameBackup=-1`，终态 failed，未当作已落盘。
- **BUG-143 单计划 trim**：作业 `41b2698a1eaa432da15ddd517067c93f` `succeeded`、`saved_file_reloaded_and_verified=true`；trim `result_quilt_id=94`，kept 面积 700.7873896828373 mm²。
- **DEV-098 面选择器**：40×20×10 方块以 `points_mm=[[1000,1000,1000]]`、`tolerance_mm=0.01` 提交 draft，作业按预期失败；`candidate_count=6`、`matched_ids=[]`、`nearest_surfaces` 5 条（ids 65/67/58/53/63，`points_offset_mm` 960/980/990/1000/1000），`type="plane"`，`normal`/`origin_mm` 齐全。证据 `build/dev098_surface_nearest.json`。

## 命令记录

```text
.\.venv\Scripts\python.exe tools\check_release_records.py --version 0.35.2
.\.venv\Scripts\python.exe tools\check_backlog_counts.py
.\.venv\Scripts\python.exe tools\dev_check.py
.\.venv\Scripts\python.exe bridge.py build
```

结果：`check_release_records.py` 与 `check_backlog_counts.py` 均 exit 0（`consistent: true`）；`dev_check.py` 全量 4297 项通过、`success=true`、lint 0、unformatted 0；`bridge.py build` exit 0。种子包两次构建摘要一致（`094e25eb…`）。

## 附件与摘要

源码包摘要记录在同名 sidecar 中，一行 `<64 位 SHA256>  文件名`。四个附件：

- `MCP_CREO_MechDog-0.35.2-source.zip`
- `MCP_CREO_MechDog-0.35.2-source.zip.sha256`
- `MCP_CREO_MechDog-0.35.2-seed-library.zip`
- `MCP_CREO_MechDog-0.35.2-seed-library.zip.sha256`

- 种子包 SHA256：`094e25eb0d3aaba39d30105eaa7a9a28cb73ebcfc02622a11a792e411ab3d659`（24 个文件、9 个种子，两次构建摘要一致，与 `docs/seed_package.json` 一致）。
- 源码包：由本版合入 `main` 的提交源码构建；字节数与 SHA256 见同名 sidecar，不写入包内文件。

## 未验

- Creo 12.4 与 Creo 9（本机为 Creo 10.0.0.0 / release 42）。
- WorkBuddy 黑盒验收；DEV-098 的装配坐标实机与其他选择器形态。
- BUG-143 的非圆柱组合与完整保存闭环；BUG-113 的 `ProMdlnameBackup=-1` 根因。
- 发布后未重复执行 Creo 实机与 WorkBuddy 黑盒，实机范围以发布前记录为准。

## 发布后核对

发布后执行，当前未验证。发布后应运行 `tools\check_release_assets.py --tag v0.35.2` 并在此记录四个附件的远端名称、大小、API digest、本地重算 SHA256 与 sidecar 比对结论。
