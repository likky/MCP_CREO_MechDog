# MCP_CREO_MechDog 0.35.2 版本说明

版本类型：PATCH。承接 0.35.1。

上一版本：0.35.1（`v0.35.1`，提交 `9b933cf5507322f7c8693ea6fd6ae74648866e5b`）。

## 亮点

- **曲面特征镜像引用不再崩溃**：[BUG-143](work-items/BUG-143.md) 为 `mirror` 的曲面引用补上崩溃防护。此前用 `references=[{kind:"feature",label:<曲面特征>}]` 镜像曲面会在 `ProFeatureCreate` 触发 Creo 主线程 `EXCEPTION_NONCONTINUABLE_EXCEPTION`，作业只能以 `unknown_outcome` 收场；现在 `native/advanced.cpp` 的 `generic_mirror` 在创建前检查目标特征是否拥有 `PRO_QUILT`，命中即抛出 `must name a solid feature`，不进入创建。本机 Creo 10 实机两次运行均按该错误拒绝，`session_alive_after_refusal=true`，随后巡检仍返回 1 个 quilt，未再崩溃。
- **mirror/trim 结果标签的跨作业消费补证**：[BUG-143](work-items/BUG-143.md) 实机验证 mirror 结果标签跨作业被 `surface_trim` 消费——面积 3141.5926535897934 → 1570.7963267786718 mm²、保留区 z 60…79.944；trim 结果标签跨作业被 `thicken` 消费——体积 1405.1862192991748 mm³；另有单计划 trim 保存并重载成功（`saved_file_reloaded_and_verified=true`）。三例跨作业作业的几何与标签语义成立，但保存阶段命中 `ProMdlnameBackup=-1`，按 [BUG-113](work-items/BUG-113.md) 保持 failed、未当作已落盘。
- **面选择器零匹配的最近候选诊断**：[DEV-098](work-items/DEV-098.md) 为 `target="surface"` 的通用 `geometry_selector` 零匹配新增只读 `geometry_selector_diagnostic.nearest_surfaces`：最多 5 条可命名的平面/圆柱面，按误差再按 id 升序，给出 `id`/`type`/`origin_mm`/`normal` 或 `axis`/`error_mm` 等字段；方向对但类型不符的面仍只进入 `type_rejected_ids`，列表绝不参与选中。本机 Creo 10 实机 40×20×10 方块：`candidate_count=6`、`matched_ids=[]`、候选 ids 65/67/58/53/63。
- **装配坐标溯源**：[DEV-098](work-items/DEV-098.md) 让装配坐标选择器失败回执保留 `requested_coordinate_space="assembly"`，避免把组件模型坐标读数误当成装配坐标。

## 变更总览

- `native/advanced.cpp`：`generic_mirror` 在 `ProFeatureCreate` 前检查目标特征的 `PRO_QUILT` 归属，命中即拒绝。
- `native/geometry_selectors.cpp`：新增 `selector_nearest_surfaces()`，面选择器零匹配时发布 `geometry_selector_diagnostic.nearest_surfaces` 并补错误文案。
- `native/generic.cpp`：装配坐标选择器失败回执写入 `requested_coordinate_space="assembly"`。
- `src/creo_mechdog/capabilities.py`、`docs/REFERENCE_SYNTAX.md`、`docs/COMPATIBILITY.md`：面选择器最近候选与装配坐标溯源契约同步。
- `tests/unit/test_bug143_quilt_results.py`、`tests/unit/test_dev098_diagnostics.py`：新增镜像防护、面候选上限与装配坐标回归。
- 版本元数据同步：`version.py`、`README.md` 标题/当前版/徽章、两份种子清单与 `docs/seed_package.json`；公开工具仍 110。

## 交付项

| 项 | 摘要 |
| --- | --- |
| [BUG-143](work-items/BUG-143.md) | 曲面特征镜像引用在创建前被拒绝，实机不再崩溃；mirror/trim 标签跨作业消费与单计划 trim 保存重载补证。 |
| [DEV-098](work-items/DEV-098.md) | 面选择器零匹配发布只读 `nearest_surfaces`（≤5 条），装配坐标失败回执保留 `requested_coordinate_space`。 |

## 已知限制（如实记录）

- BUG-143 的三例跨作业作业未完成保存：`ProMdlnameBackup=-1` 的根因仍按 BUG-113 开放，未加自动重试，也未改保存路径。
- BUG-143 的非圆柱组合（锥面/拉伸曲面等）与 `{kind:"quilt",id:N}` 镜像后的完整保存闭环未验。
- DEV-098 的最近候选是诊断值，不代表可接受的选择；装配坐标仅到源码契约与单测，未取得组件模型实机。
- 本机实机环境为 Creo 10.0.0.0 / release 42；Creo 12.4、Creo 9 与 WorkBuddy 黑盒未验。

## 附件与摘要

Release：`https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.35.2`。

四个附件（源码包摘要记录在同名 sidecar 中，一行 `<64 位 SHA256>  文件名`）：

- `MCP_CREO_MechDog-0.35.2-source.zip`
- `MCP_CREO_MechDog-0.35.2-source.zip.sha256`
- `MCP_CREO_MechDog-0.35.2-seed-library.zip`
- `MCP_CREO_MechDog-0.35.2-seed-library.zip.sha256`

- 种子包 SHA256：`094e25eb0d3aaba39d30105eaa7a9a28cb73ebcfc02622a11a792e411ab3d659`（24 个文件、9 个种子，两次构建摘要一致，与 `docs/seed_package.json` 一致）。
- 源码包：由本版合入 `main` 的提交源码构建；字节数与 SHA256 见同名 sidecar，不写入包内。

## 未验

- Creo 12.4 与 Creo 9（本机环境为 Creo 10.0.0.0 / release 42）。
- WorkBuddy 黑盒验收。
- BUG-143 的非圆柱组合与完整保存闭环；BUG-113 的 `ProMdlnameBackup=-1` 根因。
- DEV-098 的装配坐标实机与其他选择器形态。
- 发布后未重复执行 Creo 实机与 WorkBuddy 黑盒，实机范围以发布前记录为准。
