# BUG-120 T1-B：按几何 ID 程序化驱动边界混合面板 — 最小研发验证报告

- 日期：2026-11-17
- Creo：10.0.0.0（`release_numeric = 42`），进程 `xtop.exe` pid 21724
- 仓库：`main` @ `ef02f07`，`git status` 仅 `?? test_runs/`（**`native/` 源码零改动**）
- 产物目录：`test_runs/2026-11-17_t1b_id_driven_blend/`
- 性质：**隔离的临时研发探针**，不是正式 MCP 功能

---

## 0. 结论（按任务书要求分项填写）

| 结论项 | 结果 | 依据 |
| --- | --- | --- |
| 两曲线按几何 ID 自动选取 | **通过** | 基线 + 矩阵 A 两例，选取错误码全 0，新特征父引用恰为两条目标草图 |
| 3 / 5 截面数量变化 | **通过**（bbox 一项偏差，见 §8.1） | 3 截面父引用 `[49,57,65]`、5 截面 `[49,57,65,73,81]`，顺序与请求一致，面积均 800 |
| 换新模型名 + 新几何 ID | **通过** | `t1b_a_03` 的 geom 54/62 与基线 45/53 编号不同，面板仍按 ID 命中 |
| 改视角窗口 | **通过** | 视图矩阵写入 `set_code=0` 且矩阵确实改变，选取结果不变 |
| 改尺寸平移 | **通过** | `(100,30,10)→(100,80,10)`、`(120,30,10)→(120,80,10)`，面积 1000、边界 140、bbox 精确 |
| 完成（Done） | **通过** | 六案例均 `Done` 收尾，特征 `incomplete=false`、`status=0` |
| 正常取消 | **部分通过**：界面侧通过，宏侧**不通过** | `dashInst0.Cancel` 不生效；只能 ✖ + 确认框「是」完成。详见 §7 |
| 临时研发探针是否通过 | **通过** | 六案例全部命中几何预期（bbox 偏差单独标注） |
| 正式公开 MCP 工具是否已集成 | **否** | 探针仅在 `test_runs/` 内运行，`native/blend_sync.cpp` 未改一行 |

> 即使探针通过，也**不能**据此报告“完整球鼻艏 MCP 已修复”。本轮只证明「会话内 DLL + 宏串 + 按 ID 选取」这条机制在六个场景下可复现，正式工具尚未集成，也未在球鼻艏真实模型上验证。

---

## 1. 环境核对（第 ① 步）

| 项 | 实际值 | 来源 |
| --- | --- | --- |
| Creo 版本 | 10.0.0.0，`release_numeric=42` | `creo_session_status` |
| Toolkit SDK | `D:\Program Files\PTC\Creo 10.0.0.0\Common Files\protoolkit` | build 脚本 include/lib 路径 |
| `ProSelection.h` 语义 | `PRO_SELECT_OVERRIDE` = unmodified（替换）；`PRO_SELECT_TOGGLE` = CTRL modified（追加） | SDK 头文件 815 行附近注释 |
| 现有驻留回调 | `native/blend_sync.cpp:168-206`，每条曲线一律 `PRO_SELECT_OVERRIDE`，靠 `section_index` 递增 | 只读核对 |
| 现有编排 | `native/blend_create.cpp`：先解析全部引用，再用宏串「开面板 + N 次命令 + Done」 | 只读核对 |
| 载荷通道 | `native/callback_api.h` 以显式 host API 转发，不直接链接 Toolkit | 只读核对 |
| 就绪判定 | `native/callback_runtime.h`：`initialize_code==0 && !terminated && !active_request` | 只读核对 |
| worker 身份 | `worker_sha256=3fbefd0d…f2de`，`source_digest=178800…`，`identity_status=verified` | `creo_session_status` |

核对结论：T1-B 的疑点确实在 `blend_sync.cpp` 的“一律 OVERRIDE”。这是**推断**（SDK 语义 + 代码阅读），本轮**没有**做全 OVERRIDE 的对照实验，原因见 §8.4。

---

## 2. 关键机制突破：异步程序不能分步驱动已开面板

第一次尝试用**异步外部 Toolkit 程序**（`protkmd_NU.lib` + `ptasyncmd.lib`）分阶段驱动：

1. `open` 阶段 `ProMacroLoad("~ Command \`ProCmdFtBndBlend\`;")` 返回 `0`，面板确实打开；
2. 紧接着的 `select` 阶段宏调用**阻塞不返回**，探针被超时终止；
3. Creo 弹出「外部程序 "UNNAMED" 没有正确初始化；可能出现了通信问题」，此后所有顶层窗口 `SendMessageTimeout` 全部超时，`creo_session_status` 返回 `toolkit_code=-11`。

**根因**：异步程序在主线程之外运行，一旦面板进入模态交互循环，外部程序对它的后续宏调用无法被处理，只能等，等到超时就变成通信故障。

**改用的方案（本轮全部结果都基于它）**：

| 组件 | 类型 | 职责 |
| --- | --- | --- |
| `probe/t1b_probe.cpp` → `t1b_probe.exe` | 异步外部程序 | 只做**不涉及面板**的事：`list`（枚举曲线与几何 ID）、`resolve`、`view`（写视图矩阵）、`save`、`close`（擦除会话模型） |
| `probe/host/probe_host.cpp` → `probe_host.dll` | **会话内驻留 DLL** | 注册一条命令 `MechDogT1BSelect`，每次调用按 `index` 选一条曲线 |
| `probe/case.py` + `probe/probe_driver.py` | 驱动 | 写请求 → 取 `toolkit.lock` → 调 `t1b_probe.exe` → 收集结果 |

会话内 DLL 的关键点：`ProCmdActionAdd` 注册命令，宏串里 `~ Command \`MechDogT1BSelect\`;` 每出现一次就执行一次 `select_next()`，因此 **一条宏串可以精确控制面板收到 N 次选择**：

```
~ Command `ProCmdFtBndBlend`;
~ Command `MechDogT1BSelect`;
~ Command `MechDogT1BSelect`;
~ Activate `main_dlg_cur` `dashInst0.Done`;
```

---

## 3. 探针的数据驱动契约（第 ② 步）

请求文件 `probe.json` 字段：

| 字段 | 含义 |
| --- | --- |
| `request_id` | 幂等键。同 `request_id` 重放时 DLL 不重复选取（`session_steps.jsonl` 有记录） |
| `stage` | `list` / `resolve` / `session` / `cancel` / `view` / `save` / `close` |
| `model` | 目标模型名 |
| `curves[]` | 有序引用列表：`index` / `owner`（模型名）/ `geom_id`（**现场解析**）/ `feature_id` / `role` |
| `macro_open` | 面板宏串（N 次命令由请求生成，不写死） |
| `require_identity` | 要求 `probe_identity.json` 存在且 `terminated=false`，否则拒绝执行 |
| `view_rotate_deg` | 仅 `view` 阶段 |

关键约束的落实：

- **曲线 ID 现场重新解析**：每次建模后先跑 `list`，从 `ProFeatureGeomitemVisit` + `ProCurveDataGet` 读出真实 `geom_id` 与端点，再写进请求。矩阵 A/C/D 的 ID（54/62/70/78/86、56/64）都是在各自模型上现取的，没有沿用基线 45/53。
- **首个 OVERRIDE、其余 TOGGLE**：`probe_host.cpp:251`
  ```cpp
  bool first = g_index == 0;
  ProSelectRecordAction action = first ? PRO_SELECT_OVERRIDE : PRO_SELECT_TOGGLE;
  ```
- **循环不写死分支**：`select_next()` 只按 `g_index` 取第 i 条，2/3/5 截面走同一段代码，宏串里命令条数由 `len(curves)` 生成。
- **TOGGLE 不重复补发**：`if (!code) g_index++;` —— 只有错误码为 0 才前进，失败不重试、不补发。
- **每步记录**：`session_steps.jsonl` 每行含 `request_id` / `phase` / `index` / `role` / `owner` / `geom_id` / `feature_id` / `api` / `selection_action` / `error`。
- **打开面板前先全量校验**：`resolve_all()` 一次性校验 owner、实体类型、长度、端点，任一不合格写 `blocked=true` 并**拒绝打开面板**（§6）。

---

## 4. 构建与加载

编译脚本见 `probe/build_probe.cmd`、`probe/host/build_host.cmd`（均 `call vcenv_x64.bat` 取环境，绕开 `reg.exe` 黑名单）。

会话内 DLL 的编译/链接（`build_host.cmd` 原文核心两行）：

```
cl /nologo /MD /EHsc /std:c++17 /bigobj /W3 /we4552 /DPRO_MACHINE=36 /DPRO_OS=4 /DPRO_USE_VAR_ARGS ^
   /I"%SDK%\includes" /I"...\MCP_CREO_MechDog\native" /c probe_host.cpp /Fo probe_host.obj
link /nologo /DLL /MACHINE:X64 /OUT:probe_host.dll probe_host.obj ^
   "%SDK%\x86e_win64\obj\protk_dllmd_NU.lib" "%SDK%\x86e_win64\obj\ucore.lib" ^
   "%SDK%\x86e_win64\obj\udata.lib" kernel32.lib ... ws2_32.lib
```

编译日志：`logs/build_host.log`（`probe_host.cpp` → `probe_host.dll`，退出码 0）、`logs/build_probe.log`、`logs/build_probe_view.log`（`t1b_probe.cpp`，退出码 0），均无警告级以上输出。

注册（`probe/host/protk.dat`）：

```
name T1BProbe
startup dll
exec_file ...\probe\host\probe_host.dll
text_dir ...\probe\host
allow_stop true
delay_start false
end
```

加载时机：Creo 启动时按 `protk.dat` 载入，**机主在安全警告中点「是(Y)」确认**（按任务书要求，该步骤交还机主）。加载后自报身份：

```json
{"command":"MechDogT1BSelect","process_id":21724,"terminated":false,
 "module_file":"...\\probe\\host\\probe_host.dll"}
```

---

## 5. 六案例结果（第 ③④ 步）

汇总表由 `probe/summarize.py` 从磁盘产物自动复算生成，输出 `evidence/matrix_summary.json`。

| 案例 | 模型 | 请求（idx/owner/geom） | 面板选取 | 新特征 | 父引用 | 面积 mm² | 边界 mm | bbox 偏差 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 基线 两曲线 | `t1b_run_01` | 0/‑/45, 1/‑/53 | OVERRIDE, TOGGLE（err 0/0） | 54 | `[40, 48]` | 800.0 | 120.0 | 0.0 |
| A 新模型+新ID | `t1b_a_03` | 0/54, 1/62 | OVERRIDE, TOGGLE（0/0） | 63 | `[49, 57]` | 800.0 | 120.0 | 0.0 |
| B 改视角 40° | `t1b_b_02` | 0/54, 1/62 | OVERRIDE, TOGGLE（0/0） | 63 | `[49, 57]` | 800.0 | 120.0 | 0.0 |
| C 三截面 | `t1b_c_03` | 0/54, 1/62, 2/70 | OVERRIDE, TOGGLE×2（0/0/0） | 71 | `[49, 57, 65]` | 800.0 | 120.0 | **0.12** |
| C 五截面 | `t1b_c_05` | 0/54, 1/62, 2/70, 3/78, 4/86 | OVERRIDE, TOGGLE×4（全 0） | 87 | `[49, 57, 65, 73, 81]` | 800.0 | 120.0 | **0.12** |
| D 平移+加长 | `t1b_d_02` | 0/56, 1/64 | OVERRIDE, TOGGLE（0/0） | 65 | `[51, 59]` | 1000.0 | 140.0 | 0.0 |

几何预期对照：

- 基线 / A / B / C：面积 800 ± 0.01 → **全部命中**；边界 4 条开放边 `20/40/20/40` → 120.0；单面、单 quilt、`closed=false`。
- D：面积 1000 ± 0.01 → 命中；边界 `20/50/20/50` → 140.0；bbox `[[100,30,10],[120,80,10]]` 精确命中。
- 全部案例：`incomplete=false`、`status=0`、无实体材料（`has_solid=false`）。

### 5.1 “面板确实收到两条独立链”的证据

`ProFeatureNumSectionsGet` 对本类曲面边界混合特征返回 `0`，**不能**用它证明链数。因此改用两条独立证据：

1. **父引用集合精确等于请求草图**，且没有多余父引用。两条曲线案例 → `[40,48]` / `[49,57]` / `[51,59]`，正好是两个截面草图；五截面案例 → `[49,57,65,73,81]` 五个草图，顺序与请求 `index` 完全一致。
2. **顺序可辨**：`parent_ids` 与请求 `index` 一一对应，不是集合无序匹配。若面板只收到最后一条（全 OVERRIDE 的表现），父引用只会剩 1 个，而边界混合单方向至少要 2 条才能完成——特征却 `incomplete=false`，反证不止一条被接受。

**采集器接受的逐步日志**（`probe/host/session_steps.jsonl`，五截面为例）：

```json
{"phase":"resolve_all","blocked":false,"references":[{"index":0,"geom_id":54,...},{"index":1,"geom_id":62,...},...]}
{"phase":"select","index":0,"geom_id":54,"api":"ProSelectExternalselectionRecord","selection_action":"PRO_SELECT_OVERRIDE","error":0}
{"phase":"select","index":1,"geom_id":62,"api":"ProSelectExternalselectionRecord","selection_action":"PRO_SELECT_TOGGLE","error":0}
{"phase":"select","index":2,"geom_id":70,...,"selection_action":"PRO_SELECT_TOGGLE","error":0}
{"phase":"select","index":3,"geom_id":78,...,"selection_action":"PRO_SELECT_TOGGLE","error":0}
{"phase":"select","index":4,"geom_id":86,...,"selection_action":"PRO_SELECT_TOGGLE","error":0}
```

**局限（如实说明）**：上述是“kernel 回执”层面的证据，不是“从仪表板采集器控件里读出链数”。Creo 没有为此提供可读接口，本轮也没有做屏幕像素级核对。

### 5.2 保存与重载

每案例：`save` 阶段 `ProMdlnameBackup` 返回 0 → `close` 阶段 `ProMdlErase` 返回 0（必须擦除，否则会话内 modified 标记会让收养被拒）→ `creo_adopt_file` inspect + apply → `saved_file_reloaded_and_verified=true`、`source_unchanged=true`。

| 案例 | 落盘文件 | 字节 | sha256 | 收养 model_id |
| --- | --- | --- | --- | --- |
| 基线 | `work/c3_save/out/t1b_run_01.prt.1` | 93,164 | `b9267c728efb142ab0440fbf55d3508cf13149df5096863c1c0ad72f844f334d` | `bbe390758d90455a8fb86e0eec39398a` |
| A | `work/a2_save/t1b_a_03.prt.1` | 100,494 | `48cfe0c6b2dfccbf6ba551a0b50e969fb2b2d338e4e65ebeb3db9a59b3bcccf3` | `f65ac145ec544c04939755b55d89fa57` |
| B | `work/b_save/t1b_b_02.prt.1` | 100,962 | `62478c40a9e85b0791608df201d7dbb5f89125f0f438ab48f4d01050a4d959a7` | `03ac1d7d835343778e2e484b872665b0` |
| C 三截面 | `work/c3_3save/t1b_c_03.prt.1` | 108,377 | `9635677e59baa6b16457e19c716c58d32a6b742f84b2a59650e306af8de22525` | `675adfafc2ff475c9714e6f7cde0550b` |
| C 五截面 | `work/c5_5save/t1b_c_05.prt.1` | 124,114 | `bfc2d4e9ab692151a13bc237f43f9abd3757a539f77005fa490a62f317bda3fe` | `4e85022c475849a2b0191b90019e8ee9` |
| D | `work/d_save/t1b_d_02.prt.1` | 100,650 | `d50336daf897032caa2acc8d51c525d24325a5072acc81c1fd4827705a021314` | `5368401f83914d27ba1abe6bc772ffbb` |

几何数值不是从探针自报里抄的，而是从收养后的 `models/<id>/output/inspection-verified-*.json` 与 `jobs/<job>/job.json`（面组测量）回读，探针无法自证。

---

## 6. 错误用例（第 ⑤ 步）

全部在**打开面板之前**拒绝，避免把通道堵死：

| 用例 | 构造 | 结果 |
| --- | --- | --- |
| 不存在的 ID | `geom_id=999999` | `blocked=true`，`error` 非 0，未开面板 |
| 其他模型的引用 | `owner=t1b_c_05` + `geom_id=54` | `blocked=true`。**当前模型里确实存在 54 这条线**，拦截依据是 owner 不一致，不是整数编号碰巧冲突 |
| 类型不符 | `geom_id=45`（`PRO_ENT_CMP_CRV` 复合曲线） | `blocked=true`，类型校验拦下 |

三次拒绝后会话仍健康，后续合法请求正常执行。

---

## 7. 完成与取消（第 ⑤ 步）

- **完成**：`~ Activate \`main_dlg_cur\` \`dashInst0.Done\`` 六个案例全部生效，面板关闭、特征生成、`incomplete=false`。
- **取消**：`~ Activate \`main_dlg_cur\` \`dashInst0.Cancel\`` **不生效**——两次实测仪表板原地不动，连提示框都没有。真正的取消路径是界面 ✖ → 弹「确实要取消吗?」→ 「是(Y)」，纯宏走不完。
  - 途中一次误判让我在面板未关闭的情况下继续重生成，把通道堵住（`toolkit_code=-11`，顶层窗口 24→37）。**没有重启 Creo、没有清 `toolkit.lock`**：点掉取消与错误提示后通道自行恢复（`connected=true`、`toolkit_code=0`）。
  - 取消后验证：`features_before=12`（取消那次没留下特征）→ 新请求成功创建特征 63，父引用 `[49,57]`。取消没有污染后续请求。
- 结论：**取消不能靠宏实现**。正式工具若需要“可取消”，必须在界面层做，或接受“取消后由用户手动收尾”。

---

## 8. 失败、偏差与未验证项

### 8.1 三截面 / 五截面 bbox 各方向偏 0.12 mm

实测 bbox `[[-0.12,-0.12,-0.12],[20.12,40.12,0.12]]`，超出 0.01 mm 容差。

判定为**包络盒余量，不是几何偏移**，定量依据：

- 若曲面真为 20.24 × 40.24，面积应为 **814.46 mm²**；实测面积恰为 **800.0**（`799.9999999999997` / `799.9999999999968`，浮点噪声内）。
- 四条开放边长度精确为 `20.0 / 40.0 / 20.0 / 40.0`。

**未直接验证**：面组测量作业只保存边长，不保存端点坐标，本轮没有单独测量 quilt 顶点。因此这一项记为“已解释但未顶点级复测”。两曲线案例无此现象（偏差 0.0），怀疑与 3 条以上截面的样条拟合包络盒算法有关，未深究。

### 8.2 `ProFeatureNumSectionsGet` 对曲面边界混合返回 0

不能用作“链数”证据，已改用父引用集合 + 顺序（§5.1）。这意味着**正式工具也无法用这个 API 回执链数**，需要在集成时另找判据。

### 8.3 收养回执里的告警

部分 `creo_adopt_file` 回执带 `inspection_warnings: native_sidecar_write_failed`，同时 `fallback_status: verified`。几何数据取自 verified 快照，但 sidecar 写入失败的原因未查。

### 8.4 没有做的对照实验：全 OVERRIDE

想用“两条曲线全 OVERRIDE”直接证明“后选覆盖前选”，从而坐实 `blend_sync.cpp` 的缺陷。**做不到**：选取动作在编译期写死，`probe_host.dll` 已加载且任务书禁止覆盖已加载 DLL，重编需重启 Creo。因此 §1 对 `blend_sync.cpp` 的判断保持为**推断**，不是实测结论。

### 8.5 其他未验证

- 未在球鼻艏真实模型（含 2 方向曲线、相切条件）上验证。
- 未验证 `role=second_dir` 的第二方向采集器——本轮全部为 `first_dir`。
- 未做“面板打开后模型被外部修改”的竞态测试。
- 视图变化只验证了旋转；缩放由 Creo 自行附加，未单独隔离。

---

## 9. 原始 mapkey 与适配说明（第 ⑦ 步要求）

T1-A 原始 mapkey（`test_runs/2026-11-17_t1_boundary_blend/gui_work/t1_blend_mapkey.pro`，294 字节，SHA256 `04098e189e924c4fa8d5e83907ffb2e4229db7d5575f4cbe089b65d86b818326`）：

```
mapkey ~ @MAPKEY_LABELblend_t1_gui;~ Command `ProCmdFtBndBlend` ;\
mapkey(continued) ~ FocusOut `bbl_12curves.1.0` `PH.Curves1DirTbl`;@PAUSE_FOR_SCREEN_PICK;\
mapkey(continued) @PAUSE_FOR_SCREEN_PICK;@PAUSE_FOR_SCREEN_PICK;\
mapkey(continued) ~ Activate `main_dlg_cur` `dashInst0.Done`;
```

**为什么不能整文件丢给 `ProMacroLoad`**：

1. 文件带 `mapkey ` / `mapkey(continued) ` 配置前缀与续行反斜杠，`ProMacroLoad` 要的是单条宏文本，前缀会被当成命令名解析失败。
2. 含 `@MAPKEY_LABELblend_t1_gui` 标签定义，不是宏体。
3. 含 3 个 `@PAUSE_FOR_SCREEN_PICK`，`ProMacroLoad` 不会等待屏幕拾取；没有“等待 + 注入选择”的通道，暂停点会被跳过或挂住。
4. **最关键**：整条宏**不含任何对象标识、不含 Ctrl 修饰、不含过滤器设置**。`FocusOut` 只是让采集器失焦，三次暂停是三次人手点击，且默认无修饰——按 SDK 语义那是三次 unmodified 选取。三次暂停也**不等于**三条曲线（T1-A 的实际结果是两条线）。所以照抄这条宏既无法复现，也无法回答“采集器收到几条链”。

**本轮的适配方式**：只保留可程序化的骨架——

```
~ Command `ProCmdFtBndBlend`;              ← 打开面板
~ Command `MechDogT1BSelect`;  × N         ← 用按 ID 选取替代 @PAUSE_FOR_SCREEN_PICK
~ Activate `main_dlg_cur` `dashInst0.Done`; ← 提交
```

`FocusOut` 被丢弃（由 `ProSelectExternalselectionRecord` 直接写入采集器），暂停点被替换为**有序的 N 次显式选择**（第 1 次 OVERRIDE，其余 TOGGLE）。

---

## 10. 复现步骤

```bash
# 0) 前置：probe_host.dll 已按 protk.dat 载入（机主确认一次安全警告）
#    校验身份
cat probe/host/probe_identity.json    # terminated 必须为 false

# 1) 编译（如需重编；注意 DLL 被占用时无法覆盖）
powershell -c "& '...\probe\build_probe.cmd'"
powershell -c "& '...\probe\host\build_host.cmd'"

# 2) 枚举模型曲线，拿到真实 geom_id
.venv/Scripts/python.exe probe/case.py --dir work/x_list \
  --probe '{"request_id":"X-LIST","stage":"list","model":"<模型名>"}'

# 3) 按 ID 驱动面板（命令条数由 curves 长度生成）
.venv/Scripts/python.exe probe/case.py --dir work/x_session \
  --probe '{"request_id":"X","stage":"session","model":"<模型>","mode":"collector",
            "require_identity":".../probe/host/probe_identity.json",
            "macro_open":"~ Command `ProCmdFtBndBlend`; ... ~ Activate `main_dlg_cur` `dashInst0.Done`;",
            "curves":[{"index":0,"owner":"<模型>","geom_id":54,"feature_id":49,"role":"first_dir"}, ...]}' \
  --host '{"request_id":"X","model":"<模型>","curves":[...]}'

# 4) 保存 → 擦除 → 收养 → 测量
.venv/Scripts/python.exe probe/case.py --dir work/x_save --probe '{... "stage":"save","save_dir":"..."}'
.venv/Scripts/python.exe probe/case.py --dir work/x_close --probe '{... "stage":"close"}'
# 然后用 creo_adopt_file inspect/apply，再 creo_inspect_model(quilts) / creo_measure_surface_group

# 5) 一键复算证据表
.venv/Scripts/python.exe probe/summarize.py
```

注意：`save_dir` 必须**已存在**，否则 `ProMdlnameBackup` 会把文件写回当前目录（A 案例踩过）。

---

## 11. 文件清单

| 路径 | 说明 |
| --- | --- |
| `probe/t1b_probe.cpp` | 异步外部程序：`list` / `resolve` / `view` / `save` / `close` |
| `probe/host/probe_host.cpp` | 会话内 DLL：注册 `MechDogT1BSelect`，按 index 选取 |
| `probe/case.py` | 单案例运行器（写请求 + 调驱动） |
| `probe/probe_driver.py` | 取 `toolkit_lock` + `native_environment()` 后启动探针 |
| `probe/summarize.py` | 从磁盘产物复算证据表 |
| `probe/build_probe.cmd`、`probe/host/build_host.cmd` | 编译脚本 |
| `probe/host/protk.dat`、`probe_config.json` | 注册与命令名 |
| `probe/host/session_steps.jsonl` | 全部案例的逐步选取日志 |
| `logs/build_probe.log`、`build_probe_view.log`、`build_host.log` | 编译日志 |
| `evidence/matrix_summary.json` | 六案例机读汇总（含量化检查项） |
| `work/*/probe.json`、`probe_result.json`、`probe_steps.jsonl` | 每案例输入与输出 |
| `work/*_save/*.prt.1` | 六份零件（摘要见 §5.2） |
| `T1B_STATUS.md` | 阶段状态（含中途会话挂死的现场记录） |

---

## 12. 对正式集成的直接含义（不构成本轮交付）

1. `blend_sync.cpp` 需要“**首次 OVERRIDE、后续 TOGGLE**”的有状态选取，而不是一律 OVERRIDE——这是本轮唯一真正的机制结论，但仍是**基于 SDK 语义的推断**，需在集成后实测。
2. 命令必须**在会话内**执行；异步外部程序只能开面板，不能分步选。
3. 取消无法宏化；正式工具要么不做取消，要么交界面层。
4. 链数没有 API 回执，验收判据只能落在“新建特征的父引用集合 + 顺序”。
