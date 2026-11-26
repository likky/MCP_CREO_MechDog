# 钣金建模实战手册（MCP_CREO_MechDog + Creo 11）

> 记录时间：2026-11-12　｜　环境：Windows x64 / Creo 11.0.0.0 / Python 3.12 / 源码 `D:\Projects\MCP_CREO_MechDog`
> 全部结论来自本机实机建模，每步都有 `saved_file_reloaded_and_verified=true` 与体积校验。
> MCP 服务层的三处修复见 [`CREO11_TEST_REPORT.md`](CREO11_TEST_REPORT.md)（缺 `PTCNMSPORT`、探测超时、响应预算）。

---

## 1. 可用能力清单

### 1.1 钣金专用工具（8 个）

| 工具 | 对应 op | 说明 |
|---|---|---|
| `creo_new_sheetmetal` | — | 建件。`template="native_planar"` 才产出真钣金件（`mmns_part_sheetmetal_abs.prt`） |
| `creo_sheetmetal_planar_wall` | `sheetmetal_planar_wall` | 原生矩形基板（unattached wall） |
| `creo_resize_sheetmetal_planar_wall` | `resize_sheetmetal_planar_wall` | 改基板长宽，特征 id 与厚度不变 |
| `creo_sheetmetal_wall` | `sheetmetal_wall` | 从开环草绘线做薄壁（thickness=板厚，depth=壁高） |
| `creo_sheetmetal_flange` | `sheetmetal_flange` | 法兰折弯：`height/angle(0~180)/radius/flip/miter_cuts/relief/end_trim_mm` |
| `creo_sheetmetal_unbend` | `sheetmetal_unbend` | 展开（`references=[]` 即全部折弯） |
| `creo_sheetmetal_flat_pattern` | `sheetmetal_flat_pattern` | 展开图特征 |
| `creo_sheetmetal_bend_back` | `sheetmetal_bend_back` | 折回 |

### 1.2 被门控（不可用）

`sheetmetal_flange_profile`（自由轮廓/hem）、`sheetmetal_corner_relief`、`sheetmetal_quilt_form`
—— 均标注为 offline candidate、未实机验证，提交会被 `require_available` 直接拒绝。

### 1.3 配合使用的通用 op

`sketch` / `extrude`(mode=cut) / `hole` / `datum_plane` / `datum_axis` / `inspect_model` / `mass_properties`

---

## 2. 已验证配方

### 2.1 建基板

```json
{"op":"sheetmetal_planar_wall","label":"base_panel","plane":"XY",
 "length":220,"width":160,"thickness":1.5}
```

* 基板占 `x∈[0,L]`、`y∈[0,W]`、`z∈[0,t]`（**从原点角开始**，不是居中）。
* 必须用钣金模板建件；用实体模板会报
  `needs a sheetmetal part: the native unattached planar wall only regenerates in one (ProMdlSubtypeGet=0)`。
* 备选 `sheetmetal_wall`（开环线 + 厚度）可从实体件转换，但后续 planar wall 就不能用了。

### 2.2 折弯（法兰）

```json
{"op":"sheetmetal_flange","label":"wall_back",
 "edge":{"kind":"edge_geometry","endpoints_mm":[[0,0,1.5],[220,0,1.5]],"tolerance_mm":1e-4},
 "height":60,"angle":90,"radius":1.5}
```

* **边引用一律用 `edge_geometry` 端点**，不要用 `{kind:'edge',id:N}`——重建后 id 会变。
* `height` 是沿折弯后法向的长度；`angle` 是相对基板的夹角（0~180）；`radius` ≥ 板厚较稳。
* `flip` 控制折向哪一侧（同一角度两个方向）。
* **斜接**：第 3、4 面墙必须带 `"miter_cuts":{"width":2}`，否则
  `adjacent_bend_ends` 守卫会拒绝（相邻折弯端部顶死）。
* `relief`：只有 `{"type":"rectangular","width":..,"depth":..}` 与 `none` 可用（折弯端释放）。
* `end_trim_mm`：把法兰两端各缩短一点，避免干涉。

#### 折弯会“吃掉”基板侧边

90° 折弯半径 R、板厚 T 完成后，基板垂直于折弯线的那两边会各缩进约 **R+T**：

| 参数 | 基板边长 | 折弯后侧边实际范围 |
|---|---|---|
| T=2, R=2 | 60 | y ∈ [4, 56] |
| T=1.5, R=1.5 | 160 | y ∈ [3, 157] |

所以**先后加墙时端点坐标要改**，否则报
`edge_geometry endpoints ... matched none of the 36 straight model edges`。

### 2.3 45° 折弯

在已有墙的**顶边**再折 45°：

```json
{"op":"sheetmetal_flange","label":"fold_back_45",
 "edge":{"kind":"edge_geometry","endpoints_mm":[[217,0,60],[3,0,60]],"tolerance_mm":1e-4},
 "height":40,"angle":45,"radius":1.5,"flip":true,"miter_cuts":{"width":2}}
```

顶边不要手写坐标，从模型里查：
`inspect_model(detail="full", section="edges")` → 取两端 `z≈壁高`、`|y|≤2`、最长的边。

### 2.4 在竖直墙上开孔（矩形 / 圆）

思路：**草绘在基准平面上 + 穿透切除**，单向切。

```json
{"op":"sketch","label":"cut_back_a_sk","plane":"XZ","offset":0.75,
 "entities":[{"type":"rectangle","name":"r","min":[25,12],"max":[85,48]}]},
{"op":"extrude","label":"cut_back_a","sketch":"cut_back_a_sk",
 "mode":"cut","depth_type":"through_all","direction":"negative"}
```

| 墙 | 草绘平面 | `offset`（该平面自身轴上的全局坐标） | 切除方向 |
|---|---|---|---|
| 后壁 y∈[0,T] | XZ | `T/2` | `negative` |
| 前壁 y∈[W-T,W] | XZ | `W-T/2` | `positive` |
| 左壁 x∈[0,T] | YZ | `T/2` | `negative` |
| 右壁 x∈[L-T,L] | YZ | `L-T/2` | `positive` |
| 底板 z∈[0,T] | XY | `T/2` | `positive` |

> ⚠️ **`direction="symmetric"` 会沿该轴把整个零件切穿**——它同时切对面那面墙。
> 只想切一面墙时用单向（注意别踩「中面草绘只切半厚」）；想一次给两面平行墙开同样的孔时，
> 恰恰应该用 `symmetric`（见 3.4 桥架侧壁孔）。
> ⚠️ 草绘的 `offset` 是**全局坐标**（XY→Z、YZ→X、XZ→Y），不是沿法向的位移。

### 2.5 圆孔（水平面用 hole，竖直面用 cut）

* 底板上：用 `hole` op（placement plane + 基准面引用 + `offset1/offset2`）。
  **不给 offset 会落在原点角上**，只切掉一小条（实测 38 mm³ 而不是 226 mm³）。
* 竖直墙上：没有 hole 的放置方式，用 2.4 的 circle sketch + cut。

### 2.6 展开

```json
{"op":"sheetmetal_unbend","label":"unbend_all",
 "fixed_surface":{"kind":"surface","id":58},"references":[]}
```

固定面取**底板**：`inspect_model(detail="full", section="surfaces")` 里
`z≈0` 且 XY 跨度最大的那个面。`references: []` = 展开全部折弯；
给具体折弯引用则只展开选中的。

---

## 3. 实测数据（可用于核对）

### 3.1 U 形槽 + 二级回折 + 孔（`demo_bend_box.py` 前身）

| 步骤 | 体积 mm³ |
|---|---:|
| 基板 120×60×2 | 14400.00 |
| 前长边 90° h30 R2 | 20810.97 |
| 后长边 90° h30 R2 | 27221.95 |
| 前法兰顶部回折 90° h20 | 31232.92 |
| 中心 Ø12 通孔 | 31006.73（−226.19 = π·6²·2）|
| 展开 | 展平后体积与折弯体不同（展开长度按折弯余量计）|

### 3.2 四壁盒 + 5 孔 + 展开（`demo_bend_box.py`）

| 步骤 | 体积 mm³ | 耗时 |
|---|---:|---:|
| 基板 160×100×2 | 32000.00 | 10s |
| 前壁 90° | 40547.96 | 9s |
| 后壁 90° | 49095.93 | 9s |
| 左壁 90° + 斜接 | 53727.97 | 10s |
| 右壁 90° + 斜接 | 58360.01 | 12s |
| 中心 D40 | 55846.74（−2513.27）| 15s |
| 4×D8 | 55444.61（−402.12）| 31s |
| **展开全部** | 54769.54 | 13s |

### 3.3 槽式电缆桥架段（实用件，600 长）

结构与市售槽式桥架一致：底板 + 两侧 90° 侧壁 + 侧壁顶部内折加强边 + 底部通风孔 + 两端连接孔。
板厚 1.5 冷轧钢板，折弯 R1.5。

| 步骤 | 体积 mm³ | 耗时 |
|---|---:|---:|
| 底板 600×100×1.5 | 90000.00 | 8s |
| 侧壁 y=0（h50） | 132780.86 | 8s |
| 侧壁 y=100（h50） | 175561.72 | 9s |
| 顶部内折 lip 15（y=0）| 186842.59 | 9s |
| 顶部内折 lip 15（y=100）| 198123.45 | 9s |
| 7×Ø10 通风孔 + 4×Ø9 连接孔（底板）| −1206.37 | 16s |
| 5×Ø8 侧壁孔 ×2 侧 + 4×Ø6 折边孔 ×2 侧 | −1293.27 | 10s |
| **合计** | **195823.81** | **69s（分步）/ 31s（单计划）** |

* 内折边取**内侧顶边**（y = T 与 y = W−T，z = 壁高）向内翻，用 `flip=false`；
  取外侧边会朝外翻，不是桥架的做法。
* 多个圆孔写在**同一张草图的 entities 里**，一个 cut 就切完，比逐孔提交快一个数量级：
  7+4 孔只用 2 个 sketch+cut 配对；侧壁 5 孔、折边 8 孔各只需 1 个配对。
* **一次草图切两侧壁**：侧壁是平行平面，在 XZ 平面上画一排孔用 `symmetric` 切，
  两侧壁同时得到同样的孔（Δ = 5×2×π·4²·1.5 = 753.98，实测一致）。
* **一次草图切两条折边**：两条折边同在 z 48.5~50，在 XY 平面 z=48.5 画 8 个孔、
  `positive` 切，两条折边一次开完（Δ = 8×π·3²·1.5 = 339.29）。
* 体积校验：1206.37 + 753.98 + 339.29 = 2299.64，从 198123.45 减到 195823.81 ✔

> **耗时规律**：连一次 Toolkit 约 5s，每个特征 8~20s，每个 sketch+cut 配对约 19s。
> 多个开孔**放进同一个计划**只连一次，比逐个提交省一半以上时间。

---

## 4. 踩坑清单

| # | 现象 | 原因 / 解法 |
|---|---|---|
| 1 | `needs a sheetmetal part … ProMdlSubtypeGet=0` | 必须用 `mmns_part_sheetmetal_abs.prt` 模板建件 |
| 2 | `edge_geometry endpoints ... matched none` | 端点没跟上折弯造成的基板缩进（R+T），或坐标写错 |
| 3 | `adjacent_bend_ends` 拒绝 | 第 3、4 面墙要带 `miter_cuts` |
| 4 | 前后墙被同时切穿 | `direction="symmetric"` 改成单向 |
| 5 | 孔落在原点角 | `hole` 要配合 `offset1/offset2`（基准面到孔心的距离）|
| 6 | `inspect_model` 的 `edges` 是空的 | 默认 full 视图会分页，改用 `section="edges"` / `"surfaces"` |
| 7 | `Provide expected_revision from creo_inspect_model` | 上一步失败后返回值里没有 revision，重新查一次 |
| 8 | 控制台 `UnicodeEncodeError: 'gbk'` | 脚本里 `sys.stdout.reconfigure(encoding="utf-8")`，打印用 ASCII（Ø 换成 D）|
| 9 | 一次提交里有多步且中间失败 | 整单回滚，模型保持上一步状态——不会留半个特征 |
| 10 | 孔只切掉**一半板厚**（体积差正好是理论值一半）| 草绘平面放在板厚的**中面**（offset=T/2）再单向 `through_all`，只从该面向外切到板料一侧；把草绘放到**起始面**（底板用 `offset=0`），或者用 `symmetric` |
| 11 | `Extrude cut removes no material`（侧壁孔）| 折弯后侧壁占 y 0~3（含 R 的包络），XZ 平面 offset=0 + `positive` 可能刚好朝材料外切；侧壁孔改用 **`symmetric`**，一次切穿两面墙且不依赖正负向 |

---

## 5. 脚本与样例索引

| 路径 | 内容 |
|---|---|
| `tools/demo_bend_box.py` | 四壁盒 → 中心孔 → 4×安装孔 → **展开**（7 步，约 96s）|
| `tools/demo_cable_tray.py` | **槽式电缆桥架段**（600×100×50，1.5 板厚）：两侧壁 + 内折加强边 + 底板通风/连接孔 + 侧壁孔 + 折边孔，33 特征；五种速度模式见第 6 节 |
| `examples/sheetmetal_bend_u.json` | U 形槽 + 二级回折 + 中心孔，单计划可重放（体积稳定 31006.73）|
| `examples/sheetmetal_wall.json`、`sheetmetal_base_yz.json` | 上游自带的最简钣金样例 |
| `build/demo_bend_box.jpg`、`build/cable_tray.jpg`、`build/sheetmetal_bend_u.jpg` | 实机预览图 |

运行方式：

```powershell
cd D:\Projects\MCP_CREO_MechDog
.\.venv\Scripts\python.exe tools\demo_bend_box.py        # 加 --fast 去掉步骤间停顿
.\.venv\Scripts\python.exe tools\demo_cable_tray.py          # 单计划 ~16s（画面只刷新 1 次）
.\.venv\Scripts\python.exe tools\demo_cable_tray.py --two    # 2 段
.\.venv\Scripts\python.exe tools\demo_cable_tray.py --groups # 3 段（推荐录屏）
.\.venv\Scripts\python.exe tools\demo_cable_tray.py --even   # 4 段（均匀节奏）
.\.venv\Scripts\python.exe tools\demo_cable_tray.py --stepwise # 8 步（逐个特征长出）
```

---

## 6. 提速：把操作合并成一次提交

每次 `submit` 都是一个独立 job：起子进程 → `ProEngineerConnect`（约 5s）→ 建模 → 保存 → 重载校验 → 断开。
**连接开销是固定成本**，所以把多个操作写进同一个 `operations` 数组能省掉绝大部分时间。

实测同一个桥架：

| 提交方式 | 耗时 | 画面刷新次数 |
|---|---:|---|
| 8 次提交（`--stepwise`，逐特征）| 98s | 8（间隔 8~9s）|
| 4 次提交（`--even`，均匀四段）| 65s | 4（间隔 15s）|
| **3 次提交（`--groups`，推荐录屏）** | **52s** | 3（间隔 12s / 16s / 21s）|
| 2 次提交（`--two`：框架 / 全部孔）| 40s | 2（间隔 28s）|
| 1 次提交（默认，13 个 op）| 31~41s | 1 |

**为什么不能又快又连续**：画面刷新发生在**每个作业结束时**
（native 的 `display_preview`：activate → display → raster → refresh → repaint），
不是每个特征结束时。所以一次提交只在建完后刷新一次。
而每次提交的固定开销约 8s（起进程 + `ProEngineerConnect` ~5s + 保存 + 重载校验），
再加上一次切除的实际工作 7~8s，**每个可见阶段的下限就是 15s**。
速度与“过程感”因此直接对冲，按录制需要选档即可。

实践要点：

* 同一计划里的 op **按顺序执行**，所以后一步可以直接引用前一步刚折出来的边（用 `edge_geometry` 端点坐标）。
* 一旦某步失败，**整单回滚**，模型保持提交前的状态——这反而比逐步提交更好排查。
* 如果需要在建模过程中自动量取边坐标（边会随折弯变化），那就得分步；能确定性写死坐标时优先合并。
* 录屏时想看到“逐特征长出”就用 `--stepwise`；只要结果就用单计划。
