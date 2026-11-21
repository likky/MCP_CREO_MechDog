# 发布记录 v0.35.4（0.35.4，2026-11-21）

- 版本：`0.35.4`（PATCH）。
- 本次发布提交：`29f9ed277d6436d9a0c6de4d4a1168fd51942444`（annotated 标签 `v0.35.4` 指向同一提交）。
- 上一版本：0.35.3（`v0.35.3`，提交 `0fa005dc44ac65c9d118e37e1bf9b58b87474486`）。
- 交付快照：[releases/0.35.4.json](../releases/0.35.4.json)。
- 版本说明：[RELEASE_NOTES_0.35.4.md](../RELEASE_NOTES_0.35.4.md)。
- Release：`https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.35.4`。
- 发布流程：[RELEASING.md](../development/RELEASING.md)；附件核对留存在 [RELEASE-POSTCHECK-2026-11-07.md](../development/RELEASE-POSTCHECK-2026-11-07.md) 的 `## v0.35.4` 段。
- 远端核对：2026-11-21 已核对，结果见下方“发布后远端核对”。

## 逐 ID 状态核对

台账以 [BACKLOG.md](../BACKLOG.md) 与 `docs/releases/0.35.4.json`（frozen 交付集）为准；工作卡状态只读首页 `分类：` 行的粗体词。本批一项随 v0.35.4 发布，保留“其他 Creo 版本与 WorkBuddy 未测”的开放范围。

| ID | 技术状态 | 交付版本 | 实际 Release | 卡首页 | 主台账 | 差异说明 |
| --- | --- | --- | --- | --- | --- | --- |
| [BUG-133](../work-items/BUG-133.md) | 已交付 0.35.4（准入按实测 1e-7 收紧） | 0.35.4 | v0.35.4 | 已交付 0.35.4（准入按实测 1e-7 收紧） | 已交付 0.35.4（准入按实测 1e-7 收紧） | — |

## 发布前核对

- 源码身份：`main` 分支工作树提交；版本以 [version.py](../../version.py) 为准，`README.md` 标题/当前版/徽章、`docs/seed_manifest.json` 与 `seed_library/seed_manifest.json` 的 `compatible_server_version` 同步为 0.35.4，公开工具仍 110。
- Ruff：`ruff check` 与 `ruff format --check` 通过（不含 `docs/validation/` 历史原件与第三方/生成文件）。
- 单元测试：`tools/dev_check.py` 全量 4299 项通过、失败 0、异常 0、跳过 6；`build/unit_test_report.json` `success=true`。跳过项为环境限制（符号链接权限、MSVC x64 独立 helper 环境、归档证据缺失）。
- 原生构建：`.\.venv\Scripts\python.exe bridge.py build` exit 0；原生 harness `tools/test_assembly_pose.py` `success=true`，I032 拒绝、30° 接受、七位小数矩阵原样回显。
- 发布记录门禁：`tools\check_release_records.py --version 0.35.4` 须 exit 0；`tools\check_backlog_counts.py` 须 `consistent: true`。

## 实机证据摘要（本机 Creo 10.0.0.0 / release 42）

- 精度阶梯（`build/live_bug133_precision.json`）：9/8/7 位小数 28° 矩阵残差 `4.5e-10`/`7.664e-9`/`4.7552320081578614e-8`，`ProAsmcompAssemble` 成功且保存重载 true。
- 扰动边界（`build/live_bug133_boundary.json`）：残差 `2.241e-7`、`4.890e-7` 均失败，`ProAsmcompAssemble` 返回 `-2`。
- 六位小数失败路径（`build/live_bug133_tolerance.json`、`live_bug133_controls.json`、`live_bug133_reposition.json`）：`ProAsmcompAssemble` 与 `ProAsmcompPositionSet` 均返回 `-2`，失败作业 `effect_status="rolled_back"`，保存重载 false。
- 正例对照：单位矩阵 + 显式 `1e-5`、精确 28° 矩阵 + 默认容差在创建/重定位均成功且保存重载 true。
- 结论：内核只接受近似严格正交矩阵，准入上限不能高于 `1e-7`；本版把 Python 与原生准入统一收紧到该值，不修复输入矩阵。

## 命令记录

```text
.\.venv\Scripts\python.exe bridge.py build
.\.venv\Scripts\python.exe tools\test_assembly_pose.py
.\.venv\Scripts\python.exe tools\dev_check.py
.\.venv\Scripts\python.exe tools\package_seeds.py --output build\MCP_CREO_MechDog-0.35.4-seed-library.zip
.\.venv\Scripts\python.exe tools\check_release_records.py --version 0.35.4
.\.venv\Scripts\python.exe tools\check_backlog_counts.py
```

结果：种子包两次构建摘要一致（`ba556e79…`，24 个文件、9 个种子）；`dev_check.py` 全量 4299 项通过、`success=true`；`bridge.py build` exit 0。

## 附件与摘要

源码包摘要记录在同名 sidecar 中，一行 `<64 位 SHA256>  文件名`。四个附件：

- `MCP_CREO_MechDog-0.35.4-source.zip`
- `MCP_CREO_MechDog-0.35.4-source.zip.sha256`
- `MCP_CREO_MechDog-0.35.4-seed-library.zip`
- `MCP_CREO_MechDog-0.35.4-seed-library.zip.sha256`

- 种子包 SHA256：`ba556e79d80f18268c38d9b5044ac15a07afa6cc676153dd8e310cc9c9aec325`（24 个文件、9 个种子，两次构建摘要一致，与 `docs/seed_package.json` 一致）。
- 源码包：由本版发布提交的源码构建；字节数与 SHA256 见同名 sidecar，不写入包内文件。

## 发布后远端核对（2026-11-21）

- Release id `453623766`，非 draft、非 prerelease，target `main`，`created_at=2026-11-21T10:52:04Z`，`published_at=2026-11-21T10:53:46Z`，正文 2431 字符（含四个附件名与“源码包摘要记录在同名 sidecar 中”）。
- 远端标签：`v0.35.4` tag object `e6e3c334cf73e8315963f64fb9f7c4c5696cf320`，peeled commit `29f9ed277d6436d9a0c6de4d4a1168fd51942444`；远端 `main` 同为 `29f9ed2`。
- `gh` 不可用、Python urllib 自动下载被网络重置，改用已认证 GitHub API 下载四附件到本地目录，再执行 `tools\check_release_assets.py --tag v0.35.4 --version 0.35.4 --dir build\release-assets\v0.35.4 --body-file build\release-assets\v0.35.4-body.md`，exit 0，输出“local_verified: four assets present; both sidecars match (version 0.35.4); release body self-proof verified”。远端 API 摘要、本地重算与 sidecar 内容逐一致：

| 附件 | 字节 | SHA256 |
| --- | ---: | --- |
| `MCP_CREO_MechDog-0.35.4-source.zip` | 11 490 057 | `681f1b1f1c0babb0561225a470d1d4e7a891c9d38d007c2583e6794934fff5e7` |
| `MCP_CREO_MechDog-0.35.4-source.zip.sha256` | 101 | `35542befea27121dd0ad0bcaa21a382e27a69ade64d84ae8c37ae2ca49b12212` |
| `MCP_CREO_MechDog-0.35.4-seed-library.zip` | 493 442 | `ba556e79d80f18268c38d9b5044ac15a07afa6cc676153dd8e310cc9c9aec325` |
| `MCP_CREO_MechDog-0.35.4-seed-library.zip.sha256` | 107 | `59aa5f581ca07e13d4929d1c0477336762d8ba341510d69de98d4e0a3ea144f3` |

- 包内快照与 `main` 的差异：冻结源码包内的 POSTCHECK 与发布记录仍是打包时点措辞（`remote_verification=pending`），本段实际结果与 `docs/releases/0.35.4.json` 的 `verified` 只存在于 `main`，不改写、不重发已发布附件。

## 未验

- Creo 12.4 与 Creo 9（本机为 Creo 10.0.0.0 / release 42）。
- WorkBuddy 黑盒验收。
- 发布后未重复执行 Creo 实机与 WorkBuddy 黑盒，实机范围以发布前记录为准。
