# FEAT-088 装配组件 packaged 放置

分类：**待实现**。功能，P1，目标版本未排期。

来源为 [0.43.1 反馈](../validation/feedback-0.43.1-2026-11-24/originals/datum-plane-normal-sketch-axis-flip.md) §5。`assemble_component.placement` 只有 `fixed/default/constraints`：`fixed` 保留变换但给每个实例加 FIX；`default` 写默认基准面对齐并丢失给定变换；`constraints` 需要实体级约束引用。报告需要“已定位但无约束”的语义。

## 范围

- `placement` 增加 `"packaged"`：写入组件位置后不加任何约束，保留调用方给定的变换。
- 回执明确 `constraint_count=0` 与最终变换；旧三值行为不变。

## 验收

用 3 个实例装配验证：packaged 实例按给定位姿落位、无 FIX/配合约束、装配重心与位姿表复算一致；保存重载通过；与 `fixed` 的回执差异可区分。失败路径回滚。
