# 2026-11-24_CREO_0.43.1_新增Creo9-10专有SDK头文件入库与DEV092唯一例外口径不一致

> 反馈对象：MCP_CREO_MechDog **0.43.1**（`main@380a46d`，2026-11-24 17:39 +0800）
> 环境：Windows 10 x64 19045 / Python 3.13.x x64 / MSVC + Windows SDK / Creo 9.0.0.0 Toolkit SDK（原生仅编译通过，未做 Creo 9 实机建模）
> 基线：0.39.0（`193b892`）。本版跨 **5 个版本**（0.40.0 / 0.41.0 / 0.42.0 / 0.43.0 / 0.43.1）/ 30 次提交 / **930 个文件 / +416131 行**，交付 BUG-171~174、175~178、179~182、183~185、BUG-017 逐阶段诊断及 FEAT-078~083（详见台账）。
> 性质：**产品功能本轮零缺陷，验证全部通过**。本反馈聚焦本轮升级过程中发现的一处**工程治理 / 合规口径一致性问题**，供作者评估是否需要补齐登记或调整入库策略。

---

## 一、本轮更新与验证结果（全部通过）

| 步骤 | 命令 / 动作 | 结果 |
| --- | --- | --- |
| 拉取 | `git fetch --tags origin main`（后台，9m16s，网络慢） | 新增 `v0.40.0`~`v0.43.1` 五个标签；`origin/main` = `380a46d`；无残留锁 |
| 运行时保护 | 备份四件运行时文件 → 后台 `checkout -B main origin/main`（4m49s） | 成功；`version.py` = 0.43.1；四件完好，`session_activity.json` 保持取消跟踪 |
| 依赖 / 包 | `pip install -r requirements.lock.txt`、`pip install --no-deps --editable .` | 成功；包从 0.39.0 升为 0.43.1 |
| 种子库 | `python seeds.py --install` | 成功；9 个种子齐全 |
| 原生编译 | `python bridge.py build` | 成功；`build/creo_worker.exe`（11,722,752 字节）正常产出 |
| MCP 契约门禁 | `test_mcp.py --protocol-only`、`--offline` | 均 exit 0；`tool_count=111, capability_contract_verified=true, capability_pages=2`（BUG-151 修复持续有效） |
| MCP 冒烟（自建脚本） | stdio 列工具 + `creo_capabilities` + `creo_check_environment` | **111 个公开工具**（持平）；`version=0.43.1`、`ready_to_build=true`、`has_reconcile=true` |
| 全量单测 | `python tools/test_unit.py`（PATH 含 PortableGit、`PYTHONPATH=""`，后台，全程零并发） | **4495 项 / 0 failures / 0 errors / 4 skipped / exit 0 / 1818.30s**；`run_id=f5b7d481…`，报告与 `unit_test_run.json` 同版本、同 commit、同源码指纹 `ef842bb4…` |
| 独立验收脚本 | `test_update_check.py --network-failure`、`test_model_reconciliation.py --offline` | 均 exit 0；前者 `success=true, tool_count=111, current_version=0.43.1` |

本轮严格保持"全量单测期间零并发"。0.40.0~0.43.1 全部新改动（恢复超时/重复检查、圆角传播与诊断、G2 曲率验证、B 样条截面面积、JPEG 正交视图、rib 逐阶段诊断等）未见回归。

---

## 二、核心问题：新增 Creo 9/10 专有 SDK 头文件入库，与 DEV-092"唯一例外"口径不一致（P3，治理/合规一致性）

### 2.1 现象

0.39.0 → 0.43.1 的 930 个变更文件中，**829 个是 PTC 专有头文件**，作为新目录正式纳入 Git 跟踪并推送到公开 GitHub 仓库：

| 目录 | 头文件数 | 目录体积 | 附带材料 |
| --- | --- | --- | --- |
| `references/creo9.0.0.0-sdk/` | 413 | 8.8 MB | README、`includes.zip`；**无 `manifest.json`** |
| `references/creo10.0.0.0-sdk/` | 415 | 7.9 MB | 仅 README；**无 `includes.zip`、无 `manifest.json`** |
| （对照）`references/creo13.4.0.0-sdk/` | 433 | 9.4 MB | README、`includes.zip`、**`manifest.json`（逐文件 SHA256）** |

`git ls-files references/` 现共 **1267 个文件`；`git diff --stat` 的 +416131 行绝大部分来自这批头文件。

### 2.2 与项目既定口径的不一致

`AGENTS.md` 第 103 行（2026-11-19 用户指定，_DEV-092_）原文明确：

> 用户指定的**唯一例外**（DEV-092）：允许将用户提供的 `Creo13.4.0.0/includes.zip` 及其 433 个原始头文件保存在 `references/creo13.4.0.0-sdk/`……该目录保留原始版权声明、原 ZIP 与逐文件 SHA256……**此例外不扩大到其他 SDK**、许可数据或本次未授权的实机操作。

对照新增的两个目录，存在三处口径落差：

1. **授权边界**：DEV-092 明文是"唯一例外 / 不扩大到其他 SDK"，而 creo9/creo10 两个新 SDK 目录的入库在 `AGENTS.md` 中**没有对应的例外登记或用户授权说明**。BUG-017 工作卡把 Creo 9 头文件记为"用户提供的参考头文件"、Creo 10 头文件记为"来自本机 `D:/Program Files/PTC/...`"，但这两处属于工作卡内叙述，**未同步为 `AGENTS.md` 的正式例外条款**。是否需要、以及如何扩大例外，建议由作者与用户确认后明确写回约定。
2. **完整性材料不齐**：13.4 目录有 `manifest.json` 逐文件 SHA256 与原始 `includes.zip`；新增的 creo9 **缺 manifest.json**、creo10 **既无 manifest.json 也无 includes.zip**。若这批头文件同样作为"开发查证资料 / 逐字节保留"收敛，建议与 13.4 对齐补齐清单，便于后续校验是否被改动。
3. **排除范围的边界**：作者做得对的部分应肯定——`.gitattributes` 第 124-132 行已为 creo9/creo10 配置 `export-ignore`，README 也保留了"适用原 PTC 许可"的原始版权声明。但 `export-ignore` 只作用于 `git archive`（源码包 / Release 附件），**不阻止 `git clone` 取得这些头文件**；它们已随提交历史进入公开仓库。这一点是否符合 PTC 头文件再分发的许可约束，建议在登记例外时一并确认。

### 2.3 可观测的工程影响（次要）

这批头文件使仓库克隆 / 更新成本显著上升：本轮实测 `git fetch` 从上次小版本的约 9 秒增至 **9m16s**，`checkout` 从约 1 秒增至 **4m49s**，`.git` 目录现约 36 MB。这属于 SDK 头文件入库的直接结果，不影响产品运行，但对每次跟进升级的用户是真实成本。若这些头文件仅为个别开发查证用途，可评估是否改为不入库、仅保留校验清单与获取途径说明。

### 2.4 为什么反馈

这不是运行时缺陷——本轮产品功能、编译、单测、工具数门禁全部通过。反馈点是**工程治理与合规口径的自洽性**：`AGENTS.md` 刚声明"唯一例外、不扩大到其他 SDK"，同期新增的两个 SDK 目录却未按同等规格登记与收敛。建议二选一处理：

- 若确有授权且希望保留：在 `AGENTS.md` 补一条明确例外（注明来源、授权、适用版本），并为 creo9/creo10 目录补齐 `manifest.json`（逐文件 SHA256）与原始 `includes.zip`，与 13.4 对齐；
- 若不希望扩大例外：将这两个目录移出公开仓库（保留在 `.gitignore` 的本地资料区），仅在文档中记录来源与校验值。

---

## 三、次要观察（不作为缺陷）

- **全量 skipped=4**：均为环境依赖用例，属跨环境差异；作者工作卡记录 4495 tests OK (skipped=6)，跳过数口径略有出入，不影响通过结论。
- **备份 `client-config.json` 时再次出现 0 字节中间文件**：常驻 MCP 进程占用导致 `cp` 被 SIGTERM 打断，已用编辑方式补齐、原文件完好；属本机操作现象，与产品无关。
- **首次自建冒烟脚本读错字段**：`ready_to_build` 属于 `creo_check_environment` 返回、不在 `creo_capabilities` 顶层；更正脚本后通过，非产品问题。

---

## 四、未验证范围（按会话纪律保留）

- Creo 9 实机建模 / Toolkit 连接：本机 Creo 9 SDK 仅原生编译通过，实机建模未验；作者实机证据在 Creo 10.0.0.0 / release 42。
- Creo 10/12/13 实机、WorkBuddy 黑盒 MCP 验收：本轮未做。
- 829 个头文件的**许可再分发合规性**本反馈不作法律判断，仅提示口径不一致，交由作者与用户确认。
- 若在本机 WorkBuddy 使用当前 111 个工具，需重启 MCP 连接器刷新工具清单。

---

## 五、结论

0.43.1 是一次**干净的升级**：产品运行时、原生编译、种子、全量单测（4495 全绿）、契约门禁与工具数门禁（111）全部通过，本批 0.40.0~0.43.1 的建模修复与 BUG-017 诊断增强未见回归，BUG-151 修复持续有效。

本轮唯一需要作者留意的是一处**治理 / 合规口径一致性问题（P3）**：新增的 829 个 Creo 9/10 专有 SDK 头文件进入公开仓库，但 `AGENTS.md` DEV-092"唯一例外、不扩大到其他 SDK"未同步登记，且缺 `manifest.json` 逐文件 SHA256（13.4 有）。产品本身无需为此改动，建议按 §2.4 补齐登记与清单，或调整入库策略。
