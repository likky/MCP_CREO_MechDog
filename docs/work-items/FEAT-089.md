# FEAT-089 base flange 附着与第二腿方向

分类：**已有修复但待验收**。功能，P2，目标版本 0.44.0。

来源为 [0.43.2 反馈](../validation/feedback-0.43.1-2026-11-24/originals/sheetmetal-base-flange-attach.md) §2.2。报告称 `sheetmetal_base_flange` 只能新建独立两段链，不能附着到已有钣金壁的边，也不能把第二腿翻到 +Z；第二腿固定朝板法向反侧。

仓库现状：`sheetmetal_base_flange` 确由“矩形 planar wall + 一条 90° flange”组合而成；但已有独立的 `SheetmetalFlangeOp`，其设计用途就是挂到已有壁的自由端边。因此“无附着力”的结论必须先用当前工具实测复核，不能直接按报告定性。

## 范围

1. 用 Creo 10 实测 `SheetmetalFlangeOp`：能否挂到已有壁自由端、能否控制第二腿方向、能否满足 ±X 壁顶边向内 20 mm + 向 +Z 折 8 mm 的场景。
2. 若已满足：本卡关闭为“现有能力覆盖”，只补文档与示例，不新增字段。
3. 若仍缺：才评估 `attach_to` 与 `second_leg_side`/`flip`，并按接口契约变更流程冻结后实现。

## 验收

复核记录必须包含实际作业、几何包络、材料侧、保存重载；不得用源码推断替代实机结论。

## 本机 Creo 10 实测复核结论（2026-11-24）

- 实机（作业 `35bd8865a9a646e58e97347defaa83cc`，钣金件 `556d7f87da4c4b6783a55fcdbc4d7482`，报告 `build/dev101_phase2/acceptance.json`）：在 `60×40×2 mm` `sheetmetal_planar_wall` 的 `+X` 自由端边用 `sheetmetal_flange`（`edge_geometry`、`flip=false, flip_thickness=true`）挂接 20 mm +Z 第一道折边，再在其顶边挂接 15 mm 向内第二道折边（`flip=false, flip_thickness=false`），包络 `[0,0,0]–[62,40,20]`、体积 `7233.982244 mm³`、`saved_file_reloaded_and_verified=true`。
- 结论：现有 `SheetmetalFlangeOp`（配合 `edge_geometry` + `flip` + `flip_thickness`）已覆盖“附着已有壁自由端并控制折边方向/材料侧”的需求，无需在 `sheetmetal_base_flange` 新增 `attach_to`。未验：Creo 9/12 与 WorkBuddy 黑盒。
