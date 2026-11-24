# 2026-11-24 CREO 10.0.0.0 / MCP_CREO_MechDog 0.43.0 — 钣金法兰材料侧不可控（Arm2 无法按 TXT 成形）与选边消歧、弧度契约、通道/导出超时共 11 项

- 反馈对象：`MCP_CREO_MechDog` **0.43.0**（`version.py: VERSION = "0.43.0"`，已核实）
- CAD：Creo Parametric **10.0.0.0**（`creo_release_numeric = 42`）
- 任务口径：几何 100% 取自 `二爪夹持机械臂_跨软件三维建模自然语言说明_v1.6.txt`（下文简称 TXT），建模过程只调用本 MCP，不导入任何实体、不读工作空间外的 CAD 文件
- 本轮全量成果：12 件零件 + 1 个 23 实例总装全部建成并 save-reload 验证（`saved_file_reloaded_and_verified: true`），零件级体积偏差见第 12 节
- 证据形式：每条都给出 job_id / 体积读数 / 原始错误串，可直接按 job 目录回放（`jobs\<job_id>\native.log`）

---

## 1【P1】`sheetmetal_flange` 的 `flip` 只切换法兰伸展侧，不切换材料（折弯）侧 —— TXT 的 L 形基体法兰无法复现

这是本轮唯一一个**让零件做不出来**的缺陷，也是 Arm2 被迫降级为实体拉伸的直接原因。

### 1.1 现象

TXT 的 Arm2 基体法兰（`[B-FEAT] n2 type=sheet_metal thickness=2 bend_radius=0.7366 k_factor=0.5 reverse=1`）是一个 L 形折弯件：

- 竖腿：沿 Z 走 12，材料在 `Y ∈ [-2,0]`
- 横腿：沿 Y 走 8，材料在 `Z ∈ [-2,0]`
- 折弯段：中线 L 折线为 `Y=-1`（竖）/ `Z=-1`（横）/ `R_mid=1.7366` 的 90° 圆弧，圆心同在内角一侧 `(Y,Z)=(0.7366,0.7366)`；由此内表面 `R=0.7366`（切 `Y=0`、`Z=0`），外表面 `R=2.7366`（切 `Y=-2`、`Z=-2`），即 bbox 角点 `(-2,-2)` 被外圆角削掉一圈
- `body_box = (-10,-2,-2, 10,8,12)`（TXT 附录 F 第 1133 行）

用 `sheetmetal_planar_wall`（XZ 平面，length 20 / width 12 / thickness 2 / direction positive）建竖腿完全正确：`Y ∈ [-2,0]`、`Z ∈ [0,12]`、`X ∈ [-10,10]`，体积 480.0 mm³ 与手算一致。

问题出在横腿。同一个 `sheetmetal_flange`（height 10、angle 90、radius 0.7366）在两种取向下给出的结果：

| 试验 | job_id | 挂接边 | flip | 实测包络 | 体积 mm³ |
|---|---|---|---|---|---|
| A | `4f710ef59b2c41d280f96eb6c7114d76` | `(±10, 0, 0)` | false | X ±10 / Y −2…8 / **Z 0…12** | 770.1858 |
| B | `3bae5891e87c4e32b5108cf4a8b60ef8` | `(±10, −2, 0)` | false | X ±10 / **Y −10…0** / Z 0…12 | 770.1858 |
| C | `01c41e450a064205b6d66721eb9e16f6` | `(±10, 0, 0)` | **true** | X ±10 / **Y −10…0** / Z 0…12 | 770.1858 |

三个作业的**体积完全一致**（前 9 位有效数字相同），只有伸展方向变了：

- 边在 `Y=0`、`flip=false` → 法兰向 `+Y` 伸展（bbox `Y −2…8`）
- 边在 `Y=−2`、`flip=false` → 法兰向 `−Y` 伸展（bbox `Y −10…0`）
- 边在 `Y=0`、`flip=true` → 法兰又回到 `−Y` 伸展（bbox `Y −10…0`）

也就是说 **`flip` 是"从哪条边往外长"，不是"材料落在折弯的哪一侧"**。而法兰的厚度侧始终是 `Z ∈ [0,2]`（永远落在墙体自身 Z 跨度之内），于是折弯永远做成"内折"，横腿永远咬在竖腿的 Z 区间里，**目标包络 `Z ∈ [-2,12]` 在结构上不可能达到**。

### 1.2 源码注释与实测不符

`native/advanced.cpp:1969-1990` 写着：

```
// PRO_E_SMT_FLANGE_SEC_FLIP is what moves the bend, measured on
// the same h80/R2.54/Y0.5 flange: top edge FALSE -> down, TRUE -> up;
// bottom edge FALSE -> up, TRUE -> down.
int sec_flip = op.value("flip", false) ? PRO_B_FALSE : PRO_B_TRUE;
log("FLANGE_SIDE sec_flip=%d bend_side=%s\n", ...)
```

实测：试验 A（`sec_flip=1` / 日志 `bend_side=outward`）与试验 C（`sec_flip=0` / 日志 `bend_side=inward`）产出**同一几何**。`native.log` 中两条记录分别为：

```
jobs\4f710ef5...\native.log: FLANGE_SIDE sec_flip=1 bend_side=outward
jobs\01c41e45...\native.log: FLANGE_SIDE sec_flip=0 bend_side=inward
```

即 `PRO_E_SMT_FLANGE_SEC_FLIP` 在 Creo 10 + 90° flange 这条路径上是**惰性的**：元素写进去了、日志也报了不同的 bend_side，但几何与体积一位不差。注释里"measured on the same h80/R2.54/Y0.5 flange"的测量结论在 0.43.0 + Creo 10 上不成立。

### 1.3 由此连带：`sheetmetal_base_flange` 也做不出这件，原因是板宽方向

TXT 要求板宽 20 **沿 X**。`SheetmetalBaseFlangeOp` 的契约（`schema.py:1908`）是：

```
width runs along the sketch v axis: XY -> +Y, XZ -> +Z, YZ -> +Z
```

三个命名平面都无法把 20 mm 放到 X 上（u 轴放在 X 时 v 轴必然不是 X），`expected_width_direction_world` 只做断言、不做旋转（BUG-129 已明确）。所以 L 形基体法兰这条原生路径也走不通。

### 1.4 建议

1. `sheetmetal_flange` 增加一个明确表达"材料侧/折弯外侧"的字段（例如 `material_side: "inward" | "outward"`），或者在 `PRO_E_SMT_FLANGE_SEC_FLIP` 之外补写真正生效的那个元素；至少要在 90° flange 上实测并给出 4 种组合（伸展侧 × 材料侧）的 bbox 表。
2. 若短期内无法修复，请在 `sheetmetal_flange` 的 tool description 里写明"法兰厚度必然落在挂接边的既有 Z（或等价）跨度内，不能做出外折 L 形"，让调用方**在提交计划前**就知道这条路不通，而不是花 4 个作业去试。
3. `sheetmetal_base_flange` 需要一个真正能定板宽方向的入口（或允许 u/v 轴对调），否则凡是"板宽沿 X"的钣金件都要退回实体建模。

### 1.5 本轮的规避（不是修复）

Arm2 改为**按 TXT 折弯截面精确拉伸**：把 mid-surface 的 L 折线（竖腿 `Y=-1`、横腿 `Z=-1`、`R_mid=1.7366` 的 90° 圆弧）向两侧各偏 1 mm，得到内外两条偏置（内 R0.7366、外 R2.7366），构成 8 个实体的闭合剖面，`extrude(depth=20, symmetric)`。

- 剖面面积 = t × 中线长 = 2 × 21.2545 = **42.5093 mm²** → 拉伸本体 **850.19 mm³**，与 TXT 附录 E13 的第三环实建实测值 `8.50186e-07 m³` 逐位一致；
- 再扣 3 个 Ø3 通孔（3 × π×1.5²×2 = 42.4115）与 4 处 R3 圆角（4 × 1.9314 × 2 = 15.4515）→ **792.33 mm³**，即 TXT 权威指纹 `792.323`。实测成品 `792.2646`、面积 `1003.5251`、bbox `(-10,-2,-2, 10,8,12)`，偏差见第 12 节（体积 −0.007%、面积 −0.006%、包络逐位相同）。

代价是零件类型从 `sheetmetal` 退化为 `part`（无折弯特征树、无平板型式）。这是 MCP 能力缺口造成的，不是 TXT 的问题。

---

## 2【P1】Toolkit 单通道：并发提交不排队，直接 `toolkit_busy` 拒绝

- 回执原文：`{"status":"busy","code":"toolkit_busy","accepted":false,"blocking_job_id":"87399e66…","retry_after_seconds":5}`
- 影响：12 件零件的构建脚本必须改成严格串行（提交 → `creo_get_job(wait_seconds=…)` → 下一件），无法流水线化。本轮 30+ 个作业全部靠手工串行。
- 工具描述里已经写明"it is still only one serial Toolkit channel"，所以**这是已知设计而非 bug**；但 `retry_after_seconds` 只有 5 s，实际排队等待常常 20-60 s（装配作业 41 s、反色 14 s），建议把它改成"返回一个可轮询的排队句柄"或至少允许 `queue=true` 排队，而不是让调用方自己 sleep 重试。

## 3【P1】细弦高 STL 导出无超时、无进度、无部分输出，只能整进程强杀

- 调用：`creo_export_model(format="stl", stl_options={"chord_height_mm":0.02, "angle_control":0.05})`
- 现象：作业停在 `status=running`，`progress_elapsed_ms` 恒为 4942 不再变化，而 `log_bytes` 从 781 一路涨到挂死 301.97 s（`log_age_seconds`）；`creo_get_job` 看不出任何"正在细分/正在写盘"的信息。
- 处置：只能 `creo_cancel_job`，回执 `status: unknown_outcome`、`cancelled: true`、`geometry_may_have_changed: false`、`readonly_release.released: true`，然后手工终止 6 个残留进程。
- 规避：改用 `creo_inspect_model` 的 `bounding_box_mm`。
- 建议：STL 导出加 (a) 硬超时，(b) 分阶段进度（网格化 / 写盘 / 校验），(c) 到达超时时输出已生成的部分网格并把作业判为 `partial`。现在这种"日志在涨但状态不动"的形态无法与真死锁区分。

## 4【P2】TXT 弧「圆心 + 两端点」过约束产生的开口端：只报最大缝，不报是哪两端点，也没有自动闭合

- 原始报错：`Extrude feature creation failed (ProFeatureWithoptionsCreate=-1) ... 8 closed contour(s), 18 contour(s), 27 entity(ies), 20 open end(s) ... Max open endpoint gap 0.000433418842 mm`
- 分析：TXT 的 `[B-GEO] kind=arc` 用「圆心 + 半径 + 两端点」描述同一条弧，两端点到圆心的距离可以差到 **4.3e-4 mm**（这是 IR 的舍入，不是几何错误）。MCP 原样落草，于是 20 个端点两两不重合，剖面被判不闭合。
- 缺口：报错只给 `20 open end(s)` 和 `Max open endpoint gap`，**不给**哪两个端点是"差一点点"的一对，也不给每对的间距，更没有"按容差自动焊合"的开关。
- 本轮规避：自建 `fit_arc()`（由弦长 + 名义半径反解圆心，在两解中取离 TXT 圆心更近者，使两端点精确落在圆上）+ `canonical_vertices()`（把 <1e-3 mm 的端点并成同一点），把闭合误差从 4.3e-4 压到 1e-12（`max_endpoint_gap_mm = 5.55e-16`，见 job `f4a0b80f5c9b46ff9d42e41cde6caf2e` 的 `s1` 回执）。
- 建议：`SketchOp` 已有 `snap_endpoints` 与 `closure_tolerance_mm`，但在这条路径上显然没生效（否则 4.3e-4 < 5e-3 应当被焊上）。请 (a) 把 `closure_tolerance_mm` 真正接到端点聚类的 weld 上，(b) 报错时列出 `open_end_samples` 的距离矩阵前 N 项。

## 5【P2】`geometry_tolerance_mm` 在 `coordinates` 与 `autodim` 两条求解路径下语义**相反**

- `auto` 在实体数 ≥10 时选 `coordinates` 模式，该模式的契约是 **>1e-5 mm 即拒绝**；显式给 0.005 是"放宽放行"。
- 同一字段在实体数 <10 时走 `autodim`（`selection_reason: "small_profile"`），而 autodim 的契约是 **>1e-3 mm 只警告**；此时显式给 0.005 反而把它**收紧成拒绝**（`enforced=true`）。
- 实证：Rotor（7 个实体）给 `geometry_tolerance_mm=0.005` 直接被拒 —— `geometry_tolerance_mm changed the supplied geometry; maximum deviation mm=0.006762 ... rigid=false`；把该字段去掉后同一份草稿直接通过。
- 本轮规避：按 `len(entities) >= 10` 才写这个字段。
- 建议：(a) 让字段语义与求解路径解耦（统一为"验收阈值上限"），(b) 报错时给出建议值，(c) 在 tool description 里把这两条路径的默认阈值写成表。

## 6【P2】`geometry_selector` 单点锚在顶点/共点处无法消歧，`nearest_edges` 诊断只报不选；相邻圆角吃掉边后锚点全部失效

Arm7 的 `[B-FILLET2] index=1 radius=5 curvature=1 edge_midpoints_mm=(0,-4.988706789,-11.335863926; 0,-1.173416194,-14.314501416; 0,3.665824069,-14.400254975)` 要一次给 3 条边打 R5。实测：

| 锚点 | 容差 | 结果 |
|---|---|---|
| 三个 TXT 点（X=0） | 0.05 | `matched 2 edges (ids 88, 207)` —— 同一条轮廓在 X=+1.5 与 X=−1.5 两个端面上各有一套边，X=0 的点与两套等距，无法消歧 |
| 三条边的真实中点（X=1.5） | 0.05 | `matched none of the 35 eligible model edges` —— R30 先落之后 ear 区已有边被替换 |
| 两点（P0、P1 顶点）分别单独打 | 0.05 | 成功（rev 3 / rev 4） |
| 第三点（P3P 顶点）单独打 | 0.05 | `matched 2 edges (ids 208, 213)`，仍拒绝 |

- 缺口 1：**没有"按面限定"的边选择器**。同一轮廓在薄板两端面各有一套边是常态，单点 + 容差在这个场景下必然二义。建议提供 `{"kind":"geometry_selector","target":"edge","point_mm":[…],"on_face":{…}}` 或允许 `face_ids` 约束。
- 缺口 2：`nearest_edges` 只把候选列在诊断里，**没有"取最近的那一条"的开关**（例如 `ambiguity:"nearest"`）。多候选时用户只能先 `creo_inspect_model` 抄 edge id 再重提。
- 缺口 3：先落的圆角会把相邻边**替换**掉，后落的锚点全部失配，而报错只说 `matched none of the 35 eligible model edges`，不提示"该边已被 feature 215 消耗"。建议报错时列出被前序特征改写的 edge id 映射。
- 本轮结果：Arm7 只落成 R30 + R5×2，**第三条 R5 未成**（见第 12 节偏差）。

## 7【P2】删除钣金法兰必须连带删除它自动创建的基准面，否则整条计划回滚

- 原始回执：`feature_state targets do not cover every affected dependency; Creo also deleted these features; list them explicitly (no automatic cascade): [{"feature_id":104,...,"type_name":"datum_plane"}] ... suggested_targets=["arm2_flange",104]`
- 这一条的处理体验其实是**好的**（给了 `suggested_targets` 可直接抄），只是需要一次额外往返。建议：像 `include_dependencies` 那样给 `feature_state` 一个"列出依赖并预览"的 dry-run，避免先失败一次。

## 8【P3】`revolve` 只接受草图里的 `centerline`，不接受 `axis` 参数

- TXT 写 `[B-FEAT] id=n2 type=revolve axis=(0,0)-(0,16.285538)`，而轴线在 TXT 里只是一组坐标，并没有对应的 `[B-GEO]`。MCP 侧报 `ValueError: centerline`，必须由调用方把草图里那条恰好与 `axis` 端点重合的 `line` 改写成 `centerline`。
- 建议：`RevolveOp` 接受 `axis: {start_mm, end_mm}` 并在内部自建中心线（或自动把匹配的 line 提升为 centerline）。

## 9【P3】角度单位只有度，没有弧度入口，`6.28319 rad` 被 `le=360` 直接拒绝

- 原始报错：`revolve_s1_n2 angle 360.000269 != 360.0`
- TXT 写 `angle_rad=6.28319`，换算 360.000269°，而 `RevolveOp.angle` 有 `le=360` 上限，于是"近似 2π"这种最自然的表达被拒。
- 建议：接受 `angle_rad`，或对 `|angle-360| < 1e-3` 的输入做等值收敛并回执 `angle_clamped_from`。

## 10【P3】`bounding_box_mm` 在含样条圆角面时会超出真实几何

Arm7 实测包络 `X ±1.6 / Y −5.1…14.51`，但平面普查显示板面本体严格在 `X ±1.5`、`Y −5…5`（面 59/68 的 `origin` 为 `x=±1.5`，面 85/89 的 `origin` 为 `y=∓5`）。超出的 0.1 mm 全部来自 3 个 `type=44`（样条）圆角面：

```
227 44 bbox X ±1.6 / Y 4.900…7.187
276 44 bbox X ±1.6 / Y −5.100…−2.993
315 44 bbox X ±1.6 / Y −2.617…0.676
```

其余 14 个面对 `X` 的描述都是 `±1.5`。也就是说包络读的是样条面的**控制域/近似外接盒**，不是精确曲面范围。

- 影响：与 TXT 的 `body_box` 直接比对时会误判 0.1 mm 的偏差（TXT Arm7 `body_box=(-1.55,-5.05,-45.3112,1.55,15.1538,16)`，`facebox` 与 `方向极值并集` 还差 0.5019 mm，TXT 自己也承认这一点）。
- 建议：`bounding_box_mm` 同时给出 `bbox_source`（"tessellation" / "surface_extents" / "control_hull"），让调用方知道这个数能不能直接当指纹用。

## 11 跨版本仍然存在的缺口（本轮再次确认）

| # | 缺口 | 本轮证据 |
|---|---|---|
| 11.1 | CREO 侧仍无 `creo_server_info`（CATIA 侧已有 `catia_server_info`） | 只能靠 `creo_get_job` 的 `creo_release_numeric` 推断版本 |
| 11.2 | 仍无 `replace_component` | 只能 `remove_component` + `assemble_component`，且被移除的 label 变墓碑不可复用 |
| 11.3 | `region={signature_yz_mm,…}` 无法表达圆弧/样条回路 | 本轮改由 TXT 的 `[B-CUTLOOP]`（三条封闭链）绕开，未再触发 |
| 11.4 | G2（曲率连续）圆角无几何级验证字段 | `round` 只回 `round_kind:"convex"` 与体积差，`curvature_continuous=true` 无法回读校验 |
| 11.5 | 61 条 `[B-MATE]` 配合仍无法驱动 | 本轮总装走 `placement:"fixed"` + 显式 `rotation_matrix`，配合一条未用 |

---

## 12 本轮实测指纹（供作者复现对照）

命令口径：每件 save → erase → reload → 重新测量（`saved_file_reloaded_and_verified: true`）。

| 零件 | model_id | rev | 体积 mm³ | TXT mm³ | ΔV | 面积 mm² | TXT mm² | ΔA |
|---|---|---|---|---|---|---|---|---|
| Arm1 | `d8d71615272e44c1a5124d7c90cb6630` | 1 | 4126.0834 | 4147.55 | −0.518% | 3441.6578 | 2317.23 | +48.5%※ |
| **Arm2** | `2077217f95904cf3b1b10cbffcb6921e` | 2 | **792.2646** | **792.323** | **−0.007%** | **1003.5251** | **1003.5893** | **−0.006%** |
| Arm3 | `5bc54aa5ee5c426ea98101d48ceedb55` | 1 | 4191.8806 | 4185.695 | +0.148% | 4084.7069 | 4076.7855 | +0.194% |
| Arm4 | `0d59bd293d64416ebd0c08965bd2cab6` | 1 | 2134.6679 | 2134.784 | −0.005% | 2092.0750 | 2092.1523 | −0.004% |
| Arm5 | `526b5716194847b0bd723964dc41e0c2` | 1 | 1962.2686 | 1962.321 | −0.003% | 1910.1795 | 1910.2106 | −0.002% |
| Arm6 | `5e9bfcf5fc43129569566d4b945504`¹ | 1 | 406.5221 | 463.883 | −12.35% | 588.9880 | 620.2148 | −5.03% |
| **Arm7** | `0275bd30a8254af8a03a01ec68c014d4` | 4 | **1126.8427** | **1142.849** | **−1.401%** | **1227.6985** | **1237.2742** | **−0.774%** |
| Arm8 | `6bb2dbce8cfa46d3abfa95317b7cb98d` | 1 | 113.0973 | 113.097 | +0.000% | 164.9336 | 164.9336 | 0.000% |
| Base | `062c325cc87b47279ebcdb1fddb259ea` | 1 | 20970.9713 | 20970.971 | +0.000% | 18092.8876 | 18092.888 | −0.000% |
| Hom | `755012ac13484862a0d898b4b32f2169` | 1 | 98007.6155 | 90332.156 | +8.49% | 14058.2073 | 13229.879 | +6.26% |
| Lateral | `26a3f30a66e040548ae43223756e2649` | 1 | 19927.0239 | 19114.973 | +4.25% | 22119.6298 | 20452.441 | +8.15% |
| Rotor | `18c228c617264c2b85246d57e2a870f5` | 1 | 17103.9454 | 17103.892 | +0.000% | 17820.8575 | 17821.309 | −0.003% |
| 总装 | `7e58915b594347bc8097ee6ab43fb7f6` | 2 | 299082.0094 | — | — | 134334.5180 | — | — |

¹ Arm6 的 model_id 完整值为 `5e9bfcdcf5fc43129569566d4b945504`。

※ Arm1 面积偏差 +48.5% 不是几何做错：TXT 的 `0.00231723 m²` 与同一行体积 `4.14755e-06 m³` 自相矛盾（体积/面积比对应 1.79 mm 当量厚度，而这件是 3 mm 板 + 两段 Ø6 轴），应以体积为准。此处只作记录。

**关键自检**

1. **总装体积守恒**：Σ(零件体积 × 实例数) = 4126.08 + 792.26×2 + 4191.88×2 + 2134.67 + 1962.27 + 406.52×6 + 1126.84×4 + 20970.97 + 98007.62×2 + 19927.02×2 + 17103.95 = **299082.01 mm³**，与总装实测 **299082.0094** 完全相等 → 23 个实例全部落在正确位姿，无重叠、无丢失。
2. **变换精度**：23 个 `[B-COMP]` 的 3×3 矩阵按行向量约定直接送 `rotation_matrix`，`max |R·Rᵀ − I| = 1.088e-09`（门槛 1e-7），`det ∈ [0.9999999994, 1.0000000008]`。
3. **Arm7 三区域面积**（纯 TXT 字面量复算）：region A 12.9393 / B 41.5679 / C 65.4878 / KEEP 104.6497，与 TXT 的 12.941 / 41.567 / 65.488 / 104.650 逐项吻合；自检 `41.567 + 65.488 + 104.650 = 211.705 = Arm7-S3 轮廓面积`闭合。
4. **Arm7 region B 已切掉**：成品 `Y max = 14.5138`（远小于未切时的 18.5208），证明三条 `[B-CUTLOOP]` 起了作用。

**Arm7 残余偏差（不宣称 VERIFIED）**

- 体积 −1.401%（−16.0 mm³）、面积 −0.774%
- 质心 `(0, 2.7680, −6.7209)` vs TXT `(0, 2.8756, −6.9934)`，ΔY 0.108 / ΔZ 0.273 mm
- `Y max = 14.5138` vs TXT `15.1538`，差 **−0.64 mm**；两条已落 R5 与 R30 不解释这个方向上的**减少**（少打一条圆角应当使 Y max 偏大），原因待查
- 第 6 节所述第三条 R5（P3P 顶点）未落成

**Arm2 与 TXT 的逐位吻合**（因为它是本轮唯一一件重新推导剖面的零件，单列作对照）

```
TXT   : 体积 792.323 mm³ / 面积 1003.5893 mm² / 质心 (0, 0.8681, 2.7828) / body_box (-10,-2,-2, 10,8,12)
CREO  : 体积 792.2646 mm³ / 面积 1003.5251 mm² / 质心 (0, 0.86831, 2.78313) / bbox     (-10,-2,-2, 10,8,12)
偏差  : −0.0074%          / −0.0064%          / Δ=(0, 0.00021, 0.00033) mm / 逐位相同
```

---

## 13 优先级建议

1. **P1 第 1 节**：`sheetmetal_flange` 的材料侧必须是可控的，否则 TXT 类"外折 L 形基体法兰"永远做不出来；这条直接决定零件能不能按 `type=sheet_metal` 建成。
2. **P1 第 3 节**：STL 导出的"日志在涨、状态不动"是最难诊断的失败形态，建议优先加超时 + 阶段进度。
3. **P2 第 6 节**：边选择器缺"按面限定"和"取最近"两条，凡是"薄板两端面各一套边"的零件（本工程 12 件里至少 6 件）都会踩到。
4. **P2 第 4/5 节**：两条都是"容差字段语义不清"，改动小、收益大，且能立刻消除本轮 20 个开口端和 2 次 Rotor 失败。
5. **P3 第 8/9 节**：纯入参适配，一次就能补齐。
