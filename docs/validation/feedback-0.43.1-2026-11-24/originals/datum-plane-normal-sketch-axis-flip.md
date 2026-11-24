# 2026-11-24 / MCP_CREO_MechDog 0.43.1 / 偏移基准面法线方向静默翻转

> 反馈对象：MCP_CREO_MechDog **0.43.1**（运行中版本；检查更新时 GitHub 已有 0.43.2，本报告全部证据来自 0.43.1）
> 宿主：Creo Parametric 9.0.0.0（`release_numeric=41`），Windows，`D:\CREO\Creo 9.0.0.0`
> 任务：仅凭一份 TXT（《斜坡升降输送机简易机构——跨软件三维建模自然语言说明 v1.9》）从空白模型建 4 个零件 + 15 实例装配，全程只用 MCP 原生特征，不导入任何实体。
> 结论：**几何全部建成并通过数值验收**，但过程中撞到 1 个会把零件"静默做错"的核心缺陷、5 个能力缺口、若干可用性问题。核心缺陷是下面第 1 条。

---

## 0. 本次实建结果（问题就是在这里暴露的）

四个零件 + 装配全部通过 MCP 原生 sketch/extrude/cut/round/assemble 建成并落盘（`saved_file_reloaded_and_verified=true`）。对照 TXT 的源件实测（B 基准）：

| 零件 | 体积 实建 / 源 | Δ相对 | 面积 实建 / 源 (mm²) | 面数 实建/源 | 体数 |
|---|---|---|---|---|---|
| Step | 2227.500 / 2227.5 | 0 | 3312.000 / 3312.0 | 6 / 6 | 1 |
| Belt | 237426.3096 / 237426.3096 | <1e−9 | 321364.9038 / 321364.9039 | 18 / 18 | 1 |
| Box | 89495.6615 / 89495.669 | 8.4e−8 | 12930.4268 / 12930.425 | 26 / 26 | 1 |
| Part 1 | 621563.690 / 621572.4115 | 1.40e−5 | 249363.031 / 249363.736 | 80(merged)/82 | 1 |
| 装配 15 实例 | 975215.661 / 975188.197 | 2.8e−5 | 623402.36 / 623486.48 | — | 15 组件 |

- 装配重心 (568.667975, 384.840033, 139.520945) vs 源 (568.667302, 384.855493, 139.491676)：**最大分量差 0.0293 mm**（判据 0.05 mm）**通过**。
- 用位姿表 + 四零件质量属性复算装配重心，与 MCP 实测装配重心**逐位一致（残差 0.000000 mm）**，说明 15 个变换确实按表写入了。
- 体积差闭合：+36.19（Box 的 C.M.S 压印文字，TXT §六 已声明不重建）−8.72（Part 1）−0.034（Belt）+0 = **+27.44 ≈ 实测 +27.46 mm³**，无未解释项。
- Part 1 少 2 张平面（48 vs 50，圆柱面 32 个与源逐类相同），判为内核差面：底梁两端面与两块侧板外表面严格共面，Creo 合并为一张，SolidWorks 源件保留为两张。几何无差（ΔV 1.4e−5）。

---

## 1. 【核心 · 高】任意偏移基准面缺失，且新建基准面的法线方向不可控 → XZ 类草图整体反号

### 现象
用 `{kind:'datum_plane', axis:'x'/'y', offset:N}` 指定非零偏移草图面时，因为模型里没有那张基准面，直接失败：

```
Plane reference must identify exactly one surface; 0 candidate surface(s) match
normal/offset axis=x offset=-100.000000 (ids: ).
Use an explicit surface or plane id from inspect, or the geometric form
{kind:'plane',normal:[...],offset:N}; the datum_plane axis+offset form needs
exactly one datum plane at that height
```

于是改用 `datum_plane` 显式建面，再按 `{kind:'datum_feature', label:...}` 引用。这一步本身是合理的，问题出在建出来的面：

**`datum_plane` 平行于默认 XZ、偏移 −30 建出的面，法线是 (0, 1, 0)**（`creo_inspect_model` 回读确认）；而 capabilities 把 XZ 帧定义为 `u=+X, v=+Z, normal=(0,-1,0)`。草图帧由 `v = n × u` 推出，法线一翻，`v` 就从 +Z 变成 **−Z**。

后果（全部发生在"作业成功"状态下）：
1. 5 张 XZ 草图（底板、轴座 ⌀15.436×117、⌀23.664×5、滚轮座 ⌀15.440×358、⌀27.496×8）整体 **z 反号**——滚轮座落到 z=+500.126（设计 −500.126）；
2. `extrude.direction` 的 "positive/negative" 是**相对法线**的，法线反了，5 个拉伸方向也随之全反——滚轮座从 y=−159 向 −Y 拉了 358（落到 −517），而不是向 +Y 到 +199；
3. 特征**全部报 `succeeded / committed`**，作业 `status=succeeded`，只有靠体积（+985 mm³）和包围盒（y −517、z +513.874）比对才发现。

修正代价：把 5 张草图的 v 全部取负、5 个拉伸方向全部反过来重跑。

### 为什么难查
- receipt 里**有** `normal / u_axis / v_axis` 回显（这点很好），但失败时人不会去看，因为没有任何错误；
- capabilities 文档写的 XZ 帧法线是 (0,−1,0)，实际建出来的面是 (0,+1,0)，**文档与行为不一致**；
- 同一个模型里默认的 XZ 基准面 id=4 法线确实是 (0,+1,0)，所以"MCP 的 XZ 帧"其实依赖某个方向被翻转的支持面，而这一步对用户不可见。

### 建议
1. `sketch.plane` 的字典形式增加**显式 `v_axis`**（现在只允许 `u_axis`，v 只能由 `n×u` 推出）；这是最直接的解法，也让"按文档给定的草图框架"可复现。
2. 或给 `datum_plane` 增加 `flip` / `normal` 控制，并在 receipt 里回显最终法线。
3. capabilities 的 `frames.XZ` 应注明"取决于支持面法线方向，建偏移面后需回读"；或在 `sketch` 的 receipt 里对 `v_axis` 与请求框架不一致时给出 warning（现在完全静默）。
4. 更根本一点：`sketch.plane` 的 `{kind:'plane',normal,offset}` 若能**合成**一张虚拟支持面（无对应基准面时自动建 helper 面），就不需要用户手工铺 6 张基准面。

### 影响面
任何"草图不在三个默认基准面上"的零件都会踩到。本次 TXT 的 Part 1 有 6 个非零偏移面（x=−100/−105、y=−30/−37/−154/−159），全部命中。为绕开，特征树里多出 6 个 `datum_plane`，与 TXT 描述的 15 个造型节点不再一一对应。

---

## 2. 【高】`dimensioning="coordinates"` 拒绝构造实体（构造圆 / 构造线）

```
Coordinate dimensioning accepts lines, polylines, rectangles, circles, arcs
and exact B-splines only
```

- 触发点：Part 1 草图 1 里第一个实体 `c01`（⌀25 **构造圆**）。native.log 显示 `ProSectionEntityGet` 只调用一次就抛错，即第一个 map 项（构造圆）就被判为非 CIRCLE/ARC/LINE 类型。
- 真实草图里构造几何极常见（TXT 的 Part 1 草图1 有 2 个 ⌀25 构造圆 + 3 条构造线；草图2 有 6 条构造线）。本次只能把它们整批删掉——几何等价（TXT 明示"构造实体不参与造型"），但丢失了设计意图，且草图和源件不再同构。
- 建议：`coordinate_dimensions()` 里 `Pro2dEntdef` 的类型判定应包含 `PRO_2D_CENTER_LINE`（已含）与**构造圆/构造线的实际类型**；或对 `construction=true` 的实体直接跳过建尺寸（它们不参与轮廓，不需要被坐标尺寸钉住）。

---

## 3. 【中】`dimensioning="auto"` 选 coordinates，然后 coordinates 模式自己拒绝提交

```
Coordinate dimensioning changed the supplied geometry; maximum deviation mm=0.000012;
shifted_sample=[{"axis":1,"entity":"a2","moved_mm":4.63e-06,"point":"center"}, ...]
```

- 场景：Part 1 的 4 个长圆槽（16 实体）。`dimensioning` 缺省 `auto` 时按 `selection_reason="entity_count"` 选了 **coordinates**，然后求解器把 3 个槽头弧心挪了 4.6e−6 … 1.2e−5 mm，被"几何不得改变"闸门拒绝。
- 闸门是好的（我赞成它存在），但：
  1. **没有暴露容差**：`geometry_deviation` 的 `warning_threshold_mm` 是只读回显，用户无法把 1.2e−5 mm 级的内核数值噪声放过；
  2. `auto` 策略把用户推进了这个坑——按实体数选策略，却没考虑"该策略可能拒绝这张草图"；
  3. 报错只给 3 个采样点，不给"哪条约束/哪个尺寸导致的"。
- 绕开方式：整张草图退回 `autodim`，精度从 6 位小数掉到 3 位小数（本次因此只能让 4 个窗口用 autodim，两块主板仍用 coordinates 保住 82 面判据）。
- 建议：coordinates 模式增加可配置 `deviation_tolerance_mm`（默认保留现在的严格值），并在 `auto` 选策略时先做一次试解，避免"选了又拒"。

---

## 4. 【高】`mirror` 不能镜像特征，只能镜像整个零件/曲面

`MirrorOp` 的校验器直接把特征引用拒掉：

> Toolkit mirror accepts curves, axes, quilts, datum planes, coordinate systems, points or the whole part; a feature reference is not a mirror item and hangs Creo. Workarounds: (1) mirror the whole solid …; (3) to mirror an individual solid boss/cut feature across a plane, recreate the sketch/extrude with coordinates reflected across the mirror plane …

这个限制本身写得清楚（还给了绕行方案，值得肯定），但对"零件内的局部镜像"是硬缺口：本次 TXT 的 Part 1 有 3 组镜像（MIR01–03）共 5 个特征（轴座、⌀23.664、挡块、滚轮座、⌀27.496），只能用坐标展开（x → −100−x）重建。结果是：
- 几何一致（体积/面积/包围盒都对上）；
- 但特征树里**没有镜像节点**，无法通过改镜像面一处而联动五处，与源件的参数化语义不等价。

建议：把"镜像已创建的实体特征"作为独立 op（内部按 body+feature 列表镜像，或至少提供"镜像 body 的指定面组"），至少覆盖"拉伸/切除特征绕平面镜像并合并"这一最常见用法。

---

## 5. 【中】装配缺"自由放置但保留给定变换"的模式

`assemble_component.placement` 只有 `fixed / default / constraints`：
- `fixed` → `ProAsmcompAssemble` 后加 FIX 约束，**变换被保留**（本次采用）；
- `default` → 写 `PRO_ASM_DEF_PLACEMENT`（对齐默认基准面），会把组件吸到装配原点，**给定变换丢失**；
- `constraints` → 需要实体级约束引用。

TXT 的装配是"Part 1-1 固定 + 其余 14 个由配合/位姿定位"。本次只能用 fixed 把 15 个实例全部固定，源件"唯一固定件"的语义无法表达（15 个 FIX 约束，TXT 验收项"固定件一致"因此不成立）。

建议：增加 `placement:"packaged"`（`ProAsmcompPositionSet` 后不加任何约束 / 或用 `PRO_ASM_PACKAGE`），这正是 Toolkit 支持"已定位但无约束"的正常做法。

---

## 6. 【中】多会话处置：`-4` → `force_new_session` → `-36`（两个会话）→ 只能杀进程，而杀进程会连坐

实际时序：
1. 本机已有一个 08:16 起的 Creo 会话，worker 连不上：`toolkit_code=-4 / PRO_TK_BAD_CONTEXT`，`diagnosis=stale_session_needs_restart`；
2. 按提示 `retry=true, force_new_session=true` → 新起一个 Creo（11:37），MCP 自己起的这个会话**也连不上**，报 `toolkit_code=-36`（多个会话匹配），提示"configure creo_session_id"；
3. 而 `session_id` 无法从 PID 推出（工具自己也说明了），`session_id` 又没有提供枚举入口 → 只能关掉旧 Creo；
4. 关掉旧 Creo 时，**新会话一起死了**（Creo 各会话共用 `nmsd` 守护进程），最后两个都没了，只能再 `retry=true` 重起。

建议：
- `-4` 时直接走 `force_new_session` 分支（现在先失败一整轮 120 s 再让人重试）；
- 提供"关闭/重连指定会话"的显式工具，或至少在 `force_new_session` 之后**优先连自己刚起的那个会话**（MCP 知道自己起的 PID/启动时间）；
- 文档注明 nmsd 连坐风险：关旧会话可能带走新会话。

---

## 7. 【中】模型名：空格/大写被拒 + 失败后同名仍占用

- `model_name="Part 1"` → `model_name must be 1-31 characters of lowercase letters, digits and underscores`。源件零件名就是 `Part 1`（TXT 明确"Step / Belt / Box / Part 1 为源文件的零件名（真实名称）"），改名后零件名与源件的对应关系丢失。
- 更麻烦的是：一个新模型的作业**失败并确认清理**（`terminal_effect.managed_model.reason="new_model_cleanup_confirmed"`）之后，同名再建仍报
  `New model name already exists in the Creo session`，
  只能换成 `part1v2`。会话里残留了失败的 `part1` 模型（`creo_list_models` 可见）。

建议：允许空格/大小写（或提供 display name 与 session name 分离）；清理确认后应释放会话内的同名占用。

---

## 8. 【低】包围盒读数系统性偏大，不能用于 0.001 mm 级比对

同一份几何，MCP 读到的 bbox 比源件（SolidWorks 读）大 0.004–0.006 mm：

| 对象 | 源 bbox | Creo 读 | 差 |
|---|---|---|---|
| Belt z 上界 | 18.500 | 18.50624 | +0.00624 |
| Belt y 上界 | 334.494 | 334.49786 | +0.00386 |
| Part 1 y 上界 | 350.892 | 350.89709 | +0.00509 |
| Part 1 z 下界 | −672.741 | −672.74553 | +0.00453 |
| Step 六个分量 | — | — | 0（无差） |

Step 的差为 0，说明不是单位/换算问题，更像 `ProSolidOutlineGet` 的离散步长（或含接缝边）造成的偏大。而体积/面积是准的（1e−7 级）。

建议：capabilities 里注明 bbox 的精度量级，或提供"解析包围盒"选项；否则用户会把 0.005 mm 当成几何误差。

---

## 9. 【信息】面数口径要显式区分 raw / merged

- Creo 把整圆柱面劈成两个半圆柱、整圆边劈成两段半圆弧（+接缝边）：Part 1 `surfaces=92`，`merged_counts.surfaces=80`；Belt 18/18 恰好相等；Box 26/26。
- 现在 `counts_convention` 有说明（很好），但 `inspection_summary.counts.surfaces` 与 `merged_counts.surfaces` 同时出现、没有"哪个用于验收"的指引，很容易与源件的面数对不上。
- 本次 Part 1 用 merged=80 对源 82，差 2 张平面（底梁端面与侧板外表面共面被合并）。这是**内核差面**，不是描述缺项——建议文档明确"跨内核比面数只能比类型+半径分组，不能比张数"。

---

## 10. 值得肯定的地方（别改坏）

1. `sketch` 的 receipt 回显 `origin / normal / u_axis / v_axis` + `profile.material_area_mm2` + `solver` + `geometry_deviation`，这次定位问题几乎全靠它——尤其 `geometry_deviation.shifted_sample` 直接点名了被挪动的实体。
2. `dimensioning="coordinates"`（配 `endpoint_policy` / 端点焊接）能把 6 位小数坐标原样落在模型上：Step 因此做到 V/A/包围盒**逐位相同**（y −6.499…8.501 完全一致），Belt 做到 ΔV<1e−9。这对"按文档精度重建"是关键能力。
3. 失败作业的 `failed_operation` / `native_progress.progress_text`（`1/30 sketch:s_plate start`）定位很快。
4. `plan_file` + sha256 回执、`response_detail="compact"`、`creo_get_job(wait_seconds=…)` 的组合对 30 特征的批量建模很好用。
5. `saved_file_reloaded_and_verified=true` + 重新读回校验，避免了"存了但没生效"的假成功。

---

## 附：建议修复优先级

| 优先级 | 条目 | 理由 |
|---|---|---|
| P0 | §1 草图 v 轴 / 基准面法线显式可控 | 会静默做错零件，且只靠体积才能发现 |
| P0 | §2 coordinates 模式放过构造实体 | 真实草图几乎都有构造几何，直接堵死精度路线 |
| P1 | §4 特征级镜像 | 局部镜像是最常见的零件结构 |
| P1 | §5 `placement:"packaged"` | 影响装配语义表达 |
| P1 | §6 多会话：`-4` 直连新会话 / 不连坐 | 每次冷启动都要人工介入 |
| P2 | §3 coordinates 容差 + auto 选策略 | 影响小特征精度 |
| P2 | §7 模型名规则与占用释放 | 影响可追溯性 |
| P3 | §8 bbox 精度说明、§9 面数口径指引 | 只影响比对方法 |

---

### 复现用的最小片段（问题 1）

```json
{"op":"datum_plane","label":"pl_m30",
 "reference":{"kind":"datum_plane","axis":"y","offset":0},"offset":-30}
```
→ 回读 `creo_inspect_model(section="datum_planes")`：`{"id":621,"normal":[0,1,0],"origin":[0,-30,0]}`
→ 随后 `{"op":"sketch","plane":{"reference":{"kind":"datum_feature","label":"pl_m30"},"origin":[0,-30,0],"u_axis":[1,0,0]}}`
的回执是 `v_axis=[0,0,-1]`（而 capabilities 写的是 `XZ: u=+X, v=+Z, normal=-Y`）。

### 本次作业号（便于查 jobs/ 目录）

| 步骤 | job_id | 结果 |
|---|---|---|
| Step（autodim，−0.001 吸附） | `be753e9eebe74f0a9b6deb749755a523` | 成功，bbox 差 0.001 |
| Step（coordinates，逐位） | `af3a2bdb96b849b5b76f6dde5f51cc9a` | 成功，逐位相同 |
| Belt | `e4b36975fe884d3d84afe5a243eb7b9c` | 成功，ΔV<1e−9 |
| Box 拉伸 + 12 棱 R2 | `e402c0c3f4d74a638d8076f1b75d8e63` / `480f0baffe934eaeb257c59ec1d451cf` | 成功 |
| Part 1 失败①（构造圆） | `b985d8ab1c454bb7a6120aae42e12b90` | 失败：coordinates 拒构造圆 |
| Part 1 失败②（槽弧心 1.2e−5） | `e5fa2920c21045de9f49674acb137f83` | 失败：coordinates 几何改变 |
| Part 1 失败③（无偏移面） | `922f39ad46974a969e3511a8bb84fdfc` | 失败：x=−100 无基准面 |
| Part 1 板 + 窗口 | `3bb0e8a2cfe54638b3b81e7b3cf71786` | 成功，52 面（源 52） |
| Part 1 凸台（方向全反） | `d336a84030384dc5b78b88106c5d7325` | **成功但几何错**：y 到 −517、z 到 +513.874 |
| Part 1 凸台（修正后） | `15e1253276c84fe3974df157bd1afc38` | 成功，80 面 / ΔV 1.4e−5 |
| 装配 15 实例 | `eff48c2956814997ac2f6b372833c00d` | 成功，重心差 0.0293 mm |
