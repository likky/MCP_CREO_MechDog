# FEAT-086 surface_loft 截面与导线接受曲线链

分类：**待实现**。功能，P1，目标版本未排期。

来源为 [0.43.0 反馈](../validation/feedback-0.43.1-2026-11-24/originals/chamfer-propagate-and-surface-loft-creo10.md) N4。`surface_loft` 的截面契约只接受“一条曲线，或两条合成一个闭合轮廓”；4 条 `line` 组成的闭合矩形与 4 点闭合 `polyline` 都被拒绝（Creo 会把它拆成 4 条 line）。球鼻艏 B030 的 3 条纵向导线各由 line + spline 两条组成，按现有 `guides`“one curve each”契约无法表达。

## 范围

- `sections` 与 `guides` 接受 `{kind:'curve_chain', ids:[...]}`，由原生侧把多条曲线合成复合曲线后交给内核。
- 先查匹配 SDK 是否有可用的 composite/chain 创建接口；若没有，卡片记录“当前 SDK 不可实现”，并交付明确、可定位的拒绝文案，不静默失败。

## 验收

用报告中的 4 条 line 闭合矩形、4 点闭合 polyline 与“line + spline”导线在独立探针件上验证；成功时核对截面数、几何、体积与保存重载，失败时核对原始错误码与回滚。Creo 10 `release_numeric=42` 上另需区分 −18 与截面契约失败。
