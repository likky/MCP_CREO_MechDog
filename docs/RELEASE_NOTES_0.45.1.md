# MCP_CREO_MechDog 0.45.1 版本说明

2026-11-25 PATCH，公开工具数 111。上一版本：0.45.0（`v0.45.0`，提交 `378990cc16d75ea2a86417619c3fefce1ef2a972`）。

- STL 细化在接缝焊接尺度附近停止，拒绝落在既有顶点附近的切分点，共享边两侧沿用同一划分。接缝补片以闭合边界环为依据。 [BUG-130](work-items/BUG-130.md)
- 细化按曲面面积分配起始预算，ASCII 写出使用 15 位有效数字。回执按最终网格重算剩余候选，`config.json` 可用 `"stl_deviation": true` 打开原生曲面偏差抽样。
- Windows x64 / Creo 10.0.0.0（release 42）实测 14 m 球鼻艏。默认设置导出 1,067,532 片，独立检查确认闭合，无重复面、零面积面或非流形边，体积比原生件低 0.00373%。4,328 个偏差样本的最大值为 0.045512 mm。额外以十二轮对照，最大抽样偏差 0.037125 mm，体积差同为 −0.00373%。源件 revision 和 SHA256 前后一致。装配 STL、Creo 9/12.4 和全曲面偏差上界仍待验证。 [验证与发布记录](validation/RELEASE-0.45.1.md)

## 附件

- `MCP_CREO_MechDog-0.45.1-source.zip`
- `MCP_CREO_MechDog-0.45.1-source.zip.sha256`
- `MCP_CREO_MechDog-0.45.1-seed-library.zip`
- `MCP_CREO_MechDog-0.45.1-seed-library.zip.sha256`

种子包 SHA256 为 `51c41e1e01d712302d639fa9302cf3af871148c7e2bbf8553a27e6d641a0a8f5`。两份同名 sidecar 分别记录各自 ZIP 的摘要。 [GitHub Release](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.45.1)
