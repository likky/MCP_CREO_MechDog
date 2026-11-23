# MCP_CREO_MechDog 0.36.0 版本说明

版本类型为 MINOR，公开工具数 111。

上一版本：0.35.8（`v0.35.8`，提交 `ed8ea5141a0574de91ec0b19d171dd22f55ca68b`）。

- **保存与恢复**。对符合条件的独立受管零件使用 `ProMdlSave`。恢复时确认会话中的同名对象已擦除，再读取并核对登记的确切检查点。恢复请求兼容把 null 转成空串的客户端。Creo 10 实机验证了四次连续保存、基线恢复后继续写入、接纳已有检查点的会话零件，以及删除重建后的保存重载。[BUG-152](work-items/BUG-152.md)
- **B 样条切除**。新增显式 `approximation_segments`。21 段近似实测与手工折线去料量一致。精确切除失败时，回执保留原生闭合、开端点与 B 样条计数，compact 保留关键读数。[BUG-153](work-items/BUG-153.md)
- **放样**。种子放样在保存前和重载后核对原生截面依赖、实体体积与端平面覆盖。矩形、圆形和三角形两截面实机通过。能力摘要列出直接 Blend 的回调检查入口及曲面元素树当前准入结果。[BUG-154](work-items/BUG-154.md)
- **同计划引用和导出**。曲面选择器可按特征标签限定候选，JPEG 可指定等轴测、正视或俯视及像素尺寸。会话清单返回可复制的 `erase_target`，共享边及端点间隙报错给出更具体的诊断。[FEAT-074](work-items/FEAT-074.md) · [参数语法](REFERENCE_SYNTAX.md)

本次原生环境为 Windows x64 / Creo 10.0.0.0 / Toolkit release 42 / 匹配 SDK / MSVC x64。原现场的保存 `-1` 触发条件、七截面种子、精确样条切除边界、Creo 9/12 与 WorkBuddy 黑盒待复验。Creo 9 SDK 编译和运行时验收仍未完成。Creo 10 曲面元素树实测提取返回 `-18`，同一执行器后续请求在创建作业前拒绝。详见[验收与发布记录](validation/RELEASE-0.36.0.md)。

## 附件

- `MCP_CREO_MechDog-0.36.0-source.zip`
- `MCP_CREO_MechDog-0.36.0-source.zip.sha256`
- `MCP_CREO_MechDog-0.36.0-seed-library.zip`
- `MCP_CREO_MechDog-0.36.0-seed-library.zip.sha256`

种子包 SHA256 为 `c43228ac6a8764cd7369fc04ee151ceb4c3ee735063c6052839e72d0146bf25f`。同名 sidecar 分别记录两个 ZIP 的实际 SHA256。[GitHub Release](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.36.0)
