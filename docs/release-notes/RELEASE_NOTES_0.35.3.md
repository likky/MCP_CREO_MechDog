# MCP_CREO_MechDog 0.35.3 版本说明

版本类型：PATCH。承接 0.35.2。

上一版本：0.35.2（`v0.35.2`，提交 `b90f0eda2a70c1f6ae5e4ae7df56c74be6786b24`）。

## 亮点

- **非圆柱组合的跨作业标签链路与保存闭环**：[BUG-143](../work-items/BUG-143.md) 用一个开放圆锥套实机跑通 mirror → trim → thicken 三步、每步一个作业。几何为 XZ 平面开放直线 `[[-25,5],[-5,20]]` 绕 X 轴旋转 360°（quilt 79、2 面、面积 1963.4907316790584 mm² = π(5+20)·25）。mirror 以 `{kind:"quilt",id:79}` 生成 quilt 99；随后 trim 在**另一个作业**里以 `{kind:"quilt_feature",label:"c_mirrored"}` 解析到 quilt 99，保留区 x 15…25、687.2181023230302 mm²；thicken 再以 `{kind:"quilt_feature",label:"c_trimmed"}` 加厚 2.0，体积 1500.0989754261154 mm³。rev 1→4，每步 `saved_file_reloaded_and_verified=true` 且无 `save_failure`。
- **闭合锥面的面积测量边界**：闭合梯形圆锥环（quilt 94 → 镜像 quilt 119）上，trim 同样由 mirror 标签正确解析并算出保留区（x 15…25、5 面/176 三角），但 `ProContourAreaEval` 对锥面返回 -1（`contour_area_eval_failed`），trim 按“无可测保留区”回滚。这是面积测量限制，不是标签解析失败；开放锥面与圆柱不受影响。
- **`ProMdlnameBackup=-1` 的受控排除与失败瞬间诊断**：[BUG-113](../work-items/BUG-113.md) 在同一 Creo 10 安装上做对照：干净会话连续 10 次保存全部成功（rev 1→11）；30 s 延迟后第二次保存仍稳定失败；Restart Manager 查询无持有者；对最新版本持共享读、预占下一版本号、verify 阶段短暂独占都没有复现 -1。因此失败与前一会话状态相关，外部 AV/文件锁假设不成立，仍不加入自动重试、不改保存路径。原生 `save_failure` 回执新增 `source_checkpoint_readable` 与 `candidate_readability`（≤20 条 `{name,readable}`，读不到即省略、不伪造），供下一次现场取证。

## 变更总览

- `native/generic.cpp`：新增 `readable_file()` 与 `candidate_readability()`；`save_failure_report` 增加 `source_checkpoint_readable` 与有界 `candidate_readability`。
- `src/creo_mechdog/operation_results.py`：`normalize_save_failure` 投影上述两键，新增 `_normalize_readability()`（上限 `SAMPLE_LIMIT`、跳过无名字项、不伪造布尔值）。
- `tests/unit/test_surface_save_recovery.py`：原生键断言补两键，新增 `test_readability_probes_stay_bounded_and_unfabricated`。
- 文档：BUG-143/BUG-113 卡片与主台账补入本轮实机证据、排除项与边界。
- 版本元数据同步：`version.py`、`README.md` 标题/当前版/徽章、两份种子清单与 `docs/seed_package.json`；公开工具仍 110。

## 交付项

| 项 | 摘要 |
| --- | --- |
| [BUG-143](../work-items/BUG-143.md) | 开放圆锥套上 mirror → trim → thicken 跨作业标签链路与保存重载闭环实机通过；闭合锥面 trim 记录为面积测量边界。 |
| [BUG-113](../work-items/BUG-113.md) | 同机受控对照排除外部文件锁，判定与会话状态相关；新增失败瞬间可读性诊断（有界、不伪造）。 |

## 已知限制（如实记录）

- 闭合梯形圆锥环的 trim 仍会回滚：`ProContourAreaEval` 对锥面返回 -1，trim 判为无可测保留区。该限制不属于 BUG-143 的标签语义。
- BUG-113 的根因仍未闭合；新增诊断尚未在真实 -1 现场触发过一次。`lock-latest-exclusive` 因独占锁阻塞提交前基线哈希读取而未执行。
- 本机实机环境为 Creo 10.0.0.0 / release 42；Creo 12.4、Creo 9 与 WorkBuddy 黑盒未验。

## 附件与摘要

Release 发布后见 `https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.35.3`。

四个附件（源码包摘要记录在同名 sidecar 中，一行 `<64 位 SHA256>  文件名`）：

- `MCP_CREO_MechDog-0.35.3-source.zip`
- `MCP_CREO_MechDog-0.35.3-source.zip.sha256`
- `MCP_CREO_MechDog-0.35.3-seed-library.zip`
- `MCP_CREO_MechDog-0.35.3-seed-library.zip.sha256`

- 种子包 SHA256：`182d25706e7868680712c2497148d6287957755554ce7d38fcc4fa6fb33be0f5`（24 个文件、9 个种子，两次构建摘要一致，与 `docs/seed_package.json` 一致）。
- 源码包：由本版发布提交的源码构建；字节数与 SHA256 见同名 sidecar，不写入包内。

## 未验

- Creo 12.4 与 Creo 9（本机环境为 Creo 10.0.0.0 / release 42）。
- WorkBuddy 黑盒验收。
- 闭合锥面/其他非圆柱形态的 trim；BUG-113 的 `ProMdlnameBackup=-1` 根因与真实现场触发。
- 发布后未重复执行 Creo 实机与 WorkBuddy 黑盒，实机范围以发布前记录为准。
