# FEAT-075：`extrude` 切除开放 `scope` 与 `depth_type="through_all"` 组合

- 类型：功能
- 优先级：P1

分类：**已有修复但待验收**（0.38.0 已交付并完成本机 Creo 10.0.0.0 实机验收；Creo 9/12 与 WorkBuddy 黑盒未验）

- 目标版本：0.38.0（MINOR）

来源：[0.35.8 反馈原件 §3.1、§7](../validation/feedback-0.35.8-2026-11-23/originals/linear-pattern-leader-and-through-all-scope.md)。关联 [BUG-150](BUG-150.md) 与 [DEV-081](DEV-081.md)（F08 切除作用域）。

## 问题与目标

`src/creo_mechdog/f08_contract.py` 自 B4 初版起以 `F08_SCOPE_THROUGH_ALL_UNSUPPORTED` 拒绝 `extrude mode="cut"` 同时携带 `depth_type="through_all"` 与 `scope={"kind":"bodies","body_ids":[...]}`，原因是当时尚未在实机上验证 `PRO_E_BODY_SELECT` 与 `PRO_EXT_DEPTH_TO_ALL` / `PRO_EXT_DEPTH_FROM_ALL` 的交互。在多实体零件上，贯穿切除因此无法限定到单个目标实体。

目标：放开单实体 `scope` 与 `depth_type="through_all"`（含 `positive`/`negative`/`symmetric` 与负初始体 ID `-5778`），保持原有单目标限制、`new_body` 互斥、`scope_applied` 元素树回读、`non_target_bodies_unchanged` 校验与失败回滚保护。

## 实现变更

- `src/creo_mechdog/f08_contract.py`：移除 `validate_scope()` 对 `depth_type == "through_all"` 的前置拒绝与 `F08_SCOPE_THROUGH_ALL_UNSUPPORTED` 准入码；同步更新 `LIMITATION_NOTE`（保持 ≤160 字符）。
- `src/creo_mechdog/capabilities.py`、`server.py`、`docs/REFERENCE_SYNTAX.md`：更新 `cut_scope` 能力边界与 `creo_extrude` 文档说明。
- `tests/unit/test_f08_contract.py`：更新契约断言，覆盖 `through_all` + 单实体 `scope`（正 ID 与 `-5778`、`positive`/`negative`/`symmetric`）准入通过，且多实体、`new_body`、非 cut 仍拒绝。

## 验收证据（2026-11-23）

- 环境：Windows x64 / Python 3.12.10 / Creo 10.0.0.0（`release_numeric=42`）/ 匹配 Toolkit SDK，执行器 `build/creo_worker.exe` SHA256 `ec443506e5e91d93b99a08973a9bf37b4ab50130abcea6f88ec53a5613e9db9e`。
- 实机测试脚本 `tools/test_feedback0358_pattern_scope.py --live --confirm-session-usable`（报告 `build/feedback0358_pattern_scope.json`，SHA256 `ad8715c31aa8e2590475f99ed5c40e5587e580a45564dc002497e2b842a3f447`）：
  1. `F075_1_two_body_positive_through_all_scope`（模型 `dbd649f8c9324f459b148044b7676a0f`，作业 `53d698c3f6d44abfa47225e646e6ff29`）：Z 向堆叠双体（Body 52 在 Z∈[0,20]，Body 92 在 Z∈[30,50]），XY Ø20 圆 `through_all` + `positive` + `scope=[52]`：`applied_body_ids=[52]`、`non_target_bodies_unchanged=true`、Body 92 面数（6）与包络完全不变、体积 `144000.0 → 137716.8146928204 mm³`（解析 `137716.81469282042`），`saved_file_reloaded_and_verified=true`。
  2. `F075_2_three_body_symmetric_through_all_scope`（模型 `18eb4265ff51478895adfce37d6dac11`，作业 `1413361eca854c1d8eff4a2a7ea7549a`）：Z 向三体（Body 131 在 Z∈[-40,-20]，Body 52 在 Z∈[-10,10]，Body 92 在 Z∈[20,40]），`through_all` + `symmetric` + `scope=[52]`：`applied_body_ids=[52]`、`non_target_bodies_unchanged=true`、两侧非目标体 92/131 均未变、体积 `216000.0 → 209716.8146928204 mm³`（解析 `209716.81469282042`），`saved_file_reloaded_and_verified=true`。
  3. `F075_3_initial_body_minus5778_symmetric_through_all`（模型 `2d6ed5675175466a943296241f5cb16a`，作业 `75ce428de3e84725b74bed5e9391abcf`）：放样基准件初始体 `-5778`，`through_all` + `symmetric` + `scope=[-5778]`（反馈 §7 复现例）：`applied_body_ids=[-5778]`、`non_target_bodies_unchanged=true`、体积 `65716.8146928204 mm³`（解析 `65716.81469282041`），`saved_file_reloaded_and_verified=true`。
  4. `F075_4_unknown_body_through_all_rollback`（模型 `dbd649f8c9324f459b148044b7676a0f`，作业 `e458ebb3ae9043b5bf52865d68fbffb8`）：`through_all` + `scope=[999999]` 以 `F08_SCOPE_RESOLVE_FAILED` 失败并回滚，revision `2 → 2`、体积保持 `137716.8146928204 mm³`。
- 未验范围：Creo 9/12 实机与 WorkBuddy 外部黑盒未验；多目标 `body_ids` 与 `revolve` 仍按现有 F08 契约保持拒绝。
