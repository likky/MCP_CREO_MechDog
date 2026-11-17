# T1-C 第 3 步：面板结束与取消流程（实机）

日期：2026-11-17　模型：`T1C_C3_COPY`（三截面副本，sha256 `d9a2eea6…ae84`）
会话：`xtop.exe` pid 21724，Creo Parametric 10.0.0.0，`release_numeric=42`

本次全程未结束/重启 Creo 与 nmsd，未清锁、未清 unknown，未覆盖已加载 DLL，
未在面板未退出时执行重生成、保存、收养或重载。

---

## 1. 结论速览

| 问题 | 结论 | 证据 |
| --- | --- | --- |
| 取消是否自动成功 | **是**，改判定。完整序列可宏化，见 §3 的差分实验 | §3、`evidence/cancel_macro_02.bmp` |
| 面板是否关闭 | **是**（两次） | §4：界面 + 独立 Toolkit 探针 + 后续合法请求三重印证 |
| 确认框是否消失 | **是** | §4：窗口枚举由 2 个降为 1 个 |
| 是否留下新特征 | **否** | §4：特征清单无 `incomplete` 残留，计数与基线一致 |
| 后续一次合法请求是否正常 | **是** | §5：连续 5 次成功，父引用均为 `[49,57]` |
| 失败是否阻止 Done | **是** | §2：`done_macro_code=-1`，Done 从未被调用 |
| 完成是否有独立观察 | **有**，但不是窗口枚举 | §6 |

---

## 2. 失败锁定：选取被拒后绝不 Done

用例 `T1C-FAIL-B01`，请求 `geom_id=999999`（不存在的曲线）。

```
{"geom_id":999999,"index":0,"phase":"lock","reason":"reference_not_a_curve"}
{"phase":"suppressed","request_id":"T1C-FAIL-B01","why":"prepare_failed"}
{"committed":false,"index":0,"locked":true,"phase":"suppressed","request_id":"T1C-FAIL-B01"}
```

- `selections_ok=0`，`committed=false`，**`done_macro_code=-1`**（从未调用 `ProMacroLoad`）
- 不推进索引、不重试 `PRO_SELECT_TOGGLE`、不发送 Done，面板**故意留在打开状态**
- `evidence/fail_b_panel_still_open.bmp`：面板确实仍打开，模型树多出未提交条目

这条路径满足任务书「失败后不继续选取、不自动重试、不发送 Done」的要求。

---

## 3. 真实取消序列（本机录制）

控件名来自 Creo 自己的 trail，不是猜的：

```
build/creo_session/trail.txt.1:773-774 / 2549-2550
~ Enter    `main_dlg_cur` `dashInst0.Quit`;
~ Activate `main_dlg_cur` `dashInst0.Quit`;
!ODUI session finished.
```

`dashInst0.Cancel` 已证明无效，全程未再使用。

序列分两级，**两级都能用宏表达**——第二级的控件名同样来自 trail，见下。

1. **第一级**：`Quit` 宏 → 面板关闭（无选择时直接完成，有选择时进入第二级）
2. **第二级**：模态框标题 `确认取消`、正文 `确实要取消吗?`、按钮 `是(Y)` / `否(N)`

trail 里紧接着这两行的内容，就是第二级的答案：

```
~ Enter    `main_dlg_cur` `dashInst0.Quit`
~ Activate `main_dlg_cur` `dashInst0.Quit`
! Message Dialog: Warning
!               : 确实要取消吗?
< 2 0.980148 1651 0 0 827 1920 0 0 1080 13
~ Activate `UI Message Dialog` `yes`
!ODUI session finished.
```

确认框的控件是 **`UI Message Dialog` 的 `yes`**，不是 `dashInst0.*`，也不是猜的。

### 差分实验（证明整条序列可宏化）

| tail | 结果 |
| --- | --- |
| 只发 `Quit`（`T1C-QUIT-01`） | 留下 `确认取消` 对话框，顶层窗口 1→3，**必须人工点** |
| `Quit` + `~ Activate `UI Message Dialog` `yes``（`T1C-CANCEL-MACRO-02`） | **无残留对话框**，面板关闭，特征数不变（18 个，`max_id=132`） |

### 一条必须记住的次序陷阱

模块自己压栈的 `Done` **先于** tail 里的取消行执行。所以对一次**合法**请求追加取消行是无效的：
面板已被 Done 正常关闭，取消根本没轮到（实测 `T1C-CANCEL-MACRO-01` 反而多出特征 132）。
取消行只在 **Done 被拒绝**（例如只有一个截面）时才起作用。

关键细节，且是以后必须记住的坑：

- **`否(N)` 是默认按钮**（蓝底高亮）。按回车等于「否」，面板不关。所以不能用
  `Enter` 代替确认；要用 `UI Message Dialog` 的 `yes`。
- 该模态框窗口类为 `HCS16139P`，**没有任何子 HWND**，无法按控件 id 点击——但宏可以，
  因为宏按控件名走 Creo 自己的界面层，不依赖 Win32 句柄。
- 上一会话 trail 第 2549-2550 行那次没有确认框，是因为那次取消发生在**尚未选任何引用**
  的时候，此种情况下 Creo 不弹确认框——两者不可混为一谈。

固化的 mapkey 见 `probe/mapkey_cancel_blend.txt`。**未写入 config.pro**。

---

## 4. 取消后的现场（两次独立复现）

### 第一次：驱动取消（`T1C-QUIT-01`）

宏（**不含 Done**）：

```
~ Command `ProCmdFtBndBlend`; ~ Command `MechDogT1CSelectB`; ~ Enter `main_dlg_cur` `dashInst0.Quit`; ~ Activate `main_dlg_cur` `dashInst0.Quit`;
```

| 观察 | 取消前 | 取消后 |
| --- | --- | --- |
| 顶层窗口数 | 3（含 `确认取消`） | **1**（仅主窗口） |
| 仪表板 | 打开，`第一方向` 1 个链 | **关闭**，功能区回到「工具」页 |
| 未提交特征 | 存在 | **消失** |

截图：`evidence/quit_b_confirm_dialog.bmp` → `evidence/quit_c_after_confirm.bmp`

### 第二次：界面 ✖（`T1C-AFTER-CANCEL-01` 选错曲线对后）

选 `geom_id=55` + `62` 时两者无法并成同一链，`确定` 按钮为灰、`取消` 可用——这是
**请求本身的引用选错**，不是面板故障。点界面 ✖ 后**同样弹出 `确认取消`**，
点 `是(Y)` 后同样干净退出。序列可重复，不是一次性巧合。

截图：`evidence/after_cancel_01_state.bmp`（灰掉的 ✓）、`evidence/after_second_cancel.bmp`

---

## 5. 后续合法请求

取消完成后用 `54`+`62`（`T1C-COMMIT-01` 验证过的配对）连做 5 次完整请求，
全部成功。由于本环境的驱动在提交后扫描特征会崩（§7），特征清单改由独立的
只读程序 `t1c_features.exe` 读取。

| 用例 | 特征 id | 父引用 | incomplete | 状态 |
| --- | --- | --- | --- | --- |
| 基线（未做 T1-C 前） | ≤71，共 16 个 | — | — | — |
| `T1C-COMMIT-01` | 83 | `[49,57]` | false | 0 |
| `T1C-AFTER-CANCEL-02` | 96 | `[49,57]` | false | 0 |
| `T1C-AFTER-CANCEL-03` | 109 | `[49,57]` | false | 0 |
| `T1C-AFTER-CANCEL-04` | 122 | `[49,57]` | false | 0 |
| `T1C-AFTER-CANCEL-05` | 135 | `[49,57]` | false | 0 |
| `T1C-AFTER-CANCEL-06` | 148 | `[49,57]` | false | 0 |

最终 **22 个特征**，`max_id=148`，**没有一个 `incomplete=true`**。
两次取消没有贡献任何特征，这既是「取消干净」的证据，也是特征清单与模型树
（`边界混合 1`…`边界混合 7`）对得上的验证。

---

## 6. 怎么证明面板真的退出了

窗口枚举**不能**用：仪表板嵌在主窗口里，不是顶层窗口。本次用了三条互补证据：

1. **后续 Toolkit 调用能立刻返回**。面板开着时异步程序的下一次调用会阻塞
   （T1_B/C 一直复现的 C1 问题；本次也复现：等待 10 秒就扫描，进程直接崩）。
   面板退出后 `creo_session_status` 返回 `connected=true / toolkit_code=0 /
   busy=false`，`creo_list_session_models` 与 `t1c_features.exe` 分别 0.9 s / 4.9 s 返回。
2. **后续一次合法请求端到端成功**：选择、提交、面板自动关闭、特征生成完整。
3. **界面状态**：功能区回到「工具」，模型树里未提交条目消失。

这三条合起来才算观察。只给截图是不够的，只给窗口数更是错的。

---

## 7. 本次修掉的探针缺陷（都会影响复现，必须记下来）

1. **状态不复位**（v2）：第二个 `request_id` 被当成「已提交」而 `suppressed`。
   因不能覆盖已加载 DLL，改用独立文件名 `probe_host_v2b.dll` + 独立命令名
   `MechDogT1CSelectB` + 独立目录 `host3/`，入口加 `refresh_request_id()`。
2. **提交后扫描必崩**（`0xC0000409`）。加 trace 定位到 `loop_done` 之后、
   `result_ready` 之前：marker 文件缺失或只写了一半时 `marker_value` 是 `null`，
   `marker_value.value("locked", false)` 抛 `nlohmann::json::type_error`，
   未捕获 → `std::terminate` → `abort()`，退出码正是 `0xC0000409`。
   加 `is_object()` 判定后不再崩。**注意：这不是 Creo 的错，是我们自己的探针。**
3. **父引用数组泄漏**：`ProFeatureParentsGet` 用 `ProArray` 分配，原来没释放，
   现按头文件要求用 `ProArrayFree` 释放。
4. `capture.py` 写 BMP 头时 `biHeight` 用了正值，导致截图上下翻转（已修，
   已有证据文件未改动）。
5. `uia.py` 未声明 DPI 感知，坐标与截图差 1707/1920 比例（已修）。
6. 驱动事后扫描默认关闭（`post_scan=false`），清单交给 `t1c_features.exe`。

---

## 8. 仍未验证

- ~~确认框的 `是(Y)` 是否可用快捷键替代点击~~ —— 已有更好答案：宏里用
  `~ Activate \`UI Message Dialog\` \`yes\`` 即可，无需点击也无需快捷键。
- 面板打开期间**不能**做什么，本次是靠约束遵守（未重生成/保存/收养/重载），
  不是靠失败阻挡。真正的防护还没做。
- 取消后同一会话里 `modified` 标记仍为 true（有未保存特征），本次不保存，
  留给第 5 步说明（`creo_save_model` 被 `model_reconciliation_required` 拦下）。
