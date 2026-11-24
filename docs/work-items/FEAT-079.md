# FEAT-079：`creo_round` / `creo_chamfer` 多引用集合失败定位诊断

- 类型：功能
- 优先级：P1

分类：**已有修复但待验收**（0.41.0 已交付并完成本机 Creo 10.0.0.0 实机验收；Creo 9/12 与 WorkBuddy 黑盒未验）

- 目标版本：0.41.0（MINOR）

来源：[0.39.0 原始反馈（Creo 9 全圆边选择器与面积查询）](../validation/feedback-0.39.0-2026-11-23/originals/creo9-full-circle-edge-selector-and-area-inspection.md) §2。

## 实现内容

1. `native/generic.cpp`：拆出共享 `build_round_tree()`；当多引用（>1 集）`round`/`chamfer` 创建或再生失败时，先删除失败特征，再通过 `probe_round_references()` 在安全上限（前 20 集）内逐集创建并立即删除单集探针，定位不可行引用索引，经 `stage_operation_result` 在失败回执中输出 `failed_reference_index`、`failed_reference` 与 `round_failure`（含 `failed_indices`、`probed_count`、`total_references`），事务保持完整回滚。
2. `src/creo_mechdog/compact_sections.py`、`src/creo_mechdog/operation_results.py`：保留 `failed_reference_index`、`failed_reference` 与 `round_failure` 为失败证据键。

## 验收证据（2026-11-24）

- 实机 `tools/test_feedback0390_edge_inspect.py`（报告 `build/feedback0390_edge_inspect.json`）：
  - `S2`（作业 `3f6cc9016f464fc3a08eaaaf79485f85`，2 集 D10 倒角，引用 0 位于 40×20 主体顶边可行、引用 1 位于 2×2 薄唇边不可行）：精准返回 `failed_reference_index=1`、`round_failure.failed_indices=[1]`、`probed_count=2`，且 `rollback_succeeded=true`、模型体积与回滚前完全一致。
- 单元测试：`tests/unit/test_feedback0390_fixes.py::Feat079RoundMultiSetLocalizationTests` 全部通过。
- 未验范围：Creo 9/12 与 WorkBuddy 黑盒。
