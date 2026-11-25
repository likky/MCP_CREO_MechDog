# MCP_CREO_MechDog 0.45.0 版本说明

2026-11-25 MINOR，公开工具数 111。上一版本：0.44.1（`v0.44.1`，提交 `5e04dcd8204759cd2eaed13aeadbb80661e307cc`）。

- **加料体积保护**。拉伸、回转、扫掠和放样的 `mode=add` 在保存前检查净体积，超差减料或无法可靠测量时拒绝提交并恢复检查点。 [BUG-191](work-items/BUG-191.md)
- **实际实体包围盒**。切除工具范围与独立草图退出实体边界计算。零件和装配返回采样来源及状态，历史快照的轮廓可从 `legacy_regeneration_outline_mm` 读取。 [FEAT-078](work-items/FEAT-078.md)
- **草图默认坐标保真**。`dimensioning="auto"` 对支持的无约束轮廓优先用 `coordinates`。创建或替换时检查绝对偏差，超差回滚。需要原生自动补尺寸的计划可显式指定 `dimensioning="autodim"`。 [BUG-108](work-items/BUG-108.md)
- **拔模反向**。`flip=false` 沿 Creo 引用方向，`flip=true` 反向。旧计划若依据原错误映射选定 `flip`，重新执行前按目标锥度复核。回执包含特征树方向枚举，平面引用还提供 `applied_pull_vector`。 [BUG-102](work-items/BUG-102.md)
- **基准面角度**。文档按实际有向轴说明 `angle` 的右手约定，并给出 RIGHT 面绕 ±Z 旋转正负 54° 的重载结果。 [BUG-094](work-items/BUG-094.md)
- **启动探针**。首次 `-4` 可显示 `session_not_ready` 并在原截止时间内重探。持续查找失败和探针自身超时分别保留证据。 [BUG-170](work-items/BUG-170.md)

本轮实机环境为 Windows x64、Python 3.12.10、Creo 10.0.0.0（release 42）与匹配 SDK。验收为上述六项专项回归。Creo 9、Creo 12.4、WorkBuddy 黑盒和全项目原生回归均未运行。原外部模型与历史差异的未测范围分别记录在工作卡。 [验收与发布记录](validation/RELEASE-0.45.0.md)

## 附件

- `MCP_CREO_MechDog-0.45.0-source.zip`
- `MCP_CREO_MechDog-0.45.0-source.zip.sha256`
- `MCP_CREO_MechDog-0.45.0-seed-library.zip`
- `MCP_CREO_MechDog-0.45.0-seed-library.zip.sha256`

种子包 SHA256 为 `1ab6d9892f764a019642a1595f59c4f8de64f04933f6657da8597abab80fa73f`。两份同名 sidecar 各记录对应 ZIP 的 SHA256。 [GitHub Release](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.45.0)
