# 发布记录 v0.35.3（0.35.3，2026-11-21）

- 版本：`0.35.3`（PATCH）。
- 发布提交：随 `v0.35.3` 标签发布，标签指向的提交即本版源码。
- 上一版本：0.35.2（`v0.35.2`，提交 `b90f0eda2a70c1f6ae5e4ae7df56c74be6786b24`）。
- 交付快照：[releases/0.35.3.json](../releases/0.35.3.json)。
- 版本说明：[RELEASE_NOTES_0.35.3.md](../RELEASE_NOTES_0.35.3.md)。
- Release：`https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.35.3`。
- 发布流程：[RELEASING.md](../development/RELEASING.md)；附件核对留存在 [RELEASE-POSTCHECK-2026-11-07.md](../development/RELEASE-POSTCHECK-2026-11-07.md) 的 `## v0.35.3` 段。
- 远端核对：发布后执行，当前未验证（待 `tools\check_release_assets.py --tag v0.35.3` 回填）。

## 逐 ID 状态核对

台账以 [BACKLOG.md](../BACKLOG.md) 与 `docs/releases/0.35.3.json`（frozen 交付集）为准；工作卡状态只读首页 `分类：` 行的粗体词。本批两项随 v0.35.3 发布，均保留已记录的未测范围（闭合锥面 trim、`ProMdlnameBackup=-1` 根因、其他 Creo 版本）。

| ID | 技术状态 | 交付版本 | 实际 Release | 卡首页 | 主台账 | 差异说明 |
| --- | --- | --- | --- | --- | --- | --- |
| [BUG-143](../work-items/BUG-143.md) | 部分交付 0.35.3，剩余待验收 | 0.35.3 | v0.35.3 | 部分交付 0.35.3，剩余待验收 | 部分交付 0.35.3，剩余待验收 | — |
| [BUG-113](../work-items/BUG-113.md) | 其它 agent 处理范围 | 0.35.3 | v0.35.3 | 其它 agent 处理范围 | 其它 agent 处理范围 | 根因仍开放，本版只增加诊断与排除证据。 |

## 发布前核对

- 源码身份：`main` 分支工作树提交；版本以 [version.py](../../version.py) 为准，`README.md` 标题/当前版/徽章、`docs/seed_manifest.json` 与 `seed_library/seed_manifest.json` 的 `compatible_server_version` 同步为 0.35.3，公开工具仍 110。
- Ruff：`ruff check` 与 `ruff format --check` 通过（不含 `docs/validation/` 历史原件与第三方/生成文件）。
- 单元测试：`tools/dev_check.py` 全量 4298 项通过、失败 0、异常 0、跳过 6；`build/unit_test_report.json` `success=true`。跳过项为环境限制（符号链接权限、MSVC x64 独立 helper 环境、归档证据缺失）。
- 原生构建：`.\.venv\Scripts\python.exe bridge.py build` 编译含新诊断的 `native/generic.cpp`，exit 0；构建指纹含 `NATIVE_BUILD_FLAGS /utf-8-v1`。
- 发布记录门禁：`tools\check_release_records.py --version 0.35.3` 须 exit 0；`tools\check_backlog_counts.py` 须 `consistent: true`。

## 实机与原生证据摘要（本机 Creo 10.0.0.0 / release 42）

- **BUG-143 非圆柱链路**：`build/probe_bug143_cone.py`（证据 `build/live_probe_bug143_cone.json`，模型 `8aac29c92def4d7d9960fe5c7f5dd942`）。开放圆锥套 quilt 79（2 面、1963.4907316790584 mm²）；mirror 作业 `69c28c2cc7404f0fb50f613adf437b15` → quilt 99、rev 2；trim 作业 `88c2fc0ca5e6462f8871d7eabbc6796d` 经 `c_mirrored` 标签解析到 quilt 99，保留区 x 15…25、687.2181023230302 mm²、rev 3；thicken 作业 `75bfabc8302549ddbdb2806ce34294bb` 经 `c_trimmed` 标签加厚 2.0、1500.0989754261154 mm³、rev 4。三步 `saved_file_reloaded_and_verified=true`、无 `save_failure`。
- **BUG-143 闭合锥面边界**：trim 作业 `77cde47c59974954a033548b2d667852`（quilt 119）由 mirror 标签正确解析、保留区 x 15…25（5 面/176 三角），但 `ProContourAreaEval` 返回 -1（`contour_area_eval_failed`），按无可测保留区回滚。
- **BUG-113 受控对照**：`build/probe_backup_lock.py` 系列（`build/probe_backup_lock_*.json`）。干净会话 10/10 保存成功（`..._fresh_natural3.json`）；30 s 延迟后第二次保存失败（`..._delay.json`，作业 `d446629db8ff4026b6ba98b867075a57`，`holders_observed=[]`）；`lock-latest`、`lock-next`、`lock-mid` 均未复现 -1；`lock-latest-exclusive` 因独占锁阻塞基线哈希读取未提交。
- **新增诊断回归**：`tests/unit/test_surface_save_recovery.py::test_readability_probes_stay_bounded_and_unfabricated` 锁定上限与“不伪造”语义；原生键断言含 `source_checkpoint_readable` 与 `candidate_readability`。

## 命令记录

```text
.\.venv\Scripts\python.exe tools\check_release_records.py --version 0.35.3
.\.venv\Scripts\python.exe tools\check_backlog_counts.py
.\.venv\Scripts\python.exe tools\dev_check.py
.\.venv\Scripts\python.exe bridge.py build
.\.venv\Scripts\python.exe tools\package_seeds.py --output build\MCP_CREO_MechDog-0.35.3-seed-library.zip
```

结果：种子包两次构建摘要一致（`182d2570…`，24 个文件、9 个种子）；`dev_check.py` 全量 4298 项通过、`success=true`；`bridge.py build` exit 0。

## 附件与摘要

源码包摘要记录在同名 sidecar 中，一行 `<64 位 SHA256>  文件名`。四个附件：

- `MCP_CREO_MechDog-0.35.3-source.zip`
- `MCP_CREO_MechDog-0.35.3-source.zip.sha256`
- `MCP_CREO_MechDog-0.35.3-seed-library.zip`
- `MCP_CREO_MechDog-0.35.3-seed-library.zip.sha256`

- 种子包 SHA256：`182d25706e7868680712c2497148d6287957755554ce7d38fcc4fa6fb33be0f5`（24 个文件、9 个种子，两次构建摘要一致，与 `docs/seed_package.json` 一致）。
- 源码包：由本版发布提交的源码构建；字节数与 SHA256 见同名 sidecar，不写入包内文件。

## 未验

- Creo 12.4 与 Creo 9（本机为 Creo 10.0.0.0 / release 42）。
- WorkBuddy 黑盒验收。
- 闭合锥面/其他非圆柱形态的 trim；BUG-113 的 `ProMdlnameBackup=-1` 根因与真实现场触发。
- 发布后未重复执行 Creo 实机与 WorkBuddy 黑盒，实机范围以发布前记录为准。
