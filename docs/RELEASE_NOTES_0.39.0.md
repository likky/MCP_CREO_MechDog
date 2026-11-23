# MCP_CREO_MechDog 0.39.0 版本说明

版本类型为 MINOR，公开工具数 111。本版基于 0.36.0 外部反馈（Creo 9.0.0.0）交付 [BUG-170](work-items/BUG-170.md)、[BUG-166](work-items/BUG-166.md)、[FEAT-076](work-items/FEAT-076.md) 与 [FEAT-077](work-items/FEAT-077.md)，并归档反馈原件与补录 [BUG-152](work-items/BUG-152.md) 外部回归确认。

上一版本：0.38.0（`v0.38.0`，提交 `266f8a014d60856dff598a49cac457fd24791bc7`）。

- **升级/重启后旧 Creo 会话不可达诊断与显式新会话入口**。当匹配安装目录的旧 Creo 进程仍在运行但探针返回 `-4` / `PRO_TK_BAD_CONTEXT` 时，`creo_startup_status` 与 `creo_session_status` 明确输出 `stale_session_detected=true`、`diagnosis="stale_session_needs_restart"` 并将“关闭旧 Creo 后重试”置为 `next_steps` 第一条；新增显式可选参数 `creo_startup_status(retry=true, force_new_session=true)` 允许在不自动杀旧进程的前提下启动新会话；`session_candidates` 明确标注 `diagnostic_only=true`、`selectable_by_pid=false`。[BUG-170](work-items/BUG-170.md)
- **跨会话恢复解死锁、`abandon_unknown_recovery` 出口、自适应预算与 `recovery_pending` 口径修正**。① `restore_baseline`、`abandon_new`、`accept_saved` 在 `inspect(live=False)` 时不再绑定重启前旧会话的失效 `session_fingerprint`（仅 `accept_live` 或当次 `live=True` 证据绑定会话），解除升级/重启 Creo 后的永久拒绝；② `creo_reconcile_model` 新增 `abandon_unknown_recovery(confirm_unknown_recovery=true)`，用于清掉已终态失败/未知恢复作业持有的 `recovery_pending` 而不改 revision 或文件（记 `disk_state_verified=false`、`session_state_verified=false`）；③ `creo_reconcile_model` 新增单次可选 `budget_seconds`（30–900 s）与 `verify_mode`（`identity`/`full`），默认恢复预算按模型记录边数自动抬高下限（6428 边 548 s）；④ 准入被 `recovery_pending` 阻塞时改报 `blocking_operation="recovery_pending"` 并在 `owner_snapshot` 中同时列出 `pending_job` 与 `recovery_pending`。[BUG-166](work-items/BUG-166.md)
- **边选择器 `feature` 过滤与 `creo_inspect_model` 空间近邻查询**。① `geometry_selector(target="edge")` 开放模型空间 `feature` 标签过滤（原生收集特征自身边及相邻面边）；② `creo_inspect_model(detail="full", section="edges"|"surfaces")` 新增 `near=[x,y,z]` 与 `max_distance_mm`，单次调用即可在千边级模型上按精确 3D 距离返回最近 `limit` 条记录并附 `distance_mm`；③ `creo_round` / `creo_chamfer` 参数说明补齐 `geometry_selector` 写法。[FEAT-076](work-items/FEAT-076.md)
- **零件 JPEG 预览隐藏基准要素与更新检查默认预算/advisory 明确化**。`native/preview.h` 将 `PreviewDatumDisplayGuard` 从仅装配扩展到 `PRO_ASSEMBLY || PRO_PART`（渲染前临时隐藏四项基准显示、析构必恢复、绝不写 `config.pro`）；`update_check.py` 默认网络超时从 5 s 放宽到 15 s 并输出 `advisory=true`、`affects_version_check=false`；逐字节归档反馈原件至 [upgrade-session-and-recovery-deadlock.md](validation/feedback-0.36.0-2026-11-23/originals/upgrade-session-and-recovery-deadlock.md)。[FEAT-077](work-items/FEAT-077.md)

本机环境为 Windows x64 / Python 3.12.10 / Creo 10.0.0.0（`release_numeric=42`）。本版通过 `bridge.py build` 编译验证，完成 `tools/test_feedback0360_recovery_preview_edges.py --live` 5/5 实机场景验收（零件构建预览与 JPEG 导出四项基准全部隐藏并恢复、`near` 定位 + `feature` 边选择器 R2 圆角精确去料、带旧会话指纹的跨会话 `restore_baseline(identity)` 与 `abandon_new`、`blocking_operation="recovery_pending"` + `abandon_unknown_recovery` 解锁后实机切除保存重载）。原始 6428 边 M113 P05 实机件、真实升级后旧 Creo `-4` 双进程启动现场、Creo 9/12 与 WorkBuddy 黑盒未验。详见[验收与发布记录](validation/RELEASE-0.39.0.md)。

## 附件

- `MCP_CREO_MechDog-0.39.0-source.zip`
- `MCP_CREO_MechDog-0.39.0-source.zip.sha256`
- `MCP_CREO_MechDog-0.39.0-seed-library.zip`
- `MCP_CREO_MechDog-0.39.0-seed-library.zip.sha256`

种子包 SHA256 为 `ef3724f92156efa5b7b01df55b9019eb541fd161ea769291793e9a5b83312587`。源码包摘要记录在同名 sidecar 中，两份 sidecar 分别记录对应 ZIP 的实际 SHA256。[GitHub Release](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.39.0)
