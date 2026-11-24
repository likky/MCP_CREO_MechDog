# FEAT-084 为组合法兰提供可指定的宽度方向

分类：**已有修复但待验收**。功能，P1，目标版本 0.44.0。

来源为 [0.43.0 机械臂反馈](../validation/feedback-0.43.0-2026-11-24-arm/originals/arm-sheetmetal-stl-and-edge-selectors.md) §1.3。当前组合法兰宽度沿命名草图面的 v 轴，Arm2 需沿世界 X。[BUG-129](BUG-129.md) 的 `expected_width_direction_world` 保留断言语义。

评估沿用已支持的草图平面定位，或新增显式局部框架。验收要求旧三个命名平面坐标不变，Arm2 与负例在匹配的 Creo 环境中有几何、方向、体积与保存重载证据。材料侧问题由 [BUG-186](BUG-186.md) 验证。


## 实现与实测

独立工具接受计划已有的字典平面，使用真实基准面、世界原点和指定的 u 轴建立 v 轴。增加首壁 `direction` 和折边 `flip_thickness`，每种取向分别核对有符号局部包络与理论体积。

Arm2 毛坯使用 Y=0 支撑、`origin=[10,0,12]`、`u_axis=[0,0,-1]`。实际 v 为 `[-1,0,0]`，首壁向 −Y 加厚，沿 X 的宽度为 20 mm。相同直线尺寸的本机对照如下。

| 作业 | 几何和状态 |
| --- | --- |
| `37a7f247defb4160aded083123483fbb` | 旧 XY 缺省，770.185801 mm³，包络 [0,0,-8]～[12,20,2]，保存重载通过。 |
| `f32742e2b6964049b8774507610772f4` | Arm2 钣金毛坯，真实首壁 49、法兰 103，850.185803 mm³，包络 [-10,-2,-2]～[10,8,12]。内外弯半径 0.7366/2.7366 mm，保存重载通过，revision 1。 |
| `0116f19951c24f1990c48745e24e9c52` | 同样的输入改用 +Z 宽向断言，触发拒绝，恢复空钣金件，revision 1 保持。 |

独立验收依据为反馈中的毛坯目标及宽度 20 mm 乘 L 形截面面积 42.5093 mm²。当前验收覆盖法兰毛坯，报告中的三个孔、四个圆角、展开型式和总装未测。

环境为 Windows x64 / Python 3.12.10 / Creo 10.0.0.0（release numeric 42）和匹配 SDK。命令 `python bridge.py build`、`python build/bug186/acceptance.py`。受测基点 `1e2cea90d3337a6401760bf50b7b07a05944f7f5`，dirty=true，源码指纹 `4d143313ef2a134b418b4907b61fc94b93e3829431732a78245f73f60adf6dfe`。本机 `build/bug186/acceptance.json` SHA256 为 `8e83f42abc9307958a1264152067f939178437e4510baf7b03aea9b989ed26ad`。Creo 9/12 与其他取向待验。

## 2026-11-24 新反馈补充

0.43.2 报告 §2.2 的 base flange 场景同时涉及宽度方向与第二腿朝向；`expected_width_direction_world` 仍只是断言不是旋转控制（BUG-129）。附着与第二腿方向复核见 [FEAT-089](FEAT-089.md)。来源见 [DEV-101](DEV-101.md)。
