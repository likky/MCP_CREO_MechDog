# 2026-11-24 · Creo 10.0.0.0 · MCP_CREO_MechDog 0.40.0 · 核心问题

**被测版本**：`MCP_CREO_MechDog 0.40.0`
`version.py` → `VERSION = "0.40.0"`；`build/creo_worker.exe` 11,685,376 字节，
sha256 `c0ca4b706b749bc027548caad9ec237ade7c9eff792cba4f6909b0d745d98b1a`（2026-11-24 07:52 构建）
**被测对象**：`frigate_v4`（`model_id = df7f74bf5e424dbeb00605e218be89ad`），由 106 条 TXT 特征重建的整船零件
**本轮区间**：rev88 → **rev97**（486 → 521 特征，833 → 862 面，2648 → 2714 边）
**体积**：5,408,243,996.5236635 → **5,388,249,228.994157 mm³**
**收尾状态**：`status=ready`、`healthy=true`、`pending_job=null`、`recovery_pending=null`，
磁盘件 `output/frigate_v4.prt.100`，`part_sha256=311f33965c697201e1e603bfb83d8ab3afcb01778e3b485f1998cf217bb13d31`

---

## 0. 结论摘要

| 编号 | 问题 | 级别 | 状态 |
|---|---|---|---|
| P1 | `chamfer` 沿切向边链自动延伸，无「不延伸 / 限定单边」开关，**已经吃掉了后续特征 B052 的目标边** | **阻断** | 新证据，跨版未闭环 |
| P2 | `round` 在「平面 × 非解析曲面」交线上失败时只报 `Regeneration produced a failed, suppressed or incomplete feature`，没有任何几何层原因 | **阻断** | 新 |
| P3 | `mirror` 拒绝特征引用，11 条 TXT 镜像特征全部要手工重建；`kind=part` 只能整件镜像 | 能力缺口 | 跨版未变 |
| P4 | `ShellOp` 仍无 body / 面组选择器，B064「只对塔桅抽壳」不可表达 | 能力缺口 | 跨版未变 |
| P5 | `round` 不报告「加料还是去料」，凹边圆角会静默增加体积 | 建议 | 新 |
| P6 | `creo_inspect_model` 的 `returned_count` 是「本页条数」而非总条数，字段名易被读成总数 | 建议 | 新 |
| P7 | `ChamferOp.chamfer_type` 仍是 `Field(exclude=True)` | 建议 | 部分修复 |

**上一版四条（BUG-171～174）实测全部生效**，另有两处改进质量明显高于同类接口，见 §5。

---

## 1. P1：`chamfer` 沿切向边链延伸，吃掉后续特征的目标边

### 1.1 本轮三次复现 + 一次致命后果

同一个 `chamfer` 入口，四条边的「TXT 定位边长」「实际被倒角长度」对不上：

| TXT | 定位边 | 边长 (mm) | 载荷 | ΔV 实测 (mm³) | 折算被倒角长度 (mm) | 偏差 |
|---|---|---|---|---|---|---|
| B043 Chamfer1 | 2 条，412.4 合计 | 282.84 | `distance_angle` 150 / 60° | −9,408,466.238 | **482.9** | +71% |
| B050 Chamfer2 | 1 条，`4317` | 480.00 | `equal_distance` 150 | −6,525,000.000 | **580.0** | +21% |
| B057 Chamfer6 | 1 条，`9744` | 210.00 | `distance_angle` 160 / 45° | −4,376,000.200 | **341.9** | +63% |

折算方法：横截面面积解析可算，B043 为 `½·150·150·tan60 = 19,485 mm²`（本轮已在新面 `11198` 上核到落深 350→90.2 = 259.8 = 150·tan60，精确），B050 为 `½·150·150 = 11,250 mm²`，B057 为 `160×160 = 12,800 mm²`。`ΔV ÷ 截面` 即被倒角的边长。

**这不是新问题**：上一版 B051 Chamfer3 已经出现过同样现象（倒角面 `9599` 沿相切边链从 X=4709.226 一直做到 5359.226，比 TXT 定位的 5209.226 多 150）。

### 1.2 关键后果：B052 的目标边被 B051 吃掉了

B052 Chamfer4（150@45°）在 TXT 里的定位边是
`(5329.226, −430, 710) → (5369.226, −390, 710)`。

这条边与模型里现存的边 `9654` 共线（同一条 `x − y = 5759.226` 的 45° 线，
`9654` 是 `(5359.226, −400, 710) → (5519.226, −240, 710)`）。

而 B051 的倒角面 `9599` bbox = `[[4709.2, −550, 590], [5359.2, −400, 710]]` ——
**恰好止于 5359.226**。也就是 TXT 里那 40 mm 的边，整段落在 B051 已经切掉的区域里：

```
      x−y = 5759.226 那条 45° 线（Z=710）
  ──────────┬───────────────┬──────────────────►  X
        5329.226        5359.226           5519.226
        └ B052 想要的边 ┘│
                     B051 倒角面的终点
        └──── B051 多吃掉的 150 mm ────┘
```

**结论**：只要 `chamfer` 不能限定在给定边上，任何「后面还有一条短倒角落在同一条切向链上」的 TXT 都无法复现。本例中 B052 已经永久失去目标边（除非删掉 B051 重做，重做还是会被延伸）。

### 1.3 建议

1. 给 `ChamferOp` 加 `propagate: "chain" | "single"`（默认 `chain` 保持现行为，`single` 只切 references 里列出的边）。
   Creo 元素树里 `PRO_E_RNDCH_SET_1 … PRO_E_RNDCH_REFERENCES` 之后有「参照传播」开关（UI 上的
   「细节 → 参照 → 相同曲面 / 相切链」），Toolkit 侧对应参照收集指令 `PRO_CURVCOLL_ADD_ONE_INSTR`
   与 `PRO_CURVCOLL_ADD_TANGENT_INSTR` 的差别 —— 现状日志里能看到
   `ProCrvcollinstrAlloc(PRO_CURVCOLL_ADD_ONE_INSTR, &instr)`，说明载荷已经是「单条边」语义，
   但 Creo 在重生时仍按相切链扩展。
2. 即使暂时给不出 `single`，也请在回执里**把实际倒角长度报出来**（`chamfered_edge_length_mm` 或
   `faces[].length`），不要只报 `succeeded=true`。现在只能靠反解体积去推，误差不透明。
3. 如果是 Creo 的固有行为（Toolkit 无法禁止），请在能力表里明确标注
   「`chamfer` 按相切链生效，`references` 只决定链上的起点」，让调用方按链长而不是单边长度评估载荷。

---

## 2. P2：`round` 在「平面 × 非解析曲面」交线上失败，且无任何几何层诊断

### 2.1 现象

B035 Fillet1（TXT：`半径 1`，即 100 mm）定位边是模型边 `119`：
平面 `63`（`n=(0,0,1)`，Z=−660 的船底平板）与曲面 `139`（`type=42`，非解析面）的交线，
形状是一段 **R=10500 mm、长 2103.8 mm 的圆弧**，两端都收在奇异点上：

- 艏端：与另一段同半径弧 `117` 交于 `(7208.974, ±0.102, −660)`，该处还有一条 **0.203 mm 长的边 `118`**（刀口）；
- 艉端：与舷侧斜边 `301`/`346` 交于 `(5120, ±210, −660)`。

提交结果：

```
job 0d5557ddcce64dab980183dec0170c35   status = failed
message: Regeneration produced a failed, suppressed or incomplete feature
```

`native_result.json` 里的实际信息量：

```json
failed_stage  = "execute_round"
failed_operation = { "feature_label": "fillet1", "index": 0, "operation": "round",
                     "stage": "execute_round", "pro_error": null,
                     "pro_error_source": "unsupported",
                     "message": "Regeneration produced a failed, suppressed or incomplete feature" }
failed_features = [ { "id": 11610, "name": "FILLET1", "type": 913, "type_name": "round",
                      "status": 6, "incomplete": false, "geometry_items": [],
                      "dimensions": [ {"symbol": "d3408", "value": 100.0} ] } ]
```

日志里圆角的元素树是逐条成功的：

```
ProCrvcollinstrAlloc(PRO_CURVCOLL_ADD_ONE_INSTR, &instr)=0
ProElementCollectionSet(element, coll)=0
ProFeatureWithoptionsCreate=0
created_feature_id=11610
ProSolidRegenerate((ProSolid)board, PRO_REGEN_NO_FLAGS)=0
```

也就是说：**特征建出来了、半径 100.0 写进去了、但 `geometry_items=[]`（一个几何都没生成）、`status=6`。

### 2.2 我做过的排除（避免误报成 MCP 缺陷）

| 假设 | 试验 | 结果 | 判定 |
|---|---|---|---|
| 半径 100 mm 太大 | 同一 `round` 入口改 `size=50` 重提 | 同样 `execute_round` 失败、同样 `geometry_items=[]` | **不是半径问题** |
| `round` 入口本身坏了 | 同一轮 B070（同一 `round` 入口、6 条边、r=30） | `succeeded`，6 个新圆柱面半径**全部 = 30.0000** | **工具正常** |
| 圆边引用形式不对 | 同一轮 B101（同一 `round` 入口、圆弧边、r=29） | `succeeded`，残留下沉环半径 **0.848276 = 29.848276 − 29.0** 逐位吻合 | **工具正常** |

所以问题局限在这一条边 / 这一对面。**最可能的物理原因是这两张面在该缝处接近相切，或圆角无法在刀口端收口**，
但 MCP 没有给出任何可以确认这一点的信息。

### 2.3 建议

1. `round` 失败时，请把 Creo 侧的**圆角失败原因枚举**带回来。元素树里
   `PRO_E_RNDCH_…` 有一组诊断字段（半径超限 / 无法收口 / 相切边失败 / 相邻圆角冲突），
   Creo UI 会弹具体提示，Toolkit 侧即使拿不到字符串，也至少能拿到
   `ProFeatureStatusGet` 的 status 与 `ProFeatureErrorGet`（若可用）的 code。
   现在的 `pro_error: null` + `pro_error_source: "unsupported"` 等于把「不知道」当成结论报出来。
2. 请在失败回执里附上**被引用边的解析信息**，让调用方能自己判断：
   - 两个相邻面的 `type`、法向（可解析面）或 `curvature` 摘要；
   - **该边两端点的相邻面数量**（本 case 两端都在三面交汇的角点，且艏端还有一条 0.203 mm 的刀口边）；
   - 该边是否与相邻边相切。
   有这三项，我就能在提交前判断「这条边能不能倒」，而不是提交完再猜。
3. 若确定是 Creo 固有约束，请在能力表写清：
   「`round` 要求目标边至少有 N mm 的可通行余量，且两端不能收在零厚度刀口上」。

---

## 3. P3：`mirror` 拒绝特征引用，11 条 TXT 镜像全部要手工重建

`MirrorOp.geometry_references` 的校验：

```python
allowed = ("curve","axis","quilt","csys","point","part",
           "datum_feature","datum_axis_feature","datum_plane")
if any(r.get("kind") not in allowed for r in self.references):
    raise ValueError(
        "Toolkit mirror accepts curves, axes, quilts, datum planes, coordinate systems, "
        "points or the whole part; a feature reference is not a mirror item and hangs "
        "Creo, so mirror the part with kind=part or the feature's quilt with kind=quilt")
```

问题在于：**实体（boss/cut）既不是 `quilt` 也不是 `part`**，而 TXT 里 11 条 Mirror 全部是
「镜像对象：<某个实体特征>；以纵向中心面 Y=0 镜像」。

本工程的做法只能是「按 Y 取反重建同一截面」，本轮用 `_gen_mirror.py` 验证可行：

| 项 | 截面 | 解析 ΔV | 实测 ΔV | 误差 |
|---|---|---|---|---|
| 原件 B046 | 2 环 × 12,000 mm² × 2 mm | 48,000 | +48,008.132 | +8.13（+0.017%） |
| 镜像 B046 | 同上，Y 取反 | 48,000 | **+47,999.857** | **−0.14** |
| 原件 B047 | 1 环 14,400 mm² × 2 mm | 28,800 | +28,783.431 | −16.57（−0.058%） |
| 镜像 B047 | 同上，Y 取反 | 28,800 | **+28,800.000** | **0.00** |

镜像面法向实测 `B046 → (0.683013, 0.683013, −0.258819)`、`B047 → (0.0, 0.965926, −0.258819)`，
两阶段回读后 `sign=+1`，无需对草图 v 取反。

**代价**：镜像实体没有关联性（改原件不会跟着改），而且对 `B102`（镜像 Boss-Extrude33/34 + Fillet6）
这类「实体 + 圆角」的组合，必须「先建镜像实体 → 重取拓扑 → 再对新边倒圆角」两段式，MCP 侧没有任何原子入口。

### 建议

1. 优先做 `kind="feature"` 的**等价安全形态**：即「按 plane 复制 feature 的截面并重建」，
   而不是真的调 `ProFeatureMirror`（后者正是打崩 Creo 的那个）。
   具体是：给定 `references=[{kind:"feature", label:"sk_b046_a"} , …]` + `plane` + `keep_original`，
   在 worker 侧解析出这些特征的父草图与深度参数，逐条按镜像面重算后重建。
2. 或者给出 `replicate` 操作：`{op:"replicate", source_labels:[...], plane:{...}, keep_original:true}`，
   语义与 `mirror` 相同但实现走「重建」。TXT 里 11 条 Mirror 就能一次性接进 plan。
3. 短期至少请在 `MirrorOp` 的报错里附一句**可行的替代做法**（现在的报错说了「不能这么做」，
   但没说「可以怎么做」）。本轮能推进完全是因为我自己写了重建器。

---

## 4. P4：`ShellOp` 仍无 body / 面组选择器

```python
class ShellOp(...):
    remove_surfaces: list[dict[str, Any]] = []
    outward: bool = False
```

TXT B064：**「仅处理塔桅，去掉两个 X 端面，向内抽壳 0.2 米；不对整艘船抽壳。」**

当前模型是**单 body**（`body_id = -5778`），`creo_execute_plan` 的 `scope` 参数只作用于
`extrude`/`cut` 的刀具体，`shell` 没有等价入口，所以一抽就是整船。0.40.0 未改动此处。

### 建议

给 `ShellOp` 加 `body_ids`（语义同 `scope.kind="bodies"`）与 `remove_surfaces` 配套校验：
若 `body_ids` 多于一个实体且未给 `remove_surfaces`，在准入阶段拒绝并说明原因。
如果 Toolkit 的 `ProSmtPartThicknessValueGet` 系列确实无法按 body 限定，请明确写进能力表，
我就改为「把塔桅拆成独立 body 再抽壳、最后 boolean 合并」。

---

## 5. 上一版四条实测结果（正面）

| 上版条目 | 本轮实测 | 证据 |
|---|---|---|
| BUG-171 恢复超时落盘 + 预算可配 | **生效** | `restore_baseline` + `verify_mode=identity` + `budget_seconds=600` 一次成功（job `ca817099f57e4785b6d3135d9eb7b8d4`，`reconciliation_committed`，rev 保持 87）；上一版同一路径连续 4 次 `recovery_phase_timeout` |
| BUG-172 去掉冗余全量巡检 | **生效，幅度大** | 486 特征下 `verify_model_start` **57.2 s**（上一版 220–571 s）；`INSPECT_SUMMARY features=474 surfaces=815 edges=2612 half_edges=5224 elapsed_ms=42654`；`native.log` 由 4.5 MB 降到 **447 字节** |
| BUG-173 单轴倾斜基准面自动建锚定面 | **生效但未被触发** | 本工程自带 `pa_*` 锚定面，回执 `helper_anchor_created=False`、`anchor_count=2`，自动逻辑正确地没有重复加面 |
| BUG-174 `chamfer_type` 内联保留 | **生效** | 本地按 `dump_plan_operations` → `validate_operations` 复验：`{"op":"chamfer","label":"chamfer1","chamfer_type":"distance_angle"}` 完整保留，二次校验通过；本轮 B043/B057 的 `distance_angle` 内联提交一次成功 |

### 另外两处质量明显高于同类的地方（请保持）

1. **`round` 的「同圆重复引用」准入闸**：
   B101 的圆边在模型里被拆成两段半圆 `6626`/`6627`，我两条一起提交，它直接回
   > `round references edges 6626 and 6627 that lie on one circle (centre 686.001288, −130.000000, −810.000000 mm, radius 29.848276 mm); keep the smallest id (6626) and remove the duplicate reference`

   **给出了圆心、半径和可执行的修法**，按提示改一次即成功。这个模式应该推广到 `chamfer`（§1.3 第 2 条）。

2. **`creo_inspect_model(section="edges"/"surfaces", near=[x,y,z])`**：
   用 `near` 精确反查边，一条 2648 边的模型不用翻页就能定位目标边。本轮 10 个倒角/圆角的边就是这样锁定的
   （例：TXT `(5779.226, −500, 350)→(5879.226, −400, 350)` 直接命中 `edge 4124`，误差 `3e-7`）。

---

## 6. P5 / P6 / P7：三个小建议

### P5　`round` 不报告「加料还是去料」

B070 Fillet2 的 6 条边是**凹边**（桅侧 90 厚斜鳍与 Z=1360/1430 甲板的根部），圆角结果 **+264,401.119 mm³**，
即补料。回执只有 `succeeded=true`，没有任何符号信息；如果调用方以为圆角总是去料，会漏掉这一类。
建议在回执里加 `volume_delta_mm3`（带符号）与 `round_kind: "convex" | "concave"`。
顺带一提：`chamfer` 已经有盲切 `cut_volume_check` 的低去料告警，`round` 值得对齐。

### P6　`returned_count` 的语义

`creo_inspect_model` 分页时，`returned_count` 是**本页条数**（受 32 KiB 上限约束），不是总条数。
我第一版脚本写
`if not cursor or len(items) >= response["returned_count"]: break`，
结果 edges 只拿到第一页 85 条就以为取完了（实际 2648 条）。
建议：改名为 `page_count`，或在响应顶层加 `total_count`（`inspection.counts.edges` 已有该数，
但不在分页响应里）。这是个纯可用性问题，不影响正确性。

### P7　`ChamferOp.chamfer_type` 仍是 `Field(exclude=True)`

```python
chamfer_type: Annotated[
    Literal["equal_distance", "distance_angle", "d1_d2"],
    Field(default="equal_distance", exclude=True, description=...)]
```

BUG-174 是在 `dump_plan_operations` 里补回来的（这段补丁是对的，实测有效）。但任何不经过该函数的
自研路径（例如直接 `ChamferOp.model_validate(...).model_dump(exclude_none=True)`）仍会丢掉
`chamfer_type`，而丢了它之后 `angle_deg`/`angle_reference`/`distance_1`/`distance_2` 都会在复验时被判非法。
建议去掉 `exclude=True`，或在字段 `description` 里写明「本字段不参与最终 native payload，需由
`dump_plan_operations` 补回」，避免下一个人重踩。

---

## 7. 复现清单

| 用途 | 路径 / 参数 |
|---|---|
| 被测模型 | `model_id = df7f74bf5e424dbeb00605e218be89ad`，rev88 起点 |
| P1 三次复现 | job `01b61b0fbc2c4923b1bed553bab4041e`(B043) / `81b8ff95d6414b48a731c48f307c3f52`(B050) / `eb075f8291174ca0af0c0f71bd7cdda9`(B057)，`request.json` 里三个 `chamfer` op |
| P1 致命后果 | 删 B051 前模型里查 `surface 9599` bbox 与 `edge 9654` 共线（`x − y = 5759.226`） |
| P2 失败 | job `0d5557ddcce64dab980183dec0170c35`（`fillet1` size=100）、对照 job `76abb5fd42f64d15a34077f480b60cf2`（`fillet1_probe` size=50），两者同为 `failed_stage=execute_round` |
| P2 反证 | job `2b319e43084046039b3a95b37d7e505e`(B070, 6 边 r=30 成功) / `55d1c0a1777f46b0a54e94a168d2f4e4`(B101, 圆边 r=29 成功)；对照 B101 第一次两条弧一起提交被准入闸拒绝的 job `0a6e274fef54404b9a9551bb75a260ab` |
| P3 重建验证 | job `4e3fb3ed960647f1adda49db60d3fc03`(镜像 B046, +47,999.857) / `e2bb315412754a95a57402a8bafcf717`(镜像 B047, +28,800.000) |
| 边反查工具 | `creo_inspect_model(model_id, section="edges", detail="full", near=[x,y,z], limit=12, max_distance_mm=400)` |
| 分页 | `creo_inspect_model(..., section="edges", limit=200, cursor=...)`；第一页 `returned_count=85`（32 KiB 截断）、`next_cursor` 非空，共 30 页 |

---

## 8. 需要 MCP 侧回答的三个问题

1. **`chamfer` 的相切链延伸能否关掉？** 若不能，请给出「实际倒角长度」的回报字段，我会按链长建模。
2. **`round` 失败的 `status=6` / `geometry_items=[]` 对应 Creo 的哪一类原因？** 是否可通过
   `ProFeatureErrorGet` 或元素树的诊断字段取到枚举？我需要它来判断「该换半径」还是「该换边」。
3. **`ShellOp` 能否按 body 限定？** 若不能，我改为拆 body + boolean，但需要确认
   `creo_boolean_bodies` 在当前单 body 模型上能否先 `new_body` 再合并。

---

## 9. 本工程侧的对应处置（不是等 MCP）

- P1：已把「倒角按链长估 ΔV」写进工程规范；B052 标记为「被 B051 吃掉，需先解 P1」。
- P2：B035 标记为「局部几何不允许」，并把 r=100 / r=50 双失败与 B070/B101 成功作为证据留档；
  不再重复提交。
- P3：`_gen_mirror.py` 已作为常规工具，剩余 8 条 Mirror 按同一路径推进。
- P4：B064 继续 blocked。
- P5：凡 `round` 都反解 ΔV 符号，凹边按补料记账。
- P6：分页一律只以 `next_cursor` 判结束。
