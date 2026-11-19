# DEV-092：2026-11-19 装配反馈离线核对证据

## 来源与原件

目录：`C:/Users/Administrator/Downloads/Creo13.4.0.0`，本次实际包含以下两项。反馈报告的日期为 2026-11-18，报告环境声称 Creo 13.4.0.0 / MCP 0.26.0；不是本次实机环境。

| 文件 | 字节数 | SHA256 | 处理 |
| --- | --- | --- | --- |
| [原始评估报告](originals/2026-11-18-Creo13.4.0.0-MCP0.26.0-装配前置评估与矩阵转置陷阱.md) | 21101 | `aad9ffa00c055dfa4a3953ac10003c381391704312d337f911866e3725f8d215` | `shutil.copyfile` 原样复制并逐字节相等检查 |
| includes.zip | 1192827 | `83bc7864d19c75ac721479ac5f6f0e998ad9e3dfe43158f511884033f18c9657` | 仅从原位置读取，不归档 SDK；434 entries，其中 433 个 .h |

没有收到说明书 8.2/8.5、9 件 PRT、原始完整矩阵/平移/体积表、22 条完整引用或原始 MCP 回执。报告内的 P03 残差、P05 bbox、9 件质心仅作为外部数据，未独立复算。压缩包名称不能单独证明 SDK 版本。

## 受测源码与环境

- 已执行 `git fetch origin --prune`；远端主干基线 `f6da6334c38007e265bf75cfb3891a62a021963f`，源码版本 0.27.0。
- 新分支 `codex/dev-092-creo13-assembly-plan` 从该主干建立；原先 BUG-120 分支未合入代码不带入。既有 `.trae/`、`underwater_plan.json` 未跟踪内容保持。
- dirty=true：起始未跟踪内容及本次文档/归档；产品代码未改。
- `creo_mechdog.source_provenance.local_provenance`：611 个 Git 跟踪 Python/原生源码文件，CRLF→LF 规范化；`source_fingerprint=81c014a92b14587b2cfa76f45ed102534c6110409aa17250948786315f746452`，`source_status=complete`。完整逐文件指纹留在本机 `build/dev092_analysis/source_provenance.json`；该范围不含文档或下述临时 probe。
- 本次离线执行环境 Windows / AMD64 / Python 3.12.14。纯数学 probe 使用本机 MSVC C++17，不链接 SDK、Toolkit 库或 Creo。未编译产品执行器、未建立 Toolkit 连接。

## 当前检查

命令均从仓库根目录执行；`python` 指 `.venv/Scripts/python.exe`。

```powershell
python -m unittest tests.unit.test_assembly_pose tests.unit.test_rotation_admission tests.unit.test_assembly_constraint_semantics tests.unit.test_session_assembly -q
```

结果：`Ran 41 tests in 0.290s`，`OK`。这些是当前回归，不覆盖显式容差的原生差异，不能用通过数量证明该缺陷不存在。

### BUG-133 软件分歧反例

合成 28° 旋转保留六位小数（非 P03 原数据）：

```json
[[0.882948,0.469472,0],[-0.469472,0.882948,0],[0,0,1]]
```

- `admission_status` 得到 `orthogonality_residual=1.1294880000178864e-6`。
- Python `validate_operations`：默认拒绝，文本含 `max |R*R^T-I| = 1.129488e-06`；显式 `rotation_tolerance=1e-5` 接受并逐值保留矩阵。
- 使用生产 `native/assembly_pose.h`、仓库内 JSON 库，在 `build/dev092_analysis/rotation_tolerance_probe.cpp` 编译 SDK 无关 probe。构建退出 0，运行退出 0 表示**成功复现预期的原生拒绝**，不是功能修复通过。
- 同样显式 `1e-5` 调 `assembly_rigid_transform`，捕获：`rotation_matrix must be orthogonal within 1e-6 (max |R*R^T-I| = 0.000001); the input is echoed and never repaired, so supply exact orthonormal values`。原生忽略显式容差，同时其文本精度掩盖了小幅超限。

probe 核心代码如下，可在本机 MSVC 环境用 `/std:c++17 /EHsc /I native` 编译；输入与生产 helper 直接相连，不模拟 Creo 行为：

```cpp
#include "assembly_pose.h"
#include "third_party/json.hpp"
#include <iostream>
using J = nlohmann::json;
int main() {
    J matrix = {{0.882948, 0.469472, 0}, {-0.469472, 0.882948, 0}, {0, 0, 1}};
    J op = {{"rotation_matrix", matrix}, {"rotation_tolerance", 1e-5}};
    double transform[4][4];
    try {
        assembly_rigid_transform(op, transform);
        std::cout << J({{"explicit_tolerance", 1e-5}, {"native_accepted", true}}).dump();
        return 1;
    } catch (const std::exception &error) {
        std::cout << J({{"explicit_tolerance", 1e-5}, {"native_accepted", false},
                       {"error", error.what()}}).dump();
        return 0;
    }
}
```

实际构建/执行命令为生成的 `cmd.exe /d /c E:/Projects/MCP_CREO_MechDog/build/dev092_analysis/build.cmd`、`build/dev092_analysis/rotation_tolerance_probe.exe`。构建日志和 JSON 在同一本机目录。无需启动或连接 Creo，未取得 Creo 内核接受放宽容差的证据。

### SDK 与官方语义核对

从 ZIP 原位置读取，并与本机 Creo 12.4.0.0 `Common Files/protoolkit/includes` 相关声明/注释比较：

| 资料 | 已确认 | 未证明 |
| --- | --- | --- |
| ProAsmcomp.h:569–624 | `ConstraintsWithComppathGet` / `ConstraintsSet` 存在；设置数组会再生组件，通用失败不返回逐条拒绝原因；所查签名/注释与本机一致 | FIX 与普通配合共存、某 22 条关系可解、准确的冗余/冲突分类 |
| ProAsmcomppath.h:33–53 | `TrfGet(bottom_up=true)` 从 member 到 assembly；文件与本机逐字节相同 | 未做本次嵌套实例世界测量 |
| ProSolid.h:958–984 | `OutlineCompute` 接受方向矩阵；所查签名/注释与本机一致 | 平移/方向返回语义、实体排除范围和精确世界 bbox 尚待对应说明/实机核验 |
| ProSurface.h:274–288 | `ProSurfaceAreaEval` 可求面积；文件与本机逐字节相同 | 新回执的单位转换与实际面积尚未实现/验收 |

另查 PTC r13 [ConstraintsSet API](https://support.ptc.com/help/creo_toolkit/protoolkit_pma/r13/usascii/creo_toolkit/api/dita/159.html) 与[装配指南](https://support.ptc.com/help/creo_toolkit/protoolkit_pma/r13/usascii/creo_toolkit/user_guide/Assembling_Components_by_Functions.html)。官方把位姿初值与约束作用区分，整体再生失败不提供报告要求的精确原因；本计划据此保留求解阶段未知值，不猜诊断。

## 验证边界

文档检查：`python tools/check_backlog_counts.py` 退出 0、`consistent=true`，194 项（BUG 87 / FEAT 66 / DEV 41），无重复；四份新增说明的本地 Markdown 链接均存在；原报告逐字节一致且 SHA256 匹配；`git diff --check` 退出 0。既有历史验证文件未修改。

独立审阅确认 BUG-133 证据和解析几何算例成立，指出超大容差边界须先冻结、column 舍入矩阵须按同一规范矩阵计算准入；计划已补入这些条件。另离线复算合成 Euler `[1,2,15]` 六位列矩阵，原始行残差 `9.626659999151244e-7`、转置后 `1.023308999981154e-6`，作为 T2 阈值等价测试数据；不是新产品测试或 Creo 实测。

本次仅源码/头文件/官方文档核对、当前专项单测、纯 C++ 数学分歧反例、归档字节与文档/台账检查。产品修改、统一开发检查、产品原生构建、Creo 12.4/13.4 实机、几何/回滚/保存重载、WorkBuddy 黑盒均未执行；BUG-001 历史卡死根因仍未确定。

本次资料归档与计划可评审，不表示 BUG-133 已修复，也不表示全部反馈都已复现。详细实施与待查项见[处理计划](../../superpowers/plans/2026-11-19-dev092-creo13-assembly.md)。
