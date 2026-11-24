# 2026-11-24 CREO 0.40.0 — B 样条除料「零除料」与无法渲染剖面正视图

- MCP：`MCP_CREO_MechDog`
- 版本：`0.40.0`（`src/creo_mechdog/version.py` → `VERSION = "0.40.0"`）
- Creo：Parametric 10.0.0.0（`creo_release_numeric = 42`）
- 被测模型：`Arm7`（TXT 唯一几何源：`二爪夹持机械臂_跨软件三维建模自然语言说明_v1.5.txt`）
- 最终 model_id：`1fd69dce9ab6498c986901efe23d8ff5`（`arm7_v0400c`，revision 3）
- 本轮所有结论均来自 `creo_execute_plan` / `creo_get_job` / `creo_inspect_model` / `creo_export_model` 的真实回执

---

## P1 — 截面含 B 样条的拉伸除料会「零除料」，且短期不报错

这是本轮唯一卡住流程的问题，直接导致 Arm7 两次重建失败。

### 现象 A：静默少切（最危险）

`arm7_r1b`（`sp1` + 5 条远场直线，闭环延伸到 Y=34 / Z=-47…-4）提交成功，但：

```json
{"op":"extrude","index":1,"label":"arm7_r1_cut","succeeded":true,
 "effect_status":"committed","material_removed_mm3":9.914107982876885}
```

`9.914 mm³ / 3 mm = 3.305 mm²`，而该区域在手臂毛坯内应切除约 `22 mm²`（`|W| = 211.7053`、`|W∩strip| = 104.6371`，扣掉已切的 R2/n6 后仍余约 25 mm²）。

结果是：`succeeded: true`、`committed`，体积只少了 0.8%，**调用方无法从回执判断这一刀基本没切到东西**。

### 现象 B：直接零除料

`arm7_r1c`（`sp1` + 4 条紧凑直线，Y=18.6 / Z=-45.311…-6）直接失败：

```json
{"status":"failed","stage":"execute_extrude",
 "message":"Extrude cut removes no material. The solved section contains a closed contour and B-splines. Creo can report zero removal for this combination. If an approximation is acceptable, create the B-spline with approximation_segments or provide a sampled polyline.",
 "cut_geometry_context":{"status":"no_material_removed",
   "volume_mm3":{"before":1194.940820096976,"after":1194.940820096976,"removed":0.0},
   "native_section":{"b_spline_entities":1,"closed_contours":1,"open_ends":0}}}
```

同一姿态、同一深度，闭环从 6 实体缩到 5 实体，结果从「少切」变成「零切」。

### 问题

1. `cut_geometry_context` 里**没有「已求解截面面积」**。有 `volume.before/after`、`depth_interval`、`native_section.b_ spline_entities`，唯独缺最该有的那个数：Creo 认为这一刀扫过的截面有多大。若回执给出 `solved_section_area_mm2`，`3.305 vs 22` 一眼就能发现，不必靠外部体积反推。
2. 草图回执对「含样条 + 将被除料」这一组合**没有任何风险提示**：
   ```json
   {"profile":{"analysis":"partial","unsupported_entities":["sp1"],
     "material_area_mm2":null,"area_status":"unavailable_unsupported_entities"},
    "native_section":{"closed_contours":1,"open_ends":0,"b_spline_entities":1}}
   ```
   `native_section` 明确说「1 个闭合环、0 个开口」，看起来完全健康；但正是这个健康的闭环让除料失效。
3. 建议（任一即可）：
   - 除料目标截面含 `b_spline` 时**前置拒绝**并给结构化错误码，而不是提交后再说「可能零除料」；
   - 或在 `cut_geometry_context` 增加 `solved_section_area_mm2` 与 `expected_region_area_mm2`，让调用方自己比对；
   - 或对 `mode=cut` 且含样条的草图，默认走 `approximation_segments`，并在回执里明确写「已降级为 N 段折线」。

### 本轮采用的绕行

不用除料，改用**凸台**表达同一条边界：把手臂直接做成 `sp0`（反序）与 `sp1` 两条 B 样条围成的窄带，一次 `mode:"add"` 拉伸。样条凸台完全正常：

```json
{"op":"sketch","label":"a7_s3","succeeded":true,
 "native_section":{"b_spline_entities":2,"closed_contours":1,"open_ends":0},
 "geometry_deviation":{"max_deviation_mm":0.00120867}}
{"op":"extrude","label":"a7_n4","mode":"add","succeeded":true}
```

体积从 `1167.218`（长圆板 + 窄带）→ 切 R0 后 `1128.641`，与解析预测 `(S∪strip−孔)×3` 一致到 0.03%。**这说明问题不在样条本身，而在「样条 + 除料」这一组合。**

---

## P1 — 无法渲染零件剖面正视图（`right` 未实现）

本零件剖面在 **YZ 平面**，法向 +X。需要沿 X 看才能看到轮廓。

`creo_export_model(format="jpeg", jpeg_options={"view": ...})` 只接受 `isometric | front | top`：

```json
{"format":"jpeg","jpeg_options":{"view":"front","width_px":1200,"height_px":900}}
→ 输出 1200×900，零件退化成一根 22 px 宽、约 490 px 高的竖条（3 mm 厚度沿 X）
```

`front` 是 XZ 面、`top` 是 XY 面，二者对本零件都是侧向；`right` 在 `src/creo_mechdog/f09_contract.py` 里已列入 `VIEWS = ("iso","front","top","right")`，但同文件 `STATUS = "designed_not_implemented"`，`schema.py` 的 `view` 也只到 `isometric|front|top`。

建议：
- 实现 `right`；
- 或允许传入显式 `view_matrix`（3×3 或 origin+两个方向向量），或允许指定「正视某个基准平面」。

对本类「平板类零件按轮廓验收」的场景，拿不到剖面正视图就等于**无法做视觉验收**，只能绕到导出 STL 再离线切片（本轮的做法）。

---

## P2 — 草图 autodim 静默吸附弦端点，偏差超过 45% 误差预算却仍提交

`a7_s5`（R0 月牙除料草图）里，两条弦的端点本应落在圆弧端点上：

```
P1  = (-1.173416194, -14.314501416)
P3p = ( 3.665824069, -14.400254975)
```

回执：

```json
{"op":"sketch","label":"a7_s5","succeeded":true,
 "profile":{"material_area_mm2":12.941082850796246,"area_status":"complete"},
 "geometry_deviation":{"available":true,"max_deviation_mm":0.04549858399999884,
   "exceeds_warning":true}}
```

实际生成的边（`creo_inspect_model(section="edges")`）：

```json
{"id":214,"start":[1.5,-1.1563432752893774,-14.36],"end":[-1.5,-1.1563432752893774,-14.36]}
{"id":213,"start":[1.5, 3.6936567247106202,-14.36],"end":[-1.5, 3.6936567247106202,-14.36]}
```

即 `Y: -1.1734 → -1.1563`、`3.6658 → 3.6937`、`Z: -14.4003/-14.3145 → -14.36`（弦被拉平到同一 Z）。`0.0455 mm` 对本零件（轮廓验收阈值 0.1 mm）已占 45% 预算，但 `exceeds_warning` 只是提示，特征照样 commit。

建议：
- 提供 `geometry_tolerance_mm` 式的**拒绝阈值**（capabilities 里已有该参数用于 `coordinates`，`autodim` 路径上却只是 warn）；
- 或在回执里列出**被吸附的具体点与位移向量**，而不只给一个标量 `max_deviation_mm`。

顺带：`a7_s1`/`a7_s5` 的 `solver.selection_reason` 都是 `"small_profile"` / `"unsupported_coordinate_entity"`，`initial_solve = -1` 后靠 `autodimension` 恢复（`recovered: true`）。这个「先失败再恢复」在回执里可见，但恢复后的几何有没有被改动，只能靠 `geometry_deviation` 反推。

---

## P2 — `round` 无法提供曲率连续（G2）的几何证据

`curvature_continuous: true` 提交成功，回执只有：

```json
{"op":"round","label":"a7_r30","succeeded":true,"size":30.0,"feature_id":226,
 "volume_before_mm3":1128.641488821258,"volume_after_mm3":1134.5648333736247,
 "material_delta_mm3":5.923344552366643,"reference_application":{"applied_set_count":1}}
```

`+5.923 mm³`（= `+1.974 mm²`）与「R30 凹圆角在 22° 折角处增料」的解析值 `r²(tan φ − φ) ≈ 2.16 mm²` 吻合，说明**半径 30 确实施加上去了**；但没有任何字段能证明**曲率连续**。因此我只能写「R30 已施加、增料 5.923 mm³」，**不能**写「G2 已验证」。

建议：`round` 回执增加可核查项，例如过渡面最小/最大主曲率、与两邻面在接缝处的切向偏差与曲率偏差，或直接给 `continuity_achieved: "G1"|"G2"` 的实测判定。

---

## P3 — `region` 签名匹配器仍无法表达圆弧/样条边界（历史遗留）

Arm7 的 `[B-REGION]` 三区域，`signature_yz_mm` 只能表达「顶点对」。而这三种边界分别是：R5 端弧、`sp1` 曲线、`sp0` 曲线 —— 一条都不是顶点对。历轮全部零命中，本轮再次实测仍是 0，只能整体绕开（改走凸台路线）。

建议：允许签名里携带「曲线段」描述（例如给出曲线上的采样点序列或 `{curve: b_spline, cps: ...}`），或允许用「平面 + 半边环」的方式命名区域。

---

## P3 — `creo_get_job` 的 `section` 需要 `detail="full"`

```json
creo_get_job(job_id=..., detail="compact", section="operations_result")
→ Error: section/cursor require detail=full
```

`section` 参数本身没有标注这个前置条件，容易踩。建议在参数描述里写明，或在 `detail="compact"` 时忽略 `section` 并给出 `detail_required:"full"` 的软提示。

---

## 附：本轮最终验收数据（供作者复现对照）

| 项 | TXT 指纹 | 本轮 `arm7_v0400c` | 偏差 |
|---|---|---|---|
| 体积 | 1142.849 mm³ | 1131.425971 mm³ | −1.00% |
| 重心 | (0, 2.8756, −6.9934) | (0, 2.81263, −6.83386) | ΔY −0.063 / ΔZ +0.160 mm |
| 面数 | 16 | 17 | +1 |
| 边数 | 40 | 45 | +5 |
| 截面积（STL 在 X=0 切片） | 380.9497 mm² | 377.42 mm² | −0.93% |
| bbox Y / Z | −5…14.5 / −45.311…16 | −5.000…14.6402 / −45.310…15.9992 | ≤0.15 mm |

对照基准：用户提供的 SolidWorks 正确建模截图 `正确01.png`，以两个 Ø3 孔 22 mm 孔距标定为 `10.60389 px/mm`，逐列上下包络比对，**全轮廓偏差 ≤ 0.1 mm（≈1 px）**，即达到该视觉基准的分辨极限。

步骤回执（可直接按 job_id 复查）：

```
strip_build  19d9add6322441148702e7cf2508cc45   rev1  1128.641488821258
r30_g2       45e8fa2007e44ef19c3878f27ee19c2b   rev2  1134.5648333736247  (+5.923344552366643)
r5x3         a465628ff068435298974f99ab73e89f   rev3  1131.4259713329739  (-2.218137904829291 / -0.8908712999875661 / -0.029852835833935387)
stl_export   ea090485a29544b3ad4ab4984145d11c
```
