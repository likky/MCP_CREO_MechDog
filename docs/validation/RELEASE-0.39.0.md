# 发布记录 v0.39.0

日期为 2026-11-23，版本类型为 MINOR，公开工具仍 111。

上一版本：0.38.0（`v0.38.0`，提交 `266f8a014d60856dff598a49cac457fd24791bc7`）。

## 验收范围

本版交付 [BUG-170](../work-items/BUG-170.md)、[BUG-166](../work-items/BUG-166.md)、[FEAT-076](../work-items/FEAT-076.md) 与 [FEAT-077](../work-items/FEAT-077.md)，归档 0.36.0 外部反馈原件 [upgrade-session-and-recovery-deadlock.md](feedback-0.36.0-2026-11-23/originals/upgrade-session-and-recovery-deadlock.md)（SHA256 `e196566d8bb7d0707807233a6a995d8e6c356afaa84398eb9b35dacc7813e9ba`），并在 [BUG-152](../work-items/BUG-152.md) 补录外部 Creo 9 连续保存/只读释放/大模型导出确认：

- `creo_startup.py`、`src/creo_mechdog/session_candidates.py`、`server.py`（[BUG-170](../work-items/BUG-170.md)）：检测旧 Creo 进程存活且探针 `-4`/`PRO_TK_BAD_CONTEXT`，在 `creo_startup_status` 与 `creo_session_status` 输出 `stale_session_detected=true`、`diagnosis="stale_session_needs_restart"` 与置顶 `next_steps`；新增 `creo_startup_status(retry=true, force_new_session=true)` 显式新会话入口（不杀旧进程）；`session_candidates` 标注 `diagnostic_only=true`、`selectable_by_pid=false`。
- `src/creo_mechdog/reconciliation.py`、`generic_bridge.py`、`server.py`（[BUG-166](../work-items/BUG-166.md)）：`restore_baseline`/`abandon_new`/`accept_saved` 在 `live=False` 时不再绑定已死旧会话指纹；新增 `abandon_unknown_recovery(confirm_unknown_recovery=true)` 元数据解锁（记 `disk_state_verified=false`、`session_state_verified=false`）；新增单次 `budget_seconds`（30–900 s）、`verify_mode` 与按边数自适应下限（6428 边 548 s）；`recovery_pending` 阻塞准入准确报 `blocking_operation="recovery_pending"`。
- `src/creo_mechdog/geometry_selectors.py`、`native/generic.cpp`、`src/creo_mechdog/model_queries.py`、`generic_bridge.py`、`server.py`（[FEAT-076](../work-items/FEAT-076.md)）：边 `geometry_selector` 开放模型空间 `feature` 标签过滤（特征自身边 ∪ 特征相邻面边）；`creo_inspect_model` 新增 `near=[x,y,z]` 与 `max_distance_mm` 空间近邻过滤；`creo_round`/`creo_chamfer` 补齐 `geometry_selector` 说明。
- `native/preview.h`、`src/creo_mechdog/update_check.py`（[FEAT-077](../work-items/FEAT-077.md)）：零件预览启用 `PreviewDatumDisplayGuard` 隐藏并恢复四项基准选项（不写 `config.pro`）；更新检查默认网络超时 5 s→15 s 并输出 `advisory=true`、`affects_version_check=false`。

## 环境与实机证据

- Windows x64 / Python 3.12.10 / Creo 10.0.0.0（`release_numeric=42`，安装目录 `D:\Program Files\PTC\Creo 10.0.0.0`）与匹配 Toolkit SDK；`bridge.py build` 编译 `build/creo_worker.exe` 成功（SHA256 `e1f4a3782146cb969264ded0a32185760dd2e0173dd36d3417e57c785257b321`）。
- `tools/test_feedback0360_recovery_preview_edges.py --live --confirm-session-usable`（报告 `build/feedback0360_recovery_preview_edges.json`，SHA256 `cd0e12d248374ac68dc409784b375ed677d85fb254709b6ee548695ba1a0c083`）：**5/5 通过**：
  - `F077_part_preview_hides_datums`（模型 `34bc1ab3…`，构建 `3c7057e2…`，导出 `db72f87e…`）：构建预览与 JPEG 导出均回报 `model_type="part"`、`applicable=true`、`attempted=true`、`hide_status="hidden"`、`restore_status="restored"`、`config_file_written=false`，四项基准选项 `get_code=0`/`hide_code=0`/`restore_code=0`，输出文件已核验。
  - `F076_near_edge_query_and_feature_scoped_round`（模型 `ebdf7e98…`，圆角 `f2840203…`）：`near=[30,30,20]` 一次定位边 `101`（`distance_mm=0.0`）；`round(size=2.0)` 组合 `geometry_selector(target="edge", point_mm=[30,30,20], feature="top_boss", tolerance_mm=0.5)` 成功，体积 `52000.0 → 51982.83180179726 mm³`（解析 `51982.831853071795`），`saved_file_reloaded_and_verified=true`。
  - `B166_1_cross_session_restore_baseline_identity`（作业 `8dad0d05…`）：带失效旧会话指纹模型经 `inspect(live=False)` → `restore_baseline` 成功恢复（`verification="identity"`、`saved_file_reloaded_and_verified=true`、`status="ready"`、rev 1）。
  - `B166_2_cross_session_abandon_new`（作业 `e80b0be2…`）：带失效旧会话指纹的 rev-0 模型经 `inspect(live=False)` → `abandon_new` 成功归档（`status="abandoned"`）。
  - `B166_3_recovery_pending_blocking_and_abandon_unknown_recovery`：`recovery_pending` 阻塞提交准确回报 `blocking_operation="recovery_pending"`、`owner_snapshot.pending_job=null`；`abandon_unknown_recovery(confirm_unknown_recovery=true)` 解锁为 `status="ready"`、`recovery_pending=null`、`disk_state_verified=false`；紧接实机切除 `46fdc9ef…` 成功（`45999.999999999985` vs 解析 `46000.0 mm³`，`saved_file_reloaded_and_verified=true`）。

## 种子包

`python tools/package_seeds.py --output build/release-0.39.0/MCP_CREO_MechDog-0.39.0-seed-library.zip --allow-record-mismatch` 首次构建得到摘要后回填 `docs/seed_package.json`；再用 `python tools/package_seeds.py --output build/release-0.39.0/confirm/MCP_CREO_MechDog-0.39.0-seed-library.zip` 重建确认，两次摘要一致：`ef3724f92156efa5b7b01df55b9019eb541fd161ea769291793e9a5b83312587`（24 个文件、9 个种子）。

## 单测证据

发布候选在 0.39.0 工作树上运行 `tools/test_unit.py`，全量 unittest 通过，0 失败、0 错误。下列数字取自本轮 `build/unit_test_report.json`，该报告不随源码包分发。

本轮 `run_id=ed728a933f9a4d45943c083b8ae1a621`，执行 4,443 项，0 失败、0 错误、6 跳过，耗时 347.23 s，报告 `version=0.39.0`、`status=completed`、`success=true`。受测提交 `6201d1b9959df01a349d324b4ede929a8f126376`（分支 `codex/feedback-0360-recovery-startup-edges`，`dirty=false`），源码指纹 `c2c4afbd2a05c1dfe1f77656b2f56e6c6156c2ba3e1f87ee591469c404eeef9f`，统计 672 个受 Git 跟踪的 `.py` 与原生头/源文件。后续回填本段文档不改动任何受跟踪 `.py` 或原生文件，源码指纹保持不变。跳过项为 Windows 符号链接权限、MSVC 独立辅助程序环境与未随仓库保存的历史作业证据，均不涉及本版改动。

语言与格式检查以 `tools/dev_check.py --skip-unit --work-item BUG-170` 执行：`success=true`，lint 0、unformatted 0（586 个 Python、69 个 C++），离线验收 3/3 通过（`test_update_check`、`test_model_reconciliation`、`test_mcp`）。

## 未测范围

- 原始 6428 边 M113 P05 履带轮实机件（以合成 6428 边单测 + 本机 Creo 10 多特征零件与跨会话恢复实机验证等价代码路径）。
- 真实升级后旧 Creo 返回 `-4` 时 `force_new_session=true` 拉起双进程现场（本机双 Windows 会话限制 Explorer 启动，由离线单测覆盖 `_drive()` 全分支）。
- Creo 9/12 实机与 WorkBuddy 外部黑盒验收未执行。

## 附件

- `MCP_CREO_MechDog-0.39.0-source.zip`
- `MCP_CREO_MechDog-0.39.0-source.zip.sha256`
- `MCP_CREO_MechDog-0.39.0-seed-library.zip`
- `MCP_CREO_MechDog-0.39.0-seed-library.zip.sha256`

种子包 SHA256 为 `ef3724f92156efa5b7b01df55b9019eb541fd161ea769291793e9a5b83312587`。源码包摘要记录在同名 sidecar 中，两份 sidecar 分别记录对应 ZIP 的实际 SHA256。

## 逐 ID 状态核对

| ID | 交付版本 | 实际 Release | 技术状态 | 卡首页 | 主台账 | 差异说明 |
| --- | --- | --- | --- | --- | --- | --- |
| [BUG-170](../work-items/BUG-170.md) | 0.39.0 | v0.39.0 | 已有修复但待验收 | 已有修复但待验收（0.39.0 交付离线单测与协议门禁全过） | 已有修复但待验收 | 剩真实 Creo 9 升级 `-4` 现场、WorkBuddy 黑盒 |
| [BUG-166](../work-items/BUG-166.md) | 0.39.0 | v0.39.0 | 已有修复但待验收 | 已有修复但待验收（0.39.0 交付并完成本机 Creo 10 实机 3/3 验收） | 已有修复但待验收 | 剩原始 6428 边实机件、Creo 9/12、WorkBuddy 黑盒 |
| [FEAT-076](../work-items/FEAT-076.md) | 0.39.0 | v0.39.0 | 已有修复但待验收 | 已有修复但待验收（0.39.0 交付并完成本机 Creo 10 实机 `near` + 按特征圆角验收） | 已有修复但待验收 | 剩原始 6428 边实机件、Creo 9/12、WorkBuddy 黑盒 |
| [FEAT-077](../work-items/FEAT-077.md) | 0.39.0 | v0.39.0 | 已有修复但待验收 | 已有修复但待验收（0.39.0 交付并完成本机 Creo 10 零件预览基准隐藏实机验收） | 已有修复但待验收 | 剩 Creo 9/12、WorkBuddy 黑盒 |

## 远端核对

发布后执行，当前未验证。[GitHub Release](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.39.0)
