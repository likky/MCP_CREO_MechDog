# DEV-092 T1/T2/T4 软件层实施证据（2026-11-19）

本文件是 [EVIDENCE](EVIDENCE.md) 之后的新增证据。历史原件与 EVIDENCE.md 保持原字节，不在此改写。

## 环境与基线

- 工作目录：`E:/Projects/MCP_CREO_MechDog`；分支 `codex/dev-092-creo13-assembly-plan`。
- 起始提交：`db1e43b`（DEV-092 资料与交接任务）；本次实施提交：`2f28f67`；版本 0.27.0。
- 工作区：改动本批源码与文档后 dirty；未跟踪 `.trae/`、`underwater_plan.json` 保留，未提交。
- 环境：Windows x64、Python 3.12.14、ruff 0.17.0、clang-format 23.1.3。
- 受测源码指纹（`tools/dev_check.py` 记录）：`9692a6b34eb07c3b46ad8680c2fb301ecd6cd6d4dc8ec4c132113dad8d3469dc`。
- 未构建产品执行器、未启动或连接 Creo、未做故障注入、未清锁或 unknown 保护、未合并 main、未发布。

## SDK 参考目录复核

- `references/creo13.4.0.0-sdk/manifest.json` 声明 `header_count=433`、`headers_total_bytes=7522183`。
- 逐文件 SHA256 复核：433 个文件全部命中，0 处不符，合计 7,522,183 字节，与清单一致。
- 该目录仍不参与产品构建、常量生成、公开源码包或发布附件。

## 修改内容

| 任务 | 文件 | 结果 |
| --- | --- | --- |
| BUG-133 / T1 | `native/assembly_pose.h`、`src/creo_mechdog/rotation_admission.py`、`src/creo_mechdog/schema.py`、`src/creo_mechdog/failure_context.py`、`native/advanced.cpp`、`native/generic.cpp`、`src/creo_mechdog/job_projection.py` | 显式 `rotation_tolerance` 贯通两层，默认 `1e-6`、上限冻结 `1e-3`；原生改用 `%.9g` 数字文本；回执与失败回显发布有效容差 |
| FEAT-012 / T2 | `src/creo_mechdog/schema.py`、`native/assembly_pose.h`、`native/advanced.cpp`、`native/generic.cpp`、`src/creo_mechdog/capabilities.py`、`docs/REFERENCE_SYNTAX.md` | `rotation_convention="column"` 只转置一次；两层测规范行矩阵；回执区分解算约定与输入约定 |
| DEV-092 / T4 | `src/creo_mechdog/schema.py`、`native/advanced.cpp`、`native/generic.cpp`、`src/creo_mechdog/failure_context.py`、`src/creo_mechdog/job_projection.py`、`docs/REFERENCE_SYNTAX.md` | 明示整组替换与 20 条只属单组件；预解析失败给 `failed_constraint_index`/`failed_constraint_type`/`constraint_stage`，整组求解失败索引 null 且 `constraint_reason="solver_failed"` |
| FEAT-045 / T3 | `docs/work-items/FEAT-045.md`、本目录 | 仅离线查证测量语义，未实现字段、未连接 Creo |

## 回归与结果

先补失败回归、确认现状失败，再实施：

1. `python tools/test_assembly_pose.py`（修改前）：`build_exit_code=0`，运行退出 `3221226505`（断言触发的进程终止）——证明原生固定 `1e-6` 拒绝 28° 六位小数矩阵。
2. `python -m unittest tests.unit.test_rotation_admission`（修改前）：2 failures + 1 error（`admission_status()` 不接受容差、缺少上限常量、错误文本不含 `rotation_tolerance`）。
3. 实施后同一命令：`python tools/test_assembly_pose.py` → `build_exit_code=0`、`success=true`、运行退出 0；被测文件 SHA256：
   - `tests/native/test_assembly_pose.cpp`（`221be6112b0225f05eba6bbb3a04e2338f169b00275f3c2529c3c075b222f8b6`）
   - `native/assembly_pose.h`（`8f0d72bcbe1352cee8db88e619ef023e4578f85057ee6230f656625155b6a8c0`）
   - `native/third_party/json.hpp`（`aaf127c04cb31c406e5b04a63f1ae89369fccde6d8fa7cdda1ed4f32dfc5de63`）
4. 专项单测（87 项）：`python -m unittest tests.unit.test_rotation_admission tests.unit.test_assembly_matrix_poses tests.unit.test_assembly_pose tests.unit.test_assembly_pipeline_requests tests.unit.test_assembly_constraint_semantics tests.unit.test_session_assembly` → `OK`。
5. 统一检查：`python tools/dev_check.py --work-item BUG-133` → `success=true`、`unit_tests=passed`、`lint_findings=0`、`unformatted_files=0`（C++ 61、Python 533 个文件），`native_validation=not_run`。

## 数值断言

- 合成 28° 六位小数矩阵 `[[0.882948,0.469472,0],[-0.469472,0.882948,0],[0,0,1]]`：`max |R Rᵀ−I| = 1.1294880000178864e-06`。默认 `1e-6` 拒绝；显式 `1e-5` 接受且输出逐值不变；`1e-7` 拒绝。
- 上限：`1e-3` 接受；`1e-3 + 1e-9`、`1.0` 拒绝；反射矩阵配 `1.0` 拒绝。
- 列约定 90° Z：`R=[[0,-1,0],[1,0,0],[0,0,1]]`、`T=[7,-8,9]`、点 `[2,3,5]` → `[4,-6,14]`；同数组缺省为行约定时结果不同。
- 阈值附近 column 样例：自身行残差 `9.62666e-7`，规范（转置）行残差 `1.023309e-6`；两层都按后者判断，默认拒绝、`1e-5` 接受。

## 未验证（不能由本次结果外推）

- 产品执行器构建（`bridge.py build`）与 Creo 实机：新建/重定位放置、原生测量、约束求解、revision、保存重载、失败回滚。
- Creo 13.4.0.0 与 0.26.0 反馈环境；本机 Creo 12.4 结果也不外推。
- Creo 内核是否接受放宽到 `1e-5` 的六位小数矩阵——两层门槛一致只说明契约一致。
- T3 逐实例 `bbox_world_mm`、`bbox_status`、逐面 `area_mm2` 字段与分页/单位/失败态回归。
- T5 固定快照与配合语义、parallel/distance 正向依据、22 条原样回放。
- WorkBuddy 黑盒验收（本轮为开发者离线验证，两者分别记录）。
