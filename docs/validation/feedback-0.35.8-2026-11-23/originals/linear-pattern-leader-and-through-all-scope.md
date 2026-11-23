# 2026-11-23 · CREO 10.0.0.0 · MCP_CREO_MechDog 0.35.8 · 阵列 leader 被解析到前驱草图致空转，through_all 无法限定实体

## 0 一句话结论

**BUG-150 已真正修复并验收**：`scope={"kind":"bodies","body_ids":[-5778]}` 通过，切入链路重新可用，单件护卫舰上一晚推进 **46 个特征**（挤压/切除/阵列/扫掠），B016/B017 的去料量分别为 **43,200.0000000 mm³**，与解析值逐位一致。
**但 0.35.8 仍有两个新问题**：
（A）**阻断级**：`linear_pattern` 对同一个 leader 标签，一次解析到**前驱草图**、一次解析到**拉伸特征**；前者返回 `succeeded`、`member_count=7`，体积变化 **0.000**，全程无任何警告。护卫舰上 5 个阵列第一次全部空转。
（B）**能力缺口**：`scope` 与 `through_all` 仍互斥，多闭环/相交闭环的实体拉伸直接拒绝。

---

## 1 【已修复·验收通过】P19 负 body id 与切除链路

### 1.1 0.35.5 报告的问题已闭环

0.35.5 时 `frigate_v4` 的唯一实体报 `id=-5778`：

- 带 `scope={"kind":"bodies","body_ids":[-5778]}` → 提交前被「必须正整数」拒绝；
- 不带 scope 的 `mode="cut"` → 一律 `Extrude cut removes no material`。

0.35.8 的 BUG-150 把 `-5778` 认定为 Creo 为零件初始实体分配的**有效 ID**。本机复测结果如下（同一 `frigate_v4`，无重建、无迁移）：

| 特征 | 作业 | revision | 体积（mm³） | ΔV（mm³） | 解析预期 |
|---|---|---|---|---|---|
| B016 Cut-Extrude2 | `e668b0282ebd4b349150128d87878aa2` | 7→8 | 4,176,293,912.796204 | **−43,200.000001** | 21,600×2 = 43,200 |
| B017 Cut-Extrude3 | `b410a69d3421475c9df2e058ca858fc5` | 8→9 | 4,176,250,712.796204 | **−43,200.000000** | 同上 |
| B018 Cut-Extrude4（双贯穿） | `fb79899e462043e694f178841d53dcc3` | 9→10 | 4,096,513,479.146997 | −79,737,233.649 | 轮廓 71,309.73 mm² × 弦长 1,118 mm |
| B019 LPattern2（该切除 ×3） | `66056ad004d645ee809d27d2ba9a6c18` | 10→11 | 3,937,039,135.849644 | −159,474,343.297 | 2×79,737,233 = 159,474,466（差 123，6×10⁻⁷） |

巡检回执也新增了 `cut_scope_id_eligible: true`，可直接判定某个 body id 能不能进作用域，这一点很实用。

### 1.2 顺带验证：切除引擎的判定是「扫掠体 ∩ 材料」，不是「截面 × 深度」

为排除「引擎少切」的可能，另建独立探针件 `probe_pat_1123b`（`ab1def121ba7400799372e510504d2d9`）：

- 200×200×200 实心块，体积 7,999,999.999999998；
- 在 `y=−100`（块外 100 mm）的 XZ 面上画 Ø50 圆，向 +Y 切 150 mm；
- 实测 ΔV = **−98,174.7704** = π·625·**50**，即只有真正落在材料里的那 50 mm 被切掉。

结论：切除本身是诚实的，前面护卫舰上出现的「小于理论值」是几何相交结果，不是引擎漏切。**这一条建议写进文档**，避免后来者把正常的盲切误判成缺陷。

---

## 2 【阻断级·新】`linear_pattern` 的 leader 标签解析到前驱草图，阵列空转且无警告

### 2.1 事实：同一标签，两次解析到不同特征

第一次（0.35.8 顺序批处理，B025）：

```
job 66041948cb3c4861980c83d8bee4e10d
op       linear_pattern  label=lpattern5
leader   "cut_extrude7"        （该标签在别名字典里指向拉伸特征 3754）
回执      leader_id = 3747  member_count = 7  succeeded = true
体积      3,936,861,347.796360 → 3,936,861,347.796360    ΔV = 0.000
```

第二次（同一模型、同一 leader 字符串，只换了输出标签）：

```
job 8e82f3798ad24c2686912988d79eac83
op       linear_pattern  label=lpattern5b
leader   "cut_extrude7"
回执      leader_id = 3754  member_count = 7  succeeded = true
体积      5,423,529,273.242569 → 5,423,218,653.512768   ΔV = −310,619.730
```

`-310,619.730 ≈ 6 × 51,778.1`（种子孔去料量），即第二次才真正复制出 6 个孔。

**同一 `cut_extrude7`，为什么第一次是 3747、第二次是 3754？** 上溯到造特征的那个作业：

```
job a8ca9a72f18b48ec96f890c0a7c78bed  （B024 = sketch60 + cut_extrude7）
operations[0]  op=sketch   label=sketch60     feature_id = 3747
operations[1]  op=extrude  label=cut_extrude7 feature_id = null   ← 拉伸特征没报出自己的 ID
aliases         "cut_extrude7": {"feature_id": 3754, "op": "extrude"}   ← 别名字典里已经是 3754
```

也就是说：**创建拉伸的那个作业里，`extrude` 结果的 `feature_id` 是 `null`，而同一作业的 `aliases` 已经写成了 3754；紧接着的下一个作业用同一个标签做阵列，拿到的是 3747（草图）。** 标签→ID 的解析在「特征刚创建、尚未重载」的窗口里不稳定。

### 2.2 删除时的依赖回执证实「阵列建在草图上」

想删掉这 4 个空转阵列时，`feature_state delete` 的拒绝回执把阵列的依赖列了出来：

```json
"feature_state targets do not cover every affected dependency; Creo also deleted these features; list them explicitly (no automatic cascade): [
  {"feature_id":5730,"label":"d3sketch2","type_name":"sketch_or_curve"},
  {"feature_id":6033,"label":"d3sketch4","type_name":"sketch_or_curve"},
  {"feature_id":6216,"label":"sketch161","type_name":"sketch_or_curve"}, ...]"
```

`d3sketch2 / d3sketch4 / sketch161` 正是这 3 个阵列想阵列的**拉伸特征的前驱草图**。Creo 认为删除阵列会连带删除这些草图，说明阵列成员确实是**草图实例**，不是实体实例——与 ΔV=0 完全吻合。

### 2.3 影响面

护卫舰这一轮有 5 个阵列第一次全部空转（B025 / B084 / B087 / B089 / B091），其中 4 个还额外把 leader 指向草图（这是我方脚本的标签映射错，见 §5 的 D9），但这 4 个阵列第二次用**同一个 leader 字符串**就成功了，说明解析在两次之间发生了变化：

| 阵列 | 第一次 ΔV | 第二次 ΔV |
|---|---|---|
| LPattern5 → cut_extrude7 | 0.000 | −310,619.730 |
| LPattern7 → sweep2 | 0.000 | +52,534.0 |
| LPattern9 → sweep4 | 0.000 | +53,598.2 |
| LPattern10 → boss_extrude26 | 0.000 | +85,999.95 |
| LPattern11 → sweep5 | 0.000 | +91,000.6 |

（B084/B087/B089/B091 第一次是我方把 leader 映射到了 `d3sketch2` 等草图标签，属于我方错误；**B025 第一次传的就是 `cut_extrude7`，这是 MCP 侧的真实解析错误**。两条必须分开看。）

### 2.4 建议（按性价比排序）

1. **`linear_pattern` 提交前做「leader 有没有实体」的预检**：读 leader 的 `ProFeature` 类型，若为 `sketch_or_curve` 或该特征无实体成员，直接拒绝并给出「阵列 leader 必须是有实体的特征（拉伸/扫掠/阵列），当前解析到 <name>(type)」——这能一次性消灭这类静默空转。
2. **回执里补 `leader_kind` 与 `leader_surface_count`**：现在只回 `leader_id`，调用方无从判断 leader 是否正确。
3. **修 `extrude` 的 `feature_id: null`**：创建作业内应能拿到新特征的 ID；拿不到也不要用草图 ID 顶上（这正是 3747 的来源）。若确实读不到，宁可返回 `null` 让别名字典回退到下一次重载后再解析。
4. **`aliases` 与运行时解析用同一份数据**：本次 `creo_inspect_model(section="aliases")` 明确写 3754，而 `linear_pattern` 用的是 3747，两处不一致本身就该报警。

---

## 3 【能力缺口】两条仍然挡路

### 3.1 `scope` 与 `through_all` 互斥（P3）

```
P3  Ø20 通孔，direction=symmetric + depth_type=through_all + scope={bodies:[-5778]}
→ Error: operations[1].scope: scope with through_all is not yet validated against the native executor;
  use blind depth or omit scope
```

`errors.py`/`f08_contract.py` 里写着「through_all and multiple targets are unsupported」。后果：**贯穿切除无法限定实体**。单体件无感，但 TXT 里大量「两方向贯穿全部 + 只作用于指定对象」的特征（B018/B020/B022/B027/B029/B065/B098）在真实多体零件上会切穿全部实体。护卫舰现在是单体，所以只能靠「事后量体积」判断有没有切到不该切的东西。

建议：through_all + 单实体作用域可以直接放行（`PRO_BODY_SELECT` 与「贯穿」在元素树里是两个独立字段，理论上不冲突）；做不到的话，至少在回执里给出「本次贯穿扫到的实体列表与其去料量」，让调用方能核对。

### 3.2 多闭环/相交闭环的实体拉伸被拒（P4）

```
B092  Sketch178 = 7 个圆（1 个中心 + 6 个环绕，部分重复同心）
→ Solid extrude profile rejected: detected 7 closed contour(s), 0 open contour(s) and 7 curve entities;
  [intersecting] contours whose boundaries cross (e01/e03) near (1178.77758, 599.902156) mm;
  [tangent] contours that touch without crossing ...
```

Creo 原生允许一个草图里多个闭环一起拉伸（相交的并成一个凸台）。当前实现只接受**恰好 1 个**闭合轮廓，且相交/相切直接拒绝。TXT 里的花形凸台（B092/B094）因此无法一次建出。

**要点**：这一条的诊断信息质量很好（给出相交点坐标、涉及实体名），比 0.35.5 时期强很多，建议保留这种「带坐标、带实体名」的拒绝原因。

---

## 4 0.35.8 实测可用能力

| 能力 | 结论 | 证据 |
|---|---|---|
| `scope=[-5778]` 切除 | 可用，去料精确 | B016/B017 = 43,200.0000000 |
| 无 scope 双贯穿 | 可用 | B018 −79,737,233.649 |
| through_all + symmetric | 可用 | B018/B020/B065/B098 |
| `linear_pattern`（leader 解析正确时） | 可用 | B019 差 6×10⁻⁷，B025 第二次 −310,619.730 |
| `sweep` 6 mm 管 | 可用，与解析值逐位一致 | 16,236.474698859818 |
| `feature_state delete` 依赖保护 | **行为正确**（拒绝并列出全部依赖） | job `20259001…` |
| 切除几何回执 `cut_geometry_context` | 可用，含方向符号/深度区间/贯穿无深度说明 | B022/B098 |
| 保存重载校验 | 每特征均 `saved_file_reloaded_and_verified=true` | 40 个作业 |

---

## 5 当前整船进度（`frigate_v4`）

- model_id `df7f74bf5e424dbeb00605e218be89ad`，**revision 59**
- 体积 **5,423,218,653.512768 mm³**（rev7 为 4,176,337,112.796205，本晚 +1,246,881,540.7）
- **347 特征 / 555 面 / 1,823 边 / 1 body / 4 quilt**（rev7：93 / 170 / 434）
- 巡检 `healthy=true, has_solid=true, inspection_source=saved_reloaded`

本轮推进的 TXT 条目：B016–B021、B024、B025、B027、B028、B039–B044、B049、B053–B055、B059–B063、B065–B068、B071、B073、B075、B077、B079、B082–B091、B093、B096、B099、B100、B103，共 **46 个特征成功、9 个失败（其中 4 个在准入阶段被剖面校验拒绝）、1 个删除被正确拒绝**。

失败清单（均已定位原因，不属于 MCP 缺陷）：

| 条目 | 原因 |
|---|---|
| B022 | 目标区域属于尚未建成的 Thicken3（依赖被阻断的 B002 Surface-Loft1），无材料可切 |
| B029 / B038 / B069 | `ProFeatureWithoptionsCreate=-1`，草图剖面被 Toolkit 拒绝（我方实体集不闭合） |
| B066 / B094 / B097 | 剖面 `0 closed contour` / `branched contour`（我方实体集有断点与分叉） |
| B092 | 7 圆相交闭环，见 §3.2 |
| B098 | 目标区域无材料（依赖的 B097 未建成） |

---

## 6 最小复现步骤 A（阵列 leader 解析不稳定）

1. 新建零件，`sketch`（XY，Ø50 圆）+ `extrude mode=cut depth=150 scope={bodies:[-5778]}` → 记下该作业回执里 `operations[1].feature_id`（本次为 `null`）。
2. 立刻在**下一个作业**里用 `linear_pattern leader="<该拉伸的标签>" count=7 spacing=430 direction=[1,0,0]`。
3. 观察 `leader_id` 是否等于第 1 步草图的 `feature_id`；若是，则阵列成员建在草图上，ΔV 恒为 0 且无警告。
4. 再跑一次相同阵列（换 label），`leader_id` 变为拉伸特征 ID，ΔV 正确为负。

我方原始作业：`a8ca9a72…`（造件）→ `66041948…`（空转）→ `8e82f379…`（正常）。

## 7 最小复现步骤 B（through_all + scope）

```
operations = [ {sketch XY Ø20}, {extrude mode=cut direction=symmetric depth_type=through_all
                                  scope={kind:"bodies", body_ids:[-5778]}} ]
```
→ 提交前拒绝：`scope with through_all is not yet validated against the native executor`。

---

## 8 遗留偏差（我方侧，非 MCP 缺陷）

- **D8**：4 个空转阵列（lpattern7/9/10/11）残留在特征树里。删除它们会连带删除 `d3sketch2/d3sketch4/sketch161`（其它特征的草图），风险大于收益，故保留；它们不含几何，对体积零影响。
- **D9**：我方批量脚本把 TXT 的「种子特征」名映射到特征的**第一个 op 标签**，对 `sketch+extrude` 组合会取到草图标签——B084/B087/B089/B091 第一次空转源于此。已改为优先取实体生成类 op 的标签。
- **B024** 的 Ø50 深 150 切除只去料 51,778.1 mm³：探针已证明引擎按「扫掠 ∩ 材料」计，故这是该处船体壁面位置造成的浅坑，非缺陷；但与本 TXT 条目的意图（贯穿）不符，记为偏差待复核。
