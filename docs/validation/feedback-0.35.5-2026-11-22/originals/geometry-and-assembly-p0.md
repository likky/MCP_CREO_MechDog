# 2026-11-22 · CREO · MCP_CREO_MechDog v0.35.5

## 核心问题：边选择器解析出的 id 无法用于圆角；嵌套装配仍被拒绝；旋转阵准入公差比输入数据精度更严

> 反馈对象：MCP_CREO_MechDog 作者
> 环境：Windows 10 19045 / Creo 10（release_numeric 41）/ MCP v0.35.5
> 场景：用一份纯文本（TXT）说明，从空白文档重建 6 个零件 + 3 级装配，全程只调 MCP。
> 本文只记录**本版新发现、且有作业号可复现**的问题。看门狗与 90 秒恢复预算那两条
> 已单独写在 `2026-11-22_CREO_v0.35.5_核心问题：停滞看门狗误杀长作业…md`，不重复。

---

## 一、结论先行

| # | 问题 | 严重度 | 可复现作业 |
|---|---|---|---|
| A | `geometry_selector(target=edge)` 解析成功但 `ProModelitemInit(...,PRO_EDGE)` 返回 −23，圆角无法用选择器建 | **高**（破坏重建稳定性） | `402bc9152ebe486ab56329fd42d2dd67` |
| B | 装配仍拒绝插入子装配，TXT 规定的三级装配结构无法按原样创建 | **高** | 提交前即被拒，无作业号 |
| C | `rotation_matrix` 准入公差 1e-7 比常见的 6 位小数坐标更严，94 个位姿里 77 个被拒 | **中** | 同上 |
| D | `b_spline` 不能与 `dimensioning="coordinates"` 同用；且该类草图的解析面积静默变成 0 | **中** | `d9c781085e184db0bf13140d3a90d342` |
| E | 同一个整圆的 2 段 180° 半圆边一起做圆角必失败，单独做其中 1 段却等效成功 | **中** | `39cd30d71e62469a9a0c78366e8ae4bb`（失败）/ `eb234c14a0884594ac80ca4eebf95a86`（成功） |
| F | 圆角半径大于相邻角弧半径时，多边一次做圆角必然再生失败，且回执不给任何几何提示 | 低（有等价做法） | `d5ab8eeffa7d43f482d0c4ff086d197a`（失败）/ `9a3584414b3d4ca0a56f0db1b07e529e`（成功） |
| G | **装配被看门狗误杀后，`creo_reconcile_model` 对装配不提供任何动作，模型永久锁死** | **最高**（交付阻断） | `77794599d560446a97f0673e7eebe32a` |
| H | `timeout_seconds` 是否抬高停滞看门狗预算没有定义，调用方无法安全试探 | 中 | 本节 10.1 的 10 个作业 |
| I | 装配没有阵列/实例复用，TXT 的 `LocalLPattern` 只能展开成 269 个零件实例 | 中 | 同上 |

> **G 的代价已量化**：该缺陷让 `33482afa…` 永久报废，唯一出路是新建模型重做。
> 重建为 `aabc94eb…` 用 10 个作业 71 分钟跑完 269 个实例（第十节），
> 这 70 分钟就是"一次看门狗误杀"的实测代价。

---

## 二、问题 A：边选择器能"匹配"却不能用

### 2.1 现象

P03 垫板（`d5ceea7fa05246b6b5fbdafad623bc36`）顶面 8 条棱边做 R12 圆角，
用 `geometry_selector` 给点/圆心+半径，提交作业 `402bc9152ebe486ab56329fd42d2dd67`：

```
failed_stage: execute_round
failed_toolkit_call: ProModelitemInit(board, id, t, &mi)
toolkit_code: -23          # PRO_TK_NOT_EXIST
```

native.log 的事实顺序很关键：

```
line 128  PHASE=execute_round
line 130  OPERATION_INDEX=0 INPUT={"references":[{"edge":{"kind":"geometry_selector",...}}, ×8]}
line 132  PHASE=round:p03_fillet
line 133…278  完整一遍 inspection（ProSurfaceContourVisit / ProEdgeIdGet … 共 88 次）
line 279  ProModelitemInit(board, id, t, &mi)=-23
line 280  BUILD_FAILED=-23
```

即：**选择器匹配阶段跑完了整遍模型遍历**，然后在把匹配结果转成 `ProSelection`
的第一步就失败。所以不是"没匹配上"，而是"匹配出来的 id 不能当 PRO_EDGE 用"。

### 2.2 对照实验（同一模型、同一组边、同一次会话）

把同一组 8 条边改成显式 id（id 来自 `creo_inspect_model(detail="full", section="edges")`）：

```json
{"edge": {"kind": "edge", "id": 67}}   … {"edge": {"kind": "edge", "id": 74}}
```

作业 `d5ab8eeffa7d43f482d0c4ff086d197a`：`-23` 消失，特征树里出现了圆角特征
（feature id 98、type 913）——**说明 id 本身是对的，是选择器→selection 这一段出的问题**。

### 2.3 影响

`geometry_selector` 的存在意义就是"重建后 id 会变，按几何锚点重找"。这条路径不通，就等于
把所有圆角/倒角都锁死在一次性的 id 上：源模型重建一次，所有圆角计划全部失效。
本次 6 个零件里，凡是圆角都只能用显式 id，正是这个原因。

### 2.4 建议

1. 在 `match_geometry_selector` 返回 id 之后、`ProSelectionAlloc` 之前，先做一次
   `ProEdgeInit/ProGeomitemInit` 探活；失败时把 selector 的匹配诊断（命中的 id、
   端点、半径、候选数）一并回传，而不是只回一个 −23。
2. 边应当走 `ProGeomitemInit`（或带 body 的 id 解析），而不是 `ProModelitemInit(...,PRO_EDGE)`；
   仓库里其他地方（如 `validate_hole_planes`）用的就是 `ProEdgeInit((ProSolid)board, id, &edge)`。
3. 若确实存在"inspection 枚举出来的边 id"与"PRO_EDGE 语义 id"不同域的情况，
   请在 `creo_inspect_model` 的输出里显式标注可回填的字段名。

---

## 三、问题 B：嵌套装配仍被拒绝（0.26.0 已报，v0.35.5 仍在）

提交 94 个实例的 Assem2（44×Assem1 + 43×Assem3 + Part5 + 5×Part6 + Part1）时，
`creo_execute_plan` 在**准入阶段**直接拒绝：

```
Nested assembly copying is not yet supported; insert owned part/sheetmetal models
```

这与 `2026-11-18_CREO_v0.26.0_核心问题：装配无法应用旋转位姿且不支持子装配嵌套.md`
的第 2 条是同一问题。**好消息**：那条里的第 1 条（旋转位姿无法应用）本版已修好——
`rotation_matrix` 行向量约定正确，Assem1 的 4 个实例重心实测
(−13.87900, 83.06612, −0.00103)，与目标 (−13.879004, 83.068957, −0.000103) 相差
0.0028 mm。

### 影响与绕行

TXT 的三级结构（Assem2 含 44+43 个子装配）无法照原样建。因为该 TXT 的实例表本身
已把位姿"合成到根"，所以可以按根坐标系把子装配展开成零件实例：
94 → 269 个零件实例（44×4 + 43×2 + 7），位姿用行向量复合
`R = R_child·R_row`、`T = T_child·R_row + T_row`（本文档同目录 `flatten_assem2.py`）。

**但这是有损的**：装配树从 3 级变成 2 级，`Assem1`/`Assem3` 作为可复用单元的语义丢失，
后续若要做子装配级的配合或替换，就没有承载对象了。

### 建议

`assemble_component` 的 `source_model_id` 允许指向 assembly 模型，内部按
"插入子装配 + 固定位姿"实现即可（不需要真正复制几何，Creo 原生支持组件为装配）。

---

## 四、问题 C：旋转阵准入公差比源数据精度更严

`rotation_matrix` 的准入：

> must be orthogonal (R·Rᵀ = I) with determinant +1 within `rotation_tolerance`
> (default 1e-7, at most 1e-7)

而实际工程数据（本例的 TXT）三轴只给到小数点后 6 位。实测 94 个位姿里：

```
max |det(R) − 1| = 1.197e-06
|det−1| > 1e-7 的个数 = 77 / 94
```

也就是说 **82% 的合法位姿会被拒**，而调用方唯一的出路是自己做 Gram-Schmidt——
这就等于让调用方"悄悄改写输入"，与文档里"values are applied exactly as given:
never transposed, orthonormalized or repaired"的承诺正好相反。

### 建议

1. 把默认准入放宽到与 Creo 内核实际接受能力一致（文档说 1e-7 就是 Creo 10 的实测边界，
   那就请在拒绝信息里明确写出"检测到的 |det−1| 值"和"该值对应的角度误差"），
   或者
2. 增加一个显式的 `orthonormalize: true` 开关，让调用方**主动声明**"允许你把我给的三轴
   正交化"，并在回执里回显正交化前后的最大改动量。本例的正交化改动量是 O(1e-6)，
   对应角度误差 < 1e-6 rad，对装配位姿完全无意义，但会决定这个 API 能不能用。

---

## 五、问题 D：`b_spline` 与坐标标注互斥，且让解析面积静默归零

### 5.1 互斥

P06 的回转剖面按 TXT 给的是 4 条 3 次 NURBS（`degree=3`、4 个控制点、节点 `0,0,0,0,1,1,1,1`）。
用 `b_spline` 精确表达时，`dimensioning="coordinates"` 被拒：

```
operations[1]: Coordinate dimensioning supports line/centerline/rectangle/polyline/circle/arc entities
```

改成 `dimensioning="auto"` 才能提交，但 auto 会走 autodim 求解，
回执 `geometry_deviation.max_deviation_mm = 0.00176`——**为了让 API 收下，剖面被挪了 1.76 µm**。

### 5.2 解析面积静默归零（更要紧）

同一作业 `d9c781085e184db0bf13140d3a90d342` 里，sketch 回执同时给出两个互相矛盾的结论：

```
profile.analysis              = "partial"
profile.unsupported_entities  = 4          # 就是那 4 条 b_spline
profile.closed_contour_count  = 0
profile.material_area_mm2     = 0          ← 面积直接变 0
native_section.closed_contours = 1         ← 而原生侧明确说闭合
native_section.entities        = 14
native_section.unsupported_entities = 0
```

`material_area_mm2 = 0` 会让所有依赖它的预检（面积守恒、拉伸体积预估）在**最复杂的那个
剖面上恰好失效**，而且 `analysis="partial"` 只是个软标记，不会阻断。

### 建议

1. 让 `b_spline` 也能走坐标标注（端点+控制点本来就都是坐标，没有欠约束问题）。
2. 解析侧支持 `b_spline` 的面积（de Boor + Green 公式即可）；在支持之前，
   `material_area_mm2` 应为 `null` 而不是 `0`，并让 `analysis="partial"` 触发可见告警。

---

## 六、问题 E：同一整圆的两段半圆边不能一起倒圆

P06 的 +X 端外缘（x=54、R220）在 inspection 里是**两条** 180° 圆弧边
（id 116、174，都报 `origin=(54,0,0) R=220`，各自 0→180°）。

| 提交 | 参考数 | 结果 |
|---|---|---|
| `39cd30d71e62469a9a0c78366e8ae4bb` | 2（116+174） | 失败，`P06_ROUND_R10 status=6` |
| `eb234c14a0884594ac80ca4eebf95a86` | 1（仅 116） | 成功，ΔV = **−29 363.24 mm³** |

关键是 ΔV：整圆 R10 圆角的理论移除量
`2π·220·10²·(1−π/4) = 29 665 mm³`（凸边还要略小），实测 −29 363 与之吻合。
**说明单条 id 116 就已经是整圆**，174 是同一个圆的第二个 id。

### 影响

调用方按"边数=参考数"的直觉去写计划，就会稳定失败；而失败信息（status 6）里
没有任何"你重复引用了同一个圆"的提示。

### 建议

1. 两条半圆边合并成一条整圆边导出；或
2. 在 `references` 里检测同圆重复（同 origin、同 radius、同轴）时给出明确拒绝理由；
3. 圆角再生失败（status 6）的回执里附上 `ProFeatureErrorlist` 的 `err_item_id/error`
   ——现在只有 `failed_features.sample`，缺少是哪条参考边出问题的信息。

---

## 七、问题 F：圆角半径 > 角弧半径时的多边圆角

P03 的顶面是 107×162 四角 R11 的圆角矩形，TXT 要求顶面周边 R12（**12 > 11**）。

- 8 条边一次做（选择器）→ −23（问题 A）
- 8 条边一次做（显式 id）→ status 6
- **只做 4 条直边** → 成功，V = 329 058.743 mm³

而 TXT 给的指纹是 329 058.937 mm³，相对偏差 **5.9e-7**；面 18、边 36 也与 TXT 完全一致。
原因很清楚：R12 的滚球中心轨迹在 R11 角弧上半径变成 11−12 = −1，角弧被相邻两条直边
圆角完全吃掉，**几何上"8 条边"就等于"4 条直边"**。

这不是 MCP 的缺陷，而是**失败信息应该讲清楚**：现在 status 6 只说明"再生失败"，
调用方没有任何线索能推出"角弧被吃掉、请只选直边"。

### 建议

圆角再生失败时，若参考集中存在 `fillet_radius > adjacent_edge_curvature_radius` 的边，
在回执里直接给出这条判断（角弧半径、圆角半径、建议排除的边 id）。

---

## 八、可复用的成功序列（本版实测）

| 零件 | 提交方式 | 作业号 | 耗时 | 体积 vs TXT |
|---|---|---|---|---|
| P04 销轴管 | 2 步单批 | `e34cb9f4b3a74635972eba69739acd3e` | 10 s | 逐位一致 |
| P01 链板 | 6 步单批 | `683aea716ba84b71b1137d07646ccbba` | 17 s | −4.79% |
| P03 垫板 | 2 步 + 1 步圆角 | `26faa04055a74ba1a298f580c90a3cc0` / `9a3584414b3d4ca0a56f0db1b07e529e` | 10 s / 12 s | −6e-7 |
| P02 连接座 | 12 步 + 1 步圆角 | `3b781fc381aa4a32898bf5317abe8873` / `724c3dfa1bc34289bf045baffef78bc2` | 50 s / 19 s | −2.3e-4 |
| P06 驱动齿 | 11 步 + 1 步圆角 | `d9c781085e184db0bf13140d3a90d342` / `eb234c14a0884594ac80ca4eebf95a86` | 80 s / 23 s | −6.4e-5 |
| P05 轮毂 | 27 步拆 7 批 | 见看门狗文档 | 7×400 s | +62%（TXT 数据矛盾，另见 P05 专项文档） |
| Assem1 | 4 实例 1 批 | `ba9aab3e5cbb4fbcbc6bf1f50dc776ad` | 15 s | −1.5e-4 |
| Assem3 | 2 实例 1 批 | `ccbd49219fc140b986cf1640e8119aae` | 11 s | −4.79%（同 P01） |
| Assem2 | 269 实例拆 3 批（展开后） | `a470cb47c498417394a938f54688fbe6` 等 | 530 s/批 | 见报告 |

**结论**：只要绕开 A–D 四条，v0.35.5 的建模主路径是可靠的——单件体积能做到 1e-6 量级，
装配位姿能做到 0.003 mm。问题集中在"锚点/位姿这类需要回填语义的地方"。

---

## 九、问题 G（本次最严重）：装配被看门狗误杀后没有任何恢复动作

### 9.1 事实链

Assem2 的第 2 批（90 个实例）作业 `77794599d560446a97f0673e7eebe32a`：
530 s 时完成 90/90（第 1 批），本批在第 60 个实例附近被终止：

```
status:      unknown_outcome
message:     Native worker log stopped growing for 600 s (budget 600 s)
stall_watchdog.log_bytes:            0          ← 判活信号
native_progress.log_bytes:  3 862 512          ← 真实进度，3.8 MB
native_progress.stage:      assemble_component:assem1_32_part4_1
termination: 已终止 PID 13912 / 24032 / 19112（父子链）
```

即**作业一直在写日志，但看门狗看的是另一个恒为 0 字节的文件**（问题 A 的老病根）。

### 9.2 致命之处：装配没有 reconcile 路径

按规范调 `creo_reconcile_model(mode="inspect")`，返回的 7 个动作**全部 unavailable**：

```
restore_baseline : Assembly/drawing reconciliation is not supported; preserve component ownership
accept_saved     : 同上
accept_live      : 同上
abandon_new      : 同上
ack_no_mutation  : Only a failed model can acknowledge zero mutation     （status 是 unknown_outcome）
ack_failure      : Model still owns a pending or recovery job           （pending_job 就是被杀那个）
confirm_panel_closed : No resident panel guard holds the Creo session
```

而基线文件是**完好且校验通过**的：

```
baseline.path   = …\assem2_v355.asm.2   441 656 bytes
baseline.verified = true
sha256 与 rev 1 保存时一致（88b6b0e3…5efe5）
runner / worker 均已 stopped（windows_error 87）
```

结论：**一个内容完好、只差一次"丢弃未提交改动"的装配，因为没有任何可用动作而永久锁死**。
零件遇到同样情形可以 `abandon_new`（本次 P05 就成功过，8.7 s），装配连这条路都没有。

### 9.3 影响

- 装配件的单次作业存在**硬 600 s 上限**（与 `timeout_seconds` 无关——那只是执行器预算，
  看门狗是另一套），而装配的插入成本随组件数近似线性增长：
  第 1 批 90 个实例 530 s（5.9 s/个）；第 2 批到第 60 个就已 600 s（10 s/个）。
- 于是"组件数 × 单件成本 > 600 s"是**必然**撞上的墙，而撞上就等于模型报废。
  94 个顶层实例 / 269 个展开实例的装配，在 v0.35.5 上无法一次建成。

### 9.4 建议（按优先级）

1. **给装配开放 `abandon_new`**：它不需要重建几何，只需要"丢弃未提交改动、把 revision
   退回基线"。`preserve component ownership` 这个理由对 abandon 不成立——abandon 恰恰是
   最保守的选择（什么都不采纳）。
2. **看门狗改成看 `native_progress` 的那个文件**（或至少取两者最大值）。这一条修好，
   本节和上一份文档里的绝大多数失败都会消失。
3. 装配作业支持"分批提交 + 断点续插"：允许 `expected_revision` 递增式追加，
   并允许把一个 269 实例的计划拆成 N 个作业**共用同一份 checkpoint**，
   而不是每批都重跑一次全量 verify。
4. 若短期做不到 1–3，请在 `creo_execute_plan` 的准入阶段按"组件数 × 单件成本"估算耗时，
   超过看门狗预算时**提前拒绝**并提示"请拆成每批 ≤ N 个实例"，而不是让作业跑到 600 s 被杀。

## 十、问题 G 的实测补充：绕过锁死的完整成本

锁死的模型 `33482afa0f154472ab18204c6d59d59b` 始终无法解锁（`ack_failure` 被
`Model still owns a pending or recovery job` 拦住，`pending_job` 指向那个已死的作业，
`creo_cancel_job` 对终态作业只会原样返回）。**唯一出路是新建模型、从第 1 个实例重做。**

本次据此重建为 `aabc94eb20e84a67b1bf1bcb4d97bc24`（`assem2_v355b`），共 **10 个作业、
71 分钟**，最终 269/269 实例、`saved_file_reloaded_and_verified: true`、rev 11。
也就是说：**一次看门狗误杀的代价约 70 分钟纯机时**，这应作为该缺陷的严重度标尺。

### 10.1 实测插入成本（5 个独立批次拟合）

| 批次 | 区间（已有→新增） | 实例数 | 实测耗时 | 平均 s/个 |
|---|---|---|---|---|
| b01 | 0 → 90 | 90 | 572 s | 6.36 |
| b02 | 90 → 115 | 25 | 309 s | 12.36 |
| b03 | 115 → 145 | 30 | 415 s | 13.83 |
| b04 | 145 → 170 | 25 | 416 s | 16.64 |
| b05 | 170 → 192 | 22 | 431 s | 19.59 |
| b06 | 192 → 210 | 18 | 393 s | 21.83 |
| b07 | 210 → 227 | 17 | 404 s | 23.76 |
| b08 | 227 → 242 | 15 | 389 s | 25.93 |
| b09 | 242 → 256 | 14 | 393 s | 28.07 |
| b10 | 256 → 269 | 13 | 390 s | 30.00 |

拟合：**t(N) ≈ 0.10·N + 1.9 秒/实例**（N = 装配中已有零件实例数），
即单件插入成本与"装配里已经有多少零件"成正比，到 N=269 时约 28.8 s/个。
这是"每批必须 ≤ ~420 s"的直接原因：一个不解锁的墙 + 一条线性上涨的成本曲线。

### 10.2 一个可复现的切批判据

设已完成 Ns 个、本批提交到 Ne 个，则本批预计耗时

```
T(Ns, Ne) = a/2·(Ne² − Ns²) + b·(Ne − Ns)      a = 0.20, b = 1.9（实测标定）
```

把 `T ≤ 420 s` 作为硬约束反解 Ne，就能保证每批都在看门狗预算内跑完。
本脚本已落地在 `_a2b/make_next.py`（可重入，按最新实测系数重算下一批）。

### 10.3 重建结果与验证

| 指标 | TXT 目标 | CREO 实测 | 偏差 |
|---|---|---|---|
| 零件实例数 | 94 顶层（含 3 个阵列实例） | 269 展开实例 | 口径不同，见问题 I |
| 体积 | 124 864 326.4 mm³ | 129 331 528.19 mm³ | **+3.58%** |
| 重心 | (1275.469, −190.148, −0.205) mm | (1228.371, −183.146, −0.212) mm | Δx **−47.10 mm** |

偏差**不来自装配**：用同一份 269 个位姿矩阵在 Python 里做的解析质量属性预测为
`129 331 528.2 mm³ / (1228.371, −183.146, −0.212)`，与 CREO 实测**逐位一致**。
也就是说 269 个变换矩阵全部正确，偏差 100% 来自零件本体：
P05 比 TXT 指纹大 +4 788 589 mm³（TXT 自身 D502/D504 矛盾，另见
`2026-11-22_P05数据自洽性核对.md`），减去 P01 少 3 498.74×87、P02 少 186.17×44 等，
正好是 +4 467 202 mm³，与实测差值吻合。

## 十一、问题 H：`timeout_seconds` 与停滞看门狗的关系没有定义

`creo_execute_plan` 的 `timeout_seconds` 文档写的是"抬高本作业的执行器预算（60–7200），
默认 600"，但**没有说明它是否同时抬高 `stall_watchdog` 的预算**。本次每批都传了
`timeout_seconds: 1800`（回执 `timeout_source: "job"`），但因为每批都在 420 s 内跑完，
**没有触发看门狗，因此无法验证**——这正是问题所在：用户没有任何办法在"不报废一个装配"
的前提下测出这条边界。

建议：在 `creo_get_job` 的 `running` 阶段就回显 `stall_watchdog.budget_seconds`
（现在只有 `stalled: true` 时才出现），并在 `creo_execute_plan` 回执里直接给出
"本作业的看门狗预算 = X s"，让调用方能据此决定批大小。

## 十二、问题 I：装配没有阵列/实例复用，TXT 的 LocalLPattern 只能展开

TXT 第 228/235 行明确写：Assem2 的 94 个顶层实例里有 3 个是 `LocalLPattern1`
（种子 Part6-1、方向 +X、间距 500、实例 4）生成的阵列实例。而 `creo_assemble_component`
与 `assemble_component` 操作只接受"一次一个零件实例 + 显式变换"，
**没有阵列/镜像/复制已有实例的能力**，所以只能把 94 个顶层实例（含 44 个 Assem1、
43 个 Assem3，而嵌套装配又被问题 B 拒绝）展开成 269 个零件实例逐个插入。

后果是三重放大：组件数 94 → 269（×2.86）、每个实例一次 Toolkit 装配调用、
再叠加 10.1 的线性成本 → 71 分钟。若支持"对已插入实例做线性/圆周阵列"，
Part6 的 3 个阵列实例可省 2 次插入；若再支持嵌套装配（问题 B），
Assem1/Assem3 的复用能把 269 降回 94，成本降到约 1/8。

## 十三、问题 J：多半径圆弧组成的闭合轮廓无法通过准入（`arc_inconsistent` 无解）

**场景**：TXT 的 SK P05-01 是轮盘毛坯轮廓，40 条圆弧首尾相接，
半径按 R22.5 / R32.037078 / R44.046123 三种交替，围成 R218.506…261.703 的齿形外缘。
解析面积 175 267.447 mm²，×252 = 44 167 397 mm³，
与 SolidWorks 附录 G-2 的 `Boss-Extrude1 = 44 167 465.85` 只差 0.00016%——数据本身没问题。

**准入直接拒绝**（无作业号，准入阶段就退）：

```
operations[4]: Solid extrude profile rejected: detected 1 closed contour(s), 0 open contour(s)
and 40 curve entities; [near_tolerance] endpoints joined only by the closure tolerance
(ar02/ar04) near (78.5702268, -489.241832) mm.
...
Weld/snap cannot fix this profile: 40 join(s) are refused for ['arc_inconsistent']
(ar23/ar24 gap 3.464e-08 mm (arc_inconsistent); ar07/ar08 gap 4.733e-08 mm ...).
Correct the geometry - both arcs on one circle, a bound that allows the move,
or separate contours - instead of relying on endpoint welding.
```

**为什么这是无解的（源码级）**。`endpoint_welding.py` 里：

```python
gap = _distance(first["point"], second["point"])
if gap <= 0.0 or gap > CLUSTER_TOLERANCE_MM:
    # An exact join is already one point, not a candidate weld.
    continue
```

只有 `gap` **严格等于 0** 才跳过候选。而两条圆心/半径都不同的弧，
端点由 `C + R·u(θ)` 算出，浮点结果**不可能逐位相同**；
只要 `gap > 0` 就成了候选，再被 `_arc_consistent`（要求"两弧同圆"）判为
`arc_inconsistent`，属于 `BLOCKING_REASONS`，整份计划被拒。
`snap_endpoints` 也救不了：`_snap_entities` 对 arc/arc 对直接
`return "arc_pair_not_snappable"`。

**影响面**：所有齿轮、花键、链轮、凸轮、齿形带轮的外轮廓都是"多半径弧交替"，
在当前校验器下**一条都建不出来**。这不是容差问题，是判据把正常几何判成非法。

**建议**（任一即可）：
1. `arc_inconsistent` 只在 `gap > 1e-9`（真正的几何不一致）时触发；
   `gap ≤ 1e-9` 视为已重合，直接跳过——两条不同圆的弧端点本来就该差 1e-8 级。
2. 允许"只移动端点、不改圆心与半径"的焊接：把端点重设为两弧的交点或中点，
   圆弧形状变化 1e-8 mm，远小于任何工程公差。
3. 至少在错误信息里明确写"本版本不支持多半径弧闭合轮廓"，
   不要让调用方误以为调容差就能过。

---

## 十四、问题 K：`b_spline` 端点存在 2.3e-13 mm 散布时被内核判为未闭合

**绕行尝试**：既然 arc 走不通，改用 40 条**有理二次 Bézier** 精确表示这 40 条弧
（`degree=2, knots=[0,0,0,1,1,1], w1=|N−C|/R`，N 为弦中点）。
校验：每条曲线采样点到原圆心的径向偏差 ≤ **9.4e-07 mm**，
40 个接缝在 JSON 里**逐位相同（gap = 0.000e+00）**，解析面积 175 247 mm²（误差 −0.011%）。

**准入通过，内核拒绝**（`5ef85f509e8a4027b766ff774c8b4a41`）：

```
failed_stage: execute_extrude
failed_toolkit_call: ProFeatureWithoptionsCreate
Extrude feature creation failed (ProFeatureWithoptionsCreate=-1).
Detected native section: 1 closed contour(s), 1 contour(s), 40 entity(ies), 0 open end(s).
The section has no open ends, but its endpoint clusters spread up to 2.30707657e-13 mm
at the diagnostic clustering tolerance: endpoints joined only by that tolerance are
not necessarily welded by the kernel.
```

**要点**：2.3e-13 mm 是 double 的极限，比任何 CAD 容差小 7 个数量级。
问题不是"点差得远"，而是 **40 条独立 b_spline 各自持有自己的端点，内核没有把它们合并成共享顶点**。
Creo 原生交互式画 40 条曲线并让端点重合，会自动捕捉成一个点；
走 Toolkit 逐条写 `Pro2dBSplinedef` 时这个捕捉不会发生。

**建议**：
- 当一份草图的端点形成单一闭合链、且相邻端点距离 < 1e-9 时，
  MCP 侧应**先在草图层生成共享顶点**再写实体（`ProVertexAdd` + 让曲线引用它），
  而不是把"是否焊接"完全交给内核的 epsilon。
- 若本版本做不到，请在错误里给出明确结论"多实体闭合轮廓在本版本仅支持 line/arc 混合，
  b_spline 序列不支持"，避免调用方反复试。

---

## 十五、问题 L（连锁最严重）：高边数零件让"看门狗杀作业 + 恢复也超时"形成死锁

**背景**：为了逼近齿形毛坯，把 40 条弧离散成 **1307 点、7 条 polyline**
（3° 步长，接缝 gap 严格 0，解析面积误差 −0.0026%）。
毛坯建成且验证通过（`16ce870d315c4a62a6ed5f0e2bb85379`）：

```
volume_mm3 = 44 166 267.588    (目标 44 167 397 / SW 44 167 465.85，差 −0.0027%)
counts = {surfaces: 1302, edges: 3900, bodies: 1}
```

**连锁一：后续每个草图都被边数拖死。**
下一批只有 3 个草图 + 3 个切除（Ø100 孔、两侧矩形腔），
600 s 时被杀（`4ed0ae65b18e41f883921d38659320a3`）：

```
stage: unknown_outcome
stall_watchdog.log_bytes: 0
native_progress.log_bytes: 4 266 915        ← 真实进度是 4.2 MB
native_progress.stage: sketch:p05_cavity_pos
native_progress.dominant_tail_line: ProEdgeIdGet(edge, &id)=0  (200 次)
```

前 4 个操作（孔草图/孔切除/第一侧腔草图/第一侧腔切除）已完成，
死在**第二个腔草图**——每次草图求解都要对全模型 3900 条边做 `ProEdgeIdGet` 推理。
同样的 3 个草图在 R240 正圆毛坯上只要 99 s（v357 实测 a 批 11 步 99 s）。

**连锁二：恢复也超时，模型永久锁死。**
`creo_reconcile_model(mode="inspect")` 显示 `restore_baseline.available = true`、
基线 `verified: true`、runner/worker `stopped: true`，于是发起恢复
（`21181c2de914476eb24f77ba5076a0b4`），结果：

```
status: unknown_outcome
failure_phase: native_worker_started
reason: native_outcome_unconfirmed
checkpoint.completion_stage: recovery_phase_timeout
native_progress.stage: recovery_verify_source
native_progress.log_age_seconds: 491
native_progress.dominant_tail_line: ProEdgeIdGet(edge, &id)=0  (88 次)
```

**恢复路径为了"验证源文件"重新打开模型并做全量检查，又被同一个高边数拖死。**
于是：作业被看门狗杀 → 恢复被同一个原因拖死 → 模型既不能 `restore_baseline`
也不能 `ack_failure`（inspect 给的是 "Model still owns a pending or recovery job"）
→ 只能新建模型重来。**v358 就是这样报废的（连同已成功验证的 44 166 267 毛坯）。**

**建议**：
1. `restore_baseline` 只需要校验磁盘文件的 sha256（基线已知、已验证），
   **不应重新打开模型做全量 inspect**。当前实现把一个 O(边数) 的操作塞进 115 s 的恢复预算里。
2. `stall_watchdog` 改看 `native_progress.log_bytes`（问题 G 已提，此处是第二个受害者）。
3. 在 `creo_execute_plan` 准入阶段按草图实体数与当前模型边数估算草图求解成本，
   超预算时提前拒绝并提示"请降低离散点数"或"请拆批"。
4. `ack_failure` 的可用条件应放宽：当 `pending_job` 本身已是 `unknown_outcome`
   且磁盘基线 sha256 与记录一致时，允许直接 ack，不必等"recovery job 结束"——
   因为 recovery 可能永远结束不了。

---

## 十六、P05 体积归因（对作者最有用的一条）

P05 的 +62% 曾被归因为"TXT 自身矛盾"。完整核算后结论更精确，**两层原因，且第二层是可修的**：

**第一层（我的建模选择）**：v357 把环形内腔按附录 B 的 SK P05-03 `loop2` 建
（r 66.791…269.472，z 0…−90，下边界为二次样条），实测切除 25 158 078 mm³。
以 SW 的 `Cut-Revolve1+Mirror1 = 32 332 934` 为裁判，用 Pappus 定理核算三种剖面：

| 剖面 | 预测切除 | 腔后体积 | 对 SW 的偏差 |
|---|---|---|---|
| loop2 原样（深 90） | 30 833 370 | 11 354 823 | +15.2% |
| loop2 加深到 101 | 34 601 893 | 7 586 300 | −23.0% |
| **矩形环 r66.8→270，z 0…−101** | **32 572 646** | **9 615 547** | **−2.4%** |

**矩形环深 101 与 SW 只差 0.74%（32 572 646 vs 32 332 934），是唯一对得上的读数。**
也就是说 D504 里"腔底 z=±90"是错的，正确的是"轴向范围 z ∓37…∓101"中的 **101**，
且腔是**平底环**而不是带样条渐变的环。

**第二层（TXT 的表述矛盾，需作者修）**：
1. D504 同时给出"腔底 z=±90"与"z ∓37…∓101"，两者互斥（90 ≠ 101）——实测应以 101 为准。
2. D504 说"外边界半径 184.2"，但附录 B 的 loop2 外边界到 269.472（超出 R240 共 29.47 mm）。
   184.2 只是样条终点的半径，不是腔的外边界。
3. D501 说"外径 480、外缘为 Ø480 圆柱面"，但附录 B 的 SK P05-01 外缘包络到 R261.703。
   若按齿形轮廓建模，毛坯体积 44 167 397（与 SW 一致）；若按 Ø480 正圆，是 45 600 846。
   两者在"内腔切穿外缘"之后最终体积只差 2.9%，但**外缘形状不同**（前者保留 10 个凸叶的薄壁，
   后者外缘被完全切平）。需作者明确外缘到底是圆柱还是齿形。
4. D502 说"24 段圆弧交替构成 12 组工字形减重腔的外边界"，但附录 B 的 SK P05-01
   是 40 条弧、10 重旋转对称（36° 周期），12 重对称检验 0/40 通过。


### 16.1 实测验证（v359 = `2de9826a4cd549549b74c769b58ffc47`，rev 8）

按上表的"矩形环 r66.8→270，z 0…−101"重建，逐里程碑实测：

| 里程碑 | v359 实测 | 预测 | SolidWorks |
|---|---|---|---|
| 毛坯 Ø480×252 | 45 600 846 | — | 44 167 465.85（齿形） |
| Ø100 孔后 | 43 621 643 | — | 42 188 262.48 |
| **两侧环形内腔后** | **9 900 328.6** | **9 901 000** | **9 855 328.00** |
| 窗阵列 + 10×Ø24 | 7 704 157.9 | — | 7 795 697.42 |
| 长圆孔 | 7 396 923.3 | — | 7 627 985.78 |
| **终值** | **7 481 205.2** | — | **7 728 342.87** |
| 对 TXT 指纹 7 725 058.863 | **−3.157%** | | −0.043% |

**腔后 9 900 328.6 与预测 9 901 000 只差 671 mm³（0.007%）**，
证明"矩形环 + 深 101"这个读数就是 TXT 的原始意图，也证明
`creo_execute_plan` 的 `revolve(kind=cut, 360°)` 本身精确无误。

v357（用 loop2 深 90）在同一步是 18 463 562 —— **+62% 的 8.56e6 全部来自这一个剖面选择**，
与 MCP 的建模能力无关。这条要写清楚，避免被误读成"CREO 建不了 P05"。

### 16.2 仍然与 MCP 能力有关的部分（占残余偏差的一部分）

v359 的 −3.16% 不是纯数值误差，其中一部分来自**缺失的 12 组工字腔**（问题 J）：
- TXT 的 P05 重心 y = −269.9046，比轮心 −270.076 偏 0.171 mm；
  v359 的重心 y = −270.076287，严格对称 → 缺一个不对称减重结构。
- 该结构就是 D502 的 12 组"工"字腔，其边界正是 SK P05-01 的 40 条弧。
- 40 弧在 v0.35.5 下三条路全堵（arc_inconsistent / b_spline 未焊接 / 折线把模型拖死），
  只能退回 Ø480 正圆毛坯，腔的边界一起丢掉。

**所以 P05 的正确归因是三层**：
1. **我的剖面选择 → 8.56e6（+53 个百分点）**，已修，纯建模层面；
2. **MCP 的弧轮廓准入 → 12 组工字腔（残余偏差的一部分 + 0.171 mm 重心偏移）**，未修，需作者；
3. **TXT 的 D501/D504 互斥（腔底 90 vs 101、外缘圆柱 vs 两片薄缘）→ 需作者**，否则任何实现都要在两种形状里二选一。


---

## 十七、问题 M：装配体里换零件版本没有 replace_component，只能删了重插，配合关系随之丢失

### 17.1 场景

P05 从 v357（体积 12 513 648，+62%）修正为 v359（7 481 205.2，−3.16%）之后，
需要把已经建好的 Assem2（269 个零件实例）里那 1 个 P05 实例换成新版本。

`creo_list_components` 能定位到它（`part5_1_part5_1` → `source_model_id: 47becd82…`），
但**没有任何工具能把这个组件的源模型就地切到另一个 model_id**。
`catia_replace_component` 是 CATIA 侧独有的；CREO 侧只有：

- `creo_remove_component`（删）
- `creo_assemble_component`（插）

### 17.2 实测代价（可接受，但语义有损）

| 步骤 | 作业 | 耗时 |
|---|---|---|
| remove | `fd8524ee24e048ada97689cf8bde2ed6` | 108 s |
| assemble（同位姿 fixed） | `7b63e344227b447fbb34759fc47f1aa8` | 152 s |

体积校验闭合：删除掉 12 513 647.6（= 旧件体积），插回涨 7 481 205.22（= 新件体积），
说明"删 + 插"这条路在数值上是干净的。

**但 `fixed` 位姿能靠 translation/rotation_matrix 复原，配合关系不能。**
本例的 P05 实例恰好是 `placement: fixed`，所以无损；若换成 mate/align/insert 约束的组件
（TXT 第 249 行记录 Assem2 有 26 条真实配合，覆盖 Part5-1、Part6-1/-5、Part1-5），
`remove_component` 会把该组件的约束一起带走，而 `assemble_component` 需要调用方
把每条 constraint 重新描述一遍 —— 调用方手上通常只有装配后的位姿，没有原始约束。

### 17.3 建议

1. 增加 `creo_replace_component(model_id, expected_revision, component, source_model_id,
   source_revision?)`：保持组件名、变换与约束条目不变，只替换底层几何快照。
   内核侧对应 `ProAsmcompReplace`。
2. 若短期不做替换，至少让 `creo_remove_component` 在删除前回吐该组件现有的
   `constraints` 数组（当前 `component_changes` 只报 `removed` + `feature_id`），
   使调用方能原样重放给 `assemble_component`。
3. `creo_list_components` 的 `fields` 投影一旦选定就被 cursor 绑定，换个 fields 再翻页
   会直接报错且不说明原因（本次实测：传 `["label","source_model_id","translation"]`
   配原 cursor 直接 `Error executing tool`）。建议在错误里回一句
   "cursor 与 fields 不一致，请重新从头查询"，而不是空错误。

### 17.4 附带发现：装配体积是零件体积的线性叠加，可当替换校验器

`124 299 085.81 − 116 817 880.59 = 7 481 205.22`，与 v359 的 7 481 205.225 差 0.01 mm³。
同密度、无干涉时这条恒等式成立，可用来判断"某零件的换版是否彻底、有无残留实例"，
比逐个 `list_components` 比对更省事。

---

## 十八、问题 N：恢复预算 90 s 让 ≥6.4k 边零件的 `restore_baseline` 永久失效，且 `live.loaded` 与 `list_session_models` 互相矛盾

### 18.1 触发链

P05 v360 终态正常（rev 12、1163 面 / **6428 边**、`.prt.13` 4 240 265 B、
`saved_file_reloaded_and_verified: true`）。
随后 `creo_export_model(format=jpeg)` 想渲染一张预览图：

| 作业 | 结果 |
|---|---|
| `ead9fd1992f84c8eb42666a606b1aa2c` | `failed`，`WinError 1450`（系统资源不足），未落盘 |
| `8e7d87dda7914db68e14a89eb53e511d` | `unknown_outcome`，模型被 pending_job 占用 |

`WinError 1450` 出现在渲染阶段，模型未被改动（`model_unchanged` 未被写成 false），
但占用已经生效 —— **一个只读的导出失败，把可编辑的模型锁住了**。

### 18.2 `restore_baseline` 在这个量级上必然超时

作业 `dc55477101f5480a9e2d1243168a7a2c`：

```text
completion_stage: recovery_phase_timeout
failure_phase:    native_worker_started
native.log:       647 349 B
dominant line:    ProEdgeIdGet(edge, &id)=0   ×146
```

`budgets`: `native_phase_seconds: 90`、`outer_seconds: 115`。
90 s 内只枚举了 **146 条边**（0.62 s/条）→ 6428 条边需 **约 66 min**。
所以 `restore_baseline` 在这个模型上不可能成功，而它是 `actions` 里**唯一** available 的动作。

同一模型的普通作业不受影响：`s06` 的 verify 阶段跑了 407 s、`s12` 473 s 都正常完成。
**同一份 `verify_model`，普通作业给的预算够，恢复给的不够。**

### 18.3 死锁的关键：两条通道对「模型在不在会话里」的判断相反

`restore_baseline` 超时后，`creo_reconcile_model(mode=inspect)` 给出：

```json
"live": { "loaded": false, "origin": "", "owned": false }
"accept_saved": { "available": false, "reason": "Required baseline/candidate/owned healthy live evidence is unavailable" }
"accept_live":  { "available": false, "reason": "同上" }
"ack_no_mutation": { "reason": "Only a failed model can acknowledge zero mutation" }
"ack_failure":     { "reason": "Only a model whose last job ended in failure can acknowledge a failure" }
```

但同一条 Toolkit 连接上：

```json
// creo_list_session_models
{ "name": "P05_V360", "model_type": "part", "modified": false,
  "has_saved_origin": true,
  "origin": "...\\output\\p05_v360.prt.13",
  "model_id": "9ea0fdd97c234775b2c6682877090fd4" }
```

模型**在会话里、未修改、受管 id 可证明**；`native.current_model` 是 `""`（没有窗口激活它）。
`live.loaded` 显然只查 `ProMdlCurrentGet()`，而不是「会话里有没有这个模型」，
于是一个**存在且健康**的模型被判定为不存在，所有能解锁的动作都被这条判据否掉。

同时 `creo_open_file` 也进不来：`SESSION_NAME_CONFLICT: a part model with this name is already in the Creo session`。
**三个工具互相锁死**：list 说在、live 说不在、open 说重名。

### 18.4 建议

1. `native_phase_seconds` 不要用固定 90 s：按 `edges × 实测单边耗时` 估算，
   或允许 `restore_baseline` 走与普通作业相同的 verify 预算（本例需要 400 s 量级）。
2. 恢复路径可跳过全量 verify：reload 后只校验 `sha256 + 文件大小 + 特征数 + 体积`（四个数都是已知的），
   没必要逐条 `ProEdgeIdGet`。本例 `.prt.13` 的哈希在 `baseline.identity` 里早就验过了。
3. `live.loaded` 改成「会话中存在同名同类型的受管模型」而不是「是否为当前窗口模型」；
   或至少在 `live.loaded=false` 但 `list_session_models` 命中时，提供 `accept_live(force_activate=true)`，
   把该模型设为当前窗口再 adopt。
4. `creo_open_file` 遇到同名冲突时，若命中项的 `model_id` 与本记录一致，应返回「已在校验中，请用 reconcile」
   而不是让调用方去关窗口。
5. 只读导出（`export_model`）失败不应产生 pending_job 占用；它不改模型，占用没有意义。

### 18.5 现状

P05 v360 的**零件文件完好**（`p05_v360.prt.13`，sha256 `3fbeebd6…`，1163 面 / 6428 边，
7 374 502.8 mm³），只是 MCP 的模型记录不可再用；装配里的 P05 仍是 v359，换版被这条死锁挡住。

### 18.6 追加实测：纳管复制与换版也被同一个瓶颈挡住（2026-11-22 22:33–22:39）

| 动作 | 作业 | 结果 |
|---|---|---|
| `creo_adopt_current_model(apply)` 复制该零件 | `2e7d1e94799c40f5a9ffcf8d7b188630` | **115 s 超时**，`native.log` 724 813 B，`ProEdgeIdGet` ×145，`adoption_unconfirmed` |
| 装配引用它 | — | `Every component source must be ready with no pending mutation` |

结论：**6428 边的零件在 v0.35.5 下不可恢复、不可复制、不可换版**。
`ProEdgeIdGet` 约 0.6 s/次，任何 O(edges) 的全量枚举都要 60 min 量级，
而所有相关预算（恢复 90 s、纳管 115 s、导出 115 s）都在 2 分钟以内。

顺带一个小问题：`abandon_new` 清不掉这个 `adopt_pending` 记录，理由是
`Recovery refused: session model origin is not owned` —— 而它自己的 origin
正是 adopt 刚生成的那个受管目录（`models/7f481d3e…/output/`）。
会话里对应的 `P05_WHEEL_FINAL` 已用 `creo_erase_session_models` 清掉，仍拒。
建议：`abandon_new` 不该依赖会话模型的 origin 归属，它本来就是要丢弃这份未完成的副本。
