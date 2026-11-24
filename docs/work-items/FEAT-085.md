# FEAT-085 按当前面与最近距离消歧边选择器

分类：**已有修复但待验收**。功能，P2，目标版本未排期。

[0.43.0 反馈](../validation/feedback-0.43.0-2026-11-24-arm/originals/arm-sheetmetal-stl-and-edge-selectors.md) §6 描述薄板两侧等距边，以及圆角修改拓扑后的旧锚点失效。沿用当前几何和边与面的相邻关系。计划新增当前面过滤和单点最近匹配；默认唯一匹配及同圆接缝规则保持。最近模式的等距候选仍拒绝。原特征消耗映射另行验证。

本机 Creo 10 / 匹配 SDK 用两面间距 2 mm 的独立薄板验证。偏心点在给定容差内同时命中两侧，最近模式选唯一最近边。等距点在默认与最近模式下拒绝，限定某一端面时选该面的边。成功须核对特征、几何和保存重载，失败须核对 revision 和回滚。


## 本机 Creo 10 验收

`on_face={"kind":"surface","id":N}` 用当前巡检的面 ID 过滤相邻边。`ambiguity:"nearest"` 只用于模型空间单点锚，按到有限直线或圆弧的实际距离排序。第一、第二候选的距离差须大于 1e-6 mm，多个等距候选仍拒绝。默认唯一性及同圆接缝规则保留。成功的消歧字段可用 `creo_get_job(detail="compact",sections=["geometry_selector_resolution"])` 单独读取。

| 作业 | 验收 |
| --- | --- |
| `387ac35950df4fd6bc8ea8b2686b60e8` | 默认选择在两边均距 1 mm 时拒绝。 |
| `40a600c910a24193b3ea188b4a4fc88d` | 显式最近模式拒绝同一组等距边，回执带两项距离和提示。 |
| `2d371cba9bad4ec987f985e808518d43` | 不存在的面 ID 给出 0 候选，无跨面回退。 |
| `f7d54592e57140518bf7694125d3f2a3` | 等距点约束顶面后，真实顶边圆角完成并保存重载。 |
| `97af09afa3fe45e49a4e598df461ad68` | 偏心点到两边为 0.8/1.2 mm，选中顶边并保存重载。 |
| `a0c60bca1be04162b45a6915a1fd137b` | 圆盘的两个圆弧候选距离 0.8/1.2 mm，选中顶侧圆弧，保存重载通过。 |

三个失败反例均回滚并维持 revision 1、体积 400 mm³。两组薄板成功例 revision 1→2、体积 399.313271 mm³，和独立算例 `400 - 20 × 0.4² × (1 - π/4)` 一致。

命令为 `python bridge.py build`、`python build/feat085/acceptance.py`、`python build/feat085/arc.py`，从开发桥接运行临时模型。Windows x64 / Python 3.12.10 / Creo 10.0.0.0（release 42）与匹配 SDK，受测基点 `a52f6be10b782e025dffeb3869034c222bc563af`，dirty=true。直边受测源码指纹 `d06e310ec40ea61602d7a411cbaccbb601b65fae8f1a96f4a13632cb6121d114`，圆弧及 compact 回读源码指纹 `e8ae21a62745d4d03e4d9fd7aedf5e985a88f6c2f6a0ffdd6a10cfd66cf9a627`。两份本机证据 SHA256 分别为 `d5feda9ea3e0f65971edcfc6a2af1d769050d31ac03d95d19636e3421ac9b4d5` 和 `a13aae12b3e50489f7ad5d31b05bc12fbf9f5d993e938796365e6f93c465be1e`。

原项目的 Arm7 第三条 R5、消耗边的历史 ID 映射及 Creo 9/12 待验证。

`python tools/dev_check.py --work-item FEAT-085` 通过，全量 4499 项，零失败、零错误、7 跳过，三项离线门禁均通过。选边与 MCP 契约 Python 专项 77 项通过。全量和圆弧实机源码指纹一致，为 `e8ae21a62745d4d03e4d9fd7aedf5e985a88f6c2f6a0ffdd6a10cfd66cf9a627`。
