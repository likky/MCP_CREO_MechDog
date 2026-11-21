# MCP_CREO_MechDog 0.35.0 版本说明

版本类型：MINOR 部分交付。承接 0.34.0。

上一版本：0.34.0（`v0.34.0`，提交 `bbd81cdbaa92f7acdc1988d574dfdab832e01bed`）。

## 亮点

- **曲面结果可被直接引用**：[BUG-143](work-items/BUG-143.md) 让 `surface_fill`、`quilt_merge`、`mirror`、`surface_trim` 成功回执发布原生实测的 `quilt_id`；同计划内 merge/fill 结果的特征标签先按实测 quilt 解析、再回退 feature 反查，`solidify` 因此能消费 merge 结果。本机 Creo 10.0.0.0 实机闭合圆柱计划（两块封盖 + 两次 merge + 按标签 `solidify`）`succeeded`，`target_quilt_id=71`、体积 785.3981633974481 mm³、保存重载通过；无法唯一确定结果 quilt 时明确拒绝并附候选，不按 bbox 或最近 quilt 猜测。跨作业的标签别名不保留，需使用回执里的 `quilt_id`。
- **两距离不等距倒角**：[FEAT-071](work-items/FEAT-071.md) 新增 `chamfer_type="d1_d2"`，要求正数 `distance_1`/`distance_2` 与显式 `reference_surface`，独立 `creo_chamfer` 与计划操作共用同一契约；SDK 依据为本机 `ProChamfer.h` 的 `PRO_CHM_D1_X_D2 = 603`。本机 Creo 10 实机 2/5 与 5/2 两方向均生效（各去除 250 mm³、保存重载 true），观测到 D1 落在未在 `reference_surface` 指定的相邻面、D2 落在 `reference_surface` 指定的面；其他参考面组合与曲面边未验。
- **断连不再吞掉执行与回滚事实**：[BUG-142](work-items/BUG-142.md) 在不可逆 disconnect 前把执行/回滚结论写入 `native_result.json`（`delivery_complete=false`），disconnect 正常返回后再发布完整终态；结果发布对 Toolkit 非 UTF-8 文本改用替换策略，避免 0 字节临时文件。本机实机复现了 0.32.0 报告过的 `0xC0000409`（`PHASE=disconnect`，作业 `0e5ea74c…`），但栈 Cookie 根因仍未定位，本版不宣称根因修复。
- **启动链两项修复**：[BUG-140](work-items/BUG-140.md) 把 legacy 指纹候选改为按需求值，并设 8 个依赖上限，10 依赖合成探针由 0.415647 s/1024 候选降到 1.8 µs/0 次调用；[BUG-141](work-items/BUG-141.md) 只忽略 `process_identity()` 确认已退出的进程条目，活跃、权限不足或状态不可知的进程继续保护，`selection_required` 不再被 `force_ready` 或近期探针绕过。
- **诊断语义与文档收口**：[DEV-098](work-items/DEV-098.md) 新增 `diagnostic_semantics`（b_spline `profile` 下界判定、closure 三态拆分），文档补充零候选选择器范围、closure 三种含义、隐藏窗口/hung 解释与已验证分步曲面封口路径。

## 变更总览

- `native/surfaces.cpp`、`native/quilt_query.h`：fill 实测 quilt 登记、solidify/merge/trim 标签按实测 quilt 解析；`operation_results.py` 只投影 committed 操作的实测 id 或唯一归属；`compact_sections.py` 保留 `quilt_id`。
- `src/creo_mechdog/schema.py`、`server.py`、`native/generic.cpp`：`d1_d2` 契约与 `PRO_CHM_D1_X_D2` 元素树。
- `native/worker_result_delivery.h`（新增）、`native/worker.cpp`、`native/result_delivery.h`：断连前预发布与非 UTF-8 容错。
- `bridge.py`、`src/creo_mechdog/build_fingerprints.py`、`creo_startup.py`：惰性指纹候选、规模保护与已退出进程判断。
- `src/creo_mechdog/diagnostic_semantics.py`（新增）、`capabilities.py`、`docs/REFERENCE_SYNTAX.md`、`docs/COMPATIBILITY.md`：诊断语义与文档契约。
- 版本元数据同步：`version.py`、`README.md` 标题/当前版/徽章、两份种子清单与 `docs/seed_package.json` 的 `compatible_server_version` 与种子包名/摘要；公开工具仍 110。

## 交付项

| 项 | 摘要 |
| --- | --- |
| [BUG-143](work-items/BUG-143.md) | 曲面结果回执给实测 `quilt_id`；同计划 merge/fill 标签可被 `solidify` 消费，实机体积 785.3981633974481 mm³、保存重载通过。 |
| [FEAT-071](work-items/FEAT-071.md) | `d1_d2` 两距离倒角与独立工具参数对齐；实机 2/5 与 5/2 各去除 250 mm³，D1/D2 面归属已记录。 |
| [BUG-142](work-items/BUG-142.md) | 断连前结果预发布与非 UTF-8 容错；实机复现 `0xC0000409`，根因未定位。 |
| [BUG-140](work-items/BUG-140.md) | 构建指纹 legacy 候选惰性求值与 8 依赖上限；合成探针 0.415647 s/1024 → 1.8 µs/0。 |
| [BUG-141](work-items/BUG-141.md) | 只忽略可确认退出的进程；真实身份冲突仍保护。 |
| [DEV-098](work-items/DEV-098.md) | 诊断语义模块与 b_spline/closure/窗口/选择器文档契约；零候选最近边原生接入留待后续。 |

## 已知限制（如实记录）

- BUG-142 的 `0xC0000409` 栈 Cookie 根因未定位；本版只保证执行与回滚事实在 disconnect 前落盘，且不把 `delivery_complete=false` 当作成功。
- BUG-143 的标签别名按作业持有：跨作业引用需使用回执 `quilt_id`；mirror 标签实机消费、trim 标签链与 coplanar 相邻 fill 合并仍受既有 Creo 10 限制影响。
- FEAT-071 只在 50×30×10 块/顶边/`reference_surface`=顶面组合上验证了方向；其他参考面组合、曲面边与其他 Creo 版本未验。
- BUG-140/141 只做离线回归；真实构建缓存的端到端启动计时与真实僵尸进程现场未验。
- DEV-098 的通用 `geometry_selector` 零候选最近边诊断尚未接入原生。

## 附件与摘要

Release：`https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.35.0`。

四个附件（源码包摘要记录在同名 sidecar 中，一行 `<64 位 SHA256>  文件名`）：

- `MCP_CREO_MechDog-0.35.0-source.zip`
- `MCP_CREO_MechDog-0.35.0-source.zip.sha256`
- `MCP_CREO_MechDog-0.35.0-seed-library.zip`
- `MCP_CREO_MechDog-0.35.0-seed-library.zip.sha256`

- 种子包 SHA256：`8f7c1645d7a324f674de6f486bd83aca0f4ad99e5abd50177843fedc6352f02d`（24 个文件、9 个种子，两次构建摘要一致，与 `docs/seed_package.json` 一致）。
- 源码包：由本版合入 `main` 的提交源码构建；字节数与 SHA256 见同名 sidecar，不写入包内。

## 未验

- Creo 12.4 与 Creo 9（本机环境为 Creo 10.0.0.0 / release 42）。
- WorkBuddy 黑盒验收。
- BUG-143 跨作业标签引用、mirror 标签与 trim 标签链；FEAT-071 其他参考面组合与曲面边。
- BUG-140/141 的真实构建缓存计时与真实僵尸进程现场；BUG-142 崩溃根因。
- 发布后未重复执行 Creo 实机与 WorkBuddy 黑盒，实机范围以发布前记录为准；远端附件核对发布后执行，当前未验证。
