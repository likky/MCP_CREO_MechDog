# FEAT-088 装配组件 packaged 放置

分类：**已有修复但待验收**。功能，P1，目标版本 0.44.0。

来源为 [0.43.1 反馈](../validation/feedback-0.43.1-2026-11-24/originals/datum-plane-normal-sketch-axis-flip.md) §5。`assemble_component.placement` 只有 `fixed/default/constraints`：`fixed` 保留变换但给每个实例加 FIX；`default` 写默认基准面对齐并丢失给定变换；`constraints` 需要实体级约束引用。报告需要“已定位但无约束”的语义。

## 范围

- `placement` 增加 `"packaged"`：写入组件位置后不加任何约束，保留调用方给定的变换。
- 回执明确 `constraint_count=0` 与最终变换；旧三值行为不变。

## 验收

用 3 个实例装配验证：packaged 实例按给定位姿落位、无 FIX/配合约束、装配重心与位姿表复算一致；保存重载通过；与 `fixed` 的回执差异可区分。失败路径回滚。

## 本机 Creo 10 实测证据（2026-11-24）

- 实现：`AssembleOp.placement`、`creo_assemble_component` 与原生 `native/advanced.cpp` 新增 `"packaged"` 分支（`ProAsmcompAssemble` 保留位姿矩阵、不写任何约束），回执通过 `ProAsmcompConstraintsWithDtmOrientGet` 实测返回 `placement` 与 `constraint_count`。
- 实机（作业 `3c502dfe6e1747688ca9572fdde5bb9b`，装配 `35376ffcac0c4e5faf233a954f0e28de`，报告 `build/dev101_phase2/acceptance.json`，SHA256 `719bb9c0518ee49d3f6222551c58a56bf7beddfc2a10c2c6c7e6ff1461b0cc3f`）：3 个 `10×10×10 mm` 方块实例（`inst_fix` `placement="fixed", constraint_count=1`；`inst_pkg1`/`inst_pkg2` `placement="packaged", constraint_count=0`），总体积 `3000.0 mm³`，实测重心 `[25.0, 8.333333, 5.0]` 与理论值吻合，`saved_file_reloaded_and_verified=true`。
- 未验：Creo 9/12 与 WorkBuddy 黑盒。
