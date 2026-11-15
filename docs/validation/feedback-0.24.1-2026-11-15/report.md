# 2026-11-14 · CREO · 0.24.1 · 钣金基体法兰与装配配合语义缺口

> 面向 MCP_CREO_MechDog 作者的能力/可用性反馈。
> 场景：仅以一份自然语言 TXT（v1.5）为几何输入，在 Creo 10 中原生重建「二爪夹持机械臂」12 个唯一零件 + 23 个装配实例。
> 建模提交全部只走 `MCP_CREO_MechDog`；未打开/导入任何 CREO、SolidWorks、NX、STEP、Parasolid、STL、原代码或实体模型。

---

## 0. 结论摘要

| 项 | 结果 |
|---|---|
| MCP 当前 / 最新公开版本 | `0.24.1` / `0.24.1`（`creo_check_update(force=true)` → `up_to_date`） |
| Creo 运行时 | `Creo 10.0.0.0`，`release_numeric=42` |
| 会话 | `connected=true`，`channel_policy=single_channel_busy_rejects_immediately` |
| 零件 | **12/12 建成**，全部 `has_solid=true`、`units=mm`、`inspection_source=saved_reloaded` |
| 总装 | **23/23 组件实例建成**，回读 4×4 transform 与 `[B-COMP]` 逐项一致 |
| 特征 | **12 条 `[B-FEAT]`/`[B-CUT]`/`[B-FILLET2]` 行无法表达**（Arm2 3、Arm3 1、Arm6 1、Arm7 3、Hom 3、Lateral 1） |
| 配合 | **61 个配合 0 个建成**，按 TXT v1.4 口径「保留参数、不替代、不删实例」 |
| 体积吻合 | 5 件 ≤0.006%（Arm4/Arm5/Arm8/Base/Rotor），其余 7 件偏差 −18.24% ~ +26.01% |
| 总体判定 | **PARTIAL / DEGRADED**，不宣称 `VERIFIED`、不宣称拓扑 `EXACT` |

**最核心的两个问题**：
1. **A1**：没有能从「两段开放折线草图」直接生成钣金基体法兰的接口，`sheetmetal_wall` 硬性要求剖面恰好 1 条直线；替代路径（planar_wall + flange）的折弯扣除语义与 SolidWorks `SMBaseFlange` 不同，Arm2 体积 −18.24%。
2. **A7**：`AssemblyConstraint` 枚举缺 `concentric/parallel/distance/gear`，且引用需要 Creo 几何 ID 而 TXT 只给锚点中心/轴/半径，61 个配合全部不可建。

---

## 1. 证据口径与边界

- 所有体积、面/边/特征计数、transform 均取自 MCP 自身的 `creo_inspect_model` / `creo_get_job` 的 **saved_reloaded** 巡检读数，**不是参数回读**；只证明实体存在与量级，不等价于拓扑 EXACT 验收。
- `creo_capabilities`：`tool_count=107`，`complete_creo_coverage=false`，`unavailable_tools = [creo_sheetmetal_flange_profile, creo_sheetmetal_corner_relief, creo_sheetmetal_quilt_form, creo_surface_boundary_fill]`；`known_limitations.count=14`。
- 本地 `Read`/`Bash`/`Grep`/Python 只用于解析 TXT、生成 `creo_plans/*.json` 计划和源码接口语义判断，**不是 CAD 建模调用**；所有建模提交均通过 `MCP_CREO_MechDog`。

### 1.1 实测体积对照（mm³）

| 零件 | 实测体积 | TXT 指纹 | dV | 主要原因 |
|---|---:|---:|---:|---|
| Arm8 | 113.097 | 113.097 | +0.0003% | 完整 |
| Base | 20970.971 | 20970.971 | +0.0000% | 完整 |
| Rotor | 17103.945 | 17103.892 | +0.0003% | 完整 |
| Arm4 | 2134.676 | 2134.784 | −0.0050% | 完整 |
| Arm5 | 1962.264 | 1962.321 | −0.0029% | 完整 |
| Arm1 | 4126.083 | 4147.550 | −0.5176% | 缺 R3 圆角（B1） |
| Arm3 | 4191.876 | 4185.695 | +0.1477% | 缺 R3 圆角（B1） |
| Lateral | 19927.024 | 19114.973 | +4.2482% | 缺 R90 等效圆角（B1） |
| Hom | 97853.677 | 90332.156 | +8.3265% | 缺 2 处带角度倒角 + 线性阵列（A3/A4） |
| Arm6 | 406.522 | 463.883 | −12.3654% | **TXT v1.5 E16 自身未闭合项，非 MCP 缺陷** |
| Arm2 | 647.774 | 792.323 | −18.2437% | 钣金基体法兰语义缺口（A1）+ 缺 4×R3（B1） |
| Arm7 | 1440.057 | 1142.849 | +26.0059% | 缺区域签名切除（A6）+ 曲率连续圆角（A5） |

---

## 2. A 类：MCP 没有的能力（接口缺失）

### A1 【P0】钣金基体法兰：`SMBaseFlange` 两段折线草图无对应 op

**TXT 输入**（附录 B，Arm2）：
```text
[B-SKETCH] id=Arm2-S1 part=Arm2.SLDPRT datum=right offset=10 origin=(0,0,0) xdir=(0,0,-1) ydir=(0,1,0)
[B-GEO] sketch=Arm2-S1 i=0 kind=line x1=0 y1=8 x2=0 y2=0
[B-GEO] sketch=Arm2-S1 i=1 kind=line x1=0 y1=0 x2=-12 y2=0
[B-FEAT] part=Arm2.SLDPRT id=n2 type=sheet_metal sketch=Arm2-S1 thickness=2 bend_radius=0.7366 k_factor=0.5 reverse=1
[B-FEAT] part=Arm2.SLDPRT id=n3 type=dimension feature_type=SMBaseFlange target=n2 dim=D2 value=20
```
TXT 明确要求：两段折线（8 mm / 12 mm 腿）→ 一个带折弯的基体法兰；板宽由 D2=20 驱动，X ∈ −10…10；指纹包络 `(-10,-2,-2,10,8,12)`，体积 `792.323 mm³`。

**MCP 现状**：
- `sheetmetal_wall`：`src/creo_mechdog/sheetmetal.py::first_wall_section_problem()` 硬性校验 `len(drawing) != 1 → 拒绝`，错误信息为 `sheetmetal_wall needs exactly one open straight line as the first wall section; got 2 drawing entities`。**两段折线必然被拒**。
- `sheetmetal_planar_wall`：只做 4 点矩形（length/width/thickness/plane/direction/origin）。
- `sheetmetal_flange`：需先有壁，再沿一条边折 90°；`angle` 被限制 `0 < angle < 180`（见 B8）。
- `creo_sheetmetal_flange_profile` 在 `unavailable_tools`，`unavailable_operations` 说明其为「offline candidate only；hem/joggle geometry、sheetmetal identity、flat pattern、saved reload 未验证」。

**实测替代路径（全部只用 MCP）**：
1. `creo_new_sheetmetal(model_name="arm2_txt", template="native_planar")` → model `3683da492c7d4b0ab95bd05800a89d54`
2. `creo_sheetmetal_planar_wall(length=20, width=12, thickness=2, plane="XZ", direction="positive", origin=[-10,0])` → 实测 `volume=480 mm³`、`thickness_validation=verified(geometry_normal_span, 2.0)`、包络 u=−10…10 / v=0…12 / 法向 Y=−2…0
3. `creo_sheetmetal_flange(edge={kind:edge_geometry,endpoints_mm:[[10,0,0],[-10,0,0]]}, height=8, angle=90, radius=0.7366, y_factor=0.5, flip=false)` → 实测 `volume=690.186 mm³`
4. `creo_execute_plan` 两次 `extrude cut through_all` → 实测去除 `28.274` + `14.137 = 42.411 mm³`，最终 `647.774 mm³`

**为什么不等价**（边表实测，job `b45ece12319a4d2c88993ec5c084b50c`）：
- 折弯扣除 `2.7366 mm = 2(thickness) + 0.7366(radius)` 被从两条腿上**各扣一次**：水平腿平面段变成 `Z ∈ [2.7366, 12]`，竖直腿变成 `Y ∈ [0.7366, 6]`、`Z ∈ [0, 2]`。
- TXT 的两条腿是**全长** 12 mm / 8 mm，折弯位于角部；Creo 的 flange 是「壁 + 附加壁」，两条腿长度都被 bend allowance 削减。
- 结果包络 `X ∈ [−10,10], Y ∈ [−2,6], Z ∈ [0,12]`，与 TXT `Y ∈ [−2,8], Z ∈ [−2,12]` 不符；体积 −18.24%。

**建议**：新增 `sheetmetal_base_flange` op，直接接受「多段开放折线草图 + thickness + bend_radius + k_factor + reverse + width(D2)」，由 native 侧一次生成带折弯的基体法兰；或在 `first_wall_section_problem` 中放开「折线链（连续共端点的 line 段）」并保留全长语义。

### A2 【P1】按符号尺寸名修改特征尺寸（D2@SMBaseFlange）

TXT 全表唯一一条 `type=dimension`：`feature_type=SMBaseFlange, target=n2, dim=D2, value=20`，并明确「不得跳过、不得删除、不得用加料/拉伸补宽代替」。
`DimensionsOp` / `DimensionValue` 需要数字 `id`（虽有 `expected_symbol`），没有「feature_type + 符号名」定位接口；本机也未找到把 `D2@基体-法兰1@<Part>` 解析成 dimension id 的工具。
**建议**：`set_dimensions` 支持 `{feature_type, symbol, value}` 或 `symbol_path` 定位，并在回执里回报解析到的数字 id。

### A3 【P1】带角度的倒角（distance_angle）

Hom n7/n8 需要 `chamfer_type=distance_angle, angle_rad=1.22173`（约 70°）。`ChamferOp` 只有 `size` + `references`，无 `angle` / `chamfer_type`。
**建议**：`ChamferOp` 增加 `angle_rad` 或 `angle_deg` + `chamfer_type`。

### A4 【P1】方向/间距/flip 线性阵列

Hom n11 需要 `direction=x, spacing=42, count=2, flip=1`。MCP 只有 `axis_pattern`（绕轴旋转）与 `dimension_pattern`（按尺寸增量），没有表达「沿指定方向 + 间距 + 数量 + 反向」的 op。
**建议**：新增 `linear_pattern` / `direction_pattern` op（direction vector、spacing、count、flip）。

### A5 【P2】曲率连续圆角

Arm7 `[B-FILLET2] curvature=1`（R30/1 边、R5/3 边，均要求曲率连续）。`RoundOp` 只有 `size` + `references`，无 `curvature` / `continuity` 字段。
**建议**：`RoundOp` 增加 `continuity: tangent|curvature`。

### A6 【P1】按区域签名选择性切除

Arm7 `[B-CUT]` 要求按 `[B-REGION]` 签名只切除 3 个区域；`extrude cut` 作用于整张草图的全部轮廓，没有 per-region / contour-id 选择。本次只能跳过该行，Arm7 体积 +26.01%。
**建议**：`ExtrudeOp` 增加 `region_selector` / `contour_ids`（或提供按签名选区的独立 op）。

### A7 【P0】装配配合类型与引用解析

TXT 61 个 `[B-MATE]`：`concentric 26 / coincident 24 / distance 4 / parallel 6 / gear 1`，另有 `[B-MENT]` 给出每侧锚点（`anchor_kind=plane|circle`、`center`、`axis`、`radius`）。
`AssemblyConstraint` 枚举只有 `mate / align / mate_offset / align_offset / insert / csys`：
- `gear`（含传动比）**完全缺失**；
- `parallel`、`distance` 没有直接等价项；
- 即使近似映射，`assembly_reference` / `component_reference` 需要 Creo `surface/edge` 几何 ID，而 TXT 只给全局坐标下的锚点中心/轴/半径，没有从「点+轴+半径」解析到当前模型几何 ID 的批量接口。

按 TXT v1.4「不可建配合按已知不可建项保留参数、不替代、不删实例」，本次保留全部 61 行参数于 `creo_plans/mates_preserved.json`，以 `[B-COMP]` 的精确 transform 固定 23 个实例（`placement=fixed`），**未建立任何配合**。
**建议**：① 补 `concentric / parallel / distance / gear(ratio)` 约束类型；② 支持「按几何锚点（center + axis + radius）」解析引用，返回解析出的 surface/edge id 供复核；③ 对 `gear` 提供 ratio 字段。

### A8 【P2】没有「从本地 JSON 文件提交 plan」的接口

多次检索 `execute plan from json file path` / `submit saved plan` 未发现 `creo_execute_plan` 支持 `plan_file` 路径参数。本次 23 个 `assemble_component` 及全部 12 个零件计划只能把 `operations` 数组内联提交，大 plan（Arm4 92 实体、Arm5 55 实体）在调用侧很不方便。
**建议**：`creo_execute_plan` 增加 `plan_file`（绝对路径）或独立 `creo_submit_plan_file`，并回报读取到的字节数与 SHA256。

---

## 3. B 类：MCP 有但用不了 / 语义不匹配

### B1 【P0】`round`/`chamfer` 需要 edge id，TXT 只给边中点

`RoundOp` / `ChamferOp` 的 `references` 需 edge/surface 选择；TXT 只给 `edge1=(10,8,-1)` 这类边中点。没有「按边中点/端点查找边并生成 round」的通用接口。
值得注意：`creo_sheetmetal_flange.edge` **已经**支持 `{kind:'edge_geometry', endpoints_mm:[[x,y,z],[x,y,z]], tolerance_mm}`，说明几何锚点解析在 native 侧是可行的；`round`/`chamfer` 没有对应形式。
本次 6 条圆角行（Arm2 1、Arm3 1、Arm6 1、Lateral 1、Arm7 2）+ 2 条倒角行全部跳过。
**建议**：把 `edge_geometry` / `point_near` 解析能力复用到 `round`/`chamfer` 的 `references`。

### B2 TXT arc 表达与 MCP Arc 不等价

TXT `[B-GEO] arc` 给 `cx/cy/x1/y1/x2/y2/dir`（圆心 + 起终点 + 方向）；MCP `Arc` 需要 `center/radius/start_angle/end_angle/dir`。TXT 自身声明 174 段圆弧反算半径噪声最大 `0.001307 mm`。直接逐段换算会在共享端点留下约 `1e-3 mm` 间隙，而 native 焊接界是 `1e-9 mm`。
本次在 `txt_to_creo_plan.py` 中**仅在 TXT 数据内部**做端点聚类（≤0.005 mm）+ 迭代投影到相关圆弧上，`creo_plans/endpoint_residuals.json` 全部 sketch 残差 `0.0`。
**建议**：提供 `arc_by_endpoints` 实体（圆心 + 两端点 + dir），由 native 侧负责端点绑定；或在文档明确「调用方必须自行做端点一致性处理」。

### B3 6 位小数 JSON 序列化会重新引入端点间隙

初版计划文件用 `round(x, 6)` 提升可读性，结果弧端点与相邻直线端点差约 `1e-6 mm`，超过 `1e-9 mm` kernel weld bound：草图看似闭合，`extrude` 仍被拒。改为保留 full double precision 后才通过。
**建议**：在 `creo_execute_plan` 文档/校验中明确禁止有损舍入，并在 sketch 回执里给出 `observed_kernel_weld_mm` 之外的「输入坐标精度」提示。

### B4 【P1】`coordinates` dimensioning 的 `1e-5 mm` 保真门限对大草图过严

`native/sketch_coordinates.cpp::profile_dimensioning_choice()` 在 `count >= 10` 时自动选 `coordinates`（`selection_reason=entity_count`）；`resolve_geometry_tolerance()` 对 `coordinates` 默认 `0.00001 mm` **强制拒绝**，`autodim` 才是 `0.001 mm` 仅警告。显式 `geometry_tolerance_mm` 可覆盖。

实测失败证据：
- `jobs/67f1312aa40c410084f95a28821c1733/native.log`（Arm3）：
  `GEOMETRY_STAGE_SHAPE points=39 shape=0.000321278159` → `BUILD_FAILED=Coordinate dimensioning changed the supplied geometry; maximum deviation mm=0.000321`
- `jobs/fdd0e242562445a5a3274ac5118088cc/native.log`（Arm5）：
  `GEOMETRY_STAGE_SHAPE points=58 shape=0.001836615447`

这些偏移是 Creo 对密集多轮廓圆弧剖面求解时的形状漂移，与 TXT 自带的 `0.001307 mm` 圆整噪声同量级，**不是调用方几何错误**。
本次 workaround：仅对 `len(entities) >= 10` 的 sketch 显式写 `geometry_tolerance_mm=0.0015`，Arm5 单独 `0.0025`（并显式记录 caveat）；小草图保持默认。
**建议**：① 允许在 plan 顶层设置一次 `geometry_tolerance_mm` 默认值，避免逐 sketch 手改遗漏；② 失败回执里直接给出「实测 deviation + 建议的 tolerance 值」；③ 考虑把 `coordinates` 默认门限放宽到与 `autodim` 同量级或按剖面实体数自适应。

### B5 `snap_endpoints` / `weld_pairs` 对多轮廓圆整剖面无效

`src/creo_mechdog/endpoint_welding.py` 对 `separate_loops` 候选对直接给出 `reason=separate_loops` 并拒绝；`_snap_entities` 明确「Arcs never move: an arc endpoint is tied to its centre and radius」。因此开关存在，但对本次含圆弧的多轮廓剖面不起作用，必须调用方自行在 TXT 数据内对齐端点。
**建议**：允许 arc 端点在受控容差内移动并回报 `max_endpoint_move_mm`，或提供 `weld_pairs` 的跨环链支持。

### B6 【P1】`ref.offset` 与 `frame.origin` 双字段契约无法 1:1 传入

> **更正**：早期判断「MCP 只有一个 `offset` 字段、完全没有自定义平面」是不准确的。`creo_capabilities` 明确返回 `arbitrary_planar_support = plane={reference:{kind:surface,id:...},origin:[x,y,z],u_axis:[x,y,z]}`，`SketchOp.plane` 也接受 dict；`src/creo_mechdog/references.py::validate_sketch_plane_frame()` 与 `native/generic.cpp` 确实解析 `origin` / `u_axis`。此处是**语义冲突**而非接口缺失。

TXT 第 2 章明确要求：
```text
offset 是草图基准面沿法线的名义偏移（mm），origin 是草图 frame 的原点（mm）。
例：right 基准面的 Arm2-S1 有 offset=10 而 origin=(0,0,0)；top 基准面的 Base-S3 有 offset=3 且 origin=(0,3,0)。
接收 AI 必须把这两个字段按原值分别传给解释器的 ref.offset 与 frame.origin，既不得自行把 offset 再加到 origin 上，也不得丢弃 offset。
```
但 `native/generic.cpp` 校验 `origin` 必须落在支撑面内（`1e-6 mm`），否则抛
`Sketch origin is outside support plane: signed distance ... exceeds the 1e-06 mm tolerance`。
于是出现二选一：
- 用固定 `plane` + `offset`（`plane_coordinate`）→ 能表达 `ref.offset`，但 `frame.origin` 只能用于局部点变换，无法作为独立字段传给解释器；
- 用 dict `plane.origin` → 必须把 origin 投影到支撑面上（如 Arm2-S1 从 `(0,0,0)` 改成 `(10,0,0)`），**违背 TXT「按原值分别传入」**。

本次取舍：固定主平面 + 以 `origin` 的对应轴向分量作为 `plane_coordinate`（对多数 sketch 与 TXT 一致，但 Arm2-S1 的 `ref.offset=10` 被丢弃，改用 `offset=0` + `direction=symmetric` 达到 X ∈ −10…10）。此偏差已在 `build_results.json` 记录，未隐瞒。
**建议**：把「平面位置（`ref.offset`）」与「草图局部坐标系原点（`frame.origin`）」拆成两个独立字段；对 `frame.origin` 不做「必须落在支撑面上」的平面内约束，或另设 `local_origin` 字段并明确它只影响局部点的全局映射。

### B7 `through_all` 切孔方向需逐例手调

`creo_extrude` 的「cut removes no material → 失败并回滚」是很好的保护，但方向约定与 TXT 的 `reversed/midplane` + frame 法线映射需逐例核对。本次 Arm2 的 `arm2_n6`（top 基准，2×Ø3，孔位于 `Y ∈ [−2,0]` 的水平腿）采用 `direction=positive`（XZ 法线为 −Y）实测成功去除 `28.274 mm³`；而 `txt_to_creo_plan.py` 按 TXT `reversed=0` + frame 映射生成的是 `negative`，按 XZ 法线推断会朝 +Y 切、切不到水平腿。**后者是方向语义推断，未单独提交失败用例**，此处只说明调用方必须逐例核对。
**建议**：提供 `depth_type=through_all_both`（双向贯穿）或基于实体包络的自动方向推断，并在回执里回报 `material_removed_mm3`（当前已有，很好）。

### B8 `sheetmetal_flange.angle` 被限制在 (0, 180)

`SheetmetalFlangeOp.angle: Annotated[float, Field(gt=0, lt=180)]`。TXT 的折弯需要落在附件边的另一侧（等价于负角度），无法表达；`flip` 只切换材料侧（"bends to the opposite, material side"），不等价于负角度。这是 A1 无法靠调参绕过的第二个原因。
**建议**：允许 `-180 < angle < 180`（或 `0 < angle < 360` 并定义方向），并在 `wall_contract` 回执里回报实际弯折侧。

### B9 gated offline candidate 缺少可预期性

`creo_sheetmetal_flange_profile` 恰是多段折线钣金所需，但处于 `unavailable_operations` 的「offline candidates only，native forming / sheetmetal identity / flat pattern / saved reload 未验证」状态。`creo_capabilities` 的 `complete_creo_coverage=false` 与 14 条 `known_limitations` 已如实声明，建议额外给出这些 candidate 的验收计划或明确「不承诺发布」，便于调用方决定是否长期 workaround。

---

## 4. 非 MCP 缺陷（诚实降级，避免误报）

1. **Arm6 −12.3654%**：TXT v1.5 第 5 章 P06 与 E16 自述「端弧分段记录不完整，按 `[B-GEO]` 的 2 段端弧建成理论体积比指纹低 12.4%，不得据本章宣称 Arm6 达 L3」。属源数据未闭合，**不是 MCP 错误**。
2. **Arm2 / Arm7 / Hom / Lateral / Arm1 / Arm3 的偏差**：主要由 A1/A3/A4/A5/A6/B1 的能力缺口引起，属 MCP 缺口，但已逐条标注，未用「参数回读通过」冒充实体验收。
3. **61 个配合未建**：遵循 TXT v1.4 自身口径（「不可建配合按已知不可建项保留参数、不替代、不删实例」）。23 个实例的位姿取自 `[B-COMP]` 精确 transform，不是拟合出来的。
4. **12 条跳过特征行**：`creo_plans/manifest.json` 逐条记录 `id / type / reason`；本次没有虚构任何特征，也没有用「加料补宽」代替 D2 尺寸修改。
5. **验证等级**：全部为 E2 级（MCP 自身 saved_reloaded 巡检），未做跨软件 `compare_parts`、未做逐 body 体积/惯性矩/惯性积比对，因此**不宣称 VERIFIED / PASS / EXACT**。

---

## 5. 建议优先级

| 优先级 | 条目 | 理由 |
|---|---|---|
| **P0** | A1 钣金基体法兰 | 唯一造成 >18% 体积偏差的语义缺口 |
| **P0** | A7 装配配合类型 + 锚点解析 | 61 个配合 0 建成 |
| **P0** | B1 round/chamfer 几何锚点解析 | 8 条特征行被卡，native 已有 `edge_geometry` 可复用 |
| **P1** | A2 符号尺寸定位、A3 带角度倒角、A4 线性阵列、A6 区域切除 | 4 类常见机械特征 |
| **P1** | B4 coordinates 保真门限、B6 offset/origin 分离 | 影响所有大草图与所有带 offset 的 sketch |
| **P2** | A5 曲率连续圆角、A8 plan 文件提交、B2/B3/B5/B7/B8 | 可用性改进 |

---

## 6. 复现材料（本工作区内）

| 文件 | 内容 |
|---|---|
| `二爪夹持机械臂_跨软件三维建模自然语言说明_v1.5.txt` | 唯一几何输入（未修改） |
| `txt_to_creo_plan.py` | 只解析 TXT，生成 `creo_plans/*.json`；含 TXT 内部端点聚类/圆弧投影、full double precision、`geometry_tolerance_mm` 策略 |
| `creo_plans/arm1.json … rotor.json` | 12 个零件的 `creo_execute_plan` 输入计划 |
| `creo_plans/assembly_template.json` / `assembly_plan.json` | 23 个 `assemble_component`（模板为占位 id，plan 已填真实 model_id） |
| `creo_plans/manifest.json` | 每个零件的 op 数 / sketch 数 / entity 数 / 12 条跳过项及原因 |
| `creo_plans/endpoint_residuals.json` | 6 个含弧草图的端点残差，全部 `0.0` |
| `creo_plans/mates_preserved.json` | 61 条 `[B-MATE]` 原文与类型统计，状态 `preserved_not_built` |
| `creo_plans/build_results.json` | 12 件 model_id / 实测体积 / 指纹 / dV% / 跳过项 / 总装证据 / caveats |
| `2026-11-14-CREO-0.24.1-钣金基体法兰与装配配合语义缺口.md` | 本文 |

关键 job id：
- Arm2 钣金：`948f0de75907474f80d16bc8af0d6bb5`（new_sheetmetal）、`78ee2f3430fd4f1cbc7caccec0bc3e37`（planar_wall）、`b45ece12319a4d2c88993ec5c084b50c`（flange）、`f8e01b0b5c594dd8a76ab387b2f952de`（3 孔切除）
- 总装：`91e7ed89266c4e0cac6070c77e10ec23`
- coordinates 门限失败证据：`67f1312aa40c410084f95a28821c1733`（Arm3）、`fdd0e242562445a5a3274ac5118088cc`（Arm5）

12 个零件 model_id（`creo_list_models` 状态均 `ready`）：
```text
arm1_txt   d8a393989ece41369a7b77928fe73bbd      arm2_txt 3683da492c7d4b0ab95bd05800a89d54 (sheetmetal)
arm3_txt   5d2de4d8af784f2eb69f67696f837972      arm4_txt b7d2f8f104b24e0ba0f36c1efcb0fe63
arm5_txt   9dfb5241c1df4496aefaaf127b707b18      arm6_txt f477ad23441d4a3cbc6982b2bbe3d3ea
arm7_txt   cf35f56e64b748d6aa6b26469e3c4999      arm8_txt 92540290b112477b87432615ca3fd6f0
base_txt   cd6231d347134c00ad9e307a895b8a8a      hom_txt  54db2dff5d9b4daaad5130560ae83ab5
lateral_txt 94df055b0e554121837d6768c80f9156    rotor_txt 9d8122f10e27472795d7dae895d34b93
assem_txt  ed272c821e634d9a8e2c3c7062846796 (assembly, 23 components)
```
注：`arm8_txt` 未出现在 23 个 `[B-COMP]` 中（TXT 第 7 章「23 实例（Arm8×0）」），但仍按 TXT 的 12 个唯一零件要求建成。

---

## 7. 提交范围声明

- 建模提交：`creo_execute_plan` / `creo_new_sheetmetal` / `creo_sheetmetal_planar_wall` / `creo_sheetmetal_flange` / `creo_inspect_model` / `creo_list_models` / `creo_get_job` / `creo_session_status` / `creo_capabilities` / `creo_check_update`，**全部属于 `MCP_CREO_MechDog`**。
- 未调用任何其他 CAD MCP（SolidPilot / NX-MCP / CATIA / Solidworks_*）参与建模。
- 未使用 `import_geometry`、未打开磁盘上的任何 `.prt/.asm/.sldprt/.sldasm/.step/.x_t/.stl`。
- 读取 `MCP_CREO_MechDog` 源码（`server.py`、`schema.py`、`sheetmetal.py`、`endpoint_welding.py`、`native/generic.cpp`、`native/sketch_coordinates.cpp`）仅用于判定接口语义与失败根因，**不是几何输入**。
