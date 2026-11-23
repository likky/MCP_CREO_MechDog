# MCP_CREO_MechDog 0.35.8 — 三点基准面草图缺第二条参考，solve 失败被误报为 AutodimensionSketch 失败

> 环境：Creo Parametric 10.0.0.0，MCP 0.35.8，模型 `frigate_v4`（`df7f74bf5e424dbeb00605e218be89ad`，rev79，410 特征 / 751 面 / 2436 边）。
> 复现日期：2026-11-23。同一份计划连跑 5 条同构特征，1 条成功、4 条失败。

## §0 一句话结论

在**三点基准面**（`datum_plane {kind:'through_points'}`）上建草图时，`ProSectionEntityFromProjection` 对模型里几乎每一个基准面都返回 `-2`（`PRO_TK_BAD_CONTEXT`），section 只剩「orientation 参考」这**一条**可用参考；此时 `ProSectionSolve` 返回 `-1` 且 `SECTION_ERRORS phase=solve count=0`（**没有任何错误详情**），随后触发的救援调用 `ProSectionAutodim` 也返回 `-1`，最终对外只报一句 `Toolkit AutodimensionSketch failed with code -1 during execute_sketch`。**报错点不是根因点**：`AutodimensionSketch` 只是失败后的救援调用，真正缺的是 section 的第二条参考。

本文另有两条更严重的后续发现，同一条失败链上：§8（保存重载后的全量比对在 474 特征树上静默挂起，3/3 复现）与 §9（恢复路径硬编码 90 s 截止，导致模型一旦 `unknown_outcome` 就永久锁死，现已实测锁死）。**如果只看一条，请看 §9。**

## §1 现象：同一配方，1 成 4 败

五条特征用同一套代码生成（同一函数、同一 `dimensioning="coordinates"`、同一个三点基准面构造方式），差别只有几何位置与法向：

| TXT | 特征 | 草图 | 基准面法向 | 结果 |
|---|---|---|---|---|
| B045 | Boss-Extrude8 | Sketch81（3 个 100×100 方块） | (0.965926, 0, −0.258819) | **失败** `AutodimensionSketch=-1` |
| B046 | Boss-Extrude9 | Sketch82（2 个 120×100 方块） | (0.683013, −0.683013, −0.258819) | **成功** rev80，ΔV +48,008.13 mm³ |
| B047 | Boss-Extrude10 | Sketch83（1 个 120×120 方块） | (0, −0.965926, −0.258819) | **失败** `AutodimensionSketch=-1` |
| B104 | Cut-Extrude16 | Sketch194（1 个闭合折线环） | (0.488742, 0.872428, 0) | **失败** `AutodimensionSketch=-1` |
| B105 | Cut-Extrude17 | Sketch195（1 个闭合折线环） | (0.488742, 0.872428, 0) | **失败** `AutodimensionSketch=-1` |

结论先行：**能不能建出来，取决于「模型里恰好有没有一个基准面能投影成功」，与草图本身是否闭合、是否欠约束、坐标是否正确无关。** 五条草图在提交前都用端点度数法验证过：所有顶点度数 = 2，闭环数 3/2/1/1/1，无分叉。

## §2 证据链（`native.log` 逐行）

### 2.1 失败的 B045（job `f0484853fd784d87928eabab8bec2e5a`）

```
PROJECT_REFERENCE=6   code=-2 entity=-1
PROJECT_REFERENCE=50  code=-2 entity=-1
...
PROJECT_REFERENCE=249 code=-2 entity=-1
SKETCH_ANCHOR_SKIPPED=451 parallel_to_orientation=1.000000000
...
SKETCH_REFERENCE_INCOMPLETE axes=0
ProSectionLocationGet(section, loc)=0
COORDINATE_AXES u_to_section_x=1.000000000 axes=0,1
SKETCH_ORIGIN_PIN_UNAVAILABLE u=0 v=1 anchors=1
SKETCH_SOLVE=-1 mode=coordinates
SECTION_ERRORS phase=solve count=0
COORDINATE_INFERRED_CONSTRAINTS=9
SKETCH_SOLVE_WITHOUT_INFERENCE=-1
AutodimensionSketch=-1
```

统计：`PROJECT_REFERENCE` 共 **101 次，101 次全部 `code=-2`，0 次成功**；另有 58 次因「与 orientation 面平行」被跳过；`axis_refs` 为空（`axes=0`），轴回退路径也无候选。

### 2.2 成功的 B046（job `7376fefb73f04fd0be070d90cfda6ed7`）

```
PROJECT_REFERENCE=9792 code=-2 entity=-1
PROJECT_REFERENCE=9804 code=0  entity=1
SKETCH_ANCHOR_PLANE=9804
...
SKETCH_ORIGIN_PIN axis=1 value=0.000000000000
SKETCH_ORIGIN_PIN axis=0 value=0.000000000000
SECTION_MATRIX_0=0.707106781,0.707106781,0.000000000,0.000000000
SKETCH_SOLVE=0 mode=coordinates
AutodimensionSketch=SKIPPED_COMPLETE_COORDINATE_DIMENSIONS
```

统计：`PROJECT_REFERENCE` 共 **360 次，358 次失败，2 次成功**（都是平面 `9804`，即同一批建的另一个 `through_points` 基准面）。一旦拿到第二条参考，两个轴都被 pin 上（值都是 0，因为该参考线正好过草图原点），`SKETCH_SOLVE=0`，**`AutodimensionSketch` 根本没被调用**。

### 2.3 失败的 B047（job `89db369bd410491abae974b3085b4929`）

与 B045 同型：107 次投影全失败，18 次因平行被跳过，`SKETCH_REFERENCE_INCOMPLETE axes=0`，`SKETCH_ORIGIN_PIN_UNAVAILABLE u=0 v=1 anchors=1`，`SKETCH_SOLVE=-1` → `AutodimensionSketch=-1`。

### 2.4 关键对照

| | B045（败） | B046（成） | B047（败） |
|---|---|---|---|
| PROJECT_REFERENCE 成功次数 | 0 / 101 | 2 / 360 | 0 / 107 |
| `SKETCH_ANCHOR_PLANE` | 无 | 9804 | 无 |
| `SKETCH_REFERENCE_INCOMPLETE` | `axes=0` | 未出现 | `axes=0` |
| `SKETCH_ORIGIN_PIN` | `UNAVAILABLE u=0 v=1` | 两轴 pin 值 0 | `UNAVAILABLE u=0 v=1` |
| `SKETCH_SOLVE` | −1 | 0 | −1 |
| `SECTION_ERRORS count` | 0（空） | 未触发 | 0（空） |

**同一份生成代码、同一种平面、同一种草图实体集，结果只由「有没有第二条可投影参考」决定。**

## §3 源码定位

| 位置 | 内容 |
|---|---|
| `native/generic.cpp:2469` | `ProSectionEntityFromProjection(section, orient, &projected)` — 第一条参考取自 orientation 面 |
| `native/generic.cpp:2479-2500` | 遍历所有基准面，跳过 `p.id == frame.orientation` 与 `fabs(dot(n, frame.n)) >= 0.95`，逐个投影，**成功后 `break`** |
| `native/generic.cpp:2486-2490` | 与 orientation 面平行的候选被 `SKETCH_ANCHOR_SKIPPED` 丢弃（本机 58 / 18 次） |
| `native/generic.cpp:2501-2526` | 只剩 1 条参考时回退到「平行于支撑面的基准轴」，本模型 **没有任何 datum axis**，`axes=0`，回退无效 |
| `native/sketch_coordinates.cpp:47-101` | `pin_coordinate_origin`：候选线必须**在 section 坐标系里轴对齐**（`fabs(end1[axis]-end2[axis]) > 1e-8` 即跳过）；`candidates.size() < 2` 时直接 `return`，只留一行日志 |
| `native/sketch_solver.cpp:69-74` | `ProSectionSolve` 返回 −1，`section_errors()` 输出 `count=0` |
| `native/sketch_solver.cpp:108-117` | `if (mode != "coordinates" || solved) { ProSectionAutodim(...); check(solved,"AutodimensionSketch"); }` — 即 coordinates 模式下**只有解算失败才会调 autodim** |
| `native/sketch_solver.cpp:115` | `check(solved, "AutodimensionSketch")` 把异常抛在救援调用处，于是错误消息丢失了真实阶段 |

## §4 三个独立缺陷

### 4.1【阻断级】`ProSectionEntityFromProjection` 在三点基准面上几乎不可能成功

101/101、107/107 全失败，成功率 0。而同一批 `through_points` 平面在**另一条**草图上却成功（9804）。也就是说投影成功与否取决于几何位置（本机观察：投影线是否落在草图形状附近），不是稳定的契约。

**建议**：不要依赖「模型里碰巧存在的某个基准面」。当 `coordinate_anchors.size() == 1` 且轴回退也无候选时，**按需自动创建一个锚定面**——过草图原点（或草图包围盒中心）、法向取 section 的 u 轴（或 v 轴）的基准面，它必然与支撑面相交、且不可能与 orientation 面平行（因为 u 按定义垂直于 orientation 法向）。这是确定性构造，不是碰运气。

### 4.2【误导级】错误消息指向错误的阶段

`AutodimensionSketch failed with code -1` 会让使用者去查 autodim，而真正失败的是 `ProSectionSolve`。而且 coordinates 模式下 autodim 是**救援**，它的失败值不值得单独上报都两说。

**建议**：`check(solved, "AutodimensionSketch")` 之前先判断主解算：
```cpp
if (mode == "coordinates" && !solved)
    throw std::runtime_error("Section solve failed ...; autodim rescue also failed");
```
并在消息里带上 `SKETCH_REFERENCE_INCOMPLETE` / `SKETCH_ORIGIN_PIN_UNAVAILABLE` 这两个已知标记，以及 `coordinate_anchors.size()`。

### 4.3【可诊断性】`SECTION_ERRORS phase=solve count=0`

解算 −1 但 `ProSecerror` 里一条错误都没有，使用者只能靠猜。至少应把 `ProSectionSolve` 的返回码、anchor 数量、以及 section 的实体数一起打进 `stage_operation_result`，让失败作业的 `native_result.json` 里有可读字段。

### 4.4【附带】`coordinates` 在四线矩形上只落 3 个尺寸

B045/B046/B047 的方块都是 4 条 `line`。日志显示共享顶点被跳过：

```
COORDINATE_AXIS_LINE_SHARED=coord_e_a00 axis=0
COORDINATE_SHARED_VERTEX_SKIPPED=coord_e_a01_start
COORDINATE_AXIS_LINE_SHARED=coord_e_a01 axis=1
COORDINATE_SHARED_VERTEX_SKIPPED=coord_e_a02_start
COORDINATE_AXIS_LINE_SHARED=coord_e_a02 axis=0
COORDINATE_SHARED_VERTEX_SKIPPED=coord_e_a03_start
COORDINATE_SHARED_VERTEX_SKIPPED=coord_e_a03_end
```

一个矩形需要 8 个坐标尺寸（4 个 x + 4 个 y）才完全约束，实际只落了 3 个。这本身不致命（B046 一样欠约束却成功了），但意味着「`coordinates` = 完全约束」这个假设不成立，值得在文档里写明。

## §5 我的绕法（确定性锚定面）

按 §4.1 的思路自己在计划里补一条锚定面，不依赖模型里碰巧存在的基准面：

1. 取该草图全部 2D 投影点的形心 `(uc, vc)`；
2. 基准三点取 `P0 = O + uc·u + vc·v`、`P1 = P0 + 100·v`、`P2 = P0 + 100·n`，于是
   `cross(P1−P0, P2−P0) = 10000 (v×n) = 10000·u`，**平面法向恰为 +u**；
3. 该面与支撑面的交线是 `u = uc`，在 section 坐标系里轴对齐（`end1[0] == end2[0]`），且穿过轮廓内部；
4. 因 `u = cross(seed, n)`，而 `seed` 正是「与 n 最不平行的世界轴」——和 `frame.orientation` 的选取准则相同，所以 **u 必然垂直于 orientation 面法向，永远不会被误判为平行而丢掉**。

实测结果见 §7。

## §6 最小复现

- 模型：任一实体件（本机 `frigate_v4` 亦可）；
- 步骤 1：`datum_points` ×3 + `datum_plane {kind:'through_points'}` 建一个斜基准面（法向如 `(0,−0.965926,−0.258819)`）；
- 步骤 2：在它上面 `sketch` 一个 120×120 的正方形（4 条 `line`），`dimensioning="coordinates"`，`plane` 用 `{reference:{kind:'datum_feature',label:…}, origin, u_axis}`；
- 结果：`AutodimensionSketch failed with code -1`。日志里必然出现 `SKETCH_REFERENCE_INCOMPLETE axes=0` 与 `SKETCH_ORIGIN_PIN_UNAVAILABLE u=0 v=1 anchors=1`。
- 对照：把同一个正方形建在默认基准面（如 FRONT）上，一切正常——因为默认面上有多条可投影参考。

## §7 本轮实测结果

### 7.1 锚定面确实解掉了 §1 的四个失败项（日志级已验证）

对 B045 补 `pa_b045`（法向 = 该草图的 u 轴、过轮廓形心 u=−1844.2）后重试，同一份草图计划：

```
PROJECT_REFERENCE=9884 code=0 entity=1      <-- pa_b045 投影成功
SKETCH_ANCHOR_PLANE=9884
SKETCH_ORIGIN_PIN axis=1 value=0.000000000000
SKETCH_ORIGIN_PIN axis=0 value=1844.200443996055   <-- 正是形心 u 值
SECTION_MATRIX_0=...
SKETCH_SOLVE=0 mode=coordinates
SectionRegenerate=0 mode=coordinates
AutodimensionSketch=SKIPPED_COMPLETE_COORDINATE_DIMENSIONS
```

三个草图全部 `SKETCH_SOLVE=0`。**§1 的「缺第二条参考」在日志层面已被确定性绕开**，锚定面的法向也与预测逐位一致（`pa_b045` 实测 `[-0.258819, 0, -0.965926]`、`pa_b047` 实测 `[0, 0.258819, -0.965926]`、`pa_b104` 实测 `[-0.872428, 0.488742, 0]`，`verified=true`，`max_point_distance` 0～3.6e-15）。

### 7.2 但同一个作业随后卡死在另一个地方（见 §8）

B045 的草图全部解算通过（3 × `SKETCH_SOLVE=0`、3 × `SKETCH_ANCHOR_PLANE`）、三次拉伸全部执行、模型保存并重载成功（`verify_model_save` / `verify_model_erase` / `verify_model_reload` / `verify_model_reload_regenerate` / `verify_model_reload_inspect` 全部返回 0），然后卡在**下一个**阶段（`verify_model_compare`，见 §8.2），601 s 后被看门狗终止，作业落 `unknown_outcome`。**三次提交、同一位置，可复现。**

### 7.3 已确认通过的三条

B046（2 个 120×100 方块，同一套生成代码）:
- 体积 5,408,112,910.9498005 → 5,408,160,919.081839，ΔV **+48,008.1320385 mm³**；
- 解析值 = 24,000.000004 mm² × 2 mm = **48,000.000007 mm³**，差 +8.13 mm³（+0.0169%）；
- 草图零位移：`GEOMETRY_STAGE_SHAPE points=8 translation=0.000000000000 shape=0.000000000000`、`max_deviation_mm=4.5e-13`；
- 模型仍是 **1 个 body**，说明两个方块并进了主体。

那 8.13 mm³ 应理解为**零件体积的绝对误差**（8.13 / 5.408e9 = 1.5e-9 相对），不是建模错误：增量只有 4.8e4 mm³，而零件是 5.4e9 mm³，前者的 0.017% 正好等于后者的 1.5e-9。

B047（1 个 120×120 方块，同一套代码，锚定面 `pa_b047`）:
- 体积 5,408,155,197.3397665 → 5,408,183,980.770802，ΔV **+28,783.4310355 mm³**；解析 14,400 mm² × 2 = 28,800，差 −16.57 mm³（同样属绝对误差量级）。

B104 / B105（`cut`，锚定面 `pa_b104` / `pa_b105`，切除本身成功但去料量异常）:

| 特征 | 每刀去料（回执） | 合计 | 解析 | 比例 |
|---|---|---|---|---|
| B104 `cut_b104`（8.4 mm） | 32.254 mm³ | 38.055 | 13,902 | **0.27%** |
| B104 `cut_b104_b`（1.0 mm，反向） | 5.801 mm³ | | | |
| B105 `cut_b105`（8.4 mm） | 5,683.687 mm³ | 5,683.687 | 10,492.3 | **54.17%** |

两条切除都返回 `execution_status=succeeded` / `effect_status=committed`，无错误码，`material_removed_mm3` 与体积差自洽。但 B104 的 1.0 mm 反向刀只去掉 5.8 mm³，说明轮廓几乎完全不在材料上方——**这一点我还没定性，先如实记录**（草图的 `geometry_deviation` 都在 1e-9 mm 量级，基准面与实体面 `6671` 共面间隙 2e-6 mm，所以不是草图放错了位置）。需要作者判断：`cut` 的 `direction` 是否应当由「材料在法向哪一侧」自动决定，而不是由使用者给 `positive/negative`。

### 7.4 第三次提交（rev87 基线）结果：仍是 `unknown_outcome`

在补齐 B046/B047/B104/B105 之后的树（474 特征 / 815 面 / 2612 边）上再提一次 B045，草图与拉伸同样全部成功（3 × `SKETCH_SOLVE=0`、3 × `SKETCH_ANCHOR_PLANE`、`DIRECTION_SIGN` 3 次、`COORDINATE_SHARED_VERTEX_SKIPPED` 12 次），然后同样 `Native worker log stopped growing for 600 s`，落 `unknown_outcome`。**3 次提交、3 次失败、3 个不同的挂起点**（详见 §8.2、§8.2.1）。

回退：`creo_reconcile_model` 的 `candidate` 为 `null`（这次是挂在保存前，磁盘没有新件），`accept_saved` / `accept_live` / `abandon_new` 全部因「缺少健康 live 证据」不可用，只有 `restore_baseline` 可用（基线 `frigate_v4.prt.90`，sha256 `3586730f…7bb4`，即 rev87 本身）。也就是说**这次连“丢掉一次成功保存”都没有，纯粹是白跑 10 分钟**。

**B045 的几何与草图解法都已经没有问题，问题全在验证阶段。** 在验证阶段修好之前，这条特征在本机拿不到 VERIFIED。


## §8 【新增·阻断级】保存重载后的全量比对（`verify_model_compare`）会静默挂起

### 8.1 现象

作业不会报错，只是**日志停止增长**，601 s 后：

```
Native worker log stopped growing for 601 s (budget 600 s);
the worker was terminated and the outcome is unknown.
```

作业落 `unknown_outcome`、`revision=None`，但磁盘上已经存在这次保存产生的 `frigate_v4.prt.86`（4,864,665 字节，比基线 `prt.85` 大 44,869 字节）。也就是说**建模本身成功了，丢的是验证与回执**。

### 8.2 卡住的准确阶段（此前记错，以本节为准）

成功作业的完整阶段序列（B047，job `64a2220a34904e9b9d90003ed78bfd8c`）：

```
connect(0.19s) → connected(4.81s) → verify_model_start(220.63s) → verify_model_regenerate(0.00s)
→ verify_model_inspect(0.03s) → verify_model_assertions(43.04s) → verify_model_before_save
→ verify_model_save(0.32s) → verify_model_erase(0.31s) → verify_model_reload(0.00s)
→ verify_model_reload_regenerate(0.55s) → verify_model_reload_inspect(0.04s)
→ verify_model_compare(51.50s) → verify_model_after_reload(0.23s) → verify_model_preview(0.61s)
```

挂起作业（B045，job `e8f40252dd3a4c5db09aaa204ff7c525`）走到同一个位置就断了：

```
... verify_model_reload_inspect elapsed_ms=36
<此后 STAGE 再无输出，601 s 后被终止>
```

`verify_model_reload_inspect` 自己是 **36 ms 就跑完的**。真正没结束的是它后面的 **`verify_model_compare`**：`native.log` 第 127,285 行是 `ProMdlTypeGet(board, &t)=0`，接着 399 行（= 133 个特征）`ProFeatureTypeGet / ProFeatureStatusGet / ProFeatureIsIncomplete` 三元组，然后一次 Toolkit 调用再没返回。

**`verify_model_compare` 做的事是「把重载后的模型再完整巡检一遍、和保存前的快照比对」**：B047 那一次产生 9,298 行日志（474 特征 + 815 面 + 5,224 次 `ProEdgeIdGet`），耗时 51.5 s。所以它不是纯内存比对，而是又跑了一次全量原生遍历——挂起点就在这一遍遍历的第 133 个特征回调。

### 8.2.1 第三次提交挂在**另一处**（这是最关键的一条）

第三次（job `bea4ec07f63947edb52cc045778fe2a5`，rev87 基线）走完了 `verify_model_reload_*` 之前的全部阶段，**`verify_model_start` 用了 570.7 s**，然后在 `verify_model_assertions` 自己的那次全量巡检里停住：

```
verify_model_start(570.7s) → verify_model_regenerate(0ms) → verify_model_inspect(36ms)
<之后 4,018 行：ProSolidFeatVisit 走完 486 个特征、ProSolidBodiesCollect，
 ProSurfaceContourVisit 只走到第 279 个面（共 815），日志停>
```

也就是说：**三次挂起分别是「reload 后的 compare 走到第 133 个特征」、「reload 后的 compare 走到第 133 个特征」、「save 前的 assertions 走到第 279 个面」——点位不固定。** 这排除了「某个特定特征有问题」，指向「只要这 3 块板在树里，全量遍历本身就进入不稳定状态」。

三次的日志停在 4,465,401 / 4,487,239 / 4,501,750 字节（各不相同，所以也不是输出缓冲填满这类固定边界）。

### 8.3 硬数据（都指向「规模」而不是「悬空料」）

| 作业 | `verify_model_start` | 日志量 | 挂起位置 | 结果 |
|---|---|---|---|---|
| B047（job `64a2220a`） | 220.6 s | 2.3 MB | — | ✅ `compare` 51.5 s |
| B104（job `728ce16b`） | 247.6 s | 2.5 MB | — | ✅ |
| B105（job `2aa0460d`） | 172.0 s | 2.0 MB | — | ✅ |
| B046（job `7376fefb`） | 476.6 s | 4.6 MB | — | ✅ |
| B045 第 1 次（job `f9680652`） | 546.7 s | 4.47 MB | `compare` 第 133 个特征 | ❌ |
| B045 第 2 次（job `e8f40252`） | 533.8 s | 4.49 MB | `compare` 第 133 个特征 | ❌ |
| B045 第 3 次（job `bea4ec07`） | 570.7 s | 4.50 MB | `assertions` 第 279 个面 | ❌ |

**只要 B045 这 3 块板在树里，`verify_model_start` 就从 220 s 涨到 533–571 s**，日志里 `ProEdgeIdGet` 达 64,392 次、`ProSurfaceContourVisit` 达 10,027 次。也就是说同一个 474 特征的树，仅仅多了 3 个 100×100×2 的方块，全量巡检成本翻 2.4 倍；而 B046（4 个面并进主体）在同量级日志（4.6 MB）下 `start` 是 476.6 s 且能走完。

### 8.4 反证：悬空多 lump 本身完全正常

我做了最小复现（模型 `probe_b045_float`，`ce04b3c400054617a25655992155b01a`）：

1. 400×400×400 方块；
2. 与 B045 完全同参数的三点斜基准面（法向 `(0.965926, 0, −0.258819)`），离方块顶面 120 mm；
3. 3 块 100×100×2 的板，沿 +n 拉伸 2 mm，**三块互不相连、也不与方块相连**。

结果：

```
P1 create  succeeded rev=1 vol=63999999.999999985
P2 datums  succeeded rev=2 vol=63999999.999999985  reloaded=True
P3 plates  succeeded rev=3 vol=64059999.99999998   reloaded=True     <-- 恰好 +60,000.000
```

```
verify_model_start=1644ms ... verify_model_reload_inspect=27ms verify_model_compare=208ms
```

保存后重载巡检里是 **28 特征 / 24 面 / 48 边 / 1 个 body**，`body_id=52` 一个 body 里装着 4 个互不相连的 lump。`verify_model_compare` 只用 **208 ms**。

**结论：`verify_model_compare` 不是「遇到悬空料就挂」，而是「在某个规模/某棵树形上挂」。** 我原来的猜测（悬空薄片导致巡检不收敛）被这个反证否掉了，特此更正。

### 8.5 影响与建议

- **影响**：`unknown_outcome` 会让模型进入保护态，后续所有计划被拒（`Creo is not ready (timeout): Toolkit verification was invalidated by a subsequent failure`），必须走 `creo_reconcile_model` 才能解锁；而 `accept_saved` 因为「没有健康的 live 证据」不可用，唯一可用的是 `restore_baseline`，**等于把这次已经保存成功的建模成果丢掉重做**。三次 B045 都是这样被丢掉的。
- **建议 1（最关键）**：`verify_model_compare` 加**进度日志**（每 N 个特征打一行）+ **迭代上限**。当前一次挂起能产生 4 万行重复调用却看不出它卡在哪个特征 id 上，请把陷入死循环的那个 `feature id / feature 名` 打出来——有了这个 id，我就能判断是哪个特征在原树里的什么属性触发的。
- **建议 2**：`verify_model_compare` 给独立可配置超时；超时后按「保存已成功、比对未完成」落一个**可 accept 的 saved 结果**（`saved_file_reloaded_and_verified=false` 但 `revision` 有效），而不是 `unknown_outcome`。
- **建议 3**：`unknown_outcome` 时若磁盘上的 `prt.N+1` 大小/时间戳正常，应允许 `accept_saved` 并做**离线**体检（不依赖 live 会话），而不是直接判为不可用。
- **建议 4**：`verify_model_start` 也值得削：474 特征要 64,392 次 `ProEdgeIdGet`（同名边被同一次巡检重复取多次），如果按 `ProSurface` 一次拿到环上的边，调用数能降一个量级。现在一次成功的提交要 8–12 min，其中 60% 花在这个阶段。
- **建议 5**：`creo_execute_plan` 的调用方如果先退出，detached runner 会被一起带走（本机 `dbd68e6d` 就是这么变成孤儿的）。建议 runner 与客户端解耦，或在 `creo_get_job` 里明确告知「本作业的 runner 依赖客户端存活」。

### 8.6 复现要点

同一个计划（3 个草图 + 3 次拉伸，全部建在三点基准面上，3 块板互不相连）在本机 `frigate_v4` 上**连续三次**复现；同一份代码换到 B046 / B047 / B104 / B105 则全部通过；把同一几何搬到 28 特征的小件上（§8.4）也全部通过。差异只有**宿主模型的规模与树形**，所以需要作者在 474 特征的树上加进度日志才能定位到具体特征。

## §9 【新增·封锁级】恢复路径有硬编码 90 s 截止，大模型一旦 `unknown_outcome` 就再也出不来

> 本节是最早的现场记录。之后又补做了「重启 Creo 换全新会话」的实验，并且把 P0/P1 汇总成一份可直接发作者的文档：
> `2026-11-23+CREO+0.35.8+验证阶段静默挂起与恢复路径90秒硬限致模型锁死.md`（§1 恢复硬限、§2 验证挂起、§3 草图缺参考）。
> 新增结论：**重启 Creo 不能绕过 90 s**——全新空会话下第 4 次恢复依旧 `recovery_phase_timeout`、依旧 18,442 行；而重启后的第一次尝试还会被 `Recovery refused: Creo session changed since recorded evidence` 直接拒掉。

§8 的挂起把模型推进了 `unknown_outcome`。按惯例走 `creo_reconcile_model(restore_baseline)`，**恢复作业自己也失败**，模型从此无法解锁。这是本次最严重的一条：它把「一次验证失败」变成了「模型永久只读」。

### 9.1 现场

```
job 0625dbaedda34d57a7b3c05d84459637  (restore_baseline)
status = unknown_outcome
stage  = reconciliation_unconfirmed
reason = native_outcome_unconfirmed    failure_phase = native_worker_started
native_checkpoint.json = {"success": false, "delivery_complete": false,
                          "completion_stage": "recovery_phase_timeout",
                          "phase_budget_seconds": 90.0}
native.log = 18,445 行，94 s 后被杀在「遍历面/边」的中途
             （ProEdgeIdGet 10,448 次、ProSurfaceContourVisit 1,630 次、特征 949 个）
```

`runner` 与 `worker` 两个进程都已 `stopped=true`，`candidate=null`，基线 `frigate_v4.prt.90` 与记录 sha256 `3586730f…7bb4` **完全一致**（文件没坏，坏的只是保护状态）。

**连续试了两次**（job `0625dbae…`、`c81cbe3a…`），两次都是同一个 `recovery_phase_timeout` / `reconciliation_unconfirmed`，不是偶发。对照：同一条路径在 08:43 曾**成功**过（job `f1bb9f6b…`，总耗时 94 s，`completion_stage=before_disconnect`），当时模型 410 特征。

### 9.2 根因（源码级）

```cpp
// native/recovery_deadline.h:11
explicit RecoveryDeadline(const std::wstring &job, DWORD budget_ms = 90000) {
    ...
    if (WaitForSingleObject(event, budget_ms) == WAIT_TIMEOUT) {
        publish_native_json(job + L"\\native_checkpoint.json",
            {{"success", false}, {"delivery_complete", false},
             {"completion_stage", "recovery_phase_timeout"},
             {"phase_budget_seconds", budget_ms / 1000.0}});
        ExitProcess(31);          // 硬杀，不写 native_result.json
    }
```

```cpp
// native/generic.cpp:9207
if (request.contains("reconciliation")) {
    recovery_deadline = std::make_unique<RecoveryDeadline>(job);   // 90 s，无法配置
}
```

这个 90 s 包住的是**整条 generic run**，其中包含一次全量模型巡检。而本机实测同一模型的巡检成本是：

| 模型 | 特征 | 巡检耗时 |
|---|---|---|
| 本模型 rev74（410 特征） | 410 | ~85 s（08:43 那次恢复刚好挤过） |
| 本模型 rev87（474 特征） | 474 | 220–571 s（§8.3） |

也就是说：**模型一旦长到巡检超过 90 s，`restore_baseline` 就再也不可能成功。** 而且 `budget_ms` 是硬编码默认参数，`config.json` 里没有对应开关（`budgets.native_phase_seconds=90` 只是把这个数字回显出来）。

### 9.3 后果：没有任何可用出口

`creo_reconcile_model` 返回的 `actions` 在这个状态下是：

| action | 可用 | 原因 |
|---|---|---|
| `restore_baseline` | ✅ | 但每次都必然 `recovery_phase_timeout` |
| `accept_saved` / `accept_live` / `abandon_new` | ❌ | 缺少健康 live 证据 |
| `ack_no_mutation` | ❌ | 只有 `failed` 状态可用，当前是 `unknown_outcome` |
| `ack_failure` | ❌ | 还被 pending / recovery job 占着 |
| `abandon_stalled_recovery` | ❌ | `stalled_intent: {proven:false, reason:"stage_advanced"}`——因为 worker 已经启动过 |
| `confirm_panel_closed` | ❌ | 无面板守卫 |

`stalled_recovery.next_step` 只说「poll `creo_get_job` 并读 stage」，而那个 job 已经是终态 `unknown_outcome`。于是形成一个**闭环**：`restore_baseline` → `recovery_phase_timeout` → `reconciliation_unconfirmed` → 保护保留 → 只能再 `restore_baseline`。

### 9.4 建议

1. **`RecoveryDeadline` 的预算必须可配、且按模型规模放大**。至少做成 `config.json` 项（如 `recovery_phase_seconds`，默认 90，允许 ≥1800），并按 `features/surfaces/edges` 数量做下限保护——否则任何超过约 450 特征的零件都进不了恢复。
2. **`recovery_phase_timeout` 不该等同于「结果未确认」**。恢复作业在超时前已经把 `native_checkpoint.json` 落盘了，且此时**没有任何模型文件被改写**（`candidate=null`、基线 sha256 未变），完全可以按「零变更确认」收尾，回到 `ready`。
3. **补一个出口**：当恢复 job 已终态、`runner`/`worker` 都 `stopped=true`、`candidate=null`、基线哈希未变时，`abandon_stalled_recovery` 应放行（现在被 `stage_advanced` 一票否决）。或者给 `ack_no_mutation` 放宽到 `unknown_outcome`：它本来就是纯元数据事务，不碰 Toolkit、不碰 revision、不碰文件，正是本场景需要的。
4. **`ExitProcess(31)` 前请顺手写一份最小 `native_result.json`**（带 `completion_stage` 与 `failure_phase`）。现在超时只留 checkpoint，上层只能从 checkpoint 猜发生了什么事。

### 9.5 现在的状态

- 模型 `frigate_v4` 停在 `unknown_outcome`，`pending_job=bea4ec07…`、`recovery_pending=0625dbae…`，两个作业的进程都已死亡。
- 磁盘文件 `prt.90` 完好（sha256 与记录一致），**几何没有丢失任何一项已完成的特征**（rev87 的 474 特征 / 5,408,183,980.770802 mm³ 完好）。
- 但通过 MCP 接口已经无法继续提交任何计划。要么等作者改 `RecoveryDeadline`，要么只能人工把 `models/<id>/model.json` 里的 `status` 改回 `ready` 并清掉 `pending_job`/`recovery_pending`（等价于作者工具里本该提供的 `ack_no_mutation`）。

## §10 与同日另外两份反馈的关系

- `2026-11-23+CREO+0.35.8+chamfer_type被dump丢弃与斜置弧坐标标注移位.md`：`chamfer_type` 被 `model_dump` 丢弃、`coordinates` 对斜置弧静默移动直线端点 8.195 mm。
- 本文：三点基准面 section 缺第二条参考（§1–§6）→ 保存重载后的全量比对静默挂起（§8）→ 恢复路径 90 s 硬截止把模型锁死（§9）。

三者互不相关，但都会在「斜置几何 + 原生特征」这条路上同时撞上。由 §1 到 §9 是一条完整的失败链：**草图缺参考 → 误报 autodim → 补锚定面绕过 → 验证阶段挂起 → 恢复阶段超时 → 模型永久锁死**。
