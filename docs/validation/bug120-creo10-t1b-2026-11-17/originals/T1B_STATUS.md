# BUG-120 T1-B 最小研发验证 · 最终状态（2026-11-17 17:50）

> 完整证据、逐步日志与结论分项见 **`T1B_REPORT.md`**。
> 本文件只保留状态总览与过程中的关键转折（含一次会话挂死的现场记录）。

## 结论速览

| 项目 | 状态 |
|---|---|
| 环境核对（Creo / SDK / 源码 / worker） | 完成 |
| 最小数据驱动探针（会话内 DLL + 异步外壳） | 完成并加载（机主确认一次安全警告） |
| 按几何 ID 解析曲线（owner/类型/端点/长度） | **通过**（现场解析，非硬编码） |
| 宏启动原生「边界混合」面板 | **通过**（`ProMacroLoad=0`，面板出现） |
| 同一次 **异步** 调用内逐步驱动面板 | **失败**（第二次宏阻塞，通道被堵）→ 改会话内 DLL 后解决 |
| 两曲线按 ID 自动选取 | **通过** |
| 3 / 5 截面数量变化 | **通过**（bbox 项偏差 0.12 mm，已解释待顶点级复测） |
| 换新模型名 + 新 ID | **通过** |
| 改视角窗口 | **通过** |
| 改尺寸平移 | **通过**（面积 1000、边界 140、bbox 精确） |
| 完成（Done） | **通过**（六案例） |
| 正常取消 | **部分通过**：界面侧通过；`dashInst0.Cancel` 宏**不生效** |
| 无效引用拒绝 | **通过**（三例，均在开面板前拦下） |
| 临时研发探针是否通过 | **通过** |
| 正式公开 MCP 工具是否已集成 | **否**（`native/` 源码零改动） |

---

## 一、环境事实（本机实测）

- Creo Parametric 10.0.0.0，`release_numeric=42`，`xtop.exe` pid 21724
- SDK：`D:\Program Files\PTC\Creo 10.0.0.0\Common Files\protoolkit`
- 项目：`main` @ `ef02f07`，`git status` 仅 `?? test_runs/`（无源码改动）
- worker `build/creo_worker.exe` sha256 `3fbefd0d…f2de`，`identity_status=verified`
- 未改 `config.pro`、未改 `open_protk_unsigned_apps`、未清 `toolkit.lock`

### SDK 语义（`ProSelection.h`）

```c
/* action - PRO_SELECT_OVERRIDE for unmodified selection.
          PRO_SELECT_TOGGLE   for CTRL modified selection. */
```

现有 `native/blend_sync.cpp` 对每条曲线一律 `OVERRIDE`，靠 `section_index` 递增——这是 T1-B 的疑点。本轮**未能**做全 OVERRIDE 对照实验（DLL 已加载不可重编），该判断保持为推断。

---

## 二、关键转折：异步程序 → 会话内 DLL

### 第一次尝试（失败，保留为证据）

`probe/t1b_probe.cpp`（异步外部程序）在 `open` 阶段成功打开面板（`ProMacroLoad=0`），随后任何宏调用**阻塞不返回**，探针被超时终止，Creo 弹出：

```
外部程序"UNNAMED"没有正确初始化; 可能出现了通信问题。
```

此后 `creo_session_status` 返回 `toolkit_code=-11`，顶层窗口 24→37，全部 `SendMessageTimeout` 超时。截图：`evidence/c1_dashboard_open.png`、`evidence/hang_message_dialog.png`。

**未做任何恢复动作**（不重启、不清锁）；按机主选择，由机主手动重启 Creo。

### 第二次尝试（成功）

改用**会话内驻留 DLL** `probe/host/probe_host.dll`，注册命令 `MechDogT1BSelect`，用**一条宏串**完成“开面板 + N 次选取 + Done”：

```
~ Command `ProCmdFtBndBlend`;
~ Command `MechDogT1BSelect`;  × N
~ Activate `main_dlg_cur` `dashInst0.Done`;
```

六案例全部由此跑通。

---

## 三、测试零件（本轮新建）

| 模型 | 用途 | 收养 model_id |
|---|---|---|
| `t1b_run_01` | 两曲线基线 | `bbe390758d90455a8fb86e0eec39398a` |
| `t1b_a_03` | 矩阵 A：新模型 + 新 ID | `f65ac145ec544c04939755b55d89fa57` |
| `t1b_b_02` | 矩阵 B：视角旋转 40° | `03ac1d7d835343778e2e484b872665b0` |
| `t1b_c_03` | 矩阵 C：3 截面 X=0/10/20 | `675adfafc2ff475c9714e6f7cde0550b` |
| `t1b_c_05` | 矩阵 C：5 截面 X=0/5/10/15/20 | `4e85022c475849a2b0191b90019e8ee9` |
| `t1b_d_02` | 矩阵 D：平移 (100,30,10) 并加长 | `5368401f83914d27ba1abe6bc772ffbb` |
| `t1b_e_02` | 错误用例 / 取消用例（仍在会话中） | 未收养 |

各模型的几何 ID 均**现场解析**后写入请求，未沿用旧编号（例：基线 45/53，A 与 B 均为 54/62，D 为 56/64）。

---

## 四、过程中踩到的三个坑（供后续参考）

1. **`ProMdlErase` 之前收养必被拒**：`modified_source` —— 会话内模型有未保存修改。必须 `save` → `ProMdlErase` → 再 `creo_adopt_file`。
2. **`save_dir` 不存在时 `ProMdlnameBackup` 会把文件写回当前目录**（A 案例），所以保存目录必须先建。
3. **`dashInst0.Cancel` 在 Creo 10 边界混合仪表板不生效**：两次实测仪表板原地不动；真正取消是 ✖ → 「确实要取消吗?」→「是(Y)」。一次误判导致面板未关就重生成，把通道堵住（`toolkit_code=-11`），点掉对话框后自行恢复，未重启 Creo。

---

## 五、明确未做的部分

- 全 OVERRIDE 对照实验（受“不覆盖已加载 DLL”限制）
- 球鼻艏真实模型（含第二方向曲线、相切条件）验证
- `role=second_dir` 第二方向采集器
- 3/5 截面 bbox 0.12 mm 的顶点级复测
- 正式工具集成（本轮只交隔离探针，`native/` 未改一行）
