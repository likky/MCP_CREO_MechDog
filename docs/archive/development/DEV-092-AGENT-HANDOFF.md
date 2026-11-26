# DEV-092：另一 AI agent 接手任务

日期：2026-11-19。当前用户要求建立计划任务，由另一 AI agent 处理；本轮只准备资料与交接，不执行产品实现，也不创建/启动另一聊天或外部 agent。

## 接手基线与资料

- 工作目录：`E:/Projects/MCP_CREO_MechDog`。
- 分支：`codex/dev-092-creo13-assembly-plan`。基于最新主干 0.27.0 的 `f6da6334c38007e265bf75cfb3891a62a021963f`；首批分析提交 `cff1f49280789241e56d175b2596ef2c8640daa8`。接手时先检查当前分支/HEAD/diff，保留用户及其他 agent 的修改，不 reset 或切回旧 BUG-120 实现。
- 必读：[AGENTS](../../AGENTS.md)、[DEV-092 工作卡](../work-items/DEV-092.md)、[BUG-133](../work-items/BUG-133.md)、[详细实施计划](../superpowers/plans/2026-11-19-dev092-creo13-assembly.md)。适用项目技能：[creo-mechdog-dev](../../.agents/skills/creo-mechdog-dev/SKILL.md)。
- 反馈原件与已有离线复现：[EVIDENCE](../validation/feedback-creo13-assembly-2026-11-19/EVIDENCE.md)。该文档和报告属于已提交的历史证据，保留原字节；后续证据新增文件，不改写历史。
- SDK：[说明](../../references/creo13.4.0.0-sdk/README.md)、[逐文件校验清单](../../references/creo13.4.0.0-sdk/manifest.json)，可直接 `rg` 检索 `references/creo13.4.0.0-sdk/includes/`。

## 计划任务与执行顺序

本表是 DEV-092 主计划的执行索引，不另立重复台账；主状态以 BACKLOG/工作卡为准。标记“待执行”均不表示能力已交付。

| 任务 | 状态 | 交付物与判断标准 | 依赖 |
| --- | --- | --- | --- |
| DEV-092/T0 资料交接 | 已完成 | 原 ZIP、433 个头文件与 SHA256 清单在项目；任务入口、原始报告和分析可定位；资料排除公开源码包 | 本轮交付 |
| BUG-133 / T1 容差贯通 | 待执行，第一优先 | 先自行查证并冻结容差上限或独立刚体判定，记录依据/兼容影响；再使 Python、原生创建/重定位/回执使用同一有效容差。默认 `1e-6` 不变，合成 28°矩阵显式 `1e-5` 的纯 C++ 回归通过；反射/缩放不因超大容差被放行 | 不依赖原始液压缸；按主计划 T1 |
| FEAT-012 / T2 显式矩阵约定 | 待执行 | 明确 row/column 输入、仅转置一次、两层按同一规范矩阵准入；已知点和阈值附近舍入矩阵测试通过，旧 row/Euler 兼容 | T1 契约已冻结；先更新 FEAT-012 卡 |
| DEV-092 / T4 约束边界与诊断 | 待执行 | 明示单组件整组替换和真实数量限制；可确知的预解析失败给 index/type/stage；整体求解失败保留原始错误，不伪造具体冗余/冲突原因 | 软件说明/离线部分可先做；与 T1/T2 共享文件顺序集成 |
| FEAT-045 / T3 实例几何检查 | 待查证后实现 | 离线先核实 bbox 变换/平移/单位/排除范围；接入逐实例世界 bbox 与逐面面积；重复实例、嵌套、单位、null/失败、分页有回归，实际几何及重载另行验收 | 以原生测量独立验收；实机部分须当次确认 |
| DEV-090 / FEAT-068 / T5 约束语义与22条回放 | 等待输入/实机依据 | 分清固定快照、驱动位姿的配合和只读关系检查；取得最小 FIX/配合、parallel/distance 正向依据；原样总装再核 22 条完整引用、几何、自由度、回滚与重载 | 未提供说明书8.2/8.5、9件完整R/T/PRT、22条引用/方向/offset、原始回执；不能猜补 |

推荐先完成 **T1 → T2 → T4** 离线实现，再推进 T3 与获得当次许可的实机步骤；T5 的原始输入缺口不应阻塞独立可做的前几项。T3/T5 查证有结果后才能决定新写模式或解除 named gap，不预先承诺 `keep_fixed`、`append`、parallel/distance 全可用。

## 接手后的第一批动作

- [ ] 读取上述文件，检查当前工作区；起始 `.trae/`、`underwater_plan.json` 保留，不纳入提交。
- [ ] 校验 SDK ZIP 与 manifest 的 433 个文件；保留版权及原字节，不格式化，不加入产品 SDK 搜索路径。
- [ ] 从 BUG-133/T1 开始。容差护栏是需由开发 AI 查证、提出并记录的技术决策，不能把未定义上限留作编码者随意猜值，也不要让维护者代做技术取证。
- [ ] 先补生产 helper 的失败回归，确认当前失败，再修改；完整步骤与已知矩阵/坐标预期按主计划执行。
- [ ] 完成一项后回填工作卡、BACKLOG 和本次新增证据，记录提交、dirty 状态、源码指纹、命令、实际环境及未测范围，再进入下一项。产品行为改动涉及 FEAT-012/045/DEV-090 等时先补其实施登记。

## 测试与权限边界

可以离线进行源码/SDK 查证、Python unittest、SDK 无关 C++ 数学 harness 和统一开发检查。Python 命令使用仓库 `.venv/Scripts/python.exe`；实机脚本不能为了补证据直接执行。

```powershell
.\.venv\Scripts\python.exe -m unittest tests.unit.test_assembly_pose tests.unit.test_rotation_admission tests.unit.test_assembly_matrix_poses tests.unit.test_assembly_constraint_semantics tests.unit.test_session_assembly -v
.\.venv\Scripts\python.exe tools/test_assembly_pose.py
.\.venv\Scripts\python.exe tools/dev_check.py --work-item BUG-133
```

上述是后续执行命令，不是本轮新测试结果；已有的 41 项通过和纯 C++ 反例只能作为旧基线。`tools/test_assembly_pose.py` 不链接 Toolkit；不要把 `bridge.py build` 或其他实机/SDK 构建命令混同为该离线 harness。

本次用户没有授权启动/连接 Creo、构建产品执行器、建模或保存重载，也没有授权故障注入、结束进程、清锁/unknown。后续确需实机时，先准备具体可评审用例，再按 AGENTS 获得当次范围确认。Creo 12.4 成功不外推为 Creo 13.4 成功；WorkBuddy 最终验收与开发者本地测试分别记录。

## 给用户的交付要求

报告实际完成的任务和可见行为、提交、验证命令/结果、实际环境与未测项；将“软件层已修”和“CAD 几何已验收”分开。按独立任务提交在当前开发分支，不擅自合并/推送 main 或发布；若后来获准合入 main，必须按项目规则完成版本和对应 Release 全流程。

可把下面这段直接交给另一个 AI agent：

> 请在 `E:/Projects/MCP_CREO_MechDog` 的 `codex/dev-092-creo13-assembly-plan` 分支接手，先读 `docs/development/DEV-092-AGENT-HANDOFF.md` 和它链接的工作卡、详细计划及 AGENTS，按 T1→T2→T4 开始离线实现并记录验收。SDK 原件在 `references/creo13.4.0.0-sdk/`，先校验 manifest。T3 先查测量语义；T5 原始模型和完整引用缺失时如实标未验证，不阻塞独立任务。不要把旧离线证据当本次结果；未经用户当次明确确认，不构建产品执行器、不启动或连接 Creo。
