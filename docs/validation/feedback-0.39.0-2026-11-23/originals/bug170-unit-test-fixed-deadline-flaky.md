# 0.39.0 反馈：新增 BUG-170 单测用固定 0.3 秒 deadline，官方干净包随机失败（15 次采样 4 次失败）

- 日期：2026-11-23
- 验证对象：`wudahua/MCP_CREO_MechDog` v0.39.0（Release id `455465647`，node_id `RE_kwDOU_ueTM4bJdqv`，published `2026-11-23T13:29:02Z`）
- 本地环境：Windows / Creo 10.0.0.0 ProToolkit SDK / WorkBuddy MCP 客户端 / Python `.venv`
- 验证性质：安装、编译、静态交叉核对、门禁对照实验、篡改实验、单测子集、**官方干净源码树反复采样**
- 实机边界：本轮**未**连接 Toolkit、**未**启动或关闭 Creo、**未**做故障注入；文中结论不代表 Creo 10 运行期验证。本文所有失败均来自离线单测，可在官方干净包复现。

## 1. 结论摘要

0.39.0 的发布数据、编译、门禁、注册、跨文档台账全部通过，但**本版新增的一个单测存在时序竞争缺陷，会在官方干净包中随机失败**，建议在下一个版本修复：

| 编号 | 问题 | 证据 | 判定 |
| --- | --- | --- | --- |
| P1 | 新增单测 `Bug170StaleSessionAndForceNewTests.test_drive_stale_session_without_and_with_force_new_session` 用固定 `monotonic() + 0.3` 秒 deadline 驱动 `_drive()`，只要 preparation 或首次探测阶段稍慢，就会在发布 stale 诊断前提前 `timeout`，断言 `stale_session_detected` 失败 | 官方干净树连续采样 15 次，4 次失败（26.7%）；本机 5 次全失败；失败点固定为 `assertion line 123: None is not true` | **0.39.0 新增缺陷，官方包可复现** |

该测试是 0.38.0→0.39.0 随 BUG-170 修复**新引入**（0.38.0 及之前版本的官方源码包中不存在此文件）。它不是本机环境问题：在**新解压的官方源码树**中，用同一 `.venv` 解释器和无污染的 `PYTHONPATH`，同样的失败以约 1/4 概率出现。

## 2. 数据层正项（便于作者区分「功能错误」与「测试时序错误」）

- 四附件本地 SHA256、sidecar、GitHub asset digest、Release body 四方一致；六个中间版（0.36.0／0.36.1／0.37.0／0.37.1／0.38.0／0.39.0）全部通过。
- 官方原包零补丁编译：`BUILD_EXIT=0`，`error C` / `error LNK` / C1083 / C2065 / C3861 / C2039 / `fatal error` / `Traceback` 全 0，C4819=0；worker `11,655,680 B / 3f63f89984cedd9c12d5a4e47b1ca5f60ac91bc3599507be2c18e71a36638287`。
- 包一致性 `2346/2346`，`real_diff=[]`，`eol_only=[]`，`missing=[]`；注册指纹 10/10 一致。
- 工具数 111，BACKLOG 计数一致，六版 `previous_release_commit` 均取上一版真实发布提交（未误用回填提交）。
- 官方门禁：assets+body `exit 0`；21 类记录门禁负例全部捕获；source-zip 6 类篡改全部 `exit 1`，正确/未改动 `exit 0`；反向资产闸门 1/1/0；fourref 四处发布引用一致。
- BUG-170 **功能本身是正确的**：`test_stale_session_diagnosis_triggers_on_minus_four_with_alive_process`、`test_stale_session_diagnosis_silent_when_connected_or_no_process`、`test_force_new_session_argument_guards`、`test_session_candidates_explicitly_marked_diagnostic_only` 在干净树与本机均通过。本文反馈的是**测试的稳定性**，不是 stale 诊断功能的实现错误。

## 3. P1 详细复现与根因

### 3.1 失败的断言

测试文件：`tests/unit/test_feedback0360_fixes.py`（20534 B，SHA256 `fe12777f29f618308a0733cdf1b2f76b3d68e27102515de138a1627accb40c7c`）。

```text
FAIL: test_drive_stale_session_without_and_with_force_new_session
  (tests.unit.test_feedback0360_fixes.Bug170StaleSessionAndForceNewTests)
  File ".../tests/unit/test_feedback0360_fixes.py", line 123, in test_drive_...
    self.assertTrue(st1.get("stale_session_detected"))
AssertionError: None is not true
```

失败行对应测试第一段场景（无 `force_new_session`）：期望 `coord1._drive(...)` 在 alive 进程 + `-4`/`PRO_TK_BAD_CONTEXT` 探测下，状态为 `timeout` 且发布 `stale_session_detected=True`。

### 3.2 根因：固定 0.3 秒 deadline 与多阶段 `_drive()` 竞争

测试用绝对墙钟 deadline 驱动 `_drive()`：

```python
# tests/unit/test_feedback0360_fixes.py:119
coord1._drive(settings, True, creo_startup.time.monotonic() + 0.3)
```

而 `_drive()` 在发布 stale 诊断前要串行走完多个阶段（`creo_startup.py`）：

```text
checking → waiting_for_channel → building_worker → connecting → (native probe: -4) → stale 诊断发布
```

`bridge.toolkit_lock()`（`startup_build`）与 `bridge.build_native()` 虽被 `patch.object` 替换，但 `panel_session_guard.require_clear()`、`read_startup_state()`、`_publish()` 写 `state.json` 等仍有真实文件 I/O；`inventory` / `process_snapshot` / `session_status` 的 mock 返回也需经过调用栈。只要这些步骤合计耗时接近或超过 0.3 秒，`_drive()` 就会在 `connecting` 之前或刚进入 `connecting` 时命中 preparation/连接预算到期，直接发布 `timeout` 并返回，**根本不到达调用 `_stale_session_diagnosis()` 的分支**，于是 `stale_session_detected` 保持缺省 `None`。

### 3.3 官方干净树采样证据（无本机污染）

在 `_creo_update_tmp/0.39.0/clean_pkg_v11/MCP_CREO_MechDog/`（从官方 `source.zip` 全新解压、无 `toolkit.lock`、无 `panel_session_guard.json`、无 `.pyc`）连续 15 次运行该单一测试：

```text
CLEAN_FLAKY pass= 11 / 15 fail= 4
  run 0  FAIL  checking->waiting_for_channel->building_worker->connecting->timeout
  run 6  FAIL  checking->waiting_for_channel->building_worker->connecting->timeout
  run 8  FAIL  checking->waiting_for_channel->building_worker->connecting->timeout
  run 10 FAIL  checking->waiting_for_channel->timeout
  （其余 11 次 OK）
```

- 失败序列全部在 `connecting` 或更早阶段就 `timeout`，确认未进入 stale 诊断分支；成功序列则继续到 `waiting_for_connection → starting → ready`。
- 用同一测试、把 deadline 放宽到 `monotonic() + 5.0`，状态序列变为 `...→connecting→...→timeout`，且 `stale_session_detected=True`，证明**功能正确、仅时间预算不足**。
- 强制 `bridge.toolkit_lock` 抛 `ToolkitBusy`，干净树中该测试在**同一行 123** 失败，进一步确认失败来自「preparation 未如期完成 → 提前 timeout」这一条路径。
- 本机连续 5 次运行该模块全部失败，但这是本机根目录残留状态放大了时序；**官方干净树 26.7% 的失败率已足以证明缺陷独立于本机环境**。

### 3.4 引入版本定位

逐版官方 `source.zip` 检索 `tests/unit/test_feedback0360_fixes.py`：

```text
0.36.0 / 0.36.1 / 0.37.0 / 0.37.1 / 0.38.0 : 不存在
0.39.0 : 存在，且含 "monotonic() + 0.3"
```

差异链 `0.38.0→0.39.0` 的 `added` 列表明确列出该文件。因此这是本版新引入的回归，不是历史遗留。

## 4. 修复建议（供作者参考）

1. 不要用墙钟绝对 deadline（0.3 秒）断言一个需要跨多个阶段、含文件 I/O 的异步协调器的中间状态；改为注入可控的假时钟 / 显式触发阶段推进，或轮询等待 `stale_session_detected` 出现并设一个宽松上限（如 2–5 秒）。
2. 若必须保留 0.3 秒场景，应把 `_drive()` 中 preparation 的 `panel_session_guard.require_clear()` 与 `read_startup_state()` 也一并 mock，使被测路径只剩状态机逻辑，消除真实 I/O 抖动。
3. 把 `assertEqual(st1["state"], "timeout")` 与 `assertTrue(st1.get("stale_session_detected"))` 拆成两个独立等待条件，并为 `stale_session_detected` 单独设超时，避免把「阶段恰好没走完」误判为「功能缺失」。

## 5. 本轮未发现的其他问题

除上述 P1 外，本轮按标准流程核对的项目均为正项或符合设计：四附件四方哈希、六版发布链（annotated tag → tag object → release commit → backfill → main）、逐版差异链、官方原包零补丁编译、包一致性、注册 10 项指纹、工具 111、BACKLOG 一致、逐 ID 交付表与快照一致、release body 与 seed 摘要、BUG-144/DEV-099/BUG-142 上轮闭环、门禁 21 类负例、source-zip 6 类篡改、反向闸门、fourref 四处引用。上轮（0.35.5／0.32.0）反馈的问题保持闭环。

## 6. 证据归档

完整证据（定版 JSON、四附件校验、差异链、编译日志、静态核对、门禁/篡改/反向闸门、fourref、单测与本次 flaky 采样脚本及日志）已归档至本地 `_local/update-0.39.0/`。关键复现脚本：

- `_creo_update_tmp/0.39.0/clean_flaky_probe_v11.py` + `clean_flaky_probe_v11_result.json`：官方干净树 15 次采样与失败序列。
- `_creo_update_tmp/0.39.0/publish_trace_v11.py` + `publish_trace_v11_result.json`：0.3 秒 vs 5.0 秒 deadline 的状态序列对照。
- `_creo_update_tmp/0.39.0/busy_causal_probe_v11.py`：强制 `ToolkitBusy` 在干净树复现同一断言失败。
