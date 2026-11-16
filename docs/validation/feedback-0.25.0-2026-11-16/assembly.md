# 2026-11-15 · CREO · 0.25.0 · 新增 coincident 与 geometry_selector 仍无法消费 TXT 锚点，致 61 条配合零建立

> 用途：反馈给 `MCP_CREO_MechDog` 作者，用于下一版优化。
> 性质：**0.25.0 实机重跑后的验收报告**，不是推测、不是静态源码审阅结论。所有「成功 / 失败」均来自 Creo 10 上实际提交的 job 与回读。

---

## 0. 结论先行

1. **0.25.0 确实修好了 0.24.1 反馈里的 3 项**：`sheetmetal_base_flange`（组合首壁）、`linear_pattern`（Hom n11）、`plan_file`（大计划文件入口）在 Creo 10 上均实机成功；`coincident → mate`、`concentric → insert` 的映射也确实生效（已用 job 回执 `normalized type=mate` 证实）。
2. **但本轮最核心的新问题是「MCP 有但用不了」**：0.25.0 新增的配合词只认 **Creo 内部几何 id**，而唯一指定 TXT 的 61 条 `[B-MATE]` 只提供 **几何锚点 `near=(x,y,z)` / `dir=(...)`**；更关键的是，**本版同时新增的 `geometry_selector` 在配合引用层被白名单直接拒绝**，所以连「用新版选区器把锚点解析成 id」这条路都不通。结果：**61 条配合 0 条建立**，总装 23 个组件仍然只有 `fix` 约束。
3. **同类「有但用不了」还有 3 处**：`geometry_selector` 要求边选区给 `endpoints_mm` 两端点，而 TXT 圆角/倒角只给单点锚点；`chamfer_type="distance_angle"` 要求 `angle_reference` 面引用，TXT 完全没有；`sheetmetal_base_flange` 是**组合特征**（2 个 feature），不等价于 TXT 要求的 SolidWorks 单特征 `SMBaseFlange` 中面加厚语义。
4. **本轮重建结果**：12/12 零件有实体、全部 `saved_reloaded` 巡检通过；23 组件总装建成并分色；但整体 verdict 仍是 **PARTIAL / DEGRADED**，不宣称 `EXACT` / `VERIFIED`。跳过特征从 0.24.1 的 12 项降到 9 项（净减少 3 项，另有 1 项上轮证据误记与 1 项计数口径变化，对账见 2.1 节），但没有任何一个零件的体积收敛到 TXT 指纹。

---

## 1. 复现环境与约束

| 项 | 值 |
|---|---|
| MCP | `MCP_CREO_MechDog` **0.25.0**（`version.py`、`creo_capabilities.version/server_version` 一致；108 个工具） |
| 在线版本核查 | 本轮早先 `creo_check_update(force=true)` 成功返回 `up_to_date`；GitHub `releases/tags/v0.25.0` 已正式发布。本次 `creo_capabilities` 内嵌的 update 字段因「超过 5 秒网络预算」`status=failed`，**不能作为「已是最新」的证据**，仅本机版本确定 |
| Creo | `Creo 10.0.0.0` / `release_numeric=42`，单 native channel，`reject_busy_without_creating_a_job` |
| 唯一几何输入 | `二爪夹持机械臂_跨软件三维建模自然语言说明_v1.5.txt`（1225 行，单位 mm） |
| 建模工具 | **仅 `MCP_CREO_MechDog`**。本地脚本只做 TXT 解析、JSON 计划生成与证据整理，不产生几何 |
| 外部模型输入 | **无**。未打开/导入 CREO 原文件、SolidWorks 原文件、NX PRT、STEP、Parasolid、STL、原代码包或任何实体 |
| 新建命名 | 全部加 `_v0250` 后缀，不复用 0.24.1 的 `.prt` / `.asm` |

---

## 2. 本轮实测结果

### 2.1 零件：12/12 建成，0.25.0 相对 0.24.1 只改动了 2 个零件

| 零件 | 0.25.0 实测体积 mm³ | TXT 指纹 mm³ | dV% | 相对 0.24.1 Δ mm³ | 跳过项 |
|---|---:|---:|---:|---:|---:|
| Arm1 | 4126.0834 | 4147.550 | −0.5176 | 0 | 0 |
| **Arm2** | **685.3020** | 792.323 | **−13.5072** | **+37.5277** | 1 |
| Arm3 | 4191.8761 | 4185.695 | +0.1477 | 0 | 1 |
| Arm4 | 2134.6764 | 2134.784 | −0.0050 | 0 | 0 |
| Arm5 | 1962.2637 | 1962.321 | −0.0029 | 0 | 0 |
| Arm6 | 406.5221 | 463.883 | −12.3654 | 0 | 1 |
| Arm7 | 1440.0575 | 1142.849 | +26.0059 | 0 | 3 |
| Arm8 | 113.0973 | 113.097 | +0.0003 | 0 | 0 |
| Base | 20970.9713 | 20970.971 | +0.0000 | 0 | 0 |
| **Hom** | **98007.6155** | 90332.156 | **+8.4969** | **+153.9380** | 2 |
| Lateral | 19927.0239 | 19114.973 | +4.2482 | 0 | 1 |
| Rotor | 17103.9454 | 17103.892 | +0.0003 | 0 | 0 |

* **其余 10 个零件体积与 0.24.1 逐位一致**，说明 0.25.0 的新能力只作用于 Arm2 与 Hom。
* **Arm2**：`creo_new_sheetmetal(native_planar)` → `creo_sheetmetal_base_flange`（revision 2）→ `plan_file` 切孔（revision 3），job 全部 `succeeded`，`inspection_source=saved_reloaded`，`quilts=2`、`features=18`。体积从 647.774 升到 685.302，但距 792.323 仍差 −13.51%。
* **Hom**：`linear_pattern n11`（`direction=[1,0,0] spacing=42 count=2 flip=true`）补回后体积从 97853.677 升到 98007.615；**距 TXT 指纹反而从 +8.33% 变 +8.50%**，因为 `chamfer n7/n8` 仍缺。不得把「阵列补回」写成「向参考值收敛」。
* **跳过项 12 → 9，但净减少只有 3 项**，计数口径必须对账：
  `12 − 1（上一轮证据误记） + 1（Arm7 两条 G2 圆角由合并计数改为逐条） − 3（被 0.25.0 新能力吸收） = 9`
  * 被吸收 3 项：Arm2 `sheet_metal` 两段折线 → `sheetmetal_base_flange`；Arm2 `dimension D2=20` → `width` 参数；Hom `linear_pattern n11` → `linear_pattern` op。
  * 误记 1 项：0.24.1 的 `build_results.json` 把 Arm1 记为 `fillet n3 (R3, 8 edges)`，但 TXT 第 464/474/477 行显示 Arm1 **只有 3 条 `extrude`**（n2/n4/n6），第 414 行的「n1/n3 圆角矩形」指草图轮廓自带的 `[B-GEO]` 圆弧，不是实体圆角特征。本轮按 TXT 原文更正，Arm1 不再计为跳过项。
  * 计数口径 1 项：0.24.1 把 Arm7 两条 `[B-FILLET2]` 合并成 1 条记录，0.25.0 manifest 拆成 2 条，**不是新增缺口**。
  * 剩余 9 项：`fillet` ×4（Arm2 n4 / Arm3 n3 / Arm6 n3 / Lateral n7）、`chamfer distance_angle` ×2（Hom n7/n8）、Arm7 `region_cut` ×1、Arm7 `curvature_continuous_round` ×2。

### 2.2 总装：23 组件建成，61 配合零建立

| 项 | 值 |
|---|---|
| 模型 | `assem_txt_v0250`，`model_id=6d5898fb73a744ea93440fb13a431eb7` |
| 建模 job | `a1411a0dc4eb45679df73ad81704fd72` → `succeeded`，23/23 `succeeded` + `committed` |
| `plan_file.sha256` | `031008d7916e2274748cdae5e909f015dd7b2fe85389ae4d75e6018e712b62c2` |
| 体积 | `300120.9377215249 mm³`，`units=mm`，`saved_reloaded` |
| 组件 | 23（11 个零件族）；transform 回读与 TXT `[B-COMP]` 输入在 1e-9 量级一致 |
| 放置方式 | `placement=fixed`，**直接写入 TXT 的 rotation_matrix / translation，不是配合求解结果** |
| 分色 job | `9264a040742845a3a7844f008ff8edeb` → `succeeded`，revision 2，23/23 painted，保存/重载前后 readback 全在 1e-6 内 |
| 独立巡检 | `creo_inspect_model(section=components)` 两页共 23/23：`appearance.state=present`、`query_code=0`、rgb 与 palette 一致；**23/23 的 `constraints` 都只有 `{type:13, type_name:"fix"}`** |
| 最终文件 | `...\models\6d5898fb73a744ea93440fb13a431eb7\output\assem_txt_v0250.asm.3` |

---

## 3. 核心问题 A【P0】：MCP 有但用不了 —— 新增配合词无法消费 TXT 锚点

### A1 现象与实机探针

TXT `[B-MATE]`（第 830–843 行起共 61 条）的引用形态是**纯几何锚点**，例如：

```text
[B-MATE] id=n24 type=concentric ... sides=n1:circle:near=(0,31.7,-27.5)|n2:circle:near=(0,-3,-25) ...
[B-MATE] id=n25 type=coincident ... sides=n1:plane:near=(0,31.7,0) dir=(0,1,0)|n2:plane:near=(0,0,0) dir=(0,-1,0) ...
```

没有 Creo 的 `surface id` / `plane id` / `edge id`，也没有基准面标签。而 `creo_component_constraints` 在 0.25.0 要求：

* `coincident` → `{kind: surface|plane|datum_plane|datum_feature}`
* `concentric` → **只能** `{kind:'surface', id:N}`

本轮在 `assem_txt_v0250` / `hom_1` / `expected_revision=1` 上提交的 8 条探针（完整原文见 `creo_plans_v0250/mates_evaluation_v0250.json`）：

| # | 探针 | 结果 | 关键回执 |
|---|---|---|---|
| P1 | `coincident` + TXT `plane_anchor` | 建 job 前拒绝 | `needs a face reference (surface/plane/datum_plane/datum_feature), not 'plane_anchor'` |
| P2 | `coincident` + **0.25.0 新增 `geometry_selector`(surface)** | 建 job 前拒绝 | `not 'geometry_selector'` |
| P3 | `concentric` + TXT `circle_anchor` | 建 job 前拒绝 | `needs a cylindrical {kind:'surface',id:N} reference, not 'circle_anchor'; axis/edge coaxiality would need the unverified LINE_PARL/LINE_DIST path` |
| P4 | `concentric` + **0.25.0 新增 `geometry_selector`(surface)** | 建 job 前拒绝 | `not 'geometry_selector'` |
| P5 | `parallel` | 准入期拒绝 | `PRO_ASM_ORIENT ... no write-side mapping is opened yet` |
| P6 | `distance` | 准入期拒绝 | `PRO_ASM_LINE_DIST/PNT_DIST ... not verified on a live assembly` |
| P7 | `gear` | schema 拒绝 | `type: Input should be 'mate' ... 'distance'`；`ratio: Extra inputs are not permitted` |
| P8 | `coincident` + 合法 kind 但不存在的 `surface id=99999999` | **job 被接受并归一化成 `mate`**，原生层失败 | `ProModelitemInit(board, id, t, &mi) failed with code -23`；`rollback_succeeded=true`，总装未变 |

**P8 是判定「有但用不了」的关键证据**：它证明 0.25.0 的 `coincident → mate` 映射、约束 admission、native 写入路径都是通的，唯一阻塞在**调用方必须自己提供 Creo 内部 surface id**。而 TXT 根本不给 id；P2/P4 又证明本版新增的 `geometry_selector` 没有被接入配合引用层，无法把 `near=(x,y,z)` 解析成 id。

根因定位（`src/creo_mechdog/assembly_constraints.py`）：

```python
FACE_REFERENCE_KINDS = frozenset({"surface", "plane", "datum_plane", "datum_feature"})
COAXIAL_REFERENCE_KINDS = frozenset({"surface"})
MAPPING = {"coincident": "mate", "concentric": "insert"}
```

白名单是**静态 kind 字符串**，不含 `"geometry_selector"`；`geometry_selectors.py` 的按坐标选面能力没有与这里打通。

**影响**：61 条配合（`concentric 26 / coincident 24 / parallel 6 / distance 4 / gear 1`）全部不可建；总装只能靠 `[B-COMP]` 的固定 transform 摆放，`underconstrained=false` 只是因为每个组件都被 `fix` 了，**不能当作配合已建立的证据**。

### A2 建议给作者（按优先级）

1. **【最高】给配合引用加「按几何锚点解析」入口**：允许 `{"kind":"geometry_selector", "target":"surface", "axis":..., "points_mm":[...], "tolerance_mm":...}` 出现在 `assembly_reference` / `component_reference`，在提交前解析成 `{kind:'surface', id:N}`，并把解析出的 id、命中数量、歧义候选一并返回供复核。要求「0 或多重匹配必须拒绝」，与现有 `geometry_selectors.py` 的策略一致。
2. **`concentric` 放宽到可解析的圆柱面/圆边锚点**：TXT 的 `circle:near=(x,y,z)` 需按「最近圆柱面 + 轴向」解析，而不是要求调用方预先知道 id。
3. **`gear`**：补类型与 `ratio` 字段；若 SDK 不支持，请给出与 `parallel`/`distance` 同格式的具名缺口说明，而不是让 schema 抛通用枚举错误。
4. 在 `creo_inspect_model(section=components)` 回执里明确区分 `fix`（固定放置）与真实 mate 约束——本轮正是靠 `constraints: [{type:13,type_name:"fix"}]` 才做出客观判定，建议把「配合数」作为一等字段直接暴露。

---

## 4. 同类问题 B【P0/P1】：新选区器与 TXT 的边引用形态不匹配

### B1 `geometry_selector` 要求两端点，TXT 只给单点锚点

TXT 的 `[B-FEAT]` 圆角/倒角行（第 484、522、685、757、758、790 行）全是**单点边锚点**：

```text
[B-FEAT] part=Arm3.SLDPRT id=n3 type=fillet radius=3 edge1=(-15.92,0,38.227) ... edge8=(-37.92,0,38.227)
[B-FEAT] part=Hom.SLDPRT id=n7 type=chamfer radius=8 angle_rad=1.22173 chamfer_type=distance_angle edge1=(19,52.8,0)
```

而 `geometry_selectors.py` 明确：

```text
An edge selector lists exactly two endpoints and matches them in either direction ...
a circular edge is not admitted in this batch.
Zero or multiple matches are always refused.
```

即边选区必须给 `endpoints_mm=[[x1,y1,z1],[x2,y2,z2]]`，且圆弧边不接受。TXT 既没有第二端点，部分边还是圆弧边。本轮因此**没有强行补建** 4 条 `fillet`（Arm2/Arm3/Arm6/Lateral）与 2 条 `chamfer`（Hom n7/n8），共 6 条特征按 skipped 留证，没有捏造 edge id。（Arm1 无实体圆角特征，见 2.1 节更正。）

**建议**：提供「按单点锚点 → 反查所属 edge id」的解析 op 或独立工具；回执里返回命中的 edge id 与两端点坐标，让调用方先解析、再用 `{"kind":"edge","id":N}` 提交 `round`/`chamfer`。同时考虑放开圆形边的 `endpoints_mm` 之外的一种合法选区（例如 `center + radius + plane`）。

### B2 `chamfer_type="distance_angle"` 需要 `angle_reference` 面，TXT 没有

TXT 给了 `angle_rad=1.22173`（≈70°）和 `chamfer_type=distance_angle`，但没有「角度所依据的面」。0.25.0 的 `ChamferOp` 要求 `angle_deg` **且** `angle_reference`（面引用或 targeting surface 的 `geometry_selector`）。由于 B1 的边锚点同样不可用，Hom 的两条倒角无合法输入。

**建议**：要么允许从 `angle_rad` + 单边锚点推断唯一的相邻面（并把推断出的面回执出来），要么提供一个「按边查相邻面」的解析工具。

### B3 `sheetmetal_base_flange` 是组合特征，不等价于 TXT 的 `SMBaseFlange`

`docs/REFERENCE_SYNTAX.md` 已明确它由两条直线组成的开口 90° 折线生成**两个特征**，`composed_features` 逐一列出，**不声称单特征基体法兰**。而 TXT 第 445 行要求的是：

```text
全表只有 1 条 [B-FEAT] type=dimension —— Arm2 的 n3，feature_type=SMBaseFlange，target=n2，dim=D2，value=20 mm。
它不是新特征，而是对已建特征的尺寸修改指令，必须执行 …… 不得跳过、不得删除该行、也不得用「加料/拉伸补宽」代替
```

本轮做法是**直接把 `width=20` 作为参数传给 `sheetmetal_base_flange`**，没有执行「先建默认 1 mm、再把 D2 改成 20」的尺寸修改步骤。几何结果可能接近，但**过程语义不同**，不得宣称已执行该尺寸修改指令，也不得宣称与 SolidWorks 中面加厚 `SMBaseFlange` 等价。实测 685.302 mm³ 距 792.323 mm³ 仍差 −13.51%，与作者 `docs/RELEASE_NOTES_0.25.0.md`「不声称组合首壁与反馈参照件 792.323 mm³ 的等价性」一致。

**建议**：若要覆盖 TXT 语义，提供「单特征首壁 + 按 `{feature, symbol, value}` 修改 D2」的完整路径，并给出与 792.323 mm³ 的实测对照；否则请在能力清单里把「组合首壁」与「SMBaseFlange 中面加厚」明确区分为两种语义。

---

## 5. 仍属「MCP 没有的能力」

### C1 Arm7 `[B-REGION]` 签名选择性切除（T6c）

TXT 第 716 行 `[B-CUT] region_count=3 region_index_hint=4,2,5`，第 801–803 行给出 3 条 `[B-REGION]` 的 `signature_yz_mm`，第 443 行明确规定「`region_index_hint` 仅供追溯，**选区必须按 `[B-REGION]` 签名唯一匹配**」。0.25.0 的 `extrude cut` 仍作用于整张草图的全部轮廓，没有 per-region / contour-id 选择能力，本轮跳过。

> 校正（已在上一篇反馈 `2026-11-15-CREO-0.25.0-Arm7区域切除签名已存在于TXT却被列为缺签名且G2圆角仍未开放.md` 中展开）：`DEV-090` 把 T6c 判为「缺 B-REGION 稳定签名、构造不出」与源数据不符；真实情况是 0.24.1 反馈只给了摘要、没附附录 B 原始行。签名就在 TXT 里。

**建议**：提供按边界签名（线段端点集合，容差可配）匹配草图闭合区域的选区 op，回执返回匹配到的 region id 与签名残差；零/多重匹配必须拒绝。

### C2 Arm7 `curvature=1` 曲率连续实体圆角（T9a）

TXT 第 717–718 行 `[B-FILLET2] radius=30 curvature=1` / `radius=5 curvature=1`。`RoundOp` 只有 `size` + `references`，无 `curvature` / `continuity` 字段；`DEV-090` 说明 `ProRoundType` 只有 CONSTANT / VARIABLE / FULL / THROUGH_CURVE / CHORDAL，没有 G2 或连续阶控制字段。**这是 SDK 层面的真实硬约束，不视为本版回归缺陷**，但请在公开能力清单里持续标注为「不支持」而非「未验」。

### C3 `gear` 配合

见 A1/P7。61 条配合里 1 条 gear，类型枚举与 `ratio` 字段均缺。

### C4 `parallel` / `distance`

见 A1/P5、P6。按 `DEV-089` 属**明示的准入期行为**（SDK 有声明但未在实机验证写入/求解），**不算回归缺陷**；但建议在拒绝文案里也给出「TXT-only 场景下的替代路径是否存在」的明确结论，避免调用方反复试探。

---

## 6. 实测确认「已修好 / 已可用」的部分（避免误报）

| 能力 | 本轮实测 |
|---|---|
| `plan_file` | Arm8 试点与总装 23 组件均成功，回执含 `plan_file.sha256`，`saved_file_reloaded_and_verified=true` |
| `linear_pattern` | Hom n11 在 Creo 10 实机成功，体积 +153.938 mm³ |
| `sheetmetal_base_flange` | Arm2 job `4e2bc5c64e3341fea52e6eedb5079746` 成功；但语义限制见 B3 |
| `coincident → mate` 映射 | P8 job 回执 `normalized type=mate`，映射层确实生效 |
| `creo_recolor_assembly` | 23/23 组件、11 族，保存/擦除/重载前后 readback 全在 1e-6 内，独立巡检复核通过 |
| `assemble_component` 固定放置 | 23/23 transform 回读与 TXT 一致，`rotation_tolerance=1e-5` 生效 |
| `creo_inspect_model` | 12 零件 + 总装均可 `saved_reloaded` 回读体积/拓扑/组件/appearance |

---

## 7. 证据文件清单（本工作区）

```text
creo_plans_v0250/build_results_v0250.json        12 零件体积/拓扑/指纹对照、skip 明细、verdict
creo_plans_v0250/mates_evaluation_v0250.json    61 条配合分布 + 8 条实机探针完整回执 + 独立巡检结论
creo_plans_v0250/assembly_build_v0250.json      总装 job / transform / 体积 / 最终文件与 sha256
creo_plans_v0250/assembly_palette_v0250.json    11 族配色、23 组件、readback 验证
creo_plans_v0250/assembly_ops_v0250.json        提交给 plan_file 的纯 operations array
creo_plans_v0250/manifest.json                  12 零件操作数 / 实体数 / skipped 理由
creo_plans_v0250/edge_anchors.json              TXT 圆角/倒角单点锚点导出
creo_plans_v0250/endpoint_residuals.json        圆弧端点投影残差（max 0.0 mm）
creo_plans_v0250/mates_preserved.json           61 条 [B-MATE] 原始参数保留
txt_to_creo_plan_v0250.py                       0.25.0 计划生成器（只读 TXT）
build_v0250_evidence.py / finalize_v0250_evidence.py  证据整理脚本（不产生几何）
```

最终模型：

```text
E:\WorkBuddy Space\MCP MCP_CREO_MechDog\models\6d5898fb73a744ea93440fb13a431eb7\output\assem_txt_v0250.asm.3
```

12 个零件 `.prt` 分别在各自 `models\<model_id>\output\` 下（Arm2 为 `arm2_v0250.prt.4`，其余多为 `.prt.2`）。

---

## 8. Caveats / 不归因于 MCP 的部分

* **0.24.1 结果文件里 Arm1 的 `fillet n3` 是本方上一轮的证据瑕疵，不是 MCP 缺陷，也不是 TXT 缺陷**：TXT 第 464/474/477 行只有 3 条 `extrude`，无实体圆角特征。本轮已按源文本更正 `build_results_v0250.json`，因此「12 → 9」不能简单解读为「0.25.0 多修好了 3 项」中的全部；真实吸收是 3 项，另 2 项是证据更正与计数口径。
* **Arm6 的 −12.37% 不是 MCP 缺陷**：TXT 第 180 行「已知未闭合项」自述 `[B-GEO]` 端弧分段记录不完整、差额形态无法判定，并明确「接收 AI 不得据本章宣称 Arm6 达 L3」。
* **TXT 指纹体积是文本给出的参考量，不是 Creo 几何的等价判据**。`dV%` 只用于定位缺口方向；本轮没有跨软件 `compare_parts`、逐 body 惯性矩/惯性积比对，验证等级仅为 MCP 自身的 `saved_reloaded` 巡检，不冒充 E3/E4。
* **Hom 的 `linear_pattern` 补回并未改善 dV%**（+8.33% → +8.50%），因为 `chamfer n7/n8` 仍缺；不得据此宣称「已向参考件收敛」。
* **P8 探针使用不存在的 `surface id`**，失败后 `rollback_succeeded=true`、`component_changes.status=rolled_back`，总装 23 组件与 300120.9377215249 mm³ 前后一致，**总装未被破坏**。
* **本轮没有把 TXT 锚点臆测映射到 Creo 默认基准面**（FRONT/TOP/RIGHT），因为那会引入 TXT 之外的几何假设，违反「几何 100% 来自 TXT」。
* `parallel` / `distance` 的拒绝与 `T9a` G2 圆角的缺失是**作者已明示的边界**，本报告将其归为「能力缺口」而非「回归缺陷」。
* 本次 `creo_capabilities` 内嵌的在线更新检查因 5 秒网络预算失败；「0.25.0 为当前最新」这一判断来自本轮早先成功的 `creo_check_update(force=true)` 与 GitHub `releases/tags/v0.25.0`，不是来自这次失败的检查。

---

## 9. 结论

0.25.0 相对 0.24.1 在**建模侧**（组合首壁、线性阵列、大计划文件）有可验证的实质进步；但在**装配配合侧与选区侧**，新增的 `coincident` / `concentric` / `geometry_selector` 与 TXT-only 的输入形态之间存在一道未被打通的引用解析层：

> 词有了、映射有了、原生写入路径也通了，唯独「把 TXT 的 `near=(x,y,z)` 变成 Creo 的 `surface id`」这一步没有任何合法入口。

因此本轮 61 条配合仍是 0 条，9 项特征仍被跳过，12 个零件无一收敛到 TXT 指纹，总 verdict 为 **PARTIAL / DEGRADED**。建议下一版优先做 **A2-1（配合引用接入 geometry_selector）** 与 **B1（单点锚点反查 edge id）**，这两项能一次性解锁「61 条配合」与「6 条圆角/倒角」两个最大的缺口。

---

## 10. 追加发现（同日晚，用户看图指错后）：B3 不是「语义不等价」而是「静默几何错误」

用户上传截图指出红圈里的紫色零件装配位置不对后，本方做了几何级复核，结论**比本文 B3 原本的判断更严重**，另起一份独立反馈文档：

> `2026-11-15-CREO-0.25.0-sheetmetal_base_flange把板宽20建到Z向致Arm2装配位置偏移9.57mm.md`

要点（不在此重复展开，详见新文档）：

* `creo_sheetmetal_base_flange(plane="YZ", width=20)` 把 20 mm 板宽沿零件 **Z 轴**展开，`creo_inspect_model(section=surfaces)` 显示 17 个面的 bbox **全部**为 `Z 0…20`；TXT 第 1113/116/417 行要求 `X −10…10`。实测局部包络 `X −12…2 / Y 0…8 / Z 0…20`，TXT 要求 `X −10…10 / Y −2…8 / Z −2…12`。
* Arm2 局部质心偏到 `(-3.7432, 5.8865, 10.0206)`，距 TXT 指纹 `(0, 0.8681, 2.7828)` **9.5699 mm**；两个实例经正确的 `[B-COMP]` 变换后世界质心各偏 9.5699 mm。
* **排除总装 transform**：`verify_assembly_placement.py` 证明 23/23 `R`/`t` 逐位一致（`max |ΔR|=0`、`max |Δt|=0 mm`），行向量约定复现 TXT 总装质心误差 0.0003 mm。
* job 全流程 `succeeded` + `saved_reloaded` + `has_solid=true`，**没有任何回执报警**，是典型静默错误；建议作者在回执里回报首壁 `body_box` / `width_axis` / 质心，并给 `width` 增加显式作用轴参数。
* 已用 0.24.1 降级路径重建 Arm2 并重建总装 `assem_txt_v0250_fix`（`e2e88719aa3d452cb62bcca0cf5cafc0`，最终 `.asm.3`，sha256 `2c153c47…`）：局部质心偏差降到 1.6647 mm（改善 7.9051 mm），板宽回到 X 轴；但仍不等价（体积 647.774 vs 792.323 mm³、R3 圆角仍缺），61 条配合仍零建立。verdict 为 **PARTIAL FIX / DEGRADED**。

因此本文第 6 节表格中「`sheetmetal_base_flange` Arm2 job 成功」需要按上述追加结论理解：**job 成功不等于几何正确**。
