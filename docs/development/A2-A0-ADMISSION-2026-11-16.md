# A2 / A0 数据准入结果（2026-11-16）

用户把测试机的三份计划数据放到了 `C:\Users\Administrator\Downloads\0.25.0`，本轮把它们复制到
`build/incoming/0250/`（只读源数据，不入发布包）并逐条跑当前公开契约。**本轮没有实机、没有
改代码、没有动用户模型。**

- 数据：`mates_preserved.json`（61 条 `[B-MATE]`）、`assembly_ops_v0250.json`（23 个组件位姿）、
  `edge_anchors.json`（6 条边锚点）
- 准入脚本：`build/incoming/0250/admit.py`（一次性，调用 `AssemblyConstraint`、`RoundOp`、
  `ChamferOp`、`AssembleOp` 与 `geometry_selectors` 的真实校验）
- 完整结果：`build/incoming/0250/admission_report.json`

## 结论

| 数据 | 数量 | 契约层结果 | 阻断原因 |
| --- | ---: | --- | --- |
| `coincident` 平面配合 | 24 | **可准入**，归一化为 `mate` | 全部缺 `n#`→组件标签映射，无法落到具体组件 |
| `concentric` 圆配合 | 26 | **拒绝** | JSON 只有 `near` 点，没有 `radius_mm`/`axis`；`concentric` 必须能唯一解析为圆柱面 |
| `parallel` | 6 | **未支持** | `PRO_ASM_ORIENT` 未在本项目实机验证，契约按类型拒绝 |
| `distance` | 4 | **未支持** | `PRO_ASM_LINE_DIST`/`PNT_DIST` 未实机验证；面距离应改用 `mate_offset` |
| `gear` | 1 | **未支持** | 约束契约没有齿轮关系 |
| 组件位姿 `assemble_component` | 23 | **全部准入**，标签唯一，旋转正交误差 `1.09e-9` | `source_model_id` 是内容哈希，不是 Creo 模型路径；没有 `.prt` 文件可重建 Arm2 |
| 圆角锚点 | 4 | **可准入** | Arm2 n4 R3、Arm3 n3 R3、Arm6 n3 R40、Lateral n7 R90，各带 4/8/4/4 个边点选择器 |
| 角度倒角锚点 | 2 | **拒绝** | `Hom n7/n8` 的 8 mm @ 70° 只有边点，缺 `angle_reference`（角度参考面） |

### 逐条口径

- 61 条 ID 与声明计数一致（`concentric 26 / coincident 24 / parallel 6 / distance 4 / gear 1`），
  没有解析失败项；`sides` 的 `n#:plane|circle:near=(x,y,z)` 全部可读。
- 24 条 `coincident` 用近点构造 `geometry_selector(target=surface, points_mm=near,
  tolerance_mm=0.05)` 后，两侧都能通过 `AssemblyConstraint` 并归一化为 `mate`。这不等于可以
  直接下发：每条还需要 `n#` 对应的组件标签，才能放进 `component_constraints`。
- 26 条 `concentric` 的拒绝信息是“a concentric selector needs radius_mm (and preferably
  axis)”。这是数据缺口，不是实现回归；不能靠放宽成“点选圆柱”绕过，否则平面也可能命中。
- 23 条 `assemble_component` 全部通过 `AssembleOp`，`placement=fixed`，标签 23/23 唯一；
  矩阵正交误差最大 `1.09e-9`，行列式在容差内为 +1。它们能证明位姿数据本身合法，不能替代
  “用模型重建 Arm2”这一步。
- `edge_anchors.json` 只有 6 条，不是交接文档预期的 61 条；其中 4 条圆角可直接生成
  `RoundOp` 的边点选择器，`Hom n7/n8` 两条倒角仍缺角度参考面。

## 仍缺的输入

1. **`n1`–`n23` 到组件标签的映射**：增强版 TXT 的 `[B-COMP]` 顺序，或 `manifest.json`
   里的 label/id 对照。
2. **26 条圆配合的半径与轴**：TXT 的 `[B-MATE]` 原文（含 `radius`/`axis`），或在 Creo 里量取
   的圆柱面参数。
3. **`Hom n7/n8` 的角度参考面**：用哪一张面作为 70° 的基准。
4. **61 条边锚点原文**：现在只有 6 条，圆角/倒角的完整清单仍未到。
5. **Arm2 / Arm3 / Arm6 / Hom / Lateral 的 Creo 模型文件**（`.prt`/`.asm`）或测试机工作目录：
   本轮 `build` 下只有旧的 T13 夹具，没有 0.25.0 实机创建的 Arm2 系列。
6. **实机授权**：G2 的单变量对照、4 条圆角与 24 条平面配合的真实建约束，都需要当次明确授权。

## G1 / G2 本轮新增证据

- G1：`ProSurfReg.h` 里确有 “Surface Region”，但元素表写的是 `PRO_FEAT_SPLIT_SURF`
  （用草图或链**分割曲面**），不是“在拉伸截面里选中已有闭合区域”。`ProExtrude.h` 仍没有
  区域选择接口，`ProSection.h` 也没有区域复选 API，因此区域切除继续不开放。
- G2：`PRO_ROUND_CURV_CONTINUOUS=3` 的静态缺口不变；需要同一 R30/1、R5/3 边做锥面 vs
  CURV_CONTINUOUS 的单变量实机对照，本轮未授权，未执行。

## 本轮没有做的事

- 没有把 24 条平面配合写成可执行计划下发（缺组件映射，硬编码会把错误藏进“看起来成功”）。
- 没有用 23 条固定位姿代替配合来宣称“61 条已建立”。
- 没有重建 Arm2 完整件，也没有核对 9.57 mm 偏移。
- 没有实机跑圆角/倒角/G2。
