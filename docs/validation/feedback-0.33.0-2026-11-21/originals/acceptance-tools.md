# 2026-11-20_CREO_0.33.0_全测全绿但独立验收脚本硬编码工具数82跨8版本必失败

> 反馈对象：MCP_CREO_MechDog **0.33.0**（`main@9585289`，2026-11-20 20:40 +0800）
> 环境：Windows 10 x64 19045 / Python 3.13.14 x64 / MSVC 19.44.35207 + Windows SDK 10.0.26100 / Creo Parametric **9.0.0.0** Toolkit SDK
> 基线：0.31.1（`235be1f`）。本次跨 **2 个版本（0.32.0、0.33.0）/ 19 次提交 / 82 个文件 / +6672 行**。
> 结论先行：更新链路（依赖、种子、Creo 9 原生编译、MCP 冒烟 **109 工具**）全部通过；**全量单测本次 4161 项全绿**（0 failures / 0 errors / 4 skipped），上一轮反馈的 `runner.log` 竞态本次未复现。但**确定性缺陷仍在且跨 8 个版本（0.27～0.33.0）未修**：项目自带的独立验收脚本 `tools/test_update_check.py:108` 硬编码 `tool_count == 82`（实际 109）、`tools/test_model_reconciliation.py:331` 断言 `== 84`，实测 `success=false` 且真实断言被 `TaskGroup` 掩盖；`dev_check.py` 与 CI 从不运行这两个脚本，因此官方"全量通过"与用户运行自带验收脚本得到"失败"的结论长期矛盾。本轮 0.33.0 处理的是另一批反馈（BUG-134/135/136、DEV-095/096），仓库根目录的这两项工程反馈未进入作者视野。

---

## 一、更新与验证结果

| 步骤 | 命令 / 动作 | 结果 |
| --- | --- | --- |
| 拉取 | `git fetch --tags origin` | 新增 `v0.32.0`、`v0.33.0`；`origin/main` = `9585289`。后台拉取，无残留锁 |
| 运行时保护 | 备份 `session_activity.json` / `seed_registry.json` / `config.json` → `checkout -B main origin/main` → 确认运行时文件 | 成功；`version.py` = 0.33.0；三个运行时文件均完好（已取消跟踪，checkout 不删除） |
| 依赖 | `pip install -r requirements.lock.txt`、`pip install --no-deps --editable .` | 成功（`requirements.lock.txt` / `pyproject.toml` 本次无变化）；包导入通过 |
| 种子库 | `python seeds.py --install` | 成功；9 个种子哈希匹配 |
| 原生编译 | `python bridge.py build` | 成功；`build/creo_worker.exe` 重编 |
| MCP 冒烟 | stdio `server.py`：列工具 + `creo_check_environment` | **109 个公开工具**（与 0.31.1 持平）；环境检查 `exists=true`，本次无启动锁警告 |
| 全量单测 | `python tools/test_unit.py`（`PATH` 含 PortableGit、`PYTHONPATH=""`，后台 24 分钟） | **4161 项、0 failures、0 errors、4 skipped、`success=true`**，耗时 **1434.2s** |

> 说明：上一轮（0.31.1）全量单测为 4078 项 / 3 errors / exit 1；本轮 4161 项全绿。差异来自测试数量增长（0.32/0.33 新增用例）与偶发竞态本次未命中，非产品行为回退。

---

## 二、核心问题：全绿假象下，独立验收脚本硬编码旧工具数必失败（跨 8 版本未修）

### 1. 现象：全量单测全绿，但项目自带脚本必失败

```text
$ python tools/test_unit.py     # 官方全量门禁
Ran 4161 tests in 1434.217s
→ build/unit_test_report.json: success=true, errors=0

$ python tools/test_update_check.py   # 项目自带独立验收脚本，环境完全正常
{"success": false, "tool_count": 109, "update": null,
 "modeling": {"status": "not_requested"},
 "failure": "unhandled errors in a TaskGroup (1 sub-exception)"}
退出码 1
```

`creo_check_update` 工具本身工作正常（up_to_date），唯一失败点是工具数断言。

### 2. 根因：硬编码 + 异常掩盖 + 门禁不覆盖，三重叠加

**（a）硬编码工具数**（`tools/test_update_check.py:108`）：

```python
assert capabilities["tool_count"] == len(tools) == 82
```

（`tools/test_model_reconciliation.py:331`）：

```python
assert capability["tool_count"] == 84
```

实际 `tool_count=109`（README / `creo_capabilities` 返回一致）。硬编码始于 2026-10-14 `da57ab9`（FEAT-020，当时工具数 82），此后工具数 82→95→102→104→107→108→109 一路增长，两处断言从未更新。`docs/UPDATE_CHECK.md:3` 仍写"工具总数为 82"，文档与断言同源过时。

**（b）异常被 TaskGroup 掩盖**：断言失败被包装成 `unhandled errors in a TaskGroup (1 sub-exception)`，`== 82` 的真实上下文在 stdio 输出中不可见，用户只知道"失败"，无法判断是工具数过时还是产品故障。

**（c）门禁从不覆盖**：

- `tools/dev_check.py` 只在第 253 行运行 `tools/test_unit.py`；
- CI `.github/workflows/checks.yml` 只跑 `tools/check_backlog_counts.py` 与 `tools/dev_check.py`；
- 二者都不运行 `tools/` 下的独立验收脚本。因此这两个脚本自 0.3.0 起从未被自动门禁执行，即使每次必失败也不影响发布"全绿"。

### 3. 跨版本未修的证据链

- `git log 235be1f..origin/main -- tools/test_update_check.py tools/test_model_reconciliation.py` 与 `git log ef02f07..origin/main -- <同上>` 均为空：从 0.26.0 反馈到 0.33.0，对这两个脚本零改动。
- 上一轮（0.31.1）反馈文档已完整报告此问题；本轮检查远端 `git grep`："跨6版本"/"硬编码82"/"上轮两项"在 `docs/` 中零匹配，说明该反馈未被登记。
- 本轮 0.33.0 的 `613cc4b` 提交处理的是 `C:\Users\Administrator\Desktop\0.31.1` 用户桌面三份反馈（BUG-134/135/136、DEV-095/096），与仓库根目录的这两项工程反馈是不同来源。

---

## 三、次要问题（同源，本轮状态更新）

### 1. `runner.log` 竞态：本次未复现，但根因代码仍未修

上一轮报告中 0.31.1 全量单测 3 errors 的 `runner.log` WinError 32，本次 4161 项全绿、日志中 `runner.log` 错误数为 0。这印证了上轮判断——它是**偶发时序竞态**，不是稳定缺陷。但根因代码在 0.33.0 仍未改：

- `bridge.py:1688` 仍是真实 `subprocess.Popen`，让 worker 继承 `runner.log` 句柄；
- `tests/unit/test_inspection_only_admission.py:128-130` 仍只 patch `subprocess.run`（synthetic worker），未 patch `subprocess.Popen`。

建议仍在：测试中隔离 `Popen` 或在 `TemporaryDirectory` 清理前 `proc.wait()`，消除偶发失败，而不是把现象归为"本机环境问题"。

### 2. 发布记录跳过数口径

`RELEASE-0.33.0.md` 写"全量单测通过（6 项跳过）"，本机报告为 4 跳过（两项 MSVC helper 不可用、两项 BUG-130 归档 job 不在本机）。跨环境差异可接受，但建议发布口径同时列出 through/failures/errors/skipped 真实数字。

### 3. 文档工具数过时

`docs/UPDATE_CHECK.md:3` 仍写"工具总数 82"，与 README 的 109 和 `creo_capabilities` 返回不一致，建议改为"以 `creo_capabilities` 返回为准"。

---

## 四、修复建议（沿用上轮，优先级 P1）

1. **去除硬编码工具数**：`test_update_check.py:108` 改为 `assert capabilities["tool_count"] == len(tools)`，`test_model_reconciliation.py:331` 去除 `== 84`，另设与版本解耦的一致性检查；`docs/UPDATE_CHECK.md:3` 改为动态口径。
2. **异常可见化**：不要把原始断言吞进 `TaskGroup`，显式打印断言上下文（期望值/实际值）。
3. **扩大门禁覆盖**：在 `dev_check.py` / CI 增加一步，至少做 `tools/test_update_check.py`、`tools/test_model_reconciliation.py` 的离线可运行性检查（不依赖 Creo），从机制上防止独立验收脚本腐化——这是让"全绿"真正可信的关键。
4. **隔离 `Popen`**（次要）：测试 patch `subprocess.Popen` 或 `proc.wait()`，消除偶发 teardown 竞态。
5. **反馈闭环**：仓库根目录的反馈文档建议纳入作者台账流程；本轮两项反馈已连续两版（0.31.1、0.33.0）写在仓库根目录但未被登记，容易漏处理。

---

## 五、本机复验命令（可复现）

```bash
cd "F:/WorkBuddy CREO Space/MCP_CREO_MechDog"
export PYTHONPATH=""
export PATH="/f/Program Files/WorkBuddy/resources/vendor/PortableGit/cmd:$PATH"
./.venv/Scripts/python.exe tools/test_unit.py > build/unit_test_console_20261120pm_full.log 2>&1
cat build/unit_test_report.json                    # success=true, 4161 项
./.venv/Scripts/python.exe tools/test_update_check.py   # success=false, exit 1
```

判定：全量单测看 `build/unit_test_report.json`；独立脚本看自身 stdout 的 `success` 字段与退出码。stdout 中的 `ERROR: Seed archive SHA256 ... differs`、`CONTRACT FAILED`、`Startup coordination lock access failed` 是负例/环境输出，非失败标志。

---

> 附：本次为**离线复验**，未连接 Creo、未启动/结束进程、未做故障注入、未改任何源码或用户模型。核心缺陷与 Creo 版本无关，在纯离线环境即可复现。0.32/0.33 新增的 Creo 10 面板放样收尾（BUG-120 任务 5）、装配约束文案（BUG-136）、发布记录交叉校验（DEV-096）等能力按项目会话纪律不在本次黑盒范围。
