# 2026-11-22_CREO_0.35.8_自带stdio冒烟脚本test_mcp未适配capabilities分页API致验证必失败

> 反馈对象：MCP_CREO_MechDog **0.35.8**（`main@b54bff6`，2026-11-22 20:06 +0800）
> 环境：Windows 10 x64 19045 / Python 3.13.14 x64 / MSVC 19.44 + Windows SDK 10.0.26100 / Creo Parametric **9.0.0.0** Toolkit SDK（原生仅编译通过，未做 Creo 9 实机建模）
> 基线：0.35.5（`919f575`）。本轮跨 **3 个版本（0.35.6、0.35.7、0.35.8）/ 16 次提交 / 86 个文件 / +5319 行**。
> 结论先行：**本轮产品运行时与环境链路全部通过**——依赖、editable 安装、9 个种子、Creo 9 原生编译、MCP stdio（**111 个公开工具**）、全量单测 **4390 项 / 0 failures / 0 errors / 4 skipped** 全绿，独立验收脚本 exit 0。上一轮（0.35.5）反馈的 flaky 时序用例本轮未再出现，确认是偶发抖动。
> **但发现一个确凿的自身问题**：仓库自带的 stdio 冒烟脚本 `tools/test_mcp.py` 未跟随 `creo_capabilities` 的 compact 分页契约变更，任何版本下按项目文档指引运行都会必然 `KeyError` 失败；而全量单测与 dev_check 均不覆盖它，属验证盲点。详见下文。产品能力本身完整，问题在验证脚本。

---

## 一、更新与验证结果（全部通过）

| 步骤 | 命令 / 动作 | 结果 |
| --- | --- | --- |
| 拉取 | `git fetch --tags origin main`（后台） | 新增 `v0.35.6`～`v0.35.8`；`origin/main` = `b54bff6`；前台 checkout 两次被 SIGTERM 留下 `.git/index.lock`，确认无活动 git 进程后清理，后台重跑成功 |
| 运行时保护 | 备份 `session_activity.json`/`seed_registry.json`/`config.json`/`client-config.json` → `checkout -B main origin/main` | 成功；`version.py` = 0.35.8；四个运行时文件均完好，`session_activity.json` 保持取消跟踪 |
| 依赖 | `pip install -r requirements.lock.txt`、`pip install --no-deps --editable .` | 成功；包从 0.35.5 升为 0.35.8；`creo_mechdog`、`creo_mechdog.unit_evidence` 导入通过 |
| 种子库 | `python seeds.py --install` | 成功；`available_count=9` |
| 原生编译 | `python bridge.py build` | 成功；`build/creo_worker.exe`（11,490,816 字节）正常产出 |
| MCP 冒烟 | stdio `server.py` + `creo_capabilities` | **111 个公开工具**（0.35.5 为 110，本版因 FEAT-057/072/073 增至 111）；`enabled_tool_count=111`、`disabled_tools_hidden=true`、`name/version` 元数据正确 |
| 全量单测 | `python tools/test_unit.py`（PATH 含 PortableGit、`PYTHONPATH=""`，后台，全程零并发） | **4390 项 / 0 failures / 0 errors / 4 skipped / exit 0 / 1646.85s**；`run_id=4ec93b7e3e374cd08b0c7f7281cf88ff`，报告与 `unit_test_run.json` 的 run_id、版本、源码指纹 `98ff84c8…` 一致 |
| 独立验收脚本 | `test_update_check.py --network-failure`、`test_model_reconciliation.py --offline` | 均 exit 0；前者 `success=true, tool_count=111` |

说明：本轮严格遵守"全量单测期间零并发"纪律（未跑 dev_check/pip/文件移动），杜绝了历史上因并发导致的子进程 `ModuleNotFoundError` 干扰。

---

## 二、核心问题：`tools/test_mcp.py` 未适配 capabilities 分页契约，必然失败（P2，验证脚本）

### 2.1 现象

按项目文档（`docs/RELEASE_NOTES_0.22.md:83`、`docs/work-items/DEV-002.md:95`、`docs/superpowers/plans/2026-11-02-dev002-batch3-package-migration.md:136` 均把 `tools/test_mcp.py` 作为"真实 MCP 协议 / 会话行为"验证入口）运行：

```
.venv\Scripts\python.exe tools\test_mcp.py
```

在列工具、schema 断言、`creo_capabilities` 调用后必然失败：

```
File "tools\test_mcp.py", line 71, in main
    assert capabilities.structured_content["families"]["loft_seed"]["interpolation"] == [
KeyError: 'interpolation'
ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
```

该失败发生于 0.35.8，且不依赖 Creo 会话状态——在任何环境运行都会复现。

### 2.2 根因（已定位：脚本契约漂移，非产品缺陷）

- `tools/test_mcp.py:67` 以**空参数**调用 `capabilities = await client.call_tool("creo_capabilities", {})`，随后第 69–83 行断言 `structured_content["families"]["loft_seed"]` 直接含 `interpolation` / `section_count_input_range` / `seed_section_count_must_match` 等细节字段。
- 但 `creo_capabilities`（`server.py:835-841`）自 **0.4.2 起默认 `detail="compact"`**：commit `fab8e0d`（FEAT-044/023/022/006/008）引入分页后，`families` 变成**精简索引**，每一项仅含 `enabled` / `tool`。实测 compact 返回：
  ```
  families["loft_seed"] = {"enabled": true, "tool": "creo_new_loft_part"}
  ```
  没有 `interpolation` 等字段，故 `KeyError`。
- `tools/test_mcp.py` 自 commit `0e92ab7`（DEV-002）后**再未改动**，其断言仍停留在 0.4.2 之前"无参数返回完整文档"的旧契约。

**产品能力完整，已核验**：用 `creo_capabilities(detail="full", section="families")` 分页（共 2 页）取回 `loft_seed` 完整条目，12 个字段齐全，且值与脚本期望完全一致：
```
interpolation = ["straight", "smooth"]
section_count_input_range = [2, 20]
seed_section_count_must_match = true
```
因此这不是能力回退或数据丢失，纯粹是验证脚本没跟上自己 API 的契约变更。

### 2.3 为何长期未被发现（验证盲点）

- `tools/test_unit.py` 与 `tools/dev_check.py` 均**不调用** `tools/test_mcp.py`（已 grep 确认），全量 4390 项全绿也覆盖不到这个失败。
- 结果是：脚本在 **0.4.2 → 0.35.8 跨 30+ 版本**一直失效，却没有任何门禁报警。这与历史上已修复的 BUG-138（验收脚本硬编码工具数 82/84、失败被 TaskGroup 掩盖、门禁不覆盖）属同一类"验证脚本与产品契约漂移"问题。

### 2.4 建议修复（P2）

二者取一，建议同时做第二项防漂移：

1. 把 `test_mcp.py` 中 `creo_capabilities` 的断言改为适配新契约：要么按 `detail="compact"` 只断言 families 索引（`enabled`/`tool`），要么用 `detail="full"` + `section="families"` 分页取回完整条目后断言细节字段（注意处理 `next_cursor` 翻页）。
2. 把这个 stdio 冒烟脚本纳入 `dev_check` 或打包门禁的定期执行清单（或至少一条轻量契约测试），避免再次出现"文档推荐的验证脚本长期失效却无人知晓"。
3. 顺带检查脚本中其他基于旧 `creo_capabilities` / job 回执结构的断言，避免修完一处又暴露下一处。

---

## 三、次要观察（不作为缺陷）

- **上一轮 flaky 用例本轮通过**：0.35.5 反馈的 `test_two_controllers_share_one_recovery_archive_and_launch`（2 秒 `Event.wait` 超时）在本轮 4390 项全量中未再失败，进一步印证是偶发调度抖动而非产品缺陷。作者可在有余力时按 P3 放宽等待，但不阻塞发布。
- **前台 git checkout 超时留锁**：本仓库文件较多，前台 `git checkout -B` 两次被 SIGTERM 并留下 `.git/index.lock`；后台执行 + 清理陈旧锁后成功。这是本机操作/环境现象，非产品问题，仅作记录供其他使用者参考。
- **全量 skipped=4**：均为环境依赖（2 项 MSVC 独立 helper、2 项归档作业缺失），与作者发布记录的 `skipped=6`（含符号链接权限等）属跨环境差异。

---

## 四、未验证范围（按会话纪律保留）

- Creo 9 实机建模 / Toolkit 连接：本机 Creo 9 SDK 仅原生编译通过，未做实机建模；作者实机证据在 Creo 10.0.0.0 / release 42。
- Creo 10/12/13 实机、WorkBuddy 黑盒 MCP 验收：本轮未做。
- 若要在本机 WorkBuddy 使用当前 111 个工具，需重启 MCP 连接器以刷新工具清单。

---

## 五、结论

0.35.8 是一次**干净的升级**：产品运行时、编译、全量单测（4390 全绿）、工具数门禁（111）全部通过，上一轮的 flaky 抖动也自然消失，BUG-149/BUG-150 与 FEAT-057/072/073 等本批修复未见回归。

本轮**唯一值得作者处理的是验证脚本 `tools/test_mcp.py` 的契约漂移（P2）**：它是项目文档推荐的真实 MCP 协议冒烟入口，却因 0.4.2 的 capabilities 分页变更而长期必然失败，且无门禁覆盖。修复成本低、价值明确——建议按 §2.4 适配断言并把它纳入门禁，避免验证工具链继续与产品契约脱节。产品本身无需修复。
