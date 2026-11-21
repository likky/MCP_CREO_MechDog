# MCP_CREO_MechDog 0.35.1 版本说明

版本类型：PATCH。承接 0.35.0。

上一版本：0.35.0（`v0.35.0`，提交 `4e42e1d4b7e801894ab296271398e9bd1bb83012`）。

## 亮点

- **`0xC0000409` 根因定位并修复**：[BUG-142](work-items/BUG-142.md) 把实机崩溃与本机可重复的编译/序列化链对上：原生构建命令缺少 `/utf-8`，MSVC 按系统代码页（CP936）解析窄字符串字面量，把 UTF-8 弯破折号 `E2 80 94` 写成非法字节 `E2 80 3F`；`native.log` 的 `BUILD_FAILED` 文本因此不是合法 UTF-8，严格 `dump(2)` 抛 `type_error`，未捕获异常触发 `terminate`/`abort`，Windows 呈现为 `0xC0000409`，而 `ofstream` 已创建 0 字节结果文件。修复为 `bridge.py` 的三条 `cl` 命令加入 `/utf-8`，并把 `NATIVE_BUILD_FLAGS /utf-8-v1` 纳入构建指纹，旧缓存不再静默复用未按 UTF-8 编译的 worker。受控夹具 `strict_dump_crash` 复现退出码 `0xC0000409` 与 0 字节文件；替换 handler 下同一回执正常发布（失败码 30、成功码 0，`delivery_complete=true`，无残留 `.tmp`）。强制重编译后二进制中的弯破折号字节由 `E2 80 3F` 变为合法的 `E2 80 94`。
- **零候选边选择器的最近边诊断**：[DEV-098](work-items/DEV-098.md) 在通用 `geometry_selector` 零匹配的失败回执中新增 `geometry_selector_diagnostic.nearest_edges`：最多 5 条合格候选，按误差再按边 id 升序；直线给 `id`/`endpoints_mm`/`error_mm`（端点形式另给 `endpoint_errors_mm`，带 `point_mm` 时给 `point_error_mm`），圆给 `center_mm`/`radius_mm`/`radius_error_mm`/`center_error_mm`/`error_mm`（带 `axis` 时给 `axis_error_deg`）。该块只读诊断、绝不自动选中；多匹配仍只给 `matched_ids`。compact 结果投影保留该块，能力说明与 `REFERENCE_SYNTAX`/`COMPATIBILITY` 同步。本机 Creo 10 实机探针：`candidate_count=12`、`matched_ids=[]`、候选 ids 54/55/56/59/60、`error_mm=100.0`。

## 变更总览

- `bridge.py`：三条原生 `cl` 命令加入 `/utf-8`；构建指纹加入 `NATIVE_BUILD_FLAGS /utf-8-v1`。
- `native/geometry_selectors.cpp`：新增 `selector_nearest_edges()`，零匹配分支发布 `geometry_selector_diagnostic.nearest_edges` 并追加诊断说明文案。
- `src/creo_mechdog/compact_sections.py`：`geometry_selector_diagnostic` 纳入保留键，compact 投影不丢该块。
- `src/creo_mechdog/capabilities.py`、`docs/REFERENCE_SYNTAX.md`、`docs/COMPATIBILITY.md`：零候选诊断字段与“只读、不自动选中”语义同步。
- `tests/native/test_bug142_result_delivery.cpp`、`tests/unit/test_bug142_result_delivery.py`：新增 `strict_dump_crash`/`invalid_utf8`/`invalid_utf8_complete` 夹具与 4 项断言（含 `/utf-8` 出现 3 次）。
- `tests/unit/test_dev098_diagnostics.py`：新增 3 项最近边诊断回归（零匹配有界列表、最近候选不成为匹配、compact 投影/能力/文档包含该块）。
- 版本元数据同步：`version.py`、`README.md` 标题/当前版/徽章、两份种子清单与 `docs/seed_package.json`；公开工具仍 110。

## 交付项

| 项 | 摘要 |
| --- | --- |
| [BUG-142](work-items/BUG-142.md) | 根因：构建缺 `/utf-8` 产生非法 UTF-8，严格 `dump` 抛异常致 `0xC0000409`；已加 `/utf-8` 并纳入构建指纹，夹具复现与修复后发布均验证。 |
| [DEV-098](work-items/DEV-098.md) | 零匹配 `geometry_selector` 发布只读 `nearest_edges`（≤5 条），实机 `candidate_count=12`、`matched_ids=[]`、ids 54/55/56/59/60。 |

## 已知限制（如实记录）

- BUG-142 未取得 0.32.0 现场的原始模型；真实 disconnect 阻塞路径未构造，看门狗路径仍只由原生夹具注入。替换 handler 已兜底其他非法字节来源，但未穷举所有 Toolkit 文本路径。
- DEV-098 的最近边列表是诊断值，不代表可接受的选择；其他选择器形态（面、圆边轴、装配坐标）与 Creo 12.4/9 未复测。
- 本机实机环境为 Creo 10.0.0.0 / release 42；Creo 12.4、Creo 9 与 WorkBuddy 黑盒未验。

## 附件与摘要

Release：`https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.35.1`。

四个附件（源码包摘要记录在同名 sidecar 中，一行 `<64 位 SHA256>  文件名`）：

- `MCP_CREO_MechDog-0.35.1-source.zip`
- `MCP_CREO_MechDog-0.35.1-source.zip.sha256`
- `MCP_CREO_MechDog-0.35.1-seed-library.zip`
- `MCP_CREO_MechDog-0.35.1-seed-library.zip.sha256`

- 种子包 SHA256：`ad1d62bfc15e2dd45b1118464df75d19ee3635a871b179e9eaa590ae8b5c0ed4`（24 个文件、9 个种子，两次构建摘要一致，与 `docs/seed_package.json` 一致）。
- 源码包：由本版合入 `main` 的提交源码构建；字节数与 SHA256 见同名 sidecar，不写入包内。

## 未验

- Creo 12.4 与 Creo 9（本机环境为 Creo 10.0.0.0 / release 42）。
- WorkBuddy 黑盒验收。
- BUG-142 的 0.32.0 原始模型与真实 disconnect 阻塞现场。
- DEV-098 的面/圆边轴/装配坐标选择器形态。
- 发布后未重复执行 Creo 实机与 WorkBuddy 黑盒，实机范围以发布前记录为准；远端附件核对发布后执行，当前未验证。
