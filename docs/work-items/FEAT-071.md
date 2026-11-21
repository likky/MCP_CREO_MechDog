# FEAT-071：两距离不等距倒角与独立 chamfer 参数对齐

分类：**部分交付 0.35.0，剩余待验收**

类型：功能

优先级：P2

状态：部分交付 0.35.0，剩余待验收（已发布；`d1_d2` 与独立工具契约落地，Creo 10 实机两方向通过；其他参考面组合与曲面边未验）

目标版本：0.35.0

来源与关联：[0.33.0 反馈归档](../validation/feedback-0.33.0-2026-11-21/SOURCE_MANIFEST.json) `startup-chamfer.md` P3/P6；关联 DEV-090 距离角度倒角、FEAT-068 引用槽位。

## 问题或目标

当前 ChamferOp 已支持等距与距离+角度，但无法表达两个相邻面分别退距。增加受校验的 `d1_d2` 形态，明确两个距离及面方向/交换语义；独立 `creo_chamfer` 与计划操作共用同一参数契约，避免独立工具只能等距。Creo 枚举、元素树与参照方向必须以本机 SDK 头文件、官方说明和实际元素树为据，不凭名称猜 `PRO_CHAMFER_D1_D2`。

## 范围

包含 schema、计划准入、独立工具、原生创建、能力/参考语法与回归。保留现有 equal_distance/distance_angle 字节与行为；不扩展到变距、转角倒角或未查证的面方向自动推断。零候选最近边诊断归 DEV-098。

## 验收标准

| 环境 / 用例 | 命令或操作 | 可判断的预期结果 |
| --- | --- | --- |
| SDK / 离线 | 头文件声明、官方说明/示例及现有元素树核对 | 枚举、距离元素与面方向来源可追溯 |
| Windows / Python | schema、独立工具、非法参数及原生结构回归 | d1_d2 正例与缺距离/负值/冲突参数负例通过；旧模式不变 |
| 本机 Creo 10 / 匹配 SDK | 可交换方向的不等距倒角对照 | 两种距离均实测生效，d1/d2 方向与契约一致，保存重载 true；失败回滚 |

## 实现与证据

2026-11-21 实现并实机验收（本机 Creo 10.0.0.0 / release 42，worker `277cbac5…`）：

- SDK 依据：`D:\Program Files\PTC\Creo 10.0.0.0\Common Files\protoolkit\includes\ProChamfer.h` 声明 `PRO_CHM_D1_X_D2 = 603`，要求 `PRO_E_RNDCH_LEG1`、`PRO_E_RNDCH_LEG2` 与 `PRO_E_RNDCH_REFERENCE_SURFACE`；未凭名称猜枚举。
- `src/creo_mechdog/schema.py`：`ChamferOp.chamfer_type` 增加 `d1_d2`，要求正数 `distance_1`/`distance_2` 与显式 `reference_surface`，拒绝与 `size`/`distance` 或角度字段混用；等距与距离+角度载荷不变。
- `server.py`：`creo_chamfer` 与计划共用契约（`distance`/`size` 等距，`chamfer_type`/`angle_deg`/`angle_reference`，`distance_1`/`distance_2`/`reference_surface`）。
- `native/generic.cpp`：`d1_d2` 写 `PRO_CHM_D1_X_D2`，LEG1=`distance_1`、LEG2=`distance_2`、第二腿类型 `PRO_ROUND_RADIUS_TYPE_VALUE`，并写显式 `PRO_E_RNDCH_REFERENCE_SURFACE`；回执给出 `chamfer_type`/两个距离。
- 离线：新增 `tests/unit/test_feat071_chamfer_d1_d2.py`；46 项聚焦/回归通过，Ruff 与格式检查通过；全量 4286 项通过。
- **实机**（`tools/test_chamfer_angle.py --live`，50×30×10 块、顶边、`reference_surface`=顶面）：
  - `d1=2,d2=5` → 前侧面腿 2.0 mm、顶面腿 5.0 mm，去除体积 250 mm³，保存重载 true（作业 `186b2b1a…`）；
  - `d1=5,d2=2` → 前侧面 5.0 mm、顶面 2.0 mm，去除体积 250 mm³，保存重载 true（作业 `3948c49d…`）；
  - 结论：**D1 落在未在 `reference_surface` 指定的相邻面，D2 落在 `reference_surface` 指定的面**；距离+角度两例回归仍通过。
- 未验证：其他参考面组合、曲面边、变距/转角倒角与其他 Creo 版本；实机脚本仍以 `distance_1/distance_2` 作为输入，不推断面方向。
