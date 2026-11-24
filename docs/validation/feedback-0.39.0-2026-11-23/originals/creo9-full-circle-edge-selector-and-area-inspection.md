# MCP_CREO_MechDog 问题反馈（Creo 9.0.0.0 / MCP 0.39.0）

- 反馈日期：2026-11-23
- MCP 版本：**0.39.0**（`creo_session_status.server_version`）
- 目标 CAD：Creo 9.0.0.0（`release_numeric = 41`，`parametric.exe` + `xtop.exe`）
- 任务：按一份纯文本（TXT）自然语言几何说明，从空白模型重建「直列四缸发动机曲柄活塞机构」= 6 个唯一零件 + 1 个 29 实例装配，全程只用 MCP_CREO_MechDog，不导入任何实体。
- 结论：**建模全部完成**（6 零件 + 29/29 组件，几何精度见附表），但过程中撞到三类硬阻断，其中 **①整圆棱边无法用几何选择器唯一命中** 直接导致 14 处圆角做不出来。

---

## 0. 本次实际达成的结果（供作者判断优先级）

| 零件 | CREO 实测 V (mm³) | TXT/源件 V | ΔV | CREO 重心 | 源重心 | 重心差 |
|---|---|---|---|---|---|---|
| P03 活塞环 | 3323.177 | 3323.18 | **−0.0001%** | (0, 2.150, 0) | (0, 2.150, 0) | 0 |
| P05 活塞销 | 73168.175 | 73168.2 | **−0.00003%** | (0, 0, 41.000) | (0, 0, 41.000) | 0 |
| P02 曲轴 | 3221838.491 | 3221710 | **+0.0040%** | (340.0106, 0, 0) | (340.032, 0, 0) | 0.021 mm |
| P01 活塞 | 155836.183 | 155790.0 | **+0.0296%** | (0, 23.6626, 0) | (0, 23.649, 0) | 0.014 mm |
| P04 连杆盖 | 120952.351 | 121018.0 | **−0.0543%** | (−0.1723, −35.184, 19) | (−0.153, −35.127, 19) | 0.06 mm |
| P06 连杆 | 125197.655 | 128842.0 | **−2.83%** | (0, 91.958, 19) | (0, 90.1596, 19) | +1.80 mm |
| 装配（29 实例） | 5162334.064 | 各件×实例数 = 5162334.065 | **−0.0000002%** | — | — | — |

> P06 的 −2.83% 是**源文档自身登记的已知不闭合**（其 D056"两侧各切 10.0"与 V=128842 不能同时成立），非 MCP 问题；但其中约 0.8% 来自下面 **问题 1** 导致 4 处 R3 圆角未能施加。

---

## 1.（核心阻断）`geometry_selector` 对"整圆棱边"永远无法唯一命中，`point_mm` 在极值点上失效

**严重度：高。这是本次唯一无法绕开的阻断——18 处 R3 圆角里只做出了 4 处。**

### 现象与复现

Creo 内核把**一个整圆棱边拆成 2 段半圆弧**（`creo_inspect_model(section="edges")` 可见：同一 center/radius 出现两个 id，例如销的两端圆各为 `52/53` 与 `55/56`）。于是：

| 尝试 | 输入 | 结果 |
|---|---|---|
| ① | `{center_mm:[0,0,0], radius_mm:16.9}` | ❌ `geometry_selector edge circular matched 2 arcs of one circle (ids 52, 53); … add point_mm on the span you want` |
| ② | 显式给两条弧 id `[52,53]` | ❌ `chamfer references edges 52 and 53 that lie on one circle …; keep the smallest id (52) and remove the duplicate reference` |
| ③ | 只给 1 段弧 id `[52]` | ✅ 成功，且 Creo **自动沿整圆传播**（两端倒角都做出来了，V=73168.175 逐位吻合） |
| ④ | `{center_mm:[118,0,0], radius_mm:36, point_mm:[118,0,36]}`（圆的 +Z 极值点） | ❌ 仍报 matched 2 arcs（id 403,404） |
| ⑤ | 同上，`point_mm` 改到 45° 方向 `[118,25.456,25.456]` | ✅ 成功 |
| ⑥ | 只给 `{point_mm:[0,30,28]}` 选一条**圆弧**边 | ❌ `a single point only matches a finite straight edge - name a circular edge with center_mm+radius_mm instead of its centre point` |

### 根因判断

- 选择器把"圆心+半径"当作**圆的身份**，然后拒绝多解；但内核的 2 段弧共享同一个圆心/半径，**该身份永远多解**。
- `point_mm` 只在"点恰好落在某一段弧的内部"时消歧义；落在 4 个象限极值点（±R 的 ±u / ±v）时，两段弧都"包含"该点，因此仍然多解。而 TXT/工程习惯给出的锚点**恰好都在极值点上**（如"凸台外缘 x=±45"、"顶部 y=223.7"）。
- 反过来的限制又不一致：单给 point 时只匹配**直线**边，圆弧边必须给 center+radius —— 于是"给 center+radius 会多解、给点又不许选弧"形成死锁。

### 建议

1. **`point_mm` 改为"点在弧上即命中，取包含该点且唯一的那一段；若点在公共端点上，取参数区间较小者或报错并列出两段的 start/end 角"**，让工程锚点（极值点）可用。
2. 或允许 `center_mm + radius_mm + normal_mm` 一次命中**整圆**，并由 MCP 内部把该圆的全部弧一次性下发给 Creo（截图③证明 Creo 本来就支持沿整圆传播，缺的只是"把 2 段弧一起提交"的能力）。
3. 提供 `{kind:'circle', center_mm, normal_mm, radius_mm, on_face|on_surface}` 这种"整圆"一等公民，而不是让调用方拼 edge id。
4. `point_mm` 也应能选圆弧边（现在只能选直线），否则任何"按坐标锚点选弧"的写法都要先反查 center/radius。

### 连带影响

本次 P02 曲轴 18 处 R3 中做出 18 处（靠"45° 方向 point + center/radius"绕过，共 2 次提交）；P06 连杆 10 处 R3 中只做出 4 处（见问题 2）。若 TXT 类文档把"18 条圆角边""10 条圆角边"作为验收项，CREO 侧目前**无法按坐标锚点施工**。

---

## 2.（阻断）`creo_round` 多集一次提交时，一条不可行即整条回滚，且不指出是哪一条

**严重度：高（可诊断性）。**

- 提交 10 个 `{edge:{...}}` 集合、R3，返回：
  `Regeneration produced a failed, suppressed or incomplete feature`，`failed_features.sample = [{id:808, name:"R3_ROD", type:913, status:6}]` —— 808 是**整个 round 特征**的 id，**没有**给出失败的 edge/set 索引。
- 只能自己二分：8 个集合 → 仍失败；缩到 4 个（凸台端面）→ 成功。
- 直接后果：连杆的 2 处"槽底腰形边"和 4 处"S14 台阶边"圆角没能加上，V 少约 800 mm³、面数少 8（TXT 的"53 面全等"因此无法复核）。

**建议**：`round`/`chamfer` 的失败回执里增加 `failed_reference_index` 与 `failed_reference`（就像已经有的 `failed_constraint_index` 那样），并支持"逐集合校验后再整体提交"的 dry-run；或允许 `continue_on_error` 让可做的集合先提交。

---

## 3.（缺口）没有面积与包围盒查询 —— TXT 的"硬闸"在 CREO 侧无法执行

**严重度：高（验收能力缺失）。**

`creo_inspect_model` 只给：
- `volume_mm3`、`center_of_gravity`、`counts.{surfaces,edges}`；
- `surfaces[]` 只有 `bbox / radius / axis / origin / type`，**没有 area**。

而这类跨软件重建文档的关键验收线恰恰是面积与包围盒，例如：

- 「**P01 面积闸（硬闸）**：A 必须落在 58171.1 的 ±1%；若 A>60000 而 V 仍在 ±1% 内，几乎必然是裙部窗口被做成了封闭洞口 —— 体积对本件**不是**充分判据。」
- 「P04 方向闸：A 必须落在 20317.9 的 ±1%…V 不是充分判据。」
- 「装配总包络 589.0 × 405.4 × 403.2（保守上界）」。

本次 **P01 的窗口**、**P04 的凸台轴向**两处都只能靠 V + 重心 + 面数旁证，A 完全不可读；装配也没有世界包围盒，包络校核做不了。

**建议**：
1. `creo_inspect_model` 增加 `total_surface_area_mm2`，并在 `surfaces[]` 里加 `area_mm2`（对装配体则给按件的汇总）。
2. 增加 `bounding_box_mm`（min/max 三点），零件与装配都支持。Creo 有 `ProSolidOutlineGet` / `ProSurfaceAreaEval` 这类直接接口，成本很低。
3. 这两个量对"体积相同但形状不同"的坑是唯一廉价判别端，收益远大于实现成本。

---

## 4.（跨内核不可比）面/边计数被"拆半"，TXT 的拓扑指纹无法用于验收

**严重度：中（文档移植性问题，非 bug，但需在工具里声明）。**

| 零件 | 源件（SolidWorks）面/边 | CREO 实测面/边 |
|---|---|---|
| P03 环 | 4 / 4 | **6 / 12** |
| P05 销 | 5 / 4 | **8 / 14** |
| P01 活塞 | 33 / 65 | **38 / 116** |

原因：整圆柱面被拆成 2 个半圆柱面、整圆棱边被拆成 2 段弧、两个半面的接缝被计为棱边；再叠加倒角/圆角后数量级进一步放大。

**建议**：`creo_inspect_model` 的 `counts` 旁注明"CREO 计数口径：圆柱面/整圆边按 2 段计"，并额外提供 `merged_counts`（按几何连续合并后的面/边数），否则任何来自 SolidWorks/CATIA 的拓扑指纹都会被误判为"形状不对"。

---

## 5.（可用性）`coordinates` 草图模式：闭合容差过严 + 无提示地"改形"，且不支持 spline

### 5.1 弧-线接缝被拒（默认 1e-5 mm）

工程文档给的圆弧端点常与直线端点差 1e-4~4e-4 mm（源数据本身的 0.001 mm 圆整 + 半径/角度换算）。例如 `{center:[-55.79,47.66], r:39.9996, 经 (-15.845,45.567)}`：该点到圆心的实际距离是 39.99975，与从起点算出的半径差 0.00015，落到角坐标上就是 0.0004 mm 的端点误差。

结果：
```
Coordinate dimensioning changed the supplied geometry; maximum deviation mm=0.012469
```
整条 plan 被拒。必须显式 `geometry_tolerance_mm: 0.05~0.2` 才放行。

**建**：同一次提交里既报了"变化"又拒绝，等于要求调用方自己先做数值闭合。建议
- 默认容差按"输入坐标的有效位数"自适应（0.001 mm 级输入就不要用 1e-5 判）；或
- 提供 `close_contours: "auto"`，由 MCP 用"弧半径 = |起点−圆心|、直线端点复用弧的计算端点"这一套规则自动闭合（这也是本次唯一能跑通的写法，但需要自己算）。
- 报错时把**具体哪一对端点、差多少**打出来（现在已经会在 `sketch_shifted.sample` 里给，但拒绝发生在提交前，sample 为空）。

### 5.2 spline 不被 coordinates 支持，静默降级

`{type:"spline"}` + `dimensioning:"coordinates"` → 直接报
`Coordinate dimensioning supports line/centerline/rectangle/polyline/circle/arc/b_spline entities`。
改成 `"auto"` 后 solver 记录 `used: "autodim", selection_reason: "unsupported_coordinate_entity"`（几何保真度仍 1e-14，可接受），但 `profile.material_area_mm2` 变成 `null`（`analysis: "partial"`，`unsupported_entities: ["sp_dome"]`）。

**建议**：`spline`（interpolating）也纳入 coordinates 模式（它本来就是"按通过点定形"，与坐标驱动完全兼容）；若不能，至少仍给出面积（对 spline 用数值积分即可），否则"回转剖面面积"这类中间校核断掉。

### 5.3 优弧（>180°）只能拆两段

`arc` 只有 `start_angle/end_angle/dir`，当目标张角 269.8° 而两角在"短边"上时，`dir` 无法表达"走长边"。本次把 A13（R22.5、269.8°）拆成两段 134.9° 才成功。文档里"圆心+起终点+张角"的写法没有直接对应。

**建议**：`arc` 允许 `sweep_deg`（带符号）替代 `end_angle`，或允许 `through_mm`（弧上一点）做三点弧。

---

## 6.（文档）基准面 (u,v) 轴与法线没有写在工具说明里

`creo_create_sketch` 的 `plane: "XY"|"XZ"|"YZ"` 说明只讲"plane_coordinate"，没有讲清：

| plane | origin | normal | u_axis | v_axis |
|---|---|---|---|---|
| XY | [0,0,offset] | +Z | +X | +Y |
| XZ | [0,offset,0] | **−Y** | +X | **+Z** |
| YZ | [offset,0,0] | +X | +Y | +Z |

后果：在 XZ 面上"向 +Y 拉伸"必须写 `direction:"negative"`（因为法线是 −Y）。这一点只能靠第一次成功后回读 `origin/normal/u_axis/v_axis` 反推，否则整个零件会镜像/反向。本次 P03 环就是靠这次回读才确认的。

**建议**：把上表直接写进 `creo_create_sketch` / `creo_extrude` 的 `plane` 与 `direction` 说明，并明确 `u = +第一轴, v = +第二轴`（即 v 恒为正，不做符号翻转）。

---

## 7.（可用性）`feature_state delete` 的依赖必须人工穷举，第一次提交必然失败

删除两个槽切除时：

```
feature_state targets do not cover every affected dependency; Creo also deleted these features;
list them explicitly (no automatic cascade): [{feature_id:404, type_name:"datum_plane"}, {feature_id:470, ...}]
```

必须把 Creo 会连带删掉的 2 个 `datum_plane` 的 **feature_id** 也写进 `targets` 才能过。另外 `labels` / `dependencies` 字段不被接受，只有 `targets`。

**建议**：
- 接受 `include_dependencies: true`，由 MCP 读回依赖后自动补齐（现在它**已经知道**依赖列表，只是不肯自动用）；
- 或在报错里直接给出可复制的 `targets` 数组。

---

## 8.（语义）`assemble_component` 会"改动"无关的既有实例

第二次插入 14 个组件时，回执的 `component_changes` 里出现：

```
{"op":"moved","label":"c13", from:[[0.7617252266526591,…]], to:[[0.7617252266526593,…]]}
{"op":"moved","label":"c5",  ...}
```

差异在 1e-18~1e-17 量级（重新写回时的浮点往返），几何上无害，但"只插入新组件"的操作改动了别的实例的变换记录。

**建议**：只对本次操作涉及的组件报 `moved`；或对 |Δ|<1e-12 的变换写回视为"未变"。

---

## 9.（小）无法用 `creo_execute_plan` 创建空装配

`{model_type:"assembly", model_name:"assem2", operations:[]}` → 返回空错误（无 message），必须改用 `creo_new_assembly`。

**建议**：要么允许 `operations: []` 建空模型，要么明确报"assembly 创建请用 creo_new_assembly"。

---

## 附：本次验证过的"能正常用"的部分（供作者确认回归面）

- `creo_extrude` 的 `cut` + `blind/through_all` + `direction` 语义准确；每次切除都回 `material_removed_mm3`，且与解析值逐位吻合（例：S14 腹板轮廓面积 3877.69 × 10 = 38776.3，实测 `material_removed_mm3 = 38777.6`）。
- `creo_extrude(mode="add")` 多次并集在共面处合并正常，P02 的"11 段圆柱 + 8 块透镜腹板"叠加后 V=3221838.49（+0.004%）、重心 x 差 0.021 mm。
- `creo_chamfer` 单段弧 → 沿整圆传播成功（P05 两端 2×45°，V 逐位吻合）。
- `creo_round` 对**整圆柱面**棱边（`center_mm + radius_mm` + 非极值 `point_mm`）成功，并回 `material_delta_mm3`（P02 单条 +445.008、17 条 +5817.629，与解析估值一致）。
- `creo_revolve` 用"草图内唯一构造中心线"旋转 360° 正常；剖面含 spline 时几何保真 1.4e-14。
- 装配位姿：`rotation_matrix` 的 `row_vectors_local_to_parent`（`p_parent = p_local · R + T`）与源文档"列主序 9 数 = 局部 X/Y/Z 的世界方向"**完全对应**，29/29 的 transform 回读与输入逐位一致（含 1e-17 级），无需任何补偿 —— 这一点做得很好，建议在文档里把这个对应关系写成示例。
- 保存后 `saved_file_reloaded_and_verified = true` 且 V/重心在重载后不变，可作验收依据。
