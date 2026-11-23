# 发布记录 v0.40.0

日期为 2026-11-23，版本类型为 MINOR，公开工具仍 111。

上一版本：0.39.0（`v0.39.0`，提交 `7518f0fa2b60287319d2e78e26f1385c9b9ee34b`）。

## 验收范围

本版交付 [BUG-171](../work-items/BUG-171.md)、[BUG-172](../work-items/BUG-172.md)、[BUG-173](../work-items/BUG-173.md) 与 [BUG-174](../work-items/BUG-174.md)，逐字节归档 0.35.8 三份外部反馈原件至 [SOURCE_MANIFEST.json](feedback-0.35.8-2026-11-23-hang-recovery/SOURCE_MANIFEST.json)（[verify-hang-and-recovery-90s-deadlock.md](feedback-0.35.8-2026-11-23-hang-recovery/originals/verify-hang-and-recovery-90s-deadlock.md) SHA256 `493988bc0b02a9030ffab9cf7bf75beeddf36d19a4c9107d0a69553be12a152e`、[three-point-plane-sketch-reference-and-autodim-misreport.md](feedback-0.35.8-2026-11-23-hang-recovery/originals/three-point-plane-sketch-reference-and-autodim-misreport.md) SHA256 `d0b2ff260b34c70e1c6760c3fb9803f3856414b9e15ef770bb113cf768186664`、[frigate-v4-status-and-deviations.md](feedback-0.35.8-2026-11-23-hang-recovery/originals/frigate-v4-status-and-deviations.md) SHA256 `a668d2105f7d9f2b12b886882dc1788bf7c05677b3abec4f2cb2f0606b897154`）：

- `native/recovery_deadline.h`、`native/generic.cpp`、`src/creo_mechdog/reconciliation.py`、`server.py`（[BUG-171](../work-items/BUG-171.md)）：原生恢复截止定时器在 `ExitProcess(31)` 前同步写出带 `completion_stage="recovery_phase_timeout"` 的最小 `native_result.json`；`reconcile_native` 的 `restore_baseline(verify_mode="full")` 复用 `before` 快照消除第二次重复 `inspection()`；恢复预算上限扩至 1800 s 并按 edges/features/surfaces 自适应抬升下限；终态 `recovery_pending` 在 `_recovery_wait()` 返回 `state="terminal_unconfirmed"` 解锁指引。
- `native/generic.cpp`（[BUG-172](../work-items/BUG-172.md)）：新增轻量查询助手 `find_default_csys_id()`、`collect_datum_planes_quiet()`、`model_has_solid()`、`active_body_count()` 与 `check_model_health()`，替换草图/基准解析/体选项/拉伸与常规操作尾部的冗余全量 `inspection()`；热循环改用 `check_quiet(code, op, item_id)` 消除逐半边 `fflush()` 刷盘，补齐 `INSPECT_PROGRESS`/`INSPECT_SUMMARY` 与遍历上限。
- `native/generic.cpp`、`native/sketch_coordinates.cpp`、`native/sketch_solver.cpp`（[BUG-173](../work-items/BUG-173.md)）：单轴倾斜三点基准面草图缺失第二正交投影锚点时自动创建并复用正交辅助锚定面（`SKETCH_ANCHOR_HELPER=1`），基准面投影按正交等级分层（`tier0`→`tier1`→`tier2`）；回执与失败暂存新增 `section_references`，`coordinates` 解算失败同时报告 `ProSectionSolve` 与救援 `ProSectionAutodim` 返回码。
- `src/creo_mechdog/schema.py`、`src/creo_mechdog/operation_results.py`、`src/creo_mechdog/compact_sections.py`、`bridge.py`、`generic_bridge.py`、`src/creo_mechdog/job_pages.py`、`docs/REFERENCE_SYNTAX.md`（[BUG-174](../work-items/BUG-174.md)）：`dump_plan_operations()` 保留显式 `chamfer_type`；盲切回执新增 `cut_volume_check` 低去料告警（`< 5%` 解析棱柱体积）；`bridge.spawn_detached_runner()` 尝试 `CREATE_BREAKAWAY_FROM_JOB` 并披露 `runner_detached_from_job`；补充语法参考文档。

## 环境与实机证据

- Windows x64 / Python 3.12.10 / Creo 10.0.0.0（`release_numeric=42`，安装目录 `D:\Program Files\PTC\Creo 10.0.0.0`）与匹配 Toolkit SDK；`bridge.py build` 编译 `build/creo_worker.exe` 成功（SHA256 `89d04068ca8fb9c066910ceb2633d809adb0475776de365f5d3fb337e193608d`，`source_digest=e9937e454b9831b54eb2a58680949aba343f0792e7c368e53e60e4b0e7785583`）。
- `tools/test_feedback0358_hang_recovery_sketch.py`（报告 `build/feedback0358_hang_recovery_sketch.json`）：**4/4 通过**（模型 `c7f5b1812ee34ed084bb4254f6015258` / `acc0358_7acf34`）：
  - `S1_base_and_tilted_plane`（作业 `875157fbe0f44d30a7631c94040a3308`）：400×400×400 mm 基体与 B045 三点斜基准面 `pl_b045` 创建成功，体积 `63,999,999.999999985 mm³`（解析 `64,000,000.0 mm³`），`runner_detached_from_job=true`，`saved_file_reloaded_and_verified=true`。
  - `S2_b045_three_plates_auto_anchor_and_fast_inspect`（作业 `efb14986f3284062a067b88a86e0791b`）：无手工锚定面下提交 B045 的 3 个 `coordinates` 四线方形草图并各拉伸 2 mm，总耗时 **9.094 s**；首草图 `helper_anchor_created=true`、后两草图复用（`helper_anchor_created=false`），3 草图均 `anchor_count=2`、`origin_pin_available=true`；全量 `INSPECT_SUMMARY` 仅 **3 次**、逐边日志 **0 行**；体积增量 `+59,999.99999999255 mm³`（解析 `+60,000.0 mm³`），`saved_file_reloaded_and_verified=true`。
  - `S3_inline_d1d2_chamfer_and_cut_volume_check`（作业 `bef52458197c4a4cbb3641f9aa384560`）：经内联 `dump_plan_operations` 路径提交 `chamfer_type="d1_d2"`（15×10 mm，去料 `-29,999.99999999255 mm³` vs 解析 `-30,000.0 mm³`）、擦边盲切（`removal_ratio=0.01`、`low_removal_warning=true`）与完整盲切（`removal_ratio=1.0`、`low_removal_warning=false`），总体积变化 `-56,000.0 mm³`，`saved_file_reloaded_and_verified=true`。
  - `S4_restore_baseline_single_full_and_1800s_identity`：`restore_baseline(verify_mode="full", budget_seconds=1200)`（作业 `a79742bf7b8142f696d91b043436bc9c`）成功且 `native.log` 仅 **1 条** `INSPECT_SUMMARY`（526 ms）；`restore_baseline(verify_mode="identity", budget_seconds=1800)`（作业 `d137ff1e00d4403689d98aaaf739ee5f`）成功，模型恢复 `status="ready"`、`revision=3`。

## 种子包

`python tools/package_seeds.py --output build/release-0.40.0/MCP_CREO_MechDog-0.40.0-seed-library.zip --allow-record-mismatch` 首次构建得到摘要后回填 `docs/seed_package.json`；再用 `python tools/package_seeds.py --output build/release-0.40.0/confirm/MCP_CREO_MechDog-0.40.0-seed-library.zip` 重建确认，两次摘要一致：`507bd0019650dd397046b1ed2cfb735a4f840a4174487b45dab55e536e8db77f`（24 个文件、9 个种子）。

## 单测证据

发布候选在 0.40.0 工作树上运行 `tools/test_unit.py`，全量 unittest 通过，0 失败、0 错误。下列数字取自本轮 `build/unit_test_report.json`，该报告不随源码包分发。

本轮 `run_id=d24025f4b4c44234971954fa592316af`，执行 4,453 项，0 失败、0 错误、6 跳过，耗时 327.06 s，报告 `version=0.40.0`、`status=completed`、`success=true`。受测提交 `0c86f01879ebecc302936f3f0c8003179fdf22ee`（分支 `codex/feedback-0358-hang-recovery-sketch`，`dirty=false`），源码指纹 `8f192e9625eea48e281425e6d67ba322a828d2bd364620bbfcbed2934b23e7e9`，统计 674 个受 Git 跟踪的 `.py` 与原生头/源文件。后续回填本段文档不改动任何受跟踪 `.py` 或原生文件，源码指纹保持不变。跳过项为 Windows 符号链接权限、MSVC 独立辅助程序环境与未随仓库保存的历史作业证据，均不涉及本版改动。

语言与格式检查以 `tools/dev_check.py --skip-unit --work-item BUG-171` 执行：`success=true`，lint 0、unformatted 0（588 个 Python、69 个 C++），离线验收 3/3 通过（`test_update_check`、`test_model_reconciliation`、`test_mcp`）。

## 未测范围

- 外部报告方的 474 特征 `frigate_v4` / 53 特征 `carrier_v2` 原始本地模型文件未随反馈包附带（已在相同几何参数的三点斜基准面上用等价 6 步作业与恢复场景完成本机 Creo 10.0.0.0 实机验证）。
- 宿主 Job Object 显式禁止 `CREATE_BREAKAWAY_FROM_JOB` 时的客户端强制退出实机现场（回退分支由单元测试覆盖）。
- Creo 9/12 实机与 WorkBuddy 外部黑盒验收未执行。

## 附件

- `MCP_CREO_MechDog-0.40.0-source.zip`
- `MCP_CREO_MechDog-0.40.0-source.zip.sha256`
- `MCP_CREO_MechDog-0.40.0-seed-library.zip`
- `MCP_CREO_MechDog-0.40.0-seed-library.zip.sha256`

种子包 SHA256 为 `507bd0019650dd397046b1ed2cfb735a4f840a4174487b45dab55e536e8db77f`。源码包摘要记录在同名 sidecar 中，两份 sidecar 分别记录对应 ZIP 的实际 SHA256。

## 逐 ID 状态核对

| ID | 交付版本 | 实际 Release | 技术状态 | 卡首页 | 主台账 | 差异说明 |
| --- | --- | --- | --- | --- | --- | --- |
| [BUG-171](../work-items/BUG-171.md) | 0.40.0 | v0.40.0 | 已有修复但待验收 | 已有修复但待验收（0.40.0 已交付并完成本机 Creo 10.0.0.0 实机验收；外部原始 `frigate_v4` 模型、Creo 9/12 与 WorkBuddy 黑盒未验） | 已有修复但待验收 | 剩原始 53 特征 `carrier_v2`、Creo 9/12、WorkBuddy 黑盒 |
| [BUG-172](../work-items/BUG-172.md) | 0.40.0 | v0.40.0 | 已有修复但待验收 | 已有修复但待验收（0.40.0 已交付并完成本机 Creo 10.0.0.0 实机验收；外部原始 `frigate_v4` 模型、Creo 9/12 与 WorkBuddy 黑盒未验） | 已有修复但待验收 | 剩原始 53 特征 `carrier_v2`、Creo 9/12、WorkBuddy 黑盒 |
| [BUG-173](../work-items/BUG-173.md) | 0.40.0 | v0.40.0 | 已有修复但待验收 | 已有修复但待验收（0.40.0 已交付并完成本机 Creo 10.0.0.0 实机验收；外部原始 `frigate_v4` 模型、Creo 9/12 与 WorkBuddy 黑盒未验） | 已有修复但待验收 | 剩 Creo 9/12、WorkBuddy 黑盒 |
| [BUG-174](../work-items/BUG-174.md) | 0.40.0 | v0.40.0 | 已有修复但待验收 | 已有修复但待验收（0.40.0 已交付并完成本机 Creo 10.0.0.0 实机验收；外部原始 `frigate_v4` 模型、Creo 9/12 与 WorkBuddy 黑盒未验） | 已有修复但待验收 | 剩客户端退出脱离实测、Creo 9/12、WorkBuddy 黑盒 |

## 远端核对

已发布并核对（2026-11-23）。Release id `455632891`（非 draft、非 prerelease），创建于 `2026-11-23T15:44:41Z`、发布于 `2026-11-23T15:45:26Z`；附注标签 `v0.40.0`（对象 `890b21c31ae7be9177e7ff5b0e2d2da185b05891`）指向 `9b7bdaa84675fef364972240a8f3d7c7677e2361`（本版合入提交），远端 `refs/heads/main` 在核对时指向同一提交。`python -X utf8 tools/check_release_assets.py --tag v0.40.0` 返回 `v0.40.0: four assets downloaded and verified; both sidecars match; release body self-proof verified`（exit 0），四个附件与两份 sidecar 摘要及远端 API digest 一致：源码包 `78ebfc8f9d93a6b3edf9fa7eb3079e2550c0ef74d2e5e28c9560a794a40ab56c`（11,971,720 字节，sidecar `aae5ef20a537cefc8426fe26265e1bbf9fc29ddcdaf782182571a772718f56a1`），种子包 `507bd0019650dd397046b1ed2cfb735a4f840a4174487b45dab55e536e8db77f`（493,442 字节，sidecar `b80175c9d34fe426922319d5c20ff644715959f051ec256718c8df66eb4ceb69`）。附件字节、摘要与环境侧发布通道见 [GitHub Release](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.40.0) 和[发布后核对](../development/RELEASE-POSTCHECK-2026-11-07.md)。
