# 2026-11-20 · CREO · 0.32.0 · 不等距倒角不可表达与启动链自锁只能重启 Windows

> 反馈对象：`MCP_CREO_MechDog` 作者
> 环境：Creo Parametric 10.0.0.0（`release_numeric 42`）、Windows 10/11 x64、WorkBuddy MCP stdio 客户端
> 版本：0.32.0｜`worker_sha256 8a36c34dea30568bda27f9b738d5cc2253815f89aafe6168586eecd8260ba0d6`｜`source_digest a9da7033281e06785af24eb9eb80e2ed8265da1163ef126b7ba3a0d184b5d3c9`
> 任务：按 `简易护卫舰_跨软件三维建模自然语言说明_v2.txt`（1,616 行 / `sha256 60f138ed…c1bf`）比对整船模型一致性，并补齐 TXT 附录 B 的 106 条特征

---

## 0. 一句话结论

**圆角与倒角这两个长期被判定为「缺失」的能力，本轮实测全部通过，并且几何精确到解析值**（60° 倒角面法线实测 60.000°，被削侧壁高度 259.81 = 150×tan60°；R20 圆角体积减少 8584.074 mm³，解析值 8584.07）。

真正卡住的是另外两件事：

1. **`chamfer` 没有「两相邻面不等距离」档**，导致 TXT 里 3 个倒角根本不可表达（不是模型问题，不是 Creo 问题，是 schema 缺一档）；
2. **启动链在同一台机器上会把自己锁死**——`legacy_digest_candidates` 为了一个永远不会被使用的参数做了 3^10 组合的急切求值，耗时 236 s，超过 `PREPARATION_BUDGET = 180` 的硬预算，于是每次启动必然超时；超时后残留的僵尸进程又因为 `HasExited=True` 被 `inventory()` 判成 `uncertain`，永久 `selection_required`，**没有任何配置或环境变量能逃生，只能重启 Windows**。

---

## 1. 本轮实测通过的能力（正面结论，请勿回改）

这几条是**建议保留并写进能力矩阵**的，之前多轮被标为不可用，本轮证明可用。

| 能力 | 入口 | 实测证据 |
|---|---|---|
| 等距倒角 | `creo_execute_plan` op=`chamfer`，`size` | edge 2621，150 mm → `effect_status: committed`，`applied_set_count 1/1`，`source: feature_tree`，新面法线 `[0.7071, 0, 0.7071]` = **45.000°**，体积 −6,525,000 mm³ |
| 距离+角度倒角 | `chamfer_type: "distance_angle"` + `angle_deg` + `angle_reference` | 两条对称边，150 mm @ 60°，`committed`，新面法线 `[0.6124, ∓0.6124, 0.5]` = **60.000°**，被削侧壁 Z 由 350 降到 **90.19** = 350 − 150·tan60° |
| 圆角 | `creo_round` / op=`round` | 独立探针零件 100×100×100 方块，R20 竖边 → 体积 −**8584.074** mm³；解析值 `(20² − π·20²/4) × 100 = 8584.07`，**误差 0.004 mm³** |
| 几何锚点选择器 | `{"kind":"geometry_selector","target":"edge","endpoints_mm":[…],"tolerance_mm":0.5}` | 在 1707 条候选边中命中 `matched_geometry_id`，重载后仍可复现，不受 id 漂移影响 |
| 线性阵列 | op=`linear_pattern`（leader + `direction` 单位向量 + `spacing` + `count`） | 探针零件：⌀20×30 凸台按 X 向 4 实例 @30 mm；收尾体积 **1,029,115.022** mm³，理论 `991,415.926 + 4×9424.778 = 1,029,115.037`，**误差 0.015 mm³**（即 4 个实例全部真实生成） |

**据此，此前多份报告里「Creo 10 上圆角/倒角不可用」的判定应当撤回。**

> 附带一条工具面观察：`linear_pattern` **没有独立工具**（只有 `creo_axis_pattern` / `creo_dimension_pattern`），必须走 `creo_execute_plan` 写 plan 文件。建议补一个 `creo_linear_pattern`。

---

## 2. 问题 P1【阻断级】启动链自杀：`legacy_digest_candidates` 做了一次永远用不上的 3^N 展开

### 现症

同一台机器、同一份源码、同一个产物哈希，`creo_worker.exe` 构建阶段每次耗时 **4 分 09 秒**，超过 `PREPARATION_BUDGET`，`creo_startup_status` 永远停在 `building_worker`，8 次尝试全部卡死（`startup.log`）。表现为「Creo 明明开着，工具就是连不上」。

### 根因（代码级）

`src/creo_mechdog/build_fingerprints.py:69` `legacy_digest_candidates()` 对每个依赖生成 `[raw, lf, lf→crlf]` 三个变体，再 `itertools.product(*variants)` 全组合求 SHA256。10 个 callback 依赖 → 3^10 = 59,049 组合，去重后仍有 **1,024** 个哈希。

而 `build_fingerprints.py:46` `match_cached_fingerprint()` 的第一行就短路：

```python
if cache.get("algorithm") == FINGERPRINT_ALGORITHM:
    if cache.get("fingerprint") == current_fingerprint:
        return True, ...
    return False, None          # ← 从这里返回，legacy_candidates 参数一次都没读
```

调用方 `bridge.py` 是这样传的：

```python
match_cached_fingerprint(callback_cache, callback_fingerprint,
                         legacy_digest_candidates(...))   # ← 先求值，再被丢弃
```

**参数是急切求值的，函数却是懒用的。** 于是 236 s 全部空转。

### 复现

```
分段计时（同一进程内）：
  config                 0.00 s
  native hash            0.09 s
  sdk hash               0.48 s
  check_environment      0.02 s
  legacy_digest_candidates 236.24 s   ← 1024 个候选
  ------------------------------------
  bridge.py build        249.97 s      （PREPARATION_BUDGET = 180，必然超时）
```

### 实测修复

调用点改为「只在缓存确实缺 `algorithm` 标记时才展开」：

```python
def _legacy_candidates_if_needed(cache, prefix, abi_digest, snapshot) -> set[str]:
    if isinstance(cache, dict) and cache.get("algorithm") == FINGERPRINT_ALGORITHM:
        return set()
    return legacy_digest_candidates(prefix, abi_digest, snapshot)
```

**结果：249 s → 2.66 s，产物 `creo_worker.exe` 的 `sha256` 与 `source_digest` 前后完全不变**（`8a36c34d…` / `a9da7033…`）。功能零影响，纯性能。

### 建议

1. `match_cached_fingerprint` 改成按需回调（传 `lambda` 而不是已求值的 set），或在函数内部先判 `algorithm` 再决定是否调用；
2. `legacy_digest_candidates` 缺少规模上限。当依赖数 > 6 时 3^N 已不可控（3^10 ≈ 5.9 万），建议加 `if len(snapshot) > 8: return set()` 或改为逐依赖序列化后整体比较；
3. `PREPARATION_BUDGET` 硬编码在 `creo_startup.py:41`，建议改为配置项并在超时消息里输出**分段耗时**——本轮定位花了很长时间，就是因为超时消息只说 "preparing"，不说卡在哪一步。

> 本地已打补丁：`bridge.py.bak-20261120-224105` 为原始备份。

---

## 3. 问题 P2【阻断级】僵尸进程 `HasExited=True` 仍被判 `uncertain`，且无任何逃生阀

### 现症

上一轮结束进程后，PID 18988 的 `xtop.exe` 变成半死状态：

```
Get-Process -Id 18988
  SessionId   : 1
  HasExited   : True      ← 已经退出
  Threads     : 0
  Handles     : 0
  WorkingSet  : 32768
```

`stop-process -Force` 拒绝访问、`taskkill /F /T` 返回 "无法终止…属于 PID 22120 子进程…拒绝访问" (exit 255)、`wmic` 被拦、`Add-Type` P/Invoke 被拦、`handle.exe` 不存在。
**这个对象既不能被使用，也不能被删除。**

### 根因（代码级）

`creo_startup.py:328` `inventory()` 对每个进程记录：

```python
if not _session(entry.pid, ...):
    uncertain = True          # HasExited=True 也走这里
```

`creo_startup.py:1125`：

```python
initial = inventory(settings)
if initial["uncertain"] or any(not p["matches"] for p in initial["processes"]):
    self._publish("selection_required", "Creo process identity is uncertain ...")
    return                      # ← 直接 return
if not settings.auto_start and ...   # ← 后面这些判断根本执行不到
```

**`uncertain` 的短路发生在 `settings.selected` 判断之前**，所以即使用户在配置里显式指定了要用的会话，也进不去。`require_ready()`（`creo_startup.py:727`）又只检查 `connected` 字段，于是整个 MCP 永久不可用。

### 建议

1. `inventory()` 里对 `HasExited` / `Threads == 0` / `Handles == 0` 的条目**直接跳过**，不要计入 `uncertain`——一个已经退出的进程不构成身份不确定性；
2. `uncertain` 的分支要放在 `settings.selected` **之后**；或者给一个显式逃生配置（如 `ignore_uncertain_processes: true`、`orphan_pid_allowlist: [...]`）；
3. 超时/异常路径上，启动时创建的进程要登记 pid，下次启动先尝试 `openProcess` + `terminateProcess`，失败就**明确告诉用户"请重启 Windows"**，而不是反复重试并卡在 preparing。

> 本轮代价：用户手动重启 Windows 才恢复。

---

## 4. 问题 P3【能力缺口】`chamfer` 没有「两相邻面不等距离」档

### 现象

`ChamferOp`（`schema.py:1138`）只有两档：

- `equal_distance`：`size` 一个值；
- `distance_angle`：`size` + `angle_deg` + `angle_reference`。

但 SolidWorks 的倒角类型里有 **「两相邻面不等距离」（Distance1 / Distance2）**，源记录里真实出现了三次：

| TXT 条目 | 两相邻面距离 | 定位边 |
|---|---|---|
| B051 Chamfer3 | **1.5 / 1.2** | 2 条，且**在模型里精确存在（误差 0.000 mm）** |
| B056 Chamfer5 | **1.6 / 0.5** | 1 条，且**精确存在（0.000 mm）** |
| B058 Chamfer7 | **0.5 / 1.6** | 1 条（另有阶梯缺失，见 P4） |

这三个倒角**锚点完全正确、几何完全具备**，唯一的问题就是 MCP 无法表达「两个面各自退不同的距离」，因此一个都建不出来。

### 建议

`ChamferOp` 增加第三档：

```python
chamfer_type: Literal["equal_distance", "distance_angle", "d1_d2"]
distance_1: float | None = None   # 面 1 上的退距
distance_2: float | None = None   # 面 2 上的退距
face_1: dict | None = None        # 可选，用 face pair 明确"哪两个面"
face_2: dict | None = None
```

Creo 侧对应 `PRO_CHAMFER_D1_D2`（或 `PRO_CHAMFER_OFFSET_OFFSET`），属于标准能力。

---

## 5. 问题 P4【一致性阻塞】模型的「阶梯」被简化后，倒角/圆角的锚边不复存在

这一条不是 MCP 缺陷，但它决定了「MCP 有能力」不等于「能补齐」，**建议在文档里写清：`round`/`chamfer` 的锚点是边，边不存在就没有任何回落路径**。

做法：把 TXT 里全部 **19 条「定位边两端」** 按 ×100 换成 mm，到模型 2,308 条边里按端点做双向匹配（容差 1 mm）。

**结果：6/19 精确命中（误差 0.000 mm），13 条不命中。**

| TXT | 特征 | 最近边误差 | 情况 |
|---|---|---|---|
| B043 | Chamfer1 | **0.000**（2 条） | ✅ 已补齐 |
| B050 | Chamfer2 | **0.000**（1 条） | ✅ 已补齐 |
| B051 | Chamfer3 | **0.000**（2 条） | 锚点在，但 P3 卡住 |
| B056 | Chamfer5 | **0.000**（1 条） | 锚点在，但 P3 卡住 |
| B052 | Chamfer4 | 212 mm | 40 mm 小倒角边不存在：模型把该处建成了一个 438 mm 的整条斜边 |
| B057 | Chamfer6 | 50 mm | 缺 Y=−160 处的台阶，边多出 50 mm |
| B058 | Chamfer7 | 160 mm | 缺 X=2539 处的台阶，边多出 160 mm |
| B095 | Chamfer8 | 150 mm | 缺 Z=200 的水平台阶，45° 斜边只在 Z=350 与 Z=0 存在 |
| B035 | Fillet1 | 1075 mm | Z=−660 处的轮廓边不存在（该处是放样曲面，截面曲线不是实边） |
| B070 | Fillet2 | 13.9～24.7 mm | 塔桅轮廓与 TXT 差 13.6 mm(Y) / 20 mm(Z)，6 条边全部偏差 |
| B076 / B078 | Fillet3 / Fillet4 | — | TXT 只给了「半径 0.02」，**没有定位边**，无法放置 |

**共同根因**：模型把若干小型附件简化成了单一棱柱，而 TXT 的倒角落在「棱柱被截断后产生的小台阶」上。B043/B050/B051/B056 正好是没被简化的那几个，所以只有它们能对上。

**给作者的请求**：`round`/`chamfer` 在零候选时的报错目前是 `zero or multiple matches are always refused`，建议补充**最近候选的距离与坐标**（例如 "nearest edge id=2620, max endpoint error 21.21 mm"），这样用户能立刻判断是"锚点写错"还是"几何不存在"。本轮我是靠自己写脚本扫 2,308 条边才得到这个结论的。

---

## 6. 问题 P5【旧账未清】`surface_loft` 的 guides 档位仍然一次都没成功

`creo_session_status` 的 `worker_build_identity` 自己就写着：

```json
"surface_loft": {
  "available": true, "state": "compiled",
  "evidence": {"create_code": 0, "extract_code": -18, "feature_incomplete": true}
}
```

即：**特征能建（create_code 0），但提取不起来（-18），于是回滚**。element_tree 路线到现在仍然只到这一步。

panel 路线（`creation_route: "resident_panel"`）在 build identity 里是 `"state": "ready"`，但 `creo_callback_status` 实际是：

```json
{"readiness": "not_loaded", "registration_status": "unknown",
 "generation": "panel", "artifact_status": "prepared",
 "manual_setup_when_not_loaded": true}
```

而模型主窗口 `MainWindowHandle: 0`、`MainWindowTitle: ""`（`Responding: True`，`ws=572 MB`），panel 路线要求的「用户在 GUI 里交互式打开的活动窗口」不成立。

### 本轮新增的事实（供作者缩小排查范围）

- **`spline`（插值样条，穿过所有点）可以建，`b_spline + line` 混合不行**：同一批导线点，用 `type:"b_spline"` + `line` 组合时 `ProSectionAutodim` 返回 −1（`AutodimensionSketch failed with code -1 during execute_sketch`）；改成单条 `type:"spline"` 后立刻成功（revision 32→33→34）。
  → 建议：`sketch_solver.cpp:105-118` 在 `mode != "coordinates"` 时对开放 `b_spline` 混排应当跳过 `ProSectionAutodim`，或给出"该组合不支持自标注"的明确错误码。
- 3 条导线草图（上/下/侧）已全部建成并在模型里（`GD_UP_T1`、`GD_LOW_T1`、`GD_SIDE_T1`），说明导线的**输入侧**完全没问题，卡的是 loft 的**消费侧**。

---

## 7. 问题 P6【体验】`creo_chamfer` 独立工具丢掉了 `distance_angle` 档

`server.py:1487` 的 `creo_chamfer(model_id, expected_revision, label, distance, references)` 只有 `distance` 一个几何参数，**无法表达角度**。要建 60° 倒角必须绕到 `creo_execute_plan` 写 plan 文件。

建议给独立工具补 `chamfer_type` / `angle_deg` / `angle_reference` 三个可选参数，与 `ChamferOp` 对齐。同理 `creo_round` 缺 `curvature_continuous`（G2）。

### 补充：`creo_project_curve` 的契约里没有「分割面」

TXT B037 要的是 SolidWorks 的 `Split Line`（投影型）——**把面分割成两片**，只改拓扑不改几何（`仅分割面，不切去整个主体`）。

`server.py:3286` `creo_project_curve` 的文档承诺是：`reports curve_id, the measured curve_length_mm and the two endpoints_mm`，并且"built as a real sweep of the source sketch along the direction plus the documented Creo intersect curve"，还会额外产生 `helper_feature_id` 这个辅助曲面特征。

也就是说它产出的是**面上的一条交线 + 一个辅助曲面**，契约里没有"把目标面分割为两片"。Creo 里对应的是 Project 特征的 split 选项（`PRO_PROJECT_SPLIT` 一类），不是 intersect curve 本身。

**请作者确认**：是否有隐藏的 split 开关？若没有，该项应记为「语义缺口：只能投影，不能分割面」。本轮没有实测这一项（球鼻艏 quilt 已在 rev37 中存在，target 侧具备条件），愿意按作者指出的参数再补测。

---

## 8. 问题 P7【工具面】没有「把会话内已有模型切为活动窗口」的工具

本轮为了不污染整船，用 `creo_new_part` 建了一个一次性探针零件做圆角/阵列实测。做完之后想把活动窗口切回整船，发现**没有路**：

- `creo_open_file(file_path=…frigate_txt_rebuild.prt, idempotency_key=…)` →
  `SESSION_NAME_CONFLICT: a part model with this name is already in the Creo session; the file was not retrieved. Close or erase it in Creo first, or **switch to it directly**.`
- 但工具列表里没有任何 activate / show / set_current 类工具；
- `creo_erase_session_models` 的契约里写明 *Managed models stay with creo_reconcile_model*，探针零件是 managed，擦不掉。

**实际可用的绕法是 `creo_refresh_model(model_id=<目标>)`** —— 它走 Toolkit 实时查询，副作用恰好会把该模型切成活动窗口（本轮实测：`current_model` 由 `ROUND_PROBE` 变为 `FRIGATE_TXT_REBUILD`，revision 37 不变）。

建议：

1. 增加 `creo_activate_model(model_id)`；
2. 或在 `creo_open_file` 的 `SESSION_NAME_CONFLICT` 里提供 `activate_existing: true` 选项；
3. `creo_refresh_model` 激活活动窗口这件事，要么写进文档，要么去掉这个副作用——现在它是「README 阅读（READ）工具改变了 GUI 状态」，属于契约不一致。

---

## 9. 本轮落地结果（可直接复算的体积对账）

模型 `frigate_txt_rebuild.prt.38`，revision 37，`sha256 df75ca1b3a193c2a4cd010fd077c5d23a839a981adfc28c2239430dff555c83b`

| 项 | 值 |
|---|---|
| 起始体积（rev34） | 5,919,802,387.113947 mm³ |
| 结束体积（rev37） | 5,903,868,920.793034 mm³ |
| 总减少 | **15,933,466.320913 mm³** |
| CHAMFER2_B050 | −6,525,000.000 |
| CHAMFER1_B043A | −4,704,233.119 |
| CHAMFER1_B043B | −4,704,233.202 |
| 三项之和 | **15,933,466.321** ✅ 与总体积差完全一致（差 0.0001 mm³ = 舍入） |

特征树实测：`features 399`（较 rev34 的 396 增 3，均为 `type 914` = chamfer，`status 0`）、`surfaces 609`、`edges 2314`、`quilts 3`、`bodies 4`。

几何级复核（面法线）：

```
新增面 9487  normal [0.61237, -0.61237, 0.50000]  → 与水平面夹角 60.000°
新增面 9524  normal [0.61237,  0.61237, 0.50000]  → 与水平面夹角 60.000°
新增面 9449  normal [0.70711,  0.00000, 0.70711]  → 与水平面夹角 45.000°（等距 150→45°）
原有面 2435/2439 的 bbox Z 上限 350.0 → 90.19 = 350 − 150·tan60°
```

---

## 10. 建议的处理优先级

| 序 | 问题 | 影响 | 建议 |
|---|---|---|---|
| 1 | P1 启动链 236 s 空转 | **完全不可用**，每次启动必超时 | 惰性求值 + 规模上限 + 分段耗时上报 |
| 2 | P2 僵尸进程无逃生阀 | **完全不可用**，只能重启 Windows | `HasExited` 跳过 + `selected` 优先 + 显式逃生配置 |
| 3 | P3 不等距倒角缺失 | 3/8 倒角不可表达 | `ChamferOp` 加 `d1_d2` 档 |
| 4 | P5 surface_loft guides | 球鼻艏导线放样仍然 0 成功 | 先修 −18 提取，再谈 panel |
| 5 | P4 零候选报错无近邻信息 | 排障成本极高 | 报出最近候选 id + 端点误差 |
| 6 | P6 独立工具缺参数 | 易用性 | 与 Op 对齐 |
| 7 | P6 附 `project_curve` 无 split | TXT 的 Split Line 语义无法表达 | 确认/补充 split 选项 |
| 8 | P7 无 activate 工具 | 多模型作业时活动窗口切不回去 | 加 `creo_activate_model` 或 `activate_existing` |

---

## 11. 一句话给作者

**能力已经够了，卡住的是「启动能不能起来」和「一个倒角档位」。** 前者让整个工具链在生产环境不可用（P1/P2），后者让一个纯 schema 层面的小缺口挡住了 3 个完全可建的倒角（P3）。
