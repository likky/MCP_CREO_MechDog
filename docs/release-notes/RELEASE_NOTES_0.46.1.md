# MCP_CREO_MechDog 0.46.1 版本说明

2026-11-26 PATCH，公开工具数 111。上一版本：0.46.0（`v0.46.0`，提交 `d6055f9b101aa40013a6f8daf8330ccff837b824`）。

- **提交前零锁 callback 预检（[BUG-193](../work-items/BUG-193.md) 追加交付）**：`bridge.py` 新增零锁本地预检 `callback_admission_status()`——仅读取本机 `callback_result.json`、进程清单（PID/创建时间防复用）、部署产物指纹与绑定的 `toolkit_health.json` 缓存即判定放样准入，并对空 `artifacts` 字典做防御；`creo_loft` 与 `creo_surface_loft`（`creation_route="resident_panel"`）的 `submit()` 预检改用该函数，未就绪时在建 job 与取 Toolkit 通道锁之前直接拒绝，不再为拒绝本身占用通道；`creo_capabilities` 与 `blend_callback` 同步切至零锁预检并补齐 `command` 字段比对；显式 `callback_status()` 保留实时探针语义并写入 `binding`。回归用例覆盖零锁/零子进程探测/零作业拦截及 `binding` 失效（`tests/unit/test_feedback0451_loft_capabilities.py`）。
- **文档目录治理（[DEV-103](../work-items/DEV-103.md)）**：新增 `docs/README.md` 文档目录与维护规范，`AGENTS.md` 历史演进抽离至 `docs/development/GOVERNANCE_HISTORY.md`，70 个过程文档零改动归档至 `docs/archive/`；受发布完整性约束的台账与发布文档保留原路径。
- 实机验证环境为 Windows x64 / Python 3.12.10 / Creo Parametric 10.0.0.0（`release_numeric=42`）及匹配 Toolkit SDK：未加载态冷启动与显式探针后 `loft`、`surface_loft(resident_panel)` 均在建 job 前拒绝（`lock_ops=[]`、`new_jobs=[]`）且 `creo_capabilities` compact 显示 `runtime_ready=False`；启动回调后旧 `binding` 自动失效并零锁返回 `admit_to_worker=true`，显式 `callback_status()` 返回 `ready`（`live_identity_verified`），`runtime_ready=True`；加载态 `loft`（作业 `26dae70670f34a90aa109d2c25fb67f8`）与 `resident_panel`（作业 `c68cef0fb3114a0b83d14092ed6d94d9`，实测锁记录仅 `['submit']`）均 `succeeded` 且 `saved_file_reloaded_and_verified=True`。历史外部 WorkBuddy 0.46.0 黑盒记录见 [BUG-193 验收补录](../work-items/BUG-193.md)。
- 未测范围：Creo 9 / Creo 12.4 实机、本版零锁预检提交后的外部 WorkBuddy 黑盒复测。 [发布记录](../validation/RELEASE-0.46.1.md)

## 附件

- `MCP_CREO_MechDog-0.46.1-source.zip`
- `MCP_CREO_MechDog-0.46.1-source.zip.sha256`
- `MCP_CREO_MechDog-0.46.1-seed-library.zip`
- `MCP_CREO_MechDog-0.46.1-seed-library.zip.sha256`

种子包 SHA256 为 `8305c26aa2c91e20c0260ec7d61532ce64595e9d033084266b646adad0f46b0d`。两份同名 sidecar 分别记录各自 ZIP 的摘要。 [GitHub Release](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.46.1)
