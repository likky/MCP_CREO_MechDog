# BUG-151：`tools/test_mcp.py` 与 capabilities 分页契约漂移修复计划

> **For agentic workers:** 按阶段顺序执行；阶段 1 登记完成后才改代码。原生构建、Creo 连接沿用 2026-11-19 常设授权，但本计划不改原生代码，无需 `bridge.py build`。不要改写历史文档（`docs/RELEASE_NOTES_0.22.md`、`docs/work-items/DEV-002.md`）中的旧命令与旧结论。

**Goal:** 让项目文档推荐的真实 stdio 冒烟入口 `tools/test_mcp.py` 在当前 `creo_capabilities` 分页契约下通过，并让“验证脚本与产品契约漂移”这一类问题在常规门禁中自动暴露，而不是跨 30+ 版本静默失效。

**Architecture:** 只动验证层，不动建模链路。把 `creo_capabilities` 的契约期望集中到一个可单测的共享模块，脚本不再自己写字段断言；门禁由单元测试承担，不把会启动服务/协调器的脚本塞进 `dev_check` 的离线脚本清单。

**Tech Stack:** Windows x64、Python 3.12、`unittest`、`mcp` stdio 客户端、Ruff；无需 Creo、不编译原生。

**Spec:** 外部反馈 `C:\Users\Administrator\Desktop\2026-11-22_CREO_0.35.8_自带stdio冒烟脚本test_mcp未适配capabilities分页API致验证必失败.md` §2；回归参照 [BUG-138](../../work-items/BUG-138.md)（验收脚本硬编码工具数、失败被 TaskGroup 掩盖、门禁不覆盖）。

---

## 0. 现状核对（2026-11-23，本机 `main@b54bff6` / 0.35.8）

以下均为本轮实测，不是引用反馈：

| 项 | 实测结果 |
| --- | --- |
| 失败复现 | `.venv\Scripts\python.exe tools\test_mcp.py` → `tools\test_mcp.py:71 KeyError: 'interpolation'`，栈被 `ExceptionGroup: unhandled errors in a TaskGroup` 包住；耗时 3.2 s，与是否连接 Creo 无关 |
| compact 实际形状 | `families["loft_seed"] = {"enabled": True, "tool": "creo_new_loft_part"}`；整个 compact 页的家庭条目键集合只有 `{enabled, tool, limits_note}`（`limits_note` 来自 DEV-081/F05 的 `surface_loft` 特例） |
| 完整条目位置 | `detail="full", section="families", limit=50` 共 **40 个族 / 2 页**（首页 27 条，`complete=false` + `next_cursor`）；`loft_seed` 在**第 2 页**，12 个字段齐全，`interpolation=["straight","smooth"]`、`section_count_input_range=[2,20]`、`seed_section_count_must_match=True` |
| 契约引入点 | `fab8e0d`（FEAT-044/023/022/006/008）把 `creo_capabilities` 改为默认 `detail="compact"` 分页；`tools/test_mcp.py` 自 `0e92ab7`（DEV-002）后未再改动 |
| 脚本其余断言的当前有效性 | 工具名集合、`loft` 输入 schema（`interpolation` 枚举/默认、`sections` 2–20、`required` 不含 `seed_*`）、`enabled_tool_count`、`disabled_tools_hidden` 均**已通过**（失败发生在其后）；`creo_check_environment().ready_to_build` 本机为 `True`；无效几何仍被拒（`ValueError: Hole 1 intersects or touches the outer boundary`） |
| 未覆盖门禁 | `tools/test_unit.py` 与 `tools/dev_check.py` 都没有调用该脚本；`dev_check` 的离线清单（BUG-138 建立）只有 `test_update_check`、`test_model_reconciliation` 两项 |

**关键判断：产品能力完整，缺陷在验证脚本与门禁覆盖；但“修完断言”只解决一次，必须同时解决“谁会发现下一次漂移”。**

---

## 1. 根因分层

| 层 | 事实 | 修复手段 |
| --- | --- | --- |
| 直接原因 | 脚本按 0.4.2 之前的“无参数返回完整文档”契约断言 `families.loft_seed.interpolation` | 改为 compact 索引断言 + `detail="full"` 分页取回完整条目后断言细节 |
| 结构原因 | 契约期望散落在脚本里，只有“人工运行”才会执行 | 把期望抽到 `src/creo_mechdog/mcp_contract.py`，由单元测试守住 |
| 观测原因 | 失败被 `ExceptionGroup` 包住，报错是 `KeyError` 而不是“契约不匹配” | 脚本失败时输出**人可读的问题清单**，并显式标注“contract drift” |
| 门禁原因 | 该脚本不在任何自动检查里 | 单测进 `tools/test_unit.py` 全量发现路径（自动进 `dev_check`） |

---

## 2. 门禁方案取舍（已定）

| 方案 | 内容 | 结论 |
| --- | --- | --- |
| A（采纳） | 单元测试直接跑共享契约函数，输入用真实 `_capabilities_payload` + 真实分页器 | 毫秒级、无 Creo、无网络、无子进程，进全量单测即进 `dev_check` |
| B（拒绝） | 把 `tools/test_mcp.py --protocol-only` 加进 `dev_check.OFFLINE_ACCEPTANCE_SCRIPTS` | `server.py` 的 lifespan 会 `startup.start()`（配置 `auto_start_creo=true` 时会拉起 Creo）并 `updates.start()` 触网；离线门禁不应有这类副作用 |
| C（补充） | 保留脚本并新增 `--protocol-only`，供无 Creo 环境人工/外部验收 | 采纳，但不入门禁 |

理由：反馈明确接受“至少一条轻量契约测试”；方案 A 满足该要求，且与 BUG-138 的“门禁要能自己报警”同源，但避免把重型副作用塞进每次 `dev_check`。

---

## 3. 分阶段实施

### 阶段 1：登记（先做，不做则后续提交无条目可挂）

1. `docs/work-items/BUG-151.md`，按 [WORK_ITEM 模板](../../templates/WORK_ITEM.md) 精简版：
   - 类型：缺陷（验证工具链）；优先级：P2；分类：`仍需修复`；目标版本：0.35.9
   - 现象（含上面的 `KeyError` 原文）、根因（契约引入点 `fab8e0d` + 脚本停更点 `0e92ab7`）、范围（只改验证层）、验收（§5 矩阵）、未验范围
   - 来源：外部反馈原件路径 + 与 BUG-138 的关系（同一类“验证脚本与产品契约漂移”，本条补的是脚本自身无人运行的问题）
2. `docs/BACKLOG.md`：在 `## 仍需修复` 表新增一行；同步三处计数：
   - 声明行 `当前唯一 ID **214**（BUG **100**…` → `215` / `BUG **101**`
   - `## 使用与计数` 分类表 `仍需修复 7` → `8`
   - 运行 `tools/check_backlog_counts.py` 必须 exit 0
3. 顶部按现有格式加一条 2026-11-23 进展行（简短，细节留工作卡）。

### 阶段 2：共享契约模块 `src/creo_mechdog/mcp_contract.py`（新增，约 90 行）

只放“对外可观察的契约期望”，不放传输细节：

```python
FAMILY_INDEX_KEYS = frozenset(
    {"enabled", "tool", "limits_note"}
)  # DEV-081/F05 的 limits_note 是白名单
LOFT_FAMILY = "loft_seed"
LOFT_TOOL = "creo_new_loft_part"
LOFT_EXPECTED = {
    "interpolation": ["straight", "smooth"],
    "section_count_input_range": [2, 20],
    "seed_section_count_must_match": True,
}
MAX_PAGES = 64


async def capability_contract_problems(compact, fetch_page) -> list[str]:
    """fetch_page(cursor) -> 一页 detail=full&section=families 的 structured_content。"""
```

必须覆盖的检查（每条都返回可读字符串，不抛异常）：

1. `compact["detail"] == "compact"`；
2. `enabled_tool_count` 为正整数、`disabled_tools_hidden is True`、`name`/`version` 为非空字符串；
3. `families` 是 dict，且**每个家庭条目的键 ⊆ `FAMILY_INDEX_KEYS`** ← 这正是本次缺陷的回归护栏；
4. `loft_seed` 的 compact 条目**不含** `interpolation` / `section_count_input_range` / `seed_section_count_must_match`；
5. compact 的 `loft_seed.enabled is True` 且 `tool == "creo_new_loft_part"`；
6. 分页自洽：首页 `detail=="full"`、`section=="families"`、`offset==0`；逐页 `offset` 严格递增、`returned>0`、键不重复；末页 `complete is True`；累计 `total == len(compact["families"])`；超过 `MAX_PAGES` 判失败（防死循环）；
7. 分页取回的 `loft_seed` 完整条目逐字段等于 `LOFT_EXPECTED`。

**为什么用 async + 回调**：脚本侧是异步 MCP 调用，单测侧是同步分页器；把翻页循环放进模块内，才能让“翻页逻辑本身”也被单测覆盖（本次要防的第二个坑就是“只取第一页仍会失败”，因为 `loft_seed` 在第 2 页）。

### 阶段 3：改造 `tools/test_mcp.py`

| 位置 | 改动 |
| --- | --- |
| 第 67–83 行 | 删除 4 条直接取字段的断言，改为：compact 调用一次，`fetch_page` 包装 `creo_capabilities(detail="full", section="families", limit=50, cursor=...)`，`problems = await capability_contract_problems(...)`；`assert not problems, "creo_capabilities contract drift: " + "; ".join(problems)`；成功记 `report["capability_contract_verified"] = True` 与 `report["capability_pages"]` |
| 第 84–89 行 | `report["server"]` 断言保留（compact 顶层仍带 `name`/`version`） |
| 第 90–97 行 | 拆成两条路径：默认（需 Creo 会话）保持 `ready_to_build`/`connected` 断言；`--protocol-only` 只断言 `creo_check_environment` 返回 dict 且含 `ready_to_build` 键（**不断言取值**），并跳过 `creo_session_status`（避免 9 s 探针与需要会话） |
| 第 98–106 行 | 摘要打印改为按模式输出（`session_connected` 仅在非 protocol 模式出现），避免 `KeyError` |
| 第 107–117 行 | 无效几何拒绝断言保留（实测仍是会话无关的准入拒绝），`--protocol-only` 下同样执行 |
| 第 135–158 行 | `creo_get_job` 显式传 `detail="full"`；取值前先断言 `"result" in job`，失败信息提示“分页 full 回执需按 section 读取”，替代裸 `KeyError` |
| 第 167–173 行 | argparse 增加 `--protocol-only`；与 `--create` 互斥（`parser.error`），因为创作路径必须有会话 |

保留 `--classic`（legacy 协议模式）不变。

### 阶段 4：新增 `tests/unit/test_mcp_contract.py`（约 100 行）

用 `unittest.IsolatedAsyncioTestCase`，输入取真实产品数据，不用手写 payload：

| 用例 | 内容 |
| --- | --- |
| `test_real_payload_satisfies_the_smoke_contract` | `server._capabilities_payload(合成 tool_entries)` → `reset_snapshot()` → compact 页 + `capabilities_response(detail="full", section="families", ...)` 作 `fetch_page` → 断言 `problems == []`，并断言 `families` 数量与分页 `total` 一致（当前 40/40、2 页） |
| `test_compact_detail_fields_are_reported_as_drift` | 人为把 compact 的 `loft_seed` 填上 `interpolation` → 问题清单必须点名“compact 索引” |
| `test_wrong_loft_values_are_reported` | 分页取回后篡改 `interpolation` → 必须报 `straight`/`smooth` 期望值 |
| `test_incomplete_pagination_is_reported` | `fetch_page` 永远返回同一种 `next_cursor` → 必须报“未在 `MAX_PAGES` 内完成”，不得死循环 |
| `test_smoke_script_uses_the_shared_contract` | 读 `tools/test_mcp.py` 源码，断言其中出现 `capability_contract_problems`，防止有人再把手写字段断言加回脚本 |

`reset_snapshot()` 必须放 `addCleanup`，否则 `capability_pages` 的 600 s 进程级缓存会污染其他单测。

### 阶段 5：文档

| 文件 | 改动 |
| --- | --- |
| `docs/DEVELOPMENT.md` | 命令清单补两条：`tools\test_mcp.py --protocol-only`（无 Creo 契约检查）与 `tools\test_mcp.py`（需已连接会话）；说明契约由 `tests/unit/test_mcp_contract.py` 守门 |
| `AGENTS.md` | “构建、测试与开发命令”补同一行 `--protocol-only`，给出“真实 MCP 传输下核对工具清单与 capabilities 契约”的一句话定位 |
| `docs/RELEASE_NOTES_0.22.md`、`docs/work-items/DEV-002.md` | **不改**。历史文档按项目规则保留原日期与原结论；新入口写在工作卡与 DEVELOPMENT.md |
| `docs/work-items/BUG-151.md` | 交付后补“修复内容 / 验收证据 / 未验范围” |

### 阶段 6：验证

见 §5。全部通过后再进入阶段 7。

### 阶段 7：版本与发布（合入 `main` 即需 Release）

1. `version.py` 0.35.8 → **0.35.9**（PATCH；公开工具仍 111，`README` 不需改工具数）。
2. 按 `docs/development/RELEASING.md`：发布说明、种子包快照（本次未改种子，仍需按流程重出快照并记录 SHA256）、`tools/package.py`、`v0.35.9` annotated 标签、四附件 + sidecar、`tools/check_release_assets.py --tag v0.35.9` exit 0。
3. `docs/validation/RELEASE-0.35.9.md` 记录提交号、版本、Release 链接、附件校验、环境与未验范围；BACKLOG 该行状态与台账计数同步（交付后行移入完成档案或改为“已交付”）。

---

## 4. 精确改动清单

| 文件 | 动作 | 规模 |
| --- | --- | --- |
| `src/creo_mechdog/mcp_contract.py` | 新增 | ~90 行 |
| `tests/unit/test_mcp_contract.py` | 新增 | ~100 行 |
| `tools/test_mcp.py` | 修改 67–83、90–106、141–143、167–173 行 | ~40 行变更 |
| `docs/work-items/BUG-151.md` | 新增 | 工作卡 |
| `docs/BACKLOG.md` | 新增 1 行 + 三处计数 | 5 行 |
| `docs/DEVELOPMENT.md`、`AGENTS.md` | 各补 1–2 行命令 | 4 行 |
| `version.py`、发布资料 | 0.35.9 | 按发布流程 |

不改动：`server.py`、`bridge.py`、`generic_bridge.py`、`native/**`、`src/creo_mechdog/capability_pages.py`、`tools/dev_check.py`、`tools/test_unit.py`。

特别说明：`capability_pages.py` 的分页实现**不修**。它是产品契约的正确实现，缺陷在脚本侧；改动产品以迁就脚本会把这次教训反向固化。

---

## 5. 验收矩阵

| # | 检查 | 命令 | 判据 |
| --- | --- | --- | --- |
| 1 | 定向单测 | `.venv\Scripts\python.exe -m unittest tests.unit.test_mcp_contract -v` | 6 项全绿（2 正例 + 4 负例）；负例确实报出对应问题 |
| 2 | 语言与离线检查 | `.venv\Scripts\python.exe tools\dev_check.py --skip-unit --work-item BUG-151` | `success=true`，Ruff 0 新增、0 待格式化；离线脚本两项仍 passed |
| 3 | 台账计数 | `.venv\Scripts\python.exe tools\check_backlog_counts.py` | exit 0，`consistent=true`（215 / BUG 101） |
| 4 | 全量单测 | `.venv\Scripts\python.exe tools\test_unit.py` | 0 failures / 0 errors；`tests_run` 较基线 4390 增加 6；`run_id` 与源码指纹一致 |
| 5 | 脚本（无 Creo） | `.venv\Scripts\python.exe tools\test_mcp.py --protocol-only` | exit 0；stdout 只有 `tool_count=111`；写出 `build/mcp_protocol_test.json` 且 `capability_contract_verified=true` |
| 6 | 脚本（真实会话） | `.venv\Scripts\python.exe tools\test_mcp.py` | exit 0；`session.connected=true`；`build/mcp_protocol_test.json` 含 `capability_contract_verified`、`capability_pages=2` |
| 7 | 创作路径（可选） | `tools\test_mcp.py --create --simple` | job `succeeded` 且 `result.saved_file_reloaded_and_verified=true`；仅在已连接会话时执行 |
| 8 | 回归证明 | 临时把 `LOFT_EXPECTED["interpolation"]` 改成错误值或回退脚本为旧断言 | 单测/脚本必须以“contract drift”失败，不能以 `KeyError` 失败（恢复后再跑一次绿） |

已具备的“修复前证据”：2026-11-23 的 `KeyError: 'interpolation'` 复现记录（见 §0），写入 `build/bug151_repro_before.txt` 并在工作卡引用。

---

## 6. 风险与对策

| 风险 | 影响 | 对策 |
| --- | --- | --- |
| 分页只取首屏 | 修完仍在 `loft_seed` 上失败（它在第 2 页） | 单测固定断言 `total=40`、页数 2、末页 `complete=true`；脚本走同一翻页函数 |
| 未来 compact 正当新增索引键 | 单测误报 | 索引键集合集中在 `FAMILY_INDEX_KEYS`，变化时单测失败即提示“这是契约变更，需同步此处与反馈文档”，不是静默放过 |
| `capability_pages` 进程级快照串测 | 其他单测拿到旧 payload | `reset_snapshot()` 放 `addCleanup`；不在测试里改 payload 后复用同一快照 |
| `--protocol-only` 仍会启动协调器 | 在 `auto_start_creo=true` 的机器上可能拉起 Creo | 该模式只用于人工/外部验收，不入 `dev_check`；文档写明“会启动服务 lifespan，建议在无 Creo 或已关闭自动启动的环境使用” |
| 与 BUG-138 门禁职责重叠 | 两套离线脚本清单概念混淆 | 明确边界：`OFFLINE_ACCEPTANCE_SCRIPTS` 放“独立进程验收脚本”，契约单测放 `tests/unit`；本次不扩前者 |
| 只改脚本无法防止再漂移 | 30+ 版本静默失效重演 | 阶段 4 的 `test_smoke_script_uses_the_shared_contract` + 共享模块单一事实来源 |

---

## 7. 明确不做 / 未验范围

- 不改 `creo_capabilities` 的 compact/full 契约，不改分页预算与游标语义。
- 不改历史文档中的旧命令与旧结论；`docs/validation/` 原件不动。
- 不把 `tools/test_mcp.py` 塞进 `dev_check` 的离线脚本清单。
- 不重跑 `bridge.py build`（无原生改动）、不动种子、不连接非本机 Creo。
- 未验（交付时如实标注）：Creo 9 实机、Creo 12.4 实机建模、WorkBuddy 黑盒 MCP 验收；`--create` 路径本轮默认只跑 `--simple` 一例。
