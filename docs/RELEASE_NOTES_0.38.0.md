# MCP_CREO_MechDog 0.38.0 版本说明

版本类型为 MINOR，公开工具数 111。本版交付 [BUG-169](work-items/BUG-169.md) 与 [FEAT-075](work-items/FEAT-075.md)，并归档 0.35.8 反馈原件与补录 [BUG-150](work-items/BUG-150.md) 外部 `frigate_v4` 验证结果。

上一版本：0.37.1（`v0.37.1`，提交 `87cade1e24c91140d97789516b2ff92b49518e86`）。

- **`extrude` 等操作回执统一回填 `feature_id`**。`native/generic.cpp` 在 `extrude_or_revolve()` 与 `execute_operation_body()` 中为已登记别名的操作写入 `feature_id`；`operation_results.py` 与 `job_projection.py` 同步放行，确保全量与 compact 轮询均返回真实特征 ID 而非 `null`。[BUG-169](work-items/BUG-169.md)
- **`linear_pattern` 非实体/零面 leader 双层防呆与诊断回执**。`schema.py` / `generic_bridge.py` 在建作业前拦截指向草图/基准别名的 `leader`；`native/linear_pattern.cpp` 在 `ProPatternCreate` 前通过 `ProFeatureTypeGet` 与 `ProFeatureGeomitemVisit(..., PRO_SURFACE)`（含 `ProFeatureGroupGet` / `ProGroupFeaturesCollect` 组内汇总）拒绝草图/曲线/基准及零实体面 leader（`LINEAR_PATTERN_NON_SOLID_LEADER`）与别名/原生类型冲突（`LINEAR_PATTERN_LEADER_ALIAS_MISMATCH`），全量与 compact 回执均保留 `leader_id`、`leader_kind`、`leader_surface_count`、`member_count`、`direction_reference`。[BUG-169](work-items/BUG-169.md)
- **`extrude mode="cut"` 开放单实体 `scope` 与 `depth_type="through_all"` 组合**。移除 `f08_contract.py` 对 `through_all + scope` 的前置拒绝，支持 `positive`/`negative`/`symmetric` 与负初始体 ID `-5778`，继续保留单目标约束、`new_body` 互斥、`scope_applied` 元素树回读、`non_target_bodies_unchanged` 校验及失败回滚保护。[FEAT-075](work-items/FEAT-075.md)
- **轮廓诊断与语法文档完善**。`profile_diagnostics.py` 在仅出现 `intersecting`/`tangent` 时给出拆分/合并指引而非建议放大 `closure_tolerance_mm`；`docs/REFERENCE_SYNTAX.md` 补齐切除 `swept_volume ∩ existing_material` 语义与多闭合环边界说明；逐字节归档 0.35.8 反馈原件至 [linear-pattern-leader-and-through-all-scope.md](validation/feedback-0.35.8-2026-11-23/originals/linear-pattern-leader-and-through-all-scope.md)。

本机环境为 Windows x64 / Python 3.12.10 / Creo 10.0.0.0（`release_numeric=42`）。本版通过 `bridge.py build` 编译验证，完成 `tools/test_feedback0358_pattern_scope.py --live` 8/8 实机场景（含草图别名预检、草图数字 ID 原生拒绝回滚、切除/凸台/特征组阵列、双体单向与三体双向 `through_all + scope`、`-5778` 初始体 `symmetric + through_all + scope` 与未知体 ID 回滚）及 `tools/test_linear_pattern.py --live` 3/3 回归，全部与解析体积一致并保存重载通过。原案 B025 原始 `request.json`/`model.json` 快照、Creo 9/12 实机与 WorkBuddy 黑盒未验。详见[验收与发布记录](validation/RELEASE-0.38.0.md)。

## 附件

- `MCP_CREO_MechDog-0.38.0-source.zip`
- `MCP_CREO_MechDog-0.38.0-source.zip.sha256`
- `MCP_CREO_MechDog-0.38.0-seed-library.zip`
- `MCP_CREO_MechDog-0.38.0-seed-library.zip.sha256`

种子包 SHA256 为 `f01e832b9a8b7ea3eef7f845f53af3502c1b3656e1896a90ab02f76bb6a36223`。源码包摘要记录在同名 sidecar 中，两份 sidecar 分别记录对应 ZIP 的实际 SHA256。[GitHub Release](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.38.0)
