# 发布记录 v0.36.0

日期为 2026-11-23，版本类型为 MINOR。

上一版本：0.35.8（`v0.35.8`，提交 `ed8ea5141a0574de91ec0b19d171dd22f55ca68b`）。

## 验收范围

Windows x64 / Python 3.12.10 / Creo 10.0.0.0 release 42 / 匹配 Toolkit SDK / MSVC x64。保存重载、恢复后编辑、切除去料、种子放样的解析体积、同计划选面和 JPEG 实测见[本机验收](feedback-save-loft-2026-11-23.md)。

升版前的开发工作树全量单测通过，执行 4397 项、跳过 7 项，元数据为 0.35.8。0.36.0 使用本轮候选的独立报告作为打包证据。

适用门禁包括 `tools/dev_check.py --work-item BUG-152`、`bridge.py build`、种子包重复构建、`tools/check_release_records.py --version 0.36.0` 以及实际源码包独立解压后的 `tools/test_unit.py`。

发布候选 `tools/dev_check.py --work-item BUG-152` 通过 Ruff、clang-format、离线 MCP 验收和全量单测。单测运行 4397 项，0 失败、0 错误、7 跳过，版本为 0.36.0，`run_id=447d1d8d62ff4fe2b312706b8d97abf6`。受测提交 `2f98b62ea0e60aede631211f04d8c33f603c2cf4`，`dirty=false`，源码指纹为 `9798cd0a764df946a79ffd99e5d71476a917eccf382c583e1a61615cb2106f8d`。打包前仅补记本文件的验收摘要。正式源码包的独立单测与安装结果记在发布正文和[发布后核对](../development/RELEASE-POSTCHECK-2026-11-07.md)。

### 发布候选实机复测

- `bridge.py build` 通过。原生源码指纹为 `87e727d77a5de0c72413fd99cd24554a378c247ef064b99eae2f2c853b4bab77`，worker SHA256 为 `a2e02b5b2fd88550b700f972601505f3bfa7f05b5aeb65b228b3bbba893bb6e7`。
- `tools/test_loft_seed.py --seed-file seed_library/seeds/two_straight/mechdog_loft_reference.prt.5 --feature-id 60` 通过。矩形、圆形和三角形的体积分别为 7000、5497.787 和 3500 mm³。矩形参数编辑后为 7840 mm³，切除后为 7745.752 mm³。保存重载及失败回滚通过。
- 基线恢复作业 `9a10c203f54d491e890ddf89981a1644` 核对 24,000 mm³、revision 与原检查点摘要，恢复后可追加参数。同次完整矩阵复测在准备 `accept_saved` 的新建夹具 `c411f9750b7a4df4a4b56320f3beb312` 遇到连接 `-11`，后续两次完整矩阵尝试分别遇到通道忙碌和新建草图作业 `98a9c71fc9334b7284ed740ac110e1cf` 的 `AutodimensionSketch=-1`。四种恢复动作的开发验收和最终执行器上接纳既有检查点的独立证据见[本机验收](feedback-save-loft-2026-11-23.md)。
- 重启专用测试会话后，JPEG 正视、俯视和等轴测分别验证 1400×800、1600×900 和 1200×1000，视角矩阵、revision 和检查点摘要校验通过。21 段 B 样条近似与手工折线作业 `c96b919a44b642f4b34d138deed9d80a`、`6fbd18c0fe5e45679215a8f71fc0ab84` 均保存重载，去料量均约 215,464,586,469.734 mm³。

### 与 v0.35.8 正式包比较

`native/third_party/` 的 JSON 头与第三方许可证逐字节一致。回调 loader 和 payload 的归一化源码指纹分别维持 `cef31b4febf914c4803df314aeafc146faccf8811a3bcfc532a8f1f3fbe076b3` 和 `36dc5b958304505b4899c7e8a530beb9d228c26192fdeb92320f8512c059363d`。

| 项目 | v0.35.8 SHA256 | v0.36.0 SHA256 |
| --- | --- | --- |
| Loader DLL | `868a8cc3ef36053ff4f0beaf917eecf976450a8ef9e9735c34bb6dc13c287b8a` | `07bfa359365f5ba058a62a60ecba0a3cdaed88d2c7cab99d20ca2d76b8d24017` |
| Callback DLL | `3bbacfa87b3220d7398caa345c7ad8ead37130ea7282fc0fe2c136b31171ff73` | `37e5e40e63e6072963094afcc425c9a654d36161f8627bb36940767376d0dc64` |
| Worker | `ebee5129c0846f528e507bc31028fc1d516e544e8a58b245b18ccf0429a6bb18` | `a2e02b5b2fd88550b700f972601505f3bfa7f05b5aeb65b228b3bbba893bb6e7` |

两个独立构建的安装根不同，注册文件相对路径均为 `build/blend_callback_protk.dat`。本轮未实施现有会话的回调注册迁移。

## 附件

- `MCP_CREO_MechDog-0.36.0-source.zip`
- `MCP_CREO_MechDog-0.36.0-source.zip.sha256`
- `MCP_CREO_MechDog-0.36.0-seed-library.zip`
- `MCP_CREO_MechDog-0.36.0-seed-library.zip.sha256`

种子包 SHA256 为 `c43228ac6a8764cd7369fc04ee151ceb4c3ee735063c6052839e72d0146bf25f`，包含 24 个文件、9 个种子。两个同名 sidecar 分别记录各自 ZIP 的实际摘要。源码包自校验值随 sidecar 分发。

## 逐 ID 状态核对

| ID | 交付版本 | 实际 Release | 技术状态 | 卡首页 | 主台账 | 差异说明 |
| --- | --- | --- | --- | --- | --- | --- |
| [BUG-152](../work-items/BUG-152.md) | 0.36.0 | v0.36.0 | 已有修复但待验收 | 已有修复但待验收 | 已有修复但待验收 | 保存异常的外部原现场缺失 |
| [BUG-153](../work-items/BUG-153.md) | 0.36.0 | v0.36.0 | 已有修复但待验收 | 已有修复但待验收 | 已有修复但待验收 | 精确样条切除仍有内核限制 |
| [BUG-154](../work-items/BUG-154.md) | 0.36.0 | v0.36.0 | 已有修复但待验收 | 已有修复但待验收 | 已有修复但待验收 | 外部七截面种子待复测 |
| [FEAT-074](../work-items/FEAT-074.md) | 0.36.0 | v0.36.0 | 部分交付，剩余待验收 | 部分交付，剩余待验收 | 部分交付，剩余待验收 | 装配预览、原弧段和面角色组待复验 |

## 远端核对

发布后执行，当前未验证。见 [GitHub Release](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.36.0) 和 [发布后核对](../development/RELEASE-POSTCHECK-2026-11-07.md)。

Creo 9/12、外部模型和七截面种子、WorkBuddy 黑盒均未纳入本版实机。Creo 9 SDK 编译与运行时验收仍未完成。
