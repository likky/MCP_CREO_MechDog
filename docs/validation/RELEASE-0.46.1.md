# 发布记录 v0.46.1

2026-11-26 PATCH，公开工具数 111。上一版本：0.46.0（`v0.46.0`，提交 `d6055f9b101aa40013a6f8daf8330ccff837b824`）。

## 验收范围

交付 [BUG-193](../work-items/BUG-193.md) 的提交前零锁 callback 预检与 [DEV-103](../work-items/DEV-103.md) 文档目录治理。BUG-193：`bridge.py` 新增 `_callback_context()` 与零锁本地预检 `callback_admission_status()`（基于本机 `callback_result.json`、进程清单 PID/创建时间防复用、部署产物指纹与绑定的 `toolkit_health.json` 缓存判定准入，并对空 `artifacts` 字典防御）；`generic_bridge.submit()` 放样/曲面放样预检改用零锁预检，未就绪时在建 job 与取 Toolkit 通道锁之前直接拒绝；`creo_capabilities` 与 `blend_callback` 同步切至零锁预检并补齐 `command` 字段比对；显式 `callback_status()` 保留实时探针并写入 `binding`；`tests/unit/test_feedback0451_loft_capabilities.py` 补充零锁/零子进程探测/零作业拦截及 `binding` 失效回归用例。DEV-103：新增 `docs/README.md` 与归档规范，`AGENTS.md` 历史演进抽离至 `GOVERNANCE_HISTORY.md`，70 个过程文档零改动归档至 `docs/archive/`。

本机 Windows x64 / Python 3.12.10 / Creo Parametric 10.0.0.0（`release_numeric=42`）及匹配 Toolkit SDK 实机链路：

- 未加载态冷启动与显式探针后：`loft` 与 `surface_loft(resident_panel)` 均在建 job 前拒绝（`lock_ops=[]`、`new_jobs=[]`），`creo_capabilities` compact 显示 `runtime_ready=False`。
- 启动回调后：`callback_admission_status()` 自动失效旧 `binding` 并零锁返回 `admit_to_worker=true`；显式 `callback_status()` 返回 `ready`（`live_identity_verified`）；`creo_capabilities` compact 实时切为 `runtime_ready=True`。
- 加载态建模与保存重载：`loft`（作业 `26dae70670f34a90aa109d2c25fb67f8`，模型 `5f838529a5f84a129ad2ce2752a4829c`）与 `surface_loft(resident_panel)`（作业 `c68cef0fb3114a0b83d14092ed6d94d9`，模型 `be9ca9b34978489d94ae82e6743a1c39`，实测锁记录仅 `['submit']`）均 `succeeded` 且 `saved_file_reloaded_and_verified=True`。
- 历史外部 WorkBuddy 0.46.0 黑盒记录见 [BUG-193-CREO10-WORKBUDDY-0.46.0-2026-11-26](BUG-193-CREO10-WORKBUDDY-0.46.0-2026-11-26.md)。

离线门禁（Windows / Python 3.12.10）：`tools/dev_check.py` 通过（`success=true`，单测全过，`lint_findings=0`，`unformatted_files=0`）；`tools/test_mcp.py --offline` 与 `--offline --legacy-entry` 通过（`tool_count=111`，`capability_contract_verified=true`）。发布门禁要求候选工作树全量单测通过，打包时核对本轮 `tools/test_unit.py` 报告与发布提交的源码指纹。发布后远端核对见 [发布后核对记录](../development/RELEASE-POSTCHECK-2026-11-07.md) 和 Release 正文。

未测范围：Creo 9 / Creo 12.4 实机、本版零锁预检提交后的外部 WorkBuddy 黑盒复测。

## 逐 ID 状态核对

[主台账](../BACKLOG.md) · [开发入口](../DEVELOPMENT.md) · [版本说明](../release-notes/RELEASE_NOTES_0.46.1.md)

| ID | 交付版本 | 实际 Release | 技术状态 | 卡首页 | 主台账 | 差异说明 |
| --- | --- | --- | --- | --- | --- | --- |
| BUG-193 | 0.46.1 | v0.46.1 | 部分交付 | 部分交付 | 部分交付 | 零锁预检与 Creo 10 未加载拦截、回调自动准入、加载态建模保存重载全链路实机通过；Creo 9 / 12.4 实机与本版提交后的外部 WorkBuddy 黑盒复测未排期。 |
| DEV-103 | 0.46.1 | v0.46.1 | 已交付 | 已交付 | 已完成（0.46.1 交付） | 文档目录治理与历史归档，无剩余范围。 |

## 附件与远端核对

- `MCP_CREO_MechDog-0.46.1-source.zip`
- `MCP_CREO_MechDog-0.46.1-source.zip.sha256`
- `MCP_CREO_MechDog-0.46.1-seed-library.zip`
- `MCP_CREO_MechDog-0.46.1-seed-library.zip.sha256`

种子包 SHA256 为 `8305c26aa2c91e20c0260ec7d61532ce64595e9d033084266b646adad0f46b0d`。两份同名 sidecar 分别记录各自 ZIP 的摘要。远端校验发布后执行，当前未验证。 [GitHub Release](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.46.1)
