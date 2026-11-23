# MCP_CREO_MechDog 0.35.8 — 验证阶段静默挂起 + 恢复路径 90 s 硬限，把模型锁死到无法再提交任何计划

> 环境：Creo Parametric 10.0.0.0（release_numeric 42）、MCP 0.35.8、worker `build/creo_worker.exe` sha256 `14ef21829c82…d285b066`。
> 复现日期：2026-11-23。模型：`frigate_v4`，`model_id = df7f74bf5e424dbeb00605e218be89ad`，**474 特征 / 815 面 / 2612 边 / 1 body / 4 quilt**，体积 5,408,183,980.770802 mm³，`revision 87`。
> 场景：整船按自然语言 TXT 逐特征重建，本批要建的是 5 条「斜基准面草图」特征（B045–B047 / B104 / B105）。

## §0 结论与优先级

| 编号 | 问题 | 级别 | 后果 |
|---|---|---|---|
| P0 | 恢复路径 `RecoveryDeadline` 硬编码 90 s，包住整条 generic run（含一次全量巡检） | **封锁** | 模型只要巡检 >90 s，`restore_baseline` 永不成功；模型永久停在 `unknown_outcome`，**任何计划都提交不了** |
| P1 | 保存重载后的全量遍历（`verify_model_compare` / `verify_model_assertions`）**静默挂起**，无进度日志 | **阻断** | 作业落 `unknown_outcome`，一次正常建模被丢弃；3 次提交 3 次挂，挂点还各不相同 |
| P2 | 三点基准面草图拿不到第二条参考，失败被误报成 `AutodimensionSketch failed with code -1` | 阻断（已有绕法） | 同一配方 1 成 4 败，报错点不是根因点 |
| P3 | 斜基准面上 `cut` 成功但去料量远小于解析值（0.27% / 54.17%） | 中 | 切除切在空气里，几何与 TXT 不符，且没有任何告警 |
| P4 | `coordinates` 在四线矩形上只落 3 个尺寸 | 低 | 「coordinates = 完全约束」不成立 |
| P5 | 客户端先退出会带走 detached runner | 低（运维） | 作业变孤儿，只能走 reconcile |

**一句话**：P1 让我丢了一次本来已经建好的特征，P0 把「丢一次」变成「模型再也用不了」。P0 是本次必须先修的那一条。

---

## §1 P0【封锁级】恢复路径 90 s 硬限 → 模型永久锁死

### 1.1 现场

P1 的挂起把模型推进 `unknown_outcome`。按工具提示走 `creo_reconcile_model(restore_baseline)`，结果恢复作业自己也失败：

| # | 恢复 job | 触发时刻 | `native_checkpoint.json` | `phase_budget_seconds` | `native.log` |
|---|---|---|---|---|---|
| 1 | `0625dbaedda34d57a7b3c05d84459637` | 09:25 | `recovery_phase_timeout` | 90.0 | 18,445 行 |
| 2 | `c81cbe3a6dd048548e38963b7415ca1c` | 09:32 | `recovery_phase_timeout` | 90.0 | 18,445 行 |
| 3 | `307416806d0d45ea8a890890c8899fbe` | 10:18（**Creo 重启后**） | `before_disconnect`（被拒，见 §1.3） | — | 11 行 |
| 4 | `e984795c00934701997ee02a480d2d92` | 10:19（同上，重试） | `recovery_phase_timeout` | 90.0 | 18,442 行 |

四次全部 `status = unknown_outcome`、`stage = reconciliation_unconfirmed`，`message = Recovery outcome is unconfirmed; reservation retained; ...; protection retained`。

**对照（关键）**：同一条恢复路径在 08:43 曾**成功**过一次——job `f1bb9f6b3516493cb0c3e2aa30e152cb`，`created 08:42:07 → finished 08:43:41`，总耗时 94 s，`native_checkpoint.json = {success: true, completion_stage: "before_disconnect"}`。当时这个模型是 **410 特征**。现在 474 特征，遍历量只多约 4%（17,662 行 → 18,44x 行），就越过了 90 s 红线。

### 1.2 根因（源码级）

```cpp
// native/recovery_deadline.h:11
class RecoveryDeadline {
    ...
    explicit RecoveryDeadline(const std::wstring &job, DWORD budget_ms = 90000) {
        ...
        if (WaitForSingleObject(event, budget_ms) == WAIT_TIMEOUT) {
            publish_native_json(job + L"\\native_checkpoint.json",
                {{"success", false},
                 {"delivery_complete", false},
                 {"completion_stage", "recovery_phase_timeout"},
                 {"phase_budget_seconds", budget_ms / 1000.0}});
            ExitProcess(31);          // 硬杀；不写 native_result.json
        }
```

```cpp
// native/generic.cpp:9207
if (request.contains("reconciliation")) {
    recovery_deadline = std::make_unique<RecoveryDeadline>(job);   // 90 s，不可配置
}
```

要点三条：

1. `budget_ms` 是**硬编码默认参数**，`config.json` 里没有对应开关（`creo_reconcile_model` 返回的 `budgets.native_phase_seconds = 90` 只是把这个常量回显出来）。
2. 这 90 s 包住的是**整条 `run_generic`**，其中包含一次全量模型巡检（`ProSolidFeatVisit` + `ProSurfaceContourVisit` + 逐边 `ProEdgeIdGet`）。实测本模型的巡检成本是 **172–571 s**（见 §2.3），所以 90 s 根本不可能够。
3. 超时后 `ExitProcess(31)` 只落 `native_checkpoint.json`，**不写 `native_result.json`**，上层因此拿不到任何可用的产出，只能判 `native_outcome_unconfirmed`。

结论：**模型一旦长到「巡检 >90 s」，`restore_baseline` 就再也不可能成功。** 这不是偶发，不是会话老化——重启 Creo 换了一个全新空会话（`live.loaded=false`、`session_fingerprint 18330165643429979110`）之后，第 4 次依旧 `recovery_phase_timeout`、依旧 18,442 行。

### 1.3 重启 Creo 反而多出一种拒绝理由

重启后第一次恢复（job `30741680…`）连原生阶段都没进，直接被拒：

```
stage=connect → unknown_outcome / reconciliation_unconfirmed
message = "Recovery refused: Creo session changed since recorded evidence;
           native worker dispatch began and may have started; ...; protection retained"
```

原因：模型记录里的证据绑在旧会话上（`pending_job` 的 worker `session_fingerprint = 7925789847029956330`），新会话指纹是 `18330165643429979110`，对不上就拒。**于是重启 Creo 既不能绕过 90 s，还会多一层「会话已变」的拒绝。** 建议在文档或错误消息里写明这一点：重启不是恢复手段。

### 1.4 后果：出口矩阵全关

`creo_reconcile_model` 在这个状态下返回的 `actions`：

| action | 可用 | 原因 |
|---|---|---|
| `restore_baseline` | ✅ | 但每次都必然 `recovery_phase_timeout`（§1.1） |
| `accept_saved` / `accept_live` / `abandon_new` | ❌ | 缺少健康 live 证据 |
| `ack_no_mutation` | ❌ | 「Only a failed model can acknowledge zero mutation」——当前是 `unknown_outcome` |
| `ack_failure` | ❌ | 「Model still owns a pending or recovery job」 |
| `abandon_stalled_recovery` | ❌ | `stalled_intent: {proven: false, reason: "stage_advanced"}`——worker 已启动过 |
| `confirm_panel_closed` | ❌ | 无面板守卫 |

而 `stalled_recovery.next_step` 只说「poll `creo_get_job` 并读 stage」，那个 job 已经是终态 `unknown_outcome`。于是闭环：`restore_baseline` → `recovery_phase_timeout` → `reconciliation_unconfirmed` → 保护保留 → 只能再 `restore_baseline`。

**这次恢复超时是「零变更」的**，这一点请特别注意：

- `candidate = null`（磁盘没有产生新版本）；
- 基线 `frigate_v4.prt.90`（5,200,030 字节）sha256 `3586730f04bbffc100d657ca2abbcd3d0900c7c09fe0cd5c6a15a625cf7a7bb4`，与记录**完全一致**；
- 恢复作业在超时前没有改写任何模型文件。

也就是说：失败的是一个纯读的校验阶段，模型文件一个字节没动，却被判成「结果未确认 / 保持保护」。

### 1.5 建议（按优先级）

1. **`RecoveryDeadline` 的预算必须可配，并且按模型规模给下限**。至少加一个 `config.json` 项（例如 `recovery_phase_seconds`，默认 90，允许 ≥1800），或按 `features/surfaces/edges` 数量自动放大。当前的上限值等于「零件超过约 450 个特征就无法恢复」，这对任何真实装配件都是死路。
2. **恢复阶段的超时不该等同于「结果未确认」**。`restore_baseline` 的超时发生在校验阶段、且没有任何文件被改写（`candidate=null` + 基线哈希未变），完全可以按**零变更确认**收尾、把模型放回 `ready`，而不是保留保护。
3. **补一个可达的出口**。当前 `abandon_stalled_recovery` 被 `stage_advanced` 一票否决，而 `ack_no_mutation`/`ack_failure` 又被 `status` 和 `pending/recovery job` 挡住，三者的适用条件拼起来覆盖不了「恢复作业已终态、runner/worker 都已 stopped、candidate=null、基线哈希未变」这个最常见的失败态。建议：
   - 给 `abandon_stalled_recovery` 增加一种情形：recovery job 已终态 + runner/worker 的 `observed.alive=false`（工具已经能测出来，本机实测都是 `windows_error 87`）+ `candidate=null` + 基线哈希未变 → 放行；
   - 或者把 `ack_no_mutation` 放宽到 `unknown_outcome`：它本来就是纯元数据事务（不碰 Toolkit、不碰 revision、不碰文件），正是本场景需要的。
4. **`ExitProcess(31)` 之前最少写一份 `native_result.json`**（带 `completion_stage`、`failure_phase`、`phase_budget_seconds`）。现在只剩 checkpoint，上层只能靠猜。

---

## §2 P1【阻断级】验证阶段静默挂起（3 次提交，3 个不同挂点）

### 2.1 成功作业的阶段序列（对照基准）

B047 成功作业 `64a2220a34904e9b9d90003ed78bfd8c`：

```
connect(0.19s) → connected(4.81s) → verify_model_start(220.63s) → verify_model_regenerate(0.00s)
→ verify_model_inspect(0.03s) → verify_model_assertions(43.04s) → verify_model_before_save(0.00s)
→ verify_model_save(0.32s) → verify_model_erase(0.31s) → verify_model_reload(0.00s)
→ verify_model_reload_regenerate(0.55s) → verify_model_reload_inspect(0.04s)
→ verify_model_compare(51.50s) → verify_model_after_reload(0.23s) → verify_model_preview(0.61s)
```

`verify_model_compare` 不是纯内存比对——它把重载后的模型**再完整巡检一遍**再和快照对：那一次产生了 9,298 行日志（474 特征 + 815 面 + 5,224 次 `ProEdgeIdGet`）。

### 2.2 三次挂起的位置（都不在同一个地方）

提交的都是同一个计划（B045：`Sketch81` 的 3 个 100×100 方块，建在三点斜基准面上，各拉伸 2 mm）。

| # | job | `verify_model_start` | 日志 | 最后打印的阶段 | 挂在哪 |
|---|---|---|---|---|---|
| 1 | `f96806527f7348faabebf89ece236b44` | 546.7 s | 4.47 MB | `verify_model_reload_inspect` | 其后的 `compare` 走到第 **133 个特征**回调 |
| 2 | `e8f40252dd3a4c5db09aaa204ff7c525` | 533.8 s | 4.49 MB | `verify_model_reload_inspect` | 同上，第 **133 个特征** |
| 3 | `bea4ec07f63947edb52cc045778fe2a5` | 570.7 s | 4.50 MB | `verify_model_inspect` | `verify_model_assertions` 自己的巡检，走到第 **279 个面** |

第 2 次挂住前的尾部（第 127,285 行之后）：

```
STAGE name=verify_model_reload_inspect elapsed_ms=36
ProMdlTypeGet(board, &t)=0
ProFeatureTypeGet / ProFeatureStatusGet / ProFeatureIsIncomplete  ×133 组
<再无输出，600 s 后看门狗终止>
```

**注意 `verify_model_reload_inspect` 自己只用 36 ms**——它后面的 `compare` 才是没结束的那个。这个细节很容易误导排查方向（我一开始就记错了，特此更正）。

三次挂点各不相同（133 特征 / 133 特征 / 279 面）说明：**不是某个特征有毒，而是「只要这 3 块板在树里，全量遍历本身就会挂」**。三次日志分别停在 4,465,401 / 4,487,239 / 4,501,750 字节，也排除了「输出缓冲填满」这类固定边界。

### 2.3 硬数据：这 3 块板让巡检成本翻 2.4 倍

| 作业 | `verify_model_start` | 日志量 | 结果 |
|---|---|---|---|
| B105（`2aa0460d`） | 172.0 s | 2.0 MB | ✅ |
| B047（`64a2220a`） | 220.6 s | 2.3 MB | ✅ |
| B104（`728ce16b`） | 247.6 s | 2.5 MB | ✅ |
| B046（`7376fefb`） | 476.6 s | 4.6 MB | ✅（4 个面并进主体，量级相同却走完了） |
| B045 第 1 次 | 546.7 s | 4.47 MB | ❌ |
| B045 第 2 次 | 533.8 s | 4.49 MB | ❌ |
| B045 第 3 次 | 570.7 s | 4.50 MB | ❌ |

同一个 474 特征的树，仅仅多 3 个 100×100×2 的方块，`verify_model_start` 就从 220 s 涨到 533–571 s，其中 `ProEdgeIdGet` 达 64,392 次、`ProSurfaceContourVisit` 达 10,027 次。**巡检在还没挂之前就已经进入病态状态了。**

### 2.4 反证：悬空多 lump 本身完全正常

为排除「悬空薄片导致巡检不收敛」这个猜测，我建了最小复现 `probe_b045_float`（`model_id = ce04b3c400054617a25655992155b01a`）：

1. 400×400×400 方块（P1）；
2. 与 B045 同参数的三点斜基准面（法向 `(0.965926, 0, −0.258819)`），离方块顶面 120 mm（P2）；
3. 3 块 100×100×2 的板，沿 +n 拉伸 2 mm，**三块互不相连、也不与方块相连**（P3）。

```
P1 create  succeeded rev=1 vol=63999999.999999985
P2 datums  succeeded rev=2 vol=63999999.999999985  reloaded=True
P3 plates  succeeded rev=3 vol=64059999.99999998   reloaded=True     <-- 恰好 +60,000.000
verify_model_start=1644ms ... verify_model_reload_inspect=27ms verify_model_compare=208ms
```

保存重载后：28 特征 / 24 面 / 48 边 / **1 个 body 里装 4 个互不相连的 lump**（`body_id=52`），`healthy=true`，`verify_model_compare` 只用 **208 ms**。

**所以「多 lump / 悬空料」不是根因**；同样的几何在小模型上完全正常，只有在 474 特征的树上才挂。这一条我原来判断错了，以本节为准。

### 2.5 建议

1. **遍历要打进度点**：`verify_model_compare` / `verify_model_assertions` 每 N 个特征/面打一行（带当前 `feature id`、`surface id`、已处理数/总数）。现在一次挂起能刷 4 万行重复调用，却看不出卡在哪个 id 上——有这个 id 我就能判断是哪条特征在原树里的什么属性触发。
2. **遍历加迭代上限**，超限即报错退出（带上最后处理的 id），而不是无限等看门狗。
3. **`unknown_outcome` 应该区分「保存已成功」和「真未知」**：本次三次都是 `save` / `erase` / `reload` / `regenerate` 全部返回 0 之后才挂的。这种情形应落一个 `saved_file_reloaded_and_verified=false` 但 `revision` 有效的可 `accept_saved` 结果。
4. **削一下 `verify_model_start` 的成本**：474 特征要 64,392 次 `ProEdgeIdGet`——同一条边在一次巡检里被反复取（`ProSurfaceContourVisit` 会把相邻面的边都走一遍）。如果按面一次取环、或在一次遍历里建边缓存，调用数能降一个量级。现在一次成功的提交要 8–12 min，其中 60% 花在这里。

---

## §3 P2 三点基准面草图缺第二条参考，失败被误报成 AutodimensionSketch 失败

这一条本轮已经用**确定性构造**绕过了，详细证据另见 `2026-11-23+CREO+0.35.8+三点基准面草图缺第二条参考被误报为AutodimensionSketch失败.md` §1–§7。摘要：

- `ProSectionEntityFromProjection` 对本机 **101/101、107/107** 个基准面返回 `-2`，section 只剩 orientation 一条参考；
- 于是 `SKETCH_REFERENCE_INCOMPLETE axes=0` → `SKETCH_ORIGIN_PIN_UNAVAILABLE u=0 v=1 anchors=1` → `ProSectionSolve = -1` 且 `SECTION_ERRORS count=0`（**一条错误都没有**）→ 救援 `ProSectionAutodim` 也 −1 → 对外只报一句 `AutodimensionSketch failed with code -1`，**报错点不是根因点**；
- 同一配方 5 条：只有 B046 因某个平面（`9804`）恰好投影成功（2/360）而通过；B045/B047/B104/B105 全挂；
- 我的绕法：自己补一条「法向 = 草图 u 轴、过轮廓形心」的基准面，交线为 `u = uc`，轴对齐且穿过轮廓。实测 4 条全部 `SKETCH_SOLVE=0`，锚定面法向与预测逐位一致（`verified=true`，`max_point_distance 0～3.6e-15 mm`）。

建议仍是：`coordinate_anchors.size()==1` 且轴回退无候选时，**自动创建**这样一条锚定面（确定性构造，不靠碰运气）；并且把错误消息改到真正的失败阶段、带上 `coordinate_anchors.size()`。

---

## §4 P3 斜基准面上的 `cut` 成功但去料量远小于解析值

B104 / B105 两条切除都返回 `execution_status=succeeded` / `effect_status=committed`，无错误码，`material_removed_mm3` 与体积差自洽，但去料量严重偏小：

| 特征 | 每刀 | 去料 | 合计 | 解析 | 比例 |
|---|---|---|---|---|---|
| B104 `cut_b104`（8.4 mm） | 32.254 mm³ | | 38.055 | 13,902 | **0.27%** |
| B104 `cut_b104_b`（1.0 mm，反向） | 5.801 mm³ | | | | |
| B105 `cut_b105`（8.4 mm） | 5,683.687 mm³ | | 5,683.687 | 10,492.3 | **54.17%** |

草图本身没有问题：`geometry_deviation` 在 1e-9 mm 量级，基准面与实体面 `6671` 共面（间隙 2e-6 mm），剖面面积 1,478.918 mm²（B104）/ 1,249.086 mm²（B105）。

可疑点：B104 的 1.0 mm 反向刀只去掉 5.8 mm³，意味着**轮廓几乎完全不在材料上方**；而 `direction` 是由使用者给 `positive/negative` 的。请作者判断：

- `cut` 的 `direction` 是否应当由「材料在法向哪一侧」自动判定（至少给一个 `auto` 或回执里报告「切除体与材料的相交比例」）；
- 现在切在空气里也返回 `succeeded`，**没有任何提示**，这对批处理是危险的——建议提高回执质量：给 `cut` 也返回一个「期望去料 vs 实际去料」的比值，低于阈值就标记 `suspicious`。

---

## §5 P4 `coordinates` 在四线矩形上只落 3 个尺寸

`COORDINATE_SHARED_VERTEX_SKIPPED` 会把共享顶点跳过，一个矩形需要 8 个坐标尺寸才完全约束，实际只落 3 个。这本身不致命（本轮有些草图欠约束仍 `SKETCH_SOLVE=0`），但**「`dimensioning=coordinates` = 完全约束」这个假设不成立**，请在文档里写明，或补齐端点尺寸。

---

## §6 P5 客户端先退出会带走 detached runner

本机实测：提交后如果客户端进程退出，作业的 detached runner 会被一起带走（job `dbd68e6d178a468d843a1e68ccf0891b` 变成 `queued` + `stage=waiting_for_channel` + 空 `runner.log`，相关 pid 全部 dead）。现在我的脚本都是「提交后同会话轮询到终态」才退出，规避了这个坑，但对外部使用者仍然是个陷阱。建议在 `creo_get_job` 的回执里明确写「本作业的 runner 依赖客户端存活」，或者把 runner 与客户端解耦。

---

## §7 复现清单（可照着跑）

**P0（90 s 硬限）**——最简单：任取一个巡检 >90 s 的零件（本机 474 特征），让它进入 `unknown_outcome`，然后 `creo_reconcile_model(restore_baseline)`。观察 `native_checkpoint.json` 出现 `completion_stage=recovery_phase_timeout`、`phase_budget_seconds=90.0`。重启 Creo 后重试也一样（还会多一层 `Creo session changed since recorded evidence`）。

**P1（验证挂起）**——计划体：三条 `datum_points` + 一条 `datum_plane {kind:'through_points'}` 建斜基准面；在其上建 3 个 100×100 的方形草图（4 条 `line`，`dimensioning="coordinates"`），各沿法向拉伸 2 mm（`mode=add`）；补一条「法向 = 草图 u 轴、过形心」的锚定面。在 474 特征的树上提交，三次里必挂，位置在 `verify_model_compare` 或 `verify_model_assertions`。同一几何搬到 28 特征的小件上（`probe_b045_float`）则完全正常。

**P2（草图缺参考）**——见另一份文档 §6。

---

## §8 我方当前的临时绕法与边界

| 问题 | 临时绕法 | 边界 |
|---|---|---|
| P2 | 自己补「法向 = u、过形心」的锚定面 | 4/4 成功，已用；但每条草图要额外 4 个 datum 特征 |
| P1 | **无绕法**。换方案（3 个草图/拉伸 vs 1 个草图 3 环）未及尝试就被 P0 锁死 | 不可用 |
| P0 | **无可用绕法**。工具内所有出口都被规则挡住 | 不可用 |

因此：**在 P0 修复之前，本模型无法再提交任何计划，第 2 批（21 个 `needs-edge-ref`）与 B064 `Shell1` 也无法开始。**

---

## §9 交付物与证据索引

| 内容 | 位置 |
|---|---|
| 本文 | `2026-11-23+CREO+0.35.8+验证阶段静默挂起与恢复路径90秒硬限致模型锁死.md` |
| P2 详证（§1–§7）与逐行日志对照 | `2026-11-23+CREO+0.35.8+三点基准面草图缺第二条参考被误报为AutodimensionSketch失败.md` |
| 模型状态台账（rev7→rev87 逐特征 ΔV、偏离记录 D1–D19） | `frigate_v4-状态与偏离.md` |
| 三次挂起的作业目录 | `jobs/f96806527f7348faabebf89ece236b44`、`jobs/e8f40252dd3a4c5db09aaa204ff7c525`、`jobs/bea4ec07f63947edb52cc045778fe2a5` |
| 四次恢复的作业目录 | `jobs/0625dbaedda34d57a7b3c05d84459637`、`jobs/c81cbe3a6dd048548e38963b7415ca1c`、`jobs/307416806d0d45ea8a890890c8899fbe`、`jobs/e984795c00934701997ee02a480d2d92` |
| 成功对照（08:43 恢复、B047、B046、B104、B105） | `jobs/f1bb9f6b3516493cb0c3e2aa30e152cb`、`64a2220a34904e9b9d90003ed78bfd8c`、`7376fefb73f04fd0be070d90cfda6ed7`、`728ce16b9c5b4d17a377db8375b1f3c5`、`2aa0460d3c58422587fa050bf9f37af9` |
| 最小复现件 | `probe_b045_float` = `ce04b3c400054617a25655992155b01a`（可见 `models/…/output/probe_b045_float.prt.4`） |
| 模型当前磁盘件 | `models/df7f74bf5e424dbeb00605e218be89ad/output/frigate_v4.prt.90`（5,200,030 字节，sha256 `3586730f…7bb4`） |

---

## §10 修好之后希望能验证的几点

1. `restore_baseline` 在 474 特征的模型上能正常完成（不再 `recovery_phase_timeout`）；
2. P1 的挂起能给出「卡在哪个 feature id / surface id」，或者干脆不再挂；
3. 一次成功的提交能把总时长从 8–12 min 压下来（`verify_model_start` 的 `ProEdgeIdGet` 次数降一个量级）；
4. B045 那条特征能一次提交成功——它的几何与草图解法我这边已经验证可行（`SKETCH_SOLVE=0`，解析增量 +60,000 mm³，探针件实测正好 +60,000.000）。

**说明**：本文所有数字都来自本机 `native.log` / `native_result.json` / `native_checkpoint.json` / `job.json` 原始文件与 `creo_inspect_model` 的实测回执，没有估算值。B045 未落地、B104/B105 去料量异常这两点也如实标注，不记为已完成。
