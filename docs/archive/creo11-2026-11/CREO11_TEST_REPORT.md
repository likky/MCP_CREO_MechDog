# MCP_CREO_MechDog 在 Creo 11 上的实测报告

> 实测时间：2026-11-09 21:49–22:10　｜　机器：Windows x64 / Creo 11.0.0.0 / VS2022 / Python 3.12.10
> 源码：`D:\Projects\MCP_CREO_MechDog`（0.19.3，浅克隆）
> 钣金建模的具体配方、体积核对数据与踩坑清单见 [`SHEETMETAL_GUIDE.md`](SHEETMETAL_GUIDE.md)。

## 结论

| 层面 | 结论 |
|---|---|
| **建模内核（C++ Toolkit 执行器）** | ✅ **完全可用**，13 个方案全部建模成功并通过保存重载校验 |
| 异步 Toolkit 连接 | ✅ `connected: true`，`release_numeric: 43`（Creo 11） |
| 许可 | ✅ 够用（`protk_unlock` 为 UNLOCKED，异步运行时也能检出 Toolkit） |
| **MCP 服务层（107 个工具）** | ✅ **已修复**（2 个上游缺陷），官方验收套件 7/7 通过 |

**一句话：模型能建，AI 客户端也能直接用 107 个工具。**

## 最终验收（`tools/test_general.py`，MCP 全链路）

`GENERAL_CORE_SUCCESS=1`，exit code 0，`startup state = ready`：

| 用例 | 终态 | revision | 保存重载校验 |
|---|---|---|---|
| creo_new_part | succeeded | 1 | ✅ |
| creo_create_sketch | succeeded | 2 | ✅ |
| creo_extrude | succeeded | 3 | ✅ |
| creo_set_sketch_dimensions | succeeded | 4 | ✅ |
| creo_execute_plan（bracket，体积 10600 / bbox 正确） | succeeded | 1 | ✅ |
| creo_execute_plan | succeeded | 1 | ✅ |
| creo_create_plate | succeeded | — | ✅ |

---

## 1. 环境与构建

```
cl /nologo /MD /EHsc /std:c++17 /bigobj /W3 /we4552
   /DPRO_MACHINE=36 /DPRO_OS=4 /DPRO_USE_VAR_ARGS
link protkmd_NU.lib ptasyncmd.lib ucore.lib udata.lib bcrypt.lib ...
```

* `setup.ps1 -CreoRoot "D:\Creo11\Creo 11.0.0.0"` 一次通过
* 产物：`build/creo_worker.exe`（10.8 MB）、`creo_blend_sync.dll`、`creo_blend_loader.dll`
* `native/constants.inc` 由本机 SDK 头文件生成成功（Creo 11 的 `Probbl.h` 存在）
* 依赖全部装好：`mcp 2.3.0`、`httpx2`、`pywin32` 等（`.venv` 已建）

## 2. 逐项建模测试（全部真实执行，非 dry-run）

验证口径：`status == succeeded` **且** `result.saved_file_reloaded_and_verified == true`
（保存 `.prt.N` → 从磁盘重载 → 比对特征/尺寸/体积/参数）。

### 2.1 基础链路：圆 → 拉伸 → 改尺寸

| 步骤 | 结果 | 体积实测 | 体积理论 | 误差 |
|---|---|---|---|---|
| 草图 Ø16 + 拉伸 10 | succeeded / verified | 2010.6192982974674 | 2010.6192982974676 | 2.3e-13 |
| 改草图直径 → Ø24（不重建） | succeeded / verified，revision 1→2 | 4523.893421169301 | 4523.893421169302 | 9.1e-13 |

### 2.2 官方示例矩阵（`examples/`，12/12 全过）

| 示例 | 操作数 | 结果 | 体积累计 (mm³) | 覆盖能力 |
|---|---|---|---|---|
| bracket.json | 4 | ✅ verified | 10600.0 | 多草图 + 拉伸 + 增料 |
| turned_part.json | 6 | ✅ verified | 6324.026 | 旋转 + 2 个孔（含盲孔） |
| revolve_external_axis.json | 3 | ✅ verified | 3141.593 | 绕外部轴旋转 |
| shell.json | 3 | ✅ verified | 2672.0 | 抽壳 |
| sweep.json | 2 | ✅ verified | 502.655 | 扫掠 |
| draft.json | 3 | ✅ verified | 7790.369 | 拔模 |
| mirror.json | 3 | ✅ verified | 1000.0 | 镜像 |
| datum_points.json | 2 | ✅ verified | —（无实体） | 基准点 |
| surface_plate.json | 3 | ✅ verified | 400.0 | 曲面 + 加厚/实体化 |
| sheetmetal_wall.json | 2 | ✅ verified | 1200.0 | 钣金壁（sheetmetal 模型） |
| sheetmetal_base_yz.json | 2 | ✅ verified | 42920.0 | 钣金 YZ 基准壁 |
| dev040_recovery_baseline.json | 2 | ✅ verified | 1000.0 | 立方体基线 + 回读 |

产物：`models/<model_id>/*.prt.N`（例：`ai_part_1ff28227c753.prt.2` 140 KB），
`models/*/model.json` 记录 revision、特征别名、检查结果。

## 3. MCP 服务层问题（已修复 ✅）

### 3.1 现象

`creo_startup_status` 一直停在 `waiting_for_connection`；而同一时刻
`creo_worker.exe status 30` 手工执行却 `connected: true`。

### 3.2 根因

MCP 客户端以**受限环境**启动 `server.py` 时，子进程里没有 `PTCNMSPORT`
（Pro/Name Service 端口，本机用户环境变量 = `11239`，nmsd 正在监听 `127.0.0.1:11239`）。
`bridge.windows_process_environment()` 只回填了 Windows 运行时变量，没带这个，
于是 `ProEngineerConnect` 直接返回 **`-4 / PRO_TK_E_NOT_FOUND`**（每次探测约 1.5 s 就失败）。

对照证据（同一台机器、同一会话）：

| 服务进程环境 | worker 返回 |
|---|---|
| 缺 `PTCNMSPORT` | `{"connected":false,"connection_state":"not_found_or_unreadable","toolkit_code":-4}` |
| 带 `PTCNMSPORT` | `{"connected":true,"connection_state":"connected","toolkit_code":0}` |

### 3.3 修复（两处）

1. **`bridge.py::windows_process_environment()`**：把 Creo 运行期必需的三项加进
   从用户环境块回填的白名单 —— `PTCNMSPORT`、`PTC_D_LICENSE_FILE`、`PRO_DIRECTORY`。
   这样即使 MCP 宿主只给了最简环境，子进程也能连上已有会话。
2. **`creo_startup.py`**：启动探测的 `connect_timeout_seconds` 由 `2` 改为 `10`（三处）。
   Creo 11 冷连接实测 4.7 s，2 秒预算会永远判未就绪。

修复后（仍以 `env=None` 的受限方式启动）：`1.4s building_worker → 7.5s ready`，
`creo_session_status` 返回 `connected=True, mode=explicit_live`。

### 3.4 涉及文件

```
bridge.py                          windows_process_environment() 白名单 +3 项
creo_startup.py                    三处 connect_timeout_seconds: 2 -> 10
```

### 3.5 第二个问题：`creo_get_job` 默认 full 视图超预算报错

修好启动后跑官方验收套件，第 7 个用例在 `creo_get_job` 处中断：

```
RuntimeError: creo_get_job: Error executing tool creo_get_job:
Query metadata exceeds response budget
```

但该作业本身是成功的（`status=succeeded`、`saved_file_reloaded_and_verified=true`、`revision=1`）。
复现结果（同一 job.json）：

| 视图 | 修复前 | 修复后 |
|---|---|---|
| `section=None`（默认 full） | ❌ 抛 `Query metadata exceeds response budget` | ✅ 分页返回 39 条，32400 B，带 `next_cursor` |
| `section=operations_input` | ✅ 4387 B | ✅ 4387 B |
| `section=operations_result` | ✅ 26302 B | ✅ 26302 B |
| `section=result_entries` | ✅ 17311 B | ✅ 17311 B |

根因：`job_pages.job_page()` 在循环里按 `RESPONSE_BUDGET`（32768 B）判断“再加一条是否超预算”，
但 `next_cursor` 是在循环**之后**才写入的；页面刚好卡在 32768 B 边界时，加上游标就超了，
最后那道 `serialized_size(response) > RESPONSE_BUDGET` 检查于是抛错。

修复：两处。

1. 新增 `CURSOR_RESERVE = 512`，循环按 `RESPONSE_BUDGET - CURSOR_RESERVE` 判断（消除“刚好差一个游标”的崩溃）。
2. `RESPONSE_BUDGET` 由 **32 KiB 提到 64 KiB**。实测 Creo 11 上一个普通特征作业的完整视图约
   35 KB（`00aa9a37…` = 35358 B、`79b31498…` = 35361 B），只超出原预算 2.5 KB，
   却被推进分页视图，而分页视图没有顶层 `result` 块 —— 读内联结构的客户端（含官方测试）会直接
   `KeyError: 'result'`。提到 64 KiB 后这类作业恢复内联，真正超大的载荷仍然分页并带 `next_cursor`。

```
src/creo_mechdog/job_pages.py      + CURSOR_RESERVE，循环阈值改为 预算-512
src/creo_mechdog/model_queries.py  RESPONSE_BUDGET: 32 KiB -> 64 KiB
```

### 3.6 移植到主干基线（2026-11-26）

上面的改动写在 0.19.3（`2c78aaa`）之上；主干已到 0.46.1（`1d61dc6`，281 个提交），
入口重构成 `src/creo_mechdog/` 包，根 `bridge.py` 只剩转发。逐条结论：

| 本报告结论 | 0.46.1 处理 |
|---|---|
| `PTCNMSPORT` 必需 | **保留并移植**：`PTCNMSPORT`、`PRO_DIRECTORY` 进 `src/creo_mechdog/bridge.py::windows_process_environment()` 白名单 |
| `PTC_D_LICENSE_FILE` 回填 | **不移植**：当前实现由 `resolve_license_environment()`（含 `parametric.psf` 兜底）统一授予，用户环境块不含该项是既有安全用例 |
| 探测超时 `2 -> 10` 秒 | **已被取代**：`creo_probe_timeout_seconds` 可配置，`DEFAULT_PROBE_TIMEOUT_SECONDS = 15` |
| `CURSOR_RESERVE = 512` | **已被取代**：FEAT-023 在记录循环之后重算游标并按需回退最后一条记录，不再抛“刚好差一个游标” |
| `RESPONSE_BUDGET` 提到 64 KiB | **改为只放宽 job 整份内联门槛**：新增 `job_pages.INLINE_WHOLE_BUDGET = 64 KiB`，`RESPONSE_BUDGET`(32 KiB) 与分页单页上限不变 |

复现证据（合成载荷，与上表同形状：`operations[]` + `result.operations[]`）：

| 作业大小 | 0.46.1 改前 | 移植后 |
|---|---|---|
| 32.1 KB（50 操作） | 内联，含顶层 `result` | 内联，含顶层 `result` |
| 35.3 KB（55 操作） | 分页，顶层无 `result` | **内联，含顶层 `result`** |
| 38.5 KB（60 操作） | 分页，顶层无 `result` | **内联，含顶层 `result`** |

超过 64 KiB 的作业仍分页，单页仍按 32 KiB 预算裁剪。本次**未**重跑 Creo 11 实机（未连接 Toolkit、
未启动 Creo），实机结论仍以上面 3.3/3.5 在 0.19.3 上的原始记录为准。

2026-11-26 追加：上游随后发布 0.47.0（`baeb3d6`，并把 `BUG-194` 用于 `auto` 求解器路由修复），
本批改动按同一结论在新主干上重放，卡片重编号为 [BUG-196](../../work-items/BUG-196.md)：
`PTCNMSPORT`/`PRO_DIRECTORY` 与 `INLINE_WHOLE_BUDGET` 在 0.47.0 上仍不存在，故继续保留；
三份文档按上游 `docs/` 归档规范移入 `docs/archive/creo11-2026-11/`。

## 4. 绕过方案（已验证可用）

`toolkit.lock` 与通道锁照常工作，直接调用与 MCP 工具同源的 Python 接口即可：

```python
import sys

sys.path.insert(0, r"D:\Projects\MCP_CREO_MechDog\src")
from creo_mechdog import bridge, generic_bridge as general

manifest = general.submit(
    operations=[
        {
            "op": "sketch",
            "label": "p",
            "plane": "XY",
            "entities": [{"type": "circle", "name": "c", "center": [0, 0], "radius": 8}],
            "dimensions": [
                {
                    "name": "d",
                    "type": "diameter",
                    "refs": [{"entity": "c"}],
                    "value": 16,
                    "position": [12, 0],
                }
            ],
        },
        {"op": "extrude", "label": "s", "sketch": "p", "depth": 10},
    ],
    assertions={"require_solid": True},
)
# 轮询 jobs/<job_id>/job.json 到 status 不再为 queued/running
```

现成脚本：`direct_creo11_test.py`、`examples_matrix.py`、`mcp_probe.py` 当时未随本报告提交，
仓库里没有对应文件；移植后可直接运行的演示见 `tools/demo_bend_box.py` 与 `tools/demo_cable_tray.py`
（从仓库根执行，例如 `.\.venv\Scripts\python.exe tools\demo_bend_box.py`）。

## 5. 使用注意

* **单位**：mm / 度；特征标签小写字母开头、≤28 字符
* **revision 保护**：改已有模型必须带 `expected_revision`
* **单通道**：忙时立即 `status="busy"`，不排队、不自动重试；已提交只轮询，不重提
* **孔的参数**：必须给 `placement` + `reference1` + `reference2`（没有 `depth_type` 字段）
* 当前 Creo 会话里已打开约 13 个测试零件，需要时手动关闭
