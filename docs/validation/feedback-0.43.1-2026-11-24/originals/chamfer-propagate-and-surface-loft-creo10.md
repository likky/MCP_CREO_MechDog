# 2026-11-24 · Creo 10.0.0.0 · MCP_CREO_MechDog 0.43.0 · 核心问题

> 版本指纹：`version.py` `VERSION = "0.43.0"`；`build/creo_worker.exe` 11,784,192 字节，
> `sha256 = b25cff1a76a7272eaf6a8fd07418fbff1c4abc7bcf9f52eb03cec4d48a721950`，
> 构建时间 2026-11-24 16:41。Creo `release_numeric = 42`（10.0.0.0）。
> 机型：整船 `frigate_v4`，本轮从 rev97 推到 **rev106**，一次会话、无重启、无 `unknown_outcome`。
>
> 上一版反馈（0.40.0）提出的 P1–P7 这一版逐条核过：**P2 / P5 / P6 / P7 已闭环**，
> **P1 只是加了参数没改行为**，**P3 / P4 部分修**。另外本轮新拿到 4 条证据（N1–N4），
> 其中 N4（`surface_loft` 截面契约）是新的阻断类型。

---

## 0. 结论摘要

| # | 0.40.0 提的 | 0.43.0 实际 | 判定 |
|---|---|---|---|
| P1 | `chamfer` 沿切向边链延伸，吃掉后续特征的目标边 | 新增 `propagate: "single"｜"chain"`，但 `single` 的内部路径与 0.40.0 **一字未改**（`PRO_CURVCOLL_ADD_ONE_INSTR`），作者自己在 description 里承认延伸仍在 | ❌ **名义修复** |
| P2 | `round` 失败无几何诊断 | `round_failure.edge_diagnostics` 完整落地，本轮靠它一次定位 B035 根因 | ✅ **已修，质量高** |
| P3 | `mirror` 拒绝特征引用 | 仍未支持；但报错新增的第三条 Workaround 正是我们用的路线，本轮 **9/11 条镜像落地** | ⚠️ **部分修** |
| P4 | `ShellOp` 无 body 选择器 | `body_id` 已加（含负数 `-5778`） | ⚠️ **部分修**：有了 id，但 B064 仍做不了 |
| P5 | `round` 不报加料/去料 | `round_kind`、`volume_delta_mm3` 进了 compact 白名单 | ✅ **已修** |
| P6 | `returned_count` 语义含糊 | 新增 `page_count` / `total_count`，实测 `first_page 38 / total 521 / page_count 38` | ✅ **已修** |
| P7 | `chamfer_type` 仍 `exclude=True`，inline 路径丢字段 | `creo_execute_plan` 的 inline 分支也过 `dump_plan_operations()`，`chamfer_type` 被补回 | ✅ **已修（本轮实测）** |

本轮新增：

| # | 新问题 | 严重度 |
|---|---|---|
| N1 | `creo_inspect_model`（及同类工具）对**未知参数静默忽略**，`sections`（复数）传了就没了，不报错 | 中（吃掉一整轮排查） |
| N2 | `round_failure` / `failed_loft_input` 这类结构化诊断只在 `native_result.json` 的 `operations[]` 里，`creo_get_job` 回执与报错文案都不给路径 | 低～中 |
| N3 | `bounding_box_mm` 与 `surfaces[].bbox` 的并集不一致（−910.0 vs −885.0，差 25 mm） | 低 |
| N4 | `surface_loft` 的**截面契约**：「一条曲线，或两条合成一个闭合轮廓」——三段以上的闭合截面没有表达方式 | **高（新的阻断类型）** |

另外，**球鼻艏的核心阻断在 0.43.0 上仍然存在**，而且换了一种失败形态（详见 §7）：
`surface_loft` 现在能把特征建出来（`create_code = 0`），卡在 `ProFeatureElemtreeExtract = -18`。

---

## 1. P1：`propagate` 只开了一个口子，`single` 的行为与 0.40.0 逐字节相同

### 1.1 代码路径（这是关键证据）

`native/generic.cpp`：

```cpp
static void curve_collection(ProElement element, const J &refs) {
    curve_collection_with_propagation(element, refs, false);   // ← 第二参数恒为 false
}

static void curve_collection_with_propagation(ProElement element, const J &refs,
                                              bool propagate_chain) {
    ...
    CK(ProCrvcollinstrAlloc(PRO_CURVCOLL_ADD_ONE_INSTR, &instr));   // 每条引用都用 ADD_ONE
    ...
    if (propagate_chain) {                                          // 只有显式 chain 才追加
        CK(ProCrvcollinstrAlloc(PRO_CURVCOLL_ADD_TANGENT_INSTR, &tan_instr));
    }
}
```

也就是说：

- `propagate: "single"`（现在的默认值）走的还是 **0.40.0 里那个唯一的 `curve_collection()`**，用的是 `PRO_CURVCOLL_ADD_ONE_INSTR`；
- 0.40.0 里 B043 / B050 / B057 那三次「倒角面沿切向链延伸」**就是在 ADD_ONE 下发生的**；
- 因此 `single` 不是「改好了」的模式，而是「一直以来的模式」。

作者在 `ChamferOp.propagate` 的 description 里已经诚实写明：

> `'single'` (default, `PRO_CURVCOLL_ADD_ONE_INSTR`) selects only the listed edge(s), **though Creo's default open-end chamfer transition can still extend the chamfer plane into a tangent/oblique neighbor face**

这句承认了延伸仍在。所以 P1 的准确表述是：**文档化 + 新增 `chain` 选项，不是行为修复**。

### 1.2 0.40.0 记录的三次复现（同一路径）

| 特征 | 报的边长（折算） | 实际吃掉的长度 |
|---|---|---|
| B043 Chamfer1（150 / 60°） | 282.84 | 482.9 |
| B050 Chamfer2（150 / 150） | 480 | 580 |
| B057 Chamfer6（160 / 45°） | 210 | 341.9 |

### 1.3 B052 已经救不回来了（第二种独立方法再次确认）

上一版记的 D22 是「B052 的目标边被 B051 的倒角面吃掉」。本轮用**几何选择器**（不是翻 dump）再验一次：

```json
{"op":"chamfer","label":"p7_probe",
 "references":[{"edge":{"kind":"geometry_selector","target":"edge",
   "endpoints_mm":[[5329.225685,-430.0,710.0],[5369.225685,-390.0,710.0]],
   "tolerance_mm":0.5}}], ...}
```

回执（job `c22ee812ccae48a1af87055da88478be`）：

> `geometry_selector edge endpoints matched none of the 2076 eligible model edges (tolerance_mm=0.500000)`

TXT 给的边 `(5329.225685, −430, 710) → (5369.225685, −390, 710)` 在 **0.5 mm 容差**下匹配不到任何现存边。
最近的一条是 `9645`，起点 `(5359.225685, −400, 710)` —— 正好是 B051 倒角面 `9599` 的 x 止点 `5359.226`。

结论：**`propagate` 修好也救不回历史损失**，这条边在 0.40.0 那次 B051 里就已经被合并掉了。要补只能把 B051 之后的一整段回滚重做，代价远大于收益。

### 1.4 建议

1. 如果短期改不了内核行为，至少在 `ChamferOp.propagate` 的 description 里补一句**后果**：「`single` 不保证倒角面止于给定边；若相邻面与该边相切/斜交，倒角面可能沿面相切方向继续延伸，从而吞掉紧邻的后续特征边」。现在只说「can still extend」，没说「会吃掉别的特征要用的边」。
2. 更实际的：`chamfer` 回执里**回报实际倒角面的 bbox**（像 `round` 那样给 `created_surface_ids` + 面积/bbox），让调用方能在同一个作业里就发现「吃多了」，而不是等到后面某个特征找不到边才发现。本轮 `chamfer` 回执只给 `volume_delta_mm3` 和 `created_surface_count/area`，没有 bbox。
3. 长期：`PRO_CURVCOLL_ADD_ONE_INSTR` 之外还有「按边定长截断」的过渡选项（Creo 的 `Corner Blend` / `Chamfer Transition`），建议做成 `transition: "default"｜"stop_at_vertex"` 之类的开关。

---

## 2. P2：`round_failure` 已修，而且是本轮最有价值的一处

上一版 P2 的核心诉求是「`round` 失败只报 `Regeneration produced a failed, suppressed or incomplete feature`，没有任何几何信息」。0.43.0 修得很彻底。

### 2.1 实测回执（B035 Fillet1，r=100，job `d5dd1c7bb5764767908a747850b3b906`）

`creo_get_job` 的 message：

> `round feature failed regeneration (edge 119, length_mm=2103.005643, dihedral_deg=53.488636; see round_failure.edge_diagnostics)`

`native_result.json` → `operations[0].round_failure`：

```json
{
  "edge_diagnostics": [{
    "edge_id": 119,
    "length_mm": 2103.005643,
    "dihedral_angle_deg": 53.488636,
    "adjacent_surfaces": [
      {"id": 63,  "type_name": "plane", "area_mm2": 1922049.9,  "normal_at_midpoint": [...]},
      {"id": 139, "type_name": "ruled", "area_mm2": 1639385.5,  "normal_at_midpoint": [...]}
    ],
    "start_vertex": {"adjacent_edge_count": ..., "min_adjacent_edge_mm": 0.2030333652619447,
                     "tangent_adjacent_edge_ids": [...]},
    "end_vertex":   {"adjacent_edge_count": ..., "min_adjacent_edge_mm": 1894.7559209565798, ...}
  }],
  "feature_status": 6,
  "feature_status_name": "unregenerated",
  "feature_incomplete": true
}
```

### 2.2 这块诊断直接给出了根因

B035 折腾了五轮都没定性。这次一眼就看完：

- 边 `119` 长 2103 mm、二面角 53.49°，两侧面是 `63`（平面，1.92 m²）和 `139`（直纹面，1.64 m²）；
- **起点顶点的 `min_adjacent_edge_mm = 0.203033 mm`** —— 即圆角起点落在艏柱的刀口上；
- 终点顶点是 1894.76 mm，很宽松。

所以根因不是「半径 100 太大」（0.40.0 已用 r=50 排除过），而是**圆角起点在一个 0.203 mm 的刀口上，无法收口**。
这类信息在 0.40.0 里一条都没有。**这一项请务必保持**。

多引用时逐条 probe 隔离出 `failed_reference_index` 的设计也很好，省掉了二分试。

### 2.3 两个小问题（不影响结论）

**N2-a：位置不可发现。** 报错文案说 `see round_failure.edge_diagnostics`，但没说它在
`native_result.json` 的 `operations[]` 里、也不在 `creo_get_job` 的返回体里。
我第一遍在顶层找 `round_failure` 拿到 `null`，以为是没写。建议：
- 文案改成 `see operations[<i>].round_failure.edge_diagnostics in native_result.json`；
- 或者把 `round_failure` 也放进 `creo_get_job` 的回执（至少给 `failed_reference_index` 和两个顶点的 `min_adjacent_edge_mm`）。

**N2-b：`min_adjacent_edge_mm` 的语义值得写明。** 现在读者要自己推断「0.203 mm 的相邻边 ⇒ 刀口 ⇒ 无法收口」。建议 description 里加一句「小于 radius 太多时，圆角在顶点处没有足够材料收口，通常会 status=6」。

### 2.4 另一个正向行为（上一版 D21，请继续保留）

`round` 的准入闸能识别「两条引用落在同一个圆上」并给出可执行的替换建议：

> `round references edges 6626 and 6627 that lie on one circle (centre 686.001288, −130.000000, −810.000000 mm, radius 29.848276 mm); keep the smallest id (6626) and remove the duplicate reference`

本轮镜像 B102 后又要对新边做同样的 r=29 圆角，直接套这个规则（只报 `12922`）一次成功。**这个「报错即给出下一步」的模式是这套 MCP 里最好的一处交互**。

---

## 3. P3：镜像 —— 9/11 落地，但它仍然不是「关联镜像」

### 3.1 现状

`MirrorOp.geometry_references` 的允许集仍然是
`{curve, axis, quilt, csys, point, part, datum_feature, datum_axis_feature, datum_plane}`，**没有 `feature`**。

但 0.43.0 的报错里新增了第三条 Workaround，正是本轮用的路线：

> (3) to mirror an individual solid boss/cut feature across a plane, recreate the sketch/extrude with coordinates reflected across the mirror plane

照这条路，本轮把 **9 条镜像**做完了（全部做过几何级复核，不只读回执）：

| rev | TXT | 做法 | ΔV（mm³） | 复核 |
|---|---|---|---|---|
| 96/97 | B048 Mirror5 | 反射 Sketch82/83 | +47,999.857 / +28,800.000 | 解析 48,000 / 28,800 |
| 98 | B080 Mirror8 | XZ offset −210→+210，direction positive→negative | +720,018.329 | 两棱柱 Y 210…215，X/Z 逐位吻合 |
| 99 | B081 Mirror9 | XZ offset −500/−350→+500/+350 | +36,193.438 | 4×r25 + 4×r19 圆环面各就位 |
| 100 | B074 Mirror7 | XZ offset −500→+500，cut 反向 | −402,121.566 | 4 孔 r=40.0000，解析 402,123.86 |
| 101 | B072 Mirror6 | XY 草图 v 取反（thin 是对称偏置，无侧向歧义） | +1,152,928.746 | 壁面 Y=497.5/502.5 与原件 ±502.5 一一对应 |
| 102 | B009 Mirror2 | 反射 LPattern1 的 leader 后重发阵列 | 0.000 | 两侧各 10 片，面积 42,928.81332226138 完全相同 |
| 103 | B026 Mirror3 | 反射 Cut-Extrude7 后重发阵列 | −362,406.001 | 两侧各 7 孔，X 2600+430k 完全相同，同一斜面修剪 |
| 104 | B102 Mirror10 | YZ 草图 u 取反 | +286,591.584 | r=16.324930 / r=29.848276，中心 (Y=+130, Z=−810) |
| 106 | B102 上的 Fillet6 | 新边 `12922` 走 `round` r=29 | −26,502.037 | 与原件 B101 的 −26,502.067 **相差 0.03 mm³** |

剩 2 条（B004 Mirror1、B034 Mirror4）都吊在曲面链上；B106 Mirror11 只做了 1/3（见 3.3）。

### 3.2 但这仍然不是镜像

TXT 对每一条镜像都写「**保留原特征与关联关系**」。重建出来的副本：

- **没有任何关联** —— 源特征一改，镜像不会跟；
- **不是一条 Mirror 特征** —— 特征树里多了一整套 sketch + extrude（rev98 → rev106 这 8 条镜像共增加 68 个特征），没有一条能在特征树里读成 Mirror；
- **阵列镜像要拆成两步** —— 先反射 leader、再按原 direction/spacing/count 重发一次阵列，特征树里出现两个 `LPATTERN`；
- **斜置特征基本做不动** —— 见 3.3。

所以 P3 的诉求保留：**请给 `MirrorOp` 一个能吃 `{kind:'feature', id:N}` 的路线**。
如果 `PRO_FEATURE` 类型的 mirror item 在 Creo 10 上必挂（0.35.5 挂过两次），那退一步：
请提供 `mirror_feature_by_rebuild` 这类**一等公民操作**——输入 `{feature_id, mirror_plane}`，由 MCP 自己读出该特征的 sketch 平面与全部几何、在反射坐标系里重建，并把结果标成「Reflected copy of Feature N」。现在这段逻辑每个使用者都要自己写一遍，而且坐标系约定藏在 `sketch_frame()` 里。

### 3.3 B106 只做了 1/3 的原因（反射坐标系的约定没公开）

`Cut-Extrude16/17`（B104/B105）的草图挂在三点斜基准面 `pl_b104` / `pl_b105` 上：

```
origin = [233.5540778, 416.9049427, 0]
u_axis = [-0.8724281149, 0.488742451944, 0]
```

反射一个斜置草图坐标系要同时算三件事：`O → R(O)`、`u → R(u)`、`v → −R(v)`
（因为 `det(R) = −1` 使 `n' × u' = −R(n × u)`），草图 2D 点从 `(a, b)` 变成 `(a, −b)`。
这套推导没有任何文档，只能自己推。MCP 里也没有「镜像基准面」或「在反射坐标系里建草图」的原语。

### 3.4 建议：把三个 preset 的 u/v/n 约定直接写进 description

这是本轮最便宜的一条改进。`native/generic.cpp:2171 sketch_frame()` 里写死了：

| plane | axis | n | u | v | Y=0 反射后该怎么做 |
|---|---|---|---|---|---|
| `XY` | 2 | (0,0,1) | (1,0,0) | (0,1,0) | 草图 v 取反，offset / direction 不变 |
| `XZ` | 1 | (0,−1,0) | (1,0,0) | (0,0,1) | offset 变号，草图不变，`direction` positive↔negative |
| `YZ` | 0 | (1,0,0) | (0,1,0) | (0,0,1) | 草图 u 取反，offset / direction 不变 |

这张表我花了半轮才试出来（`XZ` 的 n 是 **−Y** 而不是 +Y，第一次按 +Y 推导致 cut 方向反了）。
放进 `SketchOp.plane` 的 description 里，一行成本。

---

## 4. P4：`ShellOp.body_id` 已可用，但 B064 还是做不了

### 4.1 已修的部分

```python
body_id: Annotated[int | None, Field(default=None,
    description="Optional exact solid body ID from creo_inspect_model bodies[] "
                "(including negative initial body IDs such as -5778). ...")]
```

校验器接受非零 32 位整数，负数放行。**这一条完全达标**，上一版提的「`-5778` 传不进去」已经不存在。

### 4.2 B064 为什么仍然做不了

TXT 原文：

> B064．Shell1：抽壳。**仅处理塔桅**，去掉两个 X 端面，向内抽壳 0.2 米；不对整艘船抽壳。

本模型 `body_counts = {objects: 1, active: 1}`，**只有一个 body**，塔桅和船体在 rev18–34 那批主体块里就已经融合成同一个实体。
`shell` 是**整体抽壳**：给了 `body_id = -5778` 只会把整条 8100 mm 的船抽成 20 mm 壁厚。
`remove_surfaces` 只能指定「哪两个面开口」，不能指定「只在塔桅范围里抽」。

所以 `body_id` 是**必要条件、不是充分条件**。缺的是下面两个之一：

1. **region 级限定**：`ShellOp` 增加 `affect_region`（一组面的集合，抽壳只在这些面围成的子区域内进行）；
2. **把已融合实体拆回 body**：Creo 有 `Insert > Shared Data` 之外还有「分割实体 / 独立化」，或者 `ProSolidBodySplit` 一类接口。有了它，就能先把塔桅拆成独立 body 再 `body_id` 抽壳。

对这个问题，**我的建议是第 2 条**：`body_id` 已经做出来了，「先拆 body 再定向操作」是一条通用的能力，能复用到 `cut` 的 `scope`、`boolean_bodies`、`quilt_merge` 等一堆地方。

---

## 5. P5 / P6 已闭环，P7 也已修（本轮实测）

- **P5 已修**：`src/creo_mechdog/compact_sections.py` 的白名单里已有 `round_kind`（251 行）与 `volume_delta_mm3`（252 行），compact 回执能看出圆角是加料还是去料。
- **P6 已修**：分页响应同时给 `returned_count` / `page_count` / `total_count`。实测 `creo_inspect_model section=features` 首屏 `first_page 38 / total 521 / page_count 38`，`next_cursor` 走 12 页拿全。上一版那个「把 `returned_count` 当总条数」的坑已经不会有人再踩。
- **P7 已修，而且是这一版里我用实测确认过的**：

  `creo_execute_plan` 的 inline 分支现在也过 `dump_plan_operations()`：

  ```python
  payload = dump_plan_operations(operations)          # server.py:1097
  ...
  elif data.get("op") == "chamfer":
      # BUG-174: ChamferOp excludes chamfer_type from the final native payload, ...
      if chamfer_type is not None and ("chamfer_type" in provided or chamfer_type != "equal_distance"):
          data["chamfer_type"] = chamfer_type          # schema.py:3394
  ```

  实测：把一条 `chamfer_type:"d1_d2"` + `distance_1/distance_2/reference_surface` 的倒角**用 inline 方式**（不带 `plan_file`）提交，
  准入闸**接受了**，作业被排队，最后在 native 侧因为边找不到而失败（job `c22ee812ccae48a1af87055da88478be`），
  体积保持 `5,389,687,300.838182` 不变。若 `chamfer_type` 仍被丢，准入闸会在提交阶段就回
  `distance_1/distance_2/reference_surface require chamfer_type='d1_d2'`。

  **`plan_file` 这个绕法现在可以不用了。** 感谢。

---

## 6. 本轮新发现

### N1（中）：未知参数被静默忽略

`creo_inspect_model` 的正确参数是 `section`（单数）。我第一遍写成了：

```json
{"model_id": "...", "detail": "full", "sections": ["features"], "limit": 200}
```

返回 **HTTP 200、无 error、无 warning**，`data` 是空的，我拿到 `FEATURES 0`，以为是模型没有特征。
同样的调用再塞一个 `bogus_field: 1` 也一样被吞掉。

这直接导致我浪费了一轮排查（改成 `section` 就正常了）。建议：

- 对所有工具入参做 `extra="forbid"` 式的严格校验（pydantic 的 `StrictModel` 已经是这个思路，漏的应该是 MCP 的 `arguments` 层）；
- 或者在响应里回一个 `ignored_arguments: ["sections", "bogus_field"]`；
- 至少要有一句 `unknown argument 'sections'; did you mean 'section'?`。

同类工具还有 `creo_capabilities`、`creo_get_job` 等，建议一并处理。

### N2（低～中）：结构化诊断只在磁盘上

见 §2.3。`round_failure`、`failed_loft_input`、`loft_checks`、`verify_stages` 这些块全部只在
`jobs/<job_id>/native_result.json` 里，`creo_get_job` 的返回体里没有。调用方必须知道这个路径才能看到最有用的信息。
建议 `creo_get_job` 至少透传 `failed_operation_index`、`failed_stage`、`failure_phase`，并在回执里给 `native_result_path`。

### N3（低）：`bounding_box_mm` 与逐面 bbox 的并集不一致

同一次 `creo_inspect_model detail=full`：

- `inspection.bounding_box_mm.min = [-0.1, -690.1, **-910.0**]`
- 但 `surfaces[]`（964 条，全部）的 `bbox` 并集最小 Z 只有 **-885.0**
- 差 25 mm，`size[2] = 2830.0 = 1920 - (-910)` 说明用的是前者

rev97 与 rev106 两次全量 dump 的逐面并集都是 −885.0，所以这 **不是** 本轮新增特征造成的。
猜是 `ProSolidOutlineGet` 把 4 个 quilt 或构造几何也算进去了，或者带精度外扩。
想确认：`bounding_box_mm` 到底覆盖哪些对象？如果它和 `surfaces[].bbox` 口径不同，建议分别命名
（例如 `solid_outline_mm` / `surface_extent_mm`）。

### N4（高，新阻断类型）：`surface_loft` 的截面契约

这是在**独立探针件**上测的，没有动整船模型（`loft_probe_043b` / `loft_probe_043c`）。

**第一轮**：两个 100×100 与 60×60 的**闭合矩形**（4 条 `line`）作截面 →

> `surface_loft section 1 section must own one curve, or two curves forming one closed profile; feature 40 owns 4 non-composite curves`

换成 `polyline closed:true` 的 4 点闭合多段线，**同样被拒**（Creo 会把它拆成 4 条 line）。

**第二轮**：两个**圆**（各 2 段圆弧，`section_curve_ids = [45,46] / [54,55]`）→ 过了截面契约，但见 §7 的 −18。

结论：现行契约只接受

- **一条**曲线（样条 / 整椭圆 / 单个闭合样条），或
- **恰好两条**曲线合成一个闭合轮廓（如 2 段圆弧组成的圆）。

**由 N>2 段组成的闭合截面没有表达方式**，除非先把它们缝成一条复合曲线 —— 而 MCP 没有
「把多条曲线合成 composite curve」的操作。

这对球鼻艏的具体影响：
- B030 的 8 个截面（Sketch108/109/110/111/112/70/72）**各是一条闭合样条** ✅ 符合契约；
- 但 B030 的 3 条纵向导线（Sketch64 / 65 / 67）**各由 line + spline 两条组成**，
  而 `guides` 的契约是「one curve each」。按字面读，这三条导线表达不了。
  （这一条我没有实测确认 —— −18 在更早一步就把作业打回了，测不到 guides。）

建议：给 `sections` / `guides` 增加 `{kind:'curve_chain', ids:[...]}` 形式，由 MCP 侧把多条曲线
拼成一条 composite curve 再喂给 kernel。否则「截面是 N 段线围成的多边形」这种最普通的建模场景永远进不来。

---

## 7. `surface_loft` 在 Creo 10 上仍然是 −18（球鼻艏的核心阻断没有变化）

这是本轮最重要的坏消息，所以单独一节。

### 7.1 实测

探针件 `loft_probe_043c`（model `21ae2b795d53443dbd58443f3a10830e`），
两个圆截面（Ø100 @ Z=0、Ø60 @ Z=100），`interpolation = "straight"`（两截面本就是直纹，不受平滑影响）。
作业 `cc6b9c855c86465fa2ace04a28e1bd2e`：

> `surface_loft created the feature (create_code=0) but this Creo release cannot extract its element tree (code -18, SURFACE_LOFT_EXTRACT_UNSUPPORTED); feature_incomplete=true, release_numeric=42; the job was rolled back`

`native_result.json` → `operations[0]` 的结构化证据：

```json
{
  "op": "surface_loft", "label": "loft_probe",
  "route": "probbl_boundary_blend",
  "create_code": 0,
  "extract_api": "ProFeatureElemtreeExtract",
  "extract_code": -18,
  "extract_unsupported": true,
  "feature_incomplete": true,
  "kernel_completion": "unsupported",
  "kernel_evidence": {"create_code": 0, "extract_code": -18, "feature_incomplete": true, "release_numeric": 42},
  "section_count": 2, "piecewise_ruled": true,
  "section_curve_ids": [45, 46, 54, 55],
  "section_geometry_ids": [[45, 46], [54, 55]],
  "section_source_kinds": ["sketch", ...],
  "guide_count": 0, "guides": []
}
```

### 7.2 和 0.19–0.26 时期的差别

- **好的一面**：现在的回执把 `create_code` / `extract_api` / `extract_code` / `kernel_completion` 全拆开了，
  能清楚看出「**特征建出来了，卡在提取**」。以前只有一个裸的 −18，很容易被误判成「建不出来」。
  `SURFACE_LOFT_EXTRACT_UNSUPPORTED` 这个错误名也比裸码有用。
- **没变的一面**：`release_numeric = 42`（Creo 10.0.0.0）上 `ProFeatureElemtreeExtract` 依然返回 −18，
  `feature_incomplete = true`，作业回滚。**0.19 → 0.43 跨了 24 个版本，这条一次都没变。**

### 7.3 我这边能确认的边界

- 不是截面类型问题：单条闭合样条、2 段圆弧的圆、2 截面直纹，都试过，都在提取这一步挂。
- 不是 guides 问题：`guide_count = 0` 的纯 2 截面也被 −18 拦下。
- 不是参数问题：`interpolation` 两种值、`creation_route` 不给，结果一致。
- 因此 **不是**我们这边喂错了参数 —— 是 Creo 10 的 boundary blend 特征树在这个 SDK 版本上取不出来。

### 7.4 建议（这条已经不是「优化」，是「要么绕，要么明说」）

1. **明说**：`creo_surface_loft` 的 description 现在写的是「Requires a Toolkit SDK whose `ProElemId.h` declares the `PRO_E_BNBLN_*` boundary-blend element ids. Missing support returns `SURFACE_LOFT_SDK_UNAVAILABLE`」。但实际在本机是「SDK 声明了、创建成功、提取 −18」。建议在这个 description 里补一句：**「On Creo 10.0.0.0 (`release_numeric=42`) creation succeeds but element-tree extraction returns −18, so the job always rolls back; the operation is effectively unavailable on that release.」** —— 这样后续使用者一眼就知道别在上面花时间，也不用每版重测。
2. **给个替代路线**：如果能用 `surface_fill`（`creo_surface_fill`）把「多截面直纹面」拆成若干四边形再逐片填，或者用 `creo_surface_boundary_fill` 之外的增长（`sweep` + `surface_trim`）拼出同一块面，也是可行的。哪怕效率低，只要能在 Creo 10 上出活就行。
3. **`creo_capabilities` 里加一条「本机实际可用性」**：现在 `unavailable_tools` 只列了 4 个工具，`creo_surface_loft` 不在里面，但它在 Creo 10 上实际不可用。建议再加一个 `runtime_unavailable: {creo_surface_loft: "extract -18 on release_numeric 42"}`，由上一次真实作业的证据回填。

---

## 8. 复现清单（全部本机可查）

| 用途 | job_id | 结果 |
|---|---|---|
| B080 Mirror8 | `4e7d44a7d5de454094db71f6edb1b037` | succeeded rev98 |
| B081 Mirror9 | `26ec09ac58974c5894f2753bb3865ff6` | succeeded rev99 |
| B074 Mirror7 | `19fd8f85285a4a66af2e25d9b46cbe54` | succeeded rev100 |
| B072 Mirror6 | `d9fc3379f54446cf9d9dd494de6c5513` | succeeded rev101 |
| B009 Mirror2 | `1a39d7492b0949e8a8e393e08247dde3` | succeeded rev102（ΔV=0） |
| B026 Mirror3 | `1eb29d14b1224184b00842548d4a953a` | succeeded rev103 |
| B102 Mirror10 | `13ecb769a96a4c4ea116adffa66c7b62` | succeeded rev104 |
| B106 Mirror11（部分） | `a8bb9ed1247147d7a6972f87bedc842a` | succeeded rev105 |
| B102 Fillet6 r=29 | `d813ece832f2497f87b91edbb0f46034` | succeeded rev106 |
| **P2** B035 r=100 诊断 | `d5dd1c7bb5764767908a747850b3b906` | failed，`round_failure` 完整 |
| **N4** 4 条 line 组成的闭合矩形截面 | `b3ce952230374e51b5ac1a52aec80fc5`（模型 `85855634484940249f7619ec2f216655`） | 被截面契约拒绝 |
| **N4** 4 点闭合 polyline 截面 | `dd6ea44bf1834fd98d32d6b0df2a5795`（模型 `905da50011604a5aa9d9cd281dc28754`） | 同上（Creo 把它拆成 4 条 line） |
| **§7** 2 圆截面放样 | `cc6b9c855c86465fa2ace04a28e1bd2e`（模型 `21ae2b795d53443dbd58443f3a10830e`） | failed，`extract_code = -18` |
| **P7** inline d1_d2 倒角 | `c22ee812ccae48a1af87055da88478be` | 准入通过、native 失败（边不存在），体积不变 |

---

## 9. 需要 MCP 侧回答的 4 个问题

1. **P1**：`propagate: "single"` 是不是就是 0.40.0 的行为（`curve_collection` → `ADD_ONE`）？
   如果是，那「倒角面沿切向延伸吃掉后续特征边」这个问题在 MCP 层还有没有别的旋钮（transition / stop-at-vertex / 定长截断）？
2. **P3**：`PRO_FEATURE` 类型的 mirror item 在 Creo 10 上必挂，那么能不能做一个
   `mirror_feature_by_rebuild` 的一等公民操作？还是说这条路必须由调用方自己写（现在的现状）？
3. **P4**：把已融合的实体拆回独立 body，Creo 10 Toolkit 里有没有可用接口？如果有，`body_id` 这条路就通了。
4. **N4 / §7**：`surface_loft` 在 `release_numeric = 42` 上还有没有别的实现路线
   （例如不走 `Probblh` 元素树、直接画 b-spline 面）？如果确定没有，请把它和
   `creo_surface_boundary_fill` 一样列进 `unavailable_tools`，并注明按 release 区分。

---

## 10. 本工程侧的对应处置（不是等 MCP）

- **已完成**：9/11 条镜像 + B102 上的 r=29 圆角，rev97 → rev106，体积 5,388,249,228.994157 → **5,389,687,300.838182**，
  全部逐面复核（引用见 §3.1 与状态文档 `frigate_v4-状态与偏离.md` 第 3 批表）。
- **不再尝试**：B052（边已不存在，§1.3）、B035（0.203 mm 刀口，§2.2）、B095（无 Z=200 台阶，D23）、
  B076/B078（TXT 无边锚，D24）。这 4 项在模型侧是**确定做不到**，不是「等 MCP」。
- **等 MCP**：B002/B030 曲面链（§7）、B064 抽壳（§4.2）、B106 的 B104/B105 部分（§3.3）、B004/B034 两条镜像。
- **明确不宣称**：Creo 10 上「球鼻艏 MCP 曲面能力已修复」——本轮探针证明 `surface_loft` 与 0.19 时期一样不可用；
  本轮完成的是**镜像批次**，不是球鼻艏。
