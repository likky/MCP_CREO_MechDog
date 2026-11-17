# BUG-120 T1-C 补证与面板结束验证 —— 报告

日期：2026-11-17　执行者：能访问 Creo 10 的开发 agent
上级计划：《Creo 10 原生创建计划》（主仓库）　本报告只覆盖 T1-C 五步

> **性质说明**：这是**试验验证**，不是正式 MCP 修复。`native/` 源码未改动，
> 探针仍是 `test_runs/` 下的临时程序，没有接入正式 loader，也没有改动任何安全配置。

---

## 0. 五步完成情况

| 步骤 | 内容 | 状态 |
| --- | --- | --- |
| 1 | 离线补齐 12 份原件 + 收养作业回执 | **完成**，缺失 0 |
| 2 | 0.12 mm bbox 偏差定因 | **完成**，已证明为数据结构余量 |
| 3 | 取消流程与完成观察 | **完成**，取消已可宏化 |
| 4 | 中间截面最小案例 | **完成**，参数方向直接证明顺序 |
| 5 | 打包返回 | 本文件所在目录 |

---

## 1. 七项结论

### 1.1 原件补齐情况

**齐全，缺失 0。** 但随包的 `handoff/audit.json` 里「12 份全缺」是**假缺陷**：
那份审计是在异地机器、没有 `--receipt-root` 的情况下跑的。在本机用
`--receipt-root D:/my/MCP_CREO_MechDog` 重跑 `review_t1b_package.py`，结果：

```
prt_matches: 6 / host_matches: 6 / integrity_ok: true / missing_receipts: 0
```

六份 `inspection-verified-*.json`、六份面组测量 `job.json` 全部定位成功；另外还补齐了
18 份 `job.json` 与 6 份 `batch.json`（六个 model_id 的 inspect/apply/item 三件套）。
六例身份核验全通过：quilt 属本次新增特征（54/63/63/71/87/65）、测量作业指向同一 quilt、
`saved_file_reloaded_and_verified=true`、`source_unchanged=true`、输入 sha256 与报告一致。
六个快照各只有 1 个 quilt，不存在「取第一个 quilt」的隐患。

**口径更正**：父引用数组顺序**不能**当采集器顺序。T1-B 报告 §5.1 的表述超出证据，已降级为集合证据。
明细见 `STEP1_FINDINGS.md`、`offline/identity_checks.json`。

### 1.2 bbox 偏差原因（0.12 mm）

**已证明：是数据结构余量，不是几何偏移。**

- 三截面副本实测 `data_range_union` = `[[-0.1200048, -0.1200048, -0.1200048], [20.1200048, 40.1200048, 0.1200048]]`，
  与快照 bbox **逐位相同**，说明 bbox 就是 `ProSurfaceDataGet` 的 `xyz_min/xyz_max` 并集。
- 625 个 UV 采样点全落在 `X∈[0,20]`、`Y∈[0,40]`、`Z=0`（三/五截面），几何没有外扩。
- 原始测量作业的 `endpoints_mm` 显示六例裁剪边界极值与预期一致（≤1e-6 mm）。
- 若真是几何外扩，20.24×40.24 的平面面积应为 **814.66 mm²**，实测 **800.0**。
- SDK 头文件本身把这两个字段注释为 "(approximate)"；`native/quilt_query.h:57-67` 取的是并集。

**按要求未修改原测试的 `bbox_ok=false`**，只在本报告给出原因。

### 1.3 取消是否自动成功

**能，前提是宏里带上确认那一行。**

完整序列（全部来自 Creo 自己的 trail，不是猜的）：

```
~ Enter    `main_dlg_cur` `dashInst0.Quit`;
~ Activate `main_dlg_cur` `dashInst0.Quit`;
~ Activate `UI Message Dialog` `yes`;
```

差分实验：只发 `Quit` 会留下「确认取消」对话框（顶层窗口 1→3，必须人工点）；
加上 `UI Message Dialog` `yes` 后无残留对话框、面板关闭、特征数不变。
`dashInst0.Cancel` 始终无效，全程未使用。

**次序陷阱**：模块压栈的 `Done` 先于 tail 执行，所以对一次**合法**请求追加取消行不会取消，
面板已被 Done 正常关闭（实测反而多出一个特征）。取消行只在 Done 被拒时生效。

### 1.4 失败是否阻止 Done

**是。** 选取失败时 `done_macro_code = -1`（`ProMacroLoad` 从未被调用），
不推进索引、不重试 TOGGLE、不发送 Done，面板**故意留在打开状态**。
`T1C-FAIL-B01`、`T1C-MID-03` 两次复现。

**但**这次还发现一个反向问题，必须一并记下：
`ProSelectExternalselectionRecord` 返回 0 **不等于**引用真的进了采集器——
把基准面 id 40 当曲线传入也返回 0，特征照样建成，父引用里却没有它。
另外 `reference_not_a_curve` 这个 reason **名不副实**，它实际表示「id 解析不到」。

### 1.5 完成是否有独立观察

**有，而且不是窗口枚举。** 仪表板嵌在主窗口里，枚举窗口证明不了它关没关。
本次用三条互补证据：

1. **后续 Toolkit 调用能立刻返回**。面板开着时异步程序的下一次调用会阻塞
   （本次也复现：等待不足就去扫描，进程直接崩）。面板退出后
   `creo_session_status` 返回 `connected=true / toolkit_code=0 / busy=false`，
   `t1c_features.exe` 4.9 s 返回。
2. **后续一次合法请求端到端成功**，特征生成完整。
3. **界面状态**：功能区回到「工具/模型」，模型树里未提交条目消失。

### 1.6 中间截面是否真正影响形状

**是，而且是几何自身的记录，不是回调返回码。**

三条平行线（20 mm，间距 20 mm），中间一条抬到 Z=3 mm。创建次序故意是「中→A→B」，
请求按空间次序「A→中→B」给出（曲线几何 51 → 45 → 57）。

- 曲面参数探针（quilt 66）：u 是跨截面方向，u=0 落在 **y=0,z=0**，u=0.5 落在
  **y=20,z=3**，u=1 落在 **y=40,z=0** → 曲面按空间次序穿过三个截面。
- 目标点 (10,20,3) 的最近采样距离 **3.62e-14 mm**；若中间截面被忽略，该距离应为 3.0 mm。
- 面积 810.75 mm²（平坦基线 800.0），bbox 的 Z 上限 3.1200048 = 3.0 + 0.12 余量。
- 四个混合的父引用全是 `[42,48,54]`（按 id 升序），与请求顺序无关——
  正好证明父引用数组不能表达顺序。

### 1.7 仍未验证的范围

- **面板打开期间禁止某类调用**这件事，靠的是人遵守（本次确实未重生成/保存/收养/重载），
  不是靠程序阻挡。真正的防护还没做。
- `T1C_MID` 上 7 个混合只在会话里，**没有存盘**：`creo_save_model` 被
  `model_reconciliation_required` 拦下（会话 18 个特征 vs 已存文件 11 个）。
  按约束**没有**做 reconcile、没有清 unknown。包里的 PRT 是建面前的 revision 4（三草图），
  配合本报告第 4 步的坐标与次序即可完整复现。
- 采集器行（仪表板里的链行）**没能截到**：面板可见时间不足 1 秒，
  区域连拍 107 帧逐字节采样差异为 0（同进程 BitBlt 读到的是不刷新静态层）。
  顺序结论改由参数探针给出，属于更强的几何证据。
- `creo_dump_feature_tree` 不可用（`ProFeatureElemtreeExtract` 返回 -18）。
- 只验证了第一方向，未做第二方向。

---

## 2. 两次历史恢复（分开记录）

两次都是 T1-C 之前的遗留，本次**没有**再次发生，也没有重启 Creo。

**第一次（首次阻塞）——由机主重启恢复。**
T1-B 阶段异步程序分步驱动面板时阻塞，强杀后 Creo 报「外部程序 UNNAMED 没有正确初始化」，
`toolkit_code=-11`，无法自行恢复，最终由机主手动重启 Creo 才恢复。
结论：异步外部 Toolkit 程序不能分步驱动已打开的面板。

**第二次（取消异常关闭对话框）——点掉对话框后自行恢复。**
T1-B 录制取消时，界面操作把对话框异常关闭，Creo 弹出残留在那里的提示框；
点掉该对话框后会话自行恢复，未重启、未清锁。

本次两次阻塞风险（`T1C-QUIT-01`、`T1C-AFTER-CANCEL-01` 后残留的面板）都是按
第 3 步记录的取消序列主动退出的，不涉及重启。

---

## 3. 环境与源码身份

| 项 | 值 |
| --- | --- |
| Creo Parametric | 10.0.0.0，`release_numeric = 42` |
| 进程 | `xtop.exe` pid 21724（2026-11-17 09:06:52 启动）、`parametric.exe` pid 15960 |
| 会话指纹 | `13719338321783973708` |
| MCP 服务 | `server_version 0.26.0`；worker `sha256 3fbefd0d…98f2de`；source digest `17880600…2d1972` |
| 正式通道 | 单通道 `toolkit.lock`，`channel_policy = single_channel_busy_rejects_immediately` |
| 启动方式 | `ProToolkitDllLoad`（SDK 接口），**未改** `open_protk_unsigned_apps` 等任何安全配置 |
| 载入模块 | `probe_host_v2.dll`（命令 `MechDogT1CSelect`）、`probe_host_v2b.dll`（命令 `MechDogT1CSelectB`） |
| 测试模型 | `T1C_C3_COPY`（三截面副本）、`T1C_MID`（新建中间截面件） |

模块身份文件：`probe/host2/probe_identity_v2.json`、`probe/host3/probe_identity_v2b.json`
（`accepts_macro_text_from_input = false`，宏文本不接受外部输入）。

---

## 4. 本次修掉的探针缺陷

1. **状态不复位**（v2）：第二个 `request_id` 被误判为「已提交」。因不能覆盖已加载 DLL，
   改用独立文件名 `probe_host_v2b.dll` + 独立命令名 + 独立目录 `host3/`，入口加 `refresh_request_id()`。
2. **提交后扫描必崩 `0xC0000409`**：marker 缺失/半写时 `marker_value` 为 `null`，
   `nlohmann::json::value("locked", false)` 抛 `type_error`，未捕获 → `abort()`。
   加 `is_object()` 判定后痊愈。**这是我们自己的探针问题，不是 Creo 的问题。**
3. **父引用数组泄漏**：`ProFeatureParentsGet` 用 `ProArray` 分配，未释放；已按头文件要求 `ProArrayFree`。
4. `capture.py` 的 BMP 头 `biHeight` 用了正值，导致截图上下翻转（已修，已有证据文件未改动）。
5. `uia.py` 缺 DPI 感知，坐标与截图差 1707/1920 比例（已修）。

---

## 5. 目录说明

```
STEP1_FINDINGS.md / STEP3_FINDINGS.md / STEP4_FINDINGS.md   分步结论
T1C_REPORT.md                                              本文件
MANIFEST.sha256                                            全包 SHA256 清单
offline/            离线审计与身份核验（audit.json、identity_checks.json、verify_identity.py）
probe/              探针源码、编译脚本、编译日志、mapkey、runnable 包装
probe/host2,host3/  两个驻留模块的源码与身份文件
trail/              Creo 实测 trail（取消序列原件）
work/               逐用例的请求、结果、窗口快照（选取/完成/取消日志）
evidence/           界面证据截图
models/             测试模型（可选择复现的 PRT）
```

日志原件：`probe/host3/session_v2b_steps.jsonl`（逐项选取/提交）、
`probe/host3/probe_end_marker_v2b.json`（每次运行的结束状态）。

`MANIFEST.sha256` 覆盖 247 个文件（26 KB）。`work/burst*/` 下的 376 张连拍原帧
是第 4 步「抓采集器行」失败尝试的原始输出（约 110 MB），**故意未列入清单**，
只为让失败可复核，可直接删除；其要点已写在 `STEP4_FINDINGS.md` §5。

旧包 `test_runs/handoff/` 与 T1-B 包 `test_runs/2026-11-17_t1b_id_driven_blend/`
全程未改动、未覆盖。
