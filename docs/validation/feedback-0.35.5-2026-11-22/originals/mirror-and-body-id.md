# 2026-11-22 + CREO 10 + MCP 0.35.5 + 镜像操作把 Creo 打成不可继续异常、body id 返回负哨兵值导致全部切除不可用

> 反馈对象：MCP_CREO_MechDog 作者
> 环境：Windows 11 + Creo Parametric 10.0.0.0（release 42）+ MCP_CREO_MechDog **0.35.5**（0.34.0 → 0.35.5）
> 任务背景：按《简易护卫舰_跨软件三维建模自然语言说明_v2.txt》用 `creo_execute_plan` 重建整船（106 特征）
> 证据口径：全部为本机实测，含 job_id、native.log 尾部、Creo traceback、体积对账数值

---

## §0 一句话结论

0.35.2 声称「曲面特征镜像引用不再崩溃」，实测**只挡住了 quilt 引用这一种形态**：换成**实体特征引用**镜像，仍然把 Creo 打成 `EXCEPTION_NONCONTINUABLE_EXCEPTION` 致命异常（弹「遇到严重错误」对话框），并且回滚与断连一起失败（`-11` / `-2`），作业只能以 `unknown_outcome` 收场；另外本机有两个模型（含本次整船模型）的**唯一 body 报出负 id −5778**，导致 `cut` 的 `scope` 直接被拒、不带 `scope` 时又只会得到「切不到材料」，**切除链路整体不可用**。

---

## §1 【致命】P17 未修完：镜像**实体特征**仍把 Creo 打成不可继续异常

### 1.1 0.35.2 的修法只覆盖了 quilt

`RELEASE_NOTES_0.35.2.md` 写明：

> `native/advanced.cpp` 的 `generic_mirror` 在创建前检查目标特征是否拥有 `PRO_QUILT`，命中即抛出 `must name a solid feature`，不进入创建。

也就是说：**目标是 quilt → 拒绝；目标是实体 → 照旧进入 `ProFeatureCreate`**。而实测证明实体目标这条路会直接崩 Creo。

### 1.2 复现一：跨作业镜像实体特征（旧会话）

- 模型 `sweep_probe`（`ad718740dc424aa494ecb1a371f7531b`），rev2，含实体扫掠 `sw1`（feature 52）
- 作业 `f45315bf4ac446f6868f25f12827cf74`
- plan：`[{"op":"mirror","label":"m_solid1","plane":{"kind":"datum_plane","id":4},"references":[{"kind":"feature","label":"sw1"}],"keep_original":true}]`
- 结果：`unknown_outcome`
- `native_result.json` 关键字段：

```json
{"failed_stage": "execute_mirror",
 "failed_toolkit_call": "ProFeatureWithoptionsCreate",
 "toolkit_code": -11, "pro_error": -11,
 "rollback_code": -11, "rollback_succeeded": false,
 "rollback_difference": {"reason": "checkpoint reload failed with code -11"},
 "disconnect_code": -2,
 "saved_file_reloaded_and_verified": false,
 "completion_stage": "result_delivery", "delivery_complete": true}
```

`native.log` 尾部：

```
ProArrayAlloc(1, sizeof(ProFeatureCreateOptions), 1, (ProArray *)&opts)=0
ProFeatureWithoptionsCreate=-11
BUILD_FAILED=-11
PHASE=rollback_to_saved_checkpoint
PHASE=disconnect
DISCONNECT=-2
PHASE=result_delivery_complete
```

### 1.3 复现二：全新会话 + 全新零件 + 同一作业内（决定性）

为了排除「旧会话已坏」「跨作业别名」「quilt 目标」三个变量，做了最干净的一次：

1. 结束全部 `xtop/parametric/nmsd/pro_comm_msg/creoagent`，由 MCP 自动重新拉起 Creo
2. `creo_new_part(model_name="mirror_probe")` → `b726f3a82e5443879d8e2a24dd88462e`，rev1
3. 单个作业（`5d4806155f5b40a3908503317675f45b`）内执行：

```json
[{"op":"sketch","label":"mp_sk","plane":"XY","offset":0,
  "entities":[{"type":"rectangle","name":"r1","min":[500,200],"max":[800,400]}],
  "dimensioning":"auto"},
 {"op":"extrude","label":"mp_box","sketch":"mp_sk","depth":20,"mode":"add",
  "direction":"positive","new_body":true},
 {"op":"mirror","label":"mp_mir","plane":{"kind":"datum_plane","id":4},
  "references":[{"kind":"feature","label":"mp_box"}],"keep_original":true}]
```

4. 结果：`unknown_outcome`，`native_result.json` 与 1.2 一模一样（`-11` / 回滚 `-11` / `DISCONNECT=-2`）

### 1.4 Creo 侧留下了什么

Creo 弹出致命错误对话框（用户截图）：

> 遇到严重错误。已将回溯写入
> `E:\WorkBuddy Space\MCP MCP_CREO_MechDog\build\creo_session\traceback.log`
> 请将其发送给"技术支持"。

`traceback.log`：

```
The trace creation timestamp is: 周日 11月 22 11:34:37 26
The traceback type is : CRASH
The release is: 10.0
The product version is: 10.0.0.0
Exception EXCEPTION_NONCONTINUABLE_EXCEPTION has occurred in the thread 21288.
```

时间 11:34:37 与作业执行窗口完全重合。栈里前三帧是 `KERNELBASE` → `coretools_sh` → `rtlcoremt`，之后是 `xtop` 内部调用链，无 MCP 侧的符号。

### 1.5 后果

- Creo 进入模态阻塞 → 之后任何调用都是 `-38`（`PRO_TK_E_BUSY`）
- 只能结束全部 Creo 进程重启（本机做了 3 次）
- 作业以 `unknown_outcome` 收场，**回滚本身也失败**，模型进入不可恢复状态（P18，见 0.34.0 文档）
- 每次代价：一个模型 + 一次 Creo 重启 + 10 分钟以上

### 1.6 建议

1. 把 `generic_mirror` 的预检查从「`PRO_QUILT` 归属」扩展为**白名单**：只有明确验证过的特征类型（如 `PROTRUSION`/`CUT` 等实体特征）才进入 `ProFeatureWithoptionsCreate`，其余一律在创建前拒绝。
2. 若暂时无法判定，提供配置项 `mirror_allow_feature_kinds`，默认只放开已实测的组合。
3. 至少要在 `ProFeatureWithoptionsCreate` 前后包一层 SEH/`__try` 保护，让致命异常不把 Creo 打成不可继续状态。
4. 回滚失败（`checkpoint reload failed with code -11`）时应保证还能 `DISCONNECT=0`，否则作业被迫降级为 `unknown_outcome`，比「干净 failed」代价大得多。

---

## §2 【阻断级】P19：body id 返回负哨兵值 −5778，导致全部切除不可用

### 2.1 事实

整船模型 `frigate_v4`（`df7f74bf5e424dbeb00605e218be89ad`，rev7，93 特征）实测：

```json
creo_inspect_model(detail="full", section="bodies")
→ {"bodies": [{"id": -5778, "state_name": "active", "material": true,
               "has_geometry": true, "surface_count": 170,
               "bbox": [[-0.1,-690.1,-660.1],[8149.6,690.1,180.0]]}],
   "complete": true}
```

只有一个 body，`material: true`，`surface_count: 170`，但 **id 是 −5778**。

对照另一个模型 `base_v0354`（`e06b58ffbaa6482db1b45d4d33c31a6d`）：id = **74**（正常正整数）。
而 `arm2_v0354`（`ba19a13c42c844b6aed9b397f05a4d64`）：id = **−5778**，与整船模型**完全相同**。

两个毫不相关的模型出现同一个负值，说明它不是几何 id，而是**未初始化/哨兵值**。

### 2.2 它如何废掉切除

**(a) 带 scope → 直接被校验拒绝**

```json
{"op":"extrude","label":"cut_extrude2","sketch":"sk55c","depth":20,"mode":"cut",
 "direction":"positive","scope":{"kind":"bodies","body_ids":[-5778]}}
```

```
Error: operations[1].scope: scope.body_ids must contain positive integer body IDs;
negative IDs from inspection are unsupported, see creo_capabilities known_limitations.cut_scope
```

**(b) 不带 scope → 只会说「切不到材料」**

```
Extrude cut removes no material; check the sketch position, direction and depth against
existing geometry Sketch origin (mm) = (0, -690, 0); normal = (-0, -1, -0);
direction sign = 1. Effective depth 15 mm spans [0, 15] mm along the reported axis.
```

这条信息把问题指向「草图位置/方向/深度」，但实际上材料就在那里——模型 bbox 是 `y ∈ [−690.1, 690.1]`、`z ∈ [−660.1, 180]`，而切除区域是 `x 4630…4870 / y −690…−675 / z 0…180`，完全落在 bbox 内部；同一区域在这个模型里确实有 2 mm 厚的板（加厚后实测面 `y=−688` 与 `y=−690`，面积各 288,000 mm²）。

### 2.3 已排除的替代解释（都试过）

| 假设 | 试验 | 结果 |
|---|---|---|
| 方向反了 | `direction="negative"` | `direction sign = 1`，沿 −Y 朝船外 → 无材料（合理） |
| 方向反了 | `direction="positive"` | `direction sign = -1`，沿 +Y 朝船内 → **仍无材料**（不合理） |
| 草图与目标面共面 | 草图从 `offset=-690` 移到 `offset=-695`，深度 20 | **仍无材料** |
| 深度不够 | 深度 15 → 20 | **仍无材料** |
| 目标在别的 body | `inspect(section="bodies")` | 只有一个 body，`material: true`，bbox 覆盖切除区 |

### 2.4 影响面

- 本任务 106 个特征里，**B016 之后的全部切除（约 30 个）都不可用**
- `boolean_bodies` 同样以 body id 为参数（`{"kind":"body","id":int}`），负 id 也被拒 → 布尔链路一起不可用
- `solidify`/`redefine_solidify_body` 的 `body_strategy` 也依赖 body 解析

### 2.5 建议

1. **优先查 −5778 的来源**：两个不同模型同值，很像 uninitialized 字段或错误返回未检查。只要 body id 读不到就应报错，而不是返回哨兵值。
2. `inspect_model` 增加 `id_source` / `id_valid` 字段，让调用方知道这个 id 能不能用。
3. 不带 `scope` 的 `cut` 失败时，回执里应给出「本次作用到哪个 body、该 body 在该区域有没有材料」，而不是仅给草图位置/方向/深度三项。现在这条信息把排查方向完全带偏了。
4. 若 body id 不可靠，提供按 `bbox`/`feature label` 指定切除目标的备用通道。

---

## §3 【体验】`sweep` 的 `AutodimensionSketch=-1` 不提示 `arc.dir` 语义

同一组 5 个实体（2 圆弧 + 3 直线）在 `XZ` 平面 `offset=-665` 上扫掠成功；把 `offset` 改成 `+665`（**同一平面，仅偏移不同**）并保持同样的实体，却报：

```
Toolkit call AutodimensionSketch failed with code -1 during execute_sweep
```

我最初以为「镜像到另一侧」需要把圆弧 `dir` 取反，改成 `dir=-1` 后就命中这个错误；改回 `dir=+1` 立刻成功。

即：**`arc.dir` 是相对草图平面法线的走向，与平面偏移的正负无关**。建议在 `sweep`/`sketch` 的文档里写清这一点，并把这个错误的提示从 `AutodimensionSketch=-1` 改成「圆弧走向可能导致自交，检查 dir/start_angle/end_angle」。

---

## §4 已验证可用的能力（供回归对照）

| 操作 | 实测结论 | 证据 |
|---|---|---|
| `creo_new_loft_part`（2 截面 straight） | 稳定，~20 s | 体积 4,173,714,361.414 |
| `extrude mode="surface"`（单条开放线） | 稳定 | quilt 面积 72,000 / 288,000 mm² |
| `thicken` 2 mm | **体积精确** | +144,000 / +576,000，相对误差 ~3×10⁻¹² |
| `sweep`（6 mm 圆截面沿拱形路径） | **体积精确** | 16,236.474698859818 = 解析值 |
| `linear_pattern`（10 个 / 间距 350） | 可用 | 体积增量 531,745.336 vs 理论 531,763.877（3.5×10⁻⁵） |
| `creo_execute_plan` 事务性 | 失败整批回滚 | revision 与特征数不变 |
| `creo_inspect_model(section="quilts")` | 给出 `quilt_id` / `area_mm2` / `bbox_mm` | 与解析值一致 |

`thicken` 的 `side` 语义实测：quilt 法线恒为 +Y 时，`side="negative"` → 沿 −Y 偏移，`side="positive"` → 沿 +Y。对 y=+690 的板要用 `negative` 才是船内，对 y=−690 的板要用 `positive`。建议文档写明 `side` 是**相对 quilt 法线**。

---

## §5 当前整船进度（供参考）

模型 `frigate_v4`（`df7f74bf5e424dbeb00605e218be89ad`）**rev7 / 93 特征 / 1 body**，体积 4,176,337,112.7962046 mm³：

- B001 放样基体（2 截面）
- B003 / B005 四块舷墙竖板曲面（quilt 72,000 与 288,000 mm²）
- B010 / B011 / B013 / B014 / B015 四处 2 mm 加厚，**全部向船内**
- B006 / B007 / B008 −Y 侧栏杆链（6 mm 管 + 1 mm 拱形板 + 10 个阵列）
- B009 的等价实现：+Y 侧同样一套并阵列（因为 mirror 崩 Creo，只能显式重建）

所有 `mirror` 相关特征（B004 / B009 / 及后续 Mirror3…）全部改为显式对称几何，属已知偏离。

---

## §6 复现步骤（最小）

### A. 镜像崩 Creo

```text
1. creo_new_part(model_name="mirror_probe")
2. creo_execute_plan，单个作业：
   [{"op":"sketch","label":"mp_sk","plane":"XY","offset":0,
     "entities":[{"type":"rectangle","name":"r1","min":[500,200],"max":[800,400]}],
     "dimensioning":"auto"},
    {"op":"extrude","label":"mp_box","sketch":"mp_sk","depth":20,"mode":"add",
     "direction":"positive","new_body":true},
    {"op":"mirror","label":"mp_mir","plane":{"kind":"datum_plane","id":4},
     "references":[{"kind":"feature","label":"mp_box"}],"keep_original":true}]
3. 现象：ProFeatureWithoptionsCreate=-11 → rollback=-11 → DISCONNECT=-2
        → 作业 unknown_outcome → Creo 弹「遇到严重错误」
        → traceback.log: EXCEPTION_NONCONTINUABLE_EXCEPTION
```

### B. 负 body id 导致切除不可用

```text
1. 模型 frigate_v4（或任意 body id = -5778 的模型）
2. creo_inspect_model(detail="full", section="bodies")
   → id = -5778, material = true, surface_count = 170
3. creo_execute_plan：草图（闭合三角形，XZ @ y=-695）+ extrude(mode="cut", depth=20, direction="positive")
   → "Extrude cut removes no material"
4. 同上但加 scope={"kind":"bodies","body_ids":[-5778]}
   → "scope.body_ids must contain positive integer body IDs"
```

---

## §7 无害化处理说明

- 未删除任何 Creo 安装、模型或用户数据；为解除 `-38`/崩溃态，结束过 `xtop/parametric/nmsd/pro_comm_msg/creoagent` 进程并由 MCP 重新拉起（本日 3 次）。
- 未修改 MCP 源码逻辑，只有上一轮已记录的 `bridge.py` 指纹候选集惰性求值补丁（与本报告问题无关）。
- 作废模型 `frigate_v2`（`7c62d3d7…`）、`frigate_v3`（`f29e034b…`）、`sweep_probe`（`ad718740…`）、`mirror_probe`（`b726f3a8…`）保留在 `models/` 下未删除，供复现 `unknown_outcome` 与负 body id。
- 完整的 Creo 崩溃回溯保留在 `build/creo_session/traceback.log`。
