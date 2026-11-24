# FEAT-089 base flange 附着与第二腿方向

分类：**待复现/待核实**。功能，P2，目标版本未排期。

来源为 [0.43.2 反馈](../validation/feedback-0.43.1-2026-11-24/originals/sheetmetal-base-flange-attach.md) §2.2。报告称 `sheetmetal_base_flange` 只能新建独立两段链，不能附着到已有钣金壁的边，也不能把第二腿翻到 +Z；第二腿固定朝板法向反侧。

仓库现状：`sheetmetal_base_flange` 确由“矩形 planar wall + 一条 90° flange”组合而成；但已有独立的 `SheetmetalFlangeOp`，其设计用途就是挂到已有壁的自由端边。因此“无附着力”的结论必须先用当前工具实测复核，不能直接按报告定性。

## 范围

1. 用 Creo 10 实测 `SheetmetalFlangeOp`：能否挂到已有壁自由端、能否控制第二腿方向、能否满足 ±X 壁顶边向内 20 mm + 向 +Z 折 8 mm 的场景。
2. 若已满足：本卡关闭为“现有能力覆盖”，只补文档与示例，不新增字段。
3. 若仍缺：才评估 `attach_to` 与 `second_leg_side`/`flip`，并按接口契约变更流程冻结后实现。

## 验收

复核记录必须包含实际作业、几何包络、材料侧、保存重载；不得用源码推断替代实机结论。
