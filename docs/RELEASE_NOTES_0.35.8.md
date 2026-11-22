# MCP_CREO_MechDog 0.35.8 版本说明

版本类型：PATCH。公开工具仍为 111。

上一版本：0.35.7（`v0.35.7`，提交 `a0aa08dd0f9efd64618868d70634718e88d9792d`）。

## 初始实体可以作为拉伸切除目标

`-5778` 是 Creo 为零件初始实体分配的有效 ID，同一个编号可分别出现在不同零件中。Creo 10 的实体枚举、默认体查询、成员面反查和引用回读均确认了该编号。此前 `scope.body_ids` 只接受正整数，导致活动实体 `-5778` 在派发前被拒绝。现在拉伸切除可传入 `scope={"kind":"bodies","body_ids":[-5778]}`，原生执行器在目标零件内按确切 ID 选取活动实体，随后从特征树回读核对。巡检回执的 `cut_scope_id_eligible` 表明 ID 格式是否可用。详见 [BUG-150](work-items/BUG-150.md) 与 [参数语法](REFERENCE_SYNTAX.md)。

## Creo 10 实机结果

Windows x64 / Creo 10.0.0.0 release 42 / 匹配 Toolkit SDK 和 MSVC x64。60×40×10 mm 板件用 10×8 mm 矩形截面贯穿。

| 工况 | 去料 | 保存重载 |
| --- | ---: | --- |
| 省略 `scope` | 800 mm³ | 通过，重载后特征树仍为全体切除 |
| 指定初始实体 `-5778` | 800 mm³ | 通过，重载后特征树仍引用 `PRO_BODY/-5778` |

双体试件指定 `-5778` 也去料 800 mm³，第二实体保持。之后沿同一刀路做全体切除，第二实体再去料 80 mm³。指定 ID 在当前零件内没有活动实体时，操作拒绝并回滚，保留原体积与 revision。正 ID 切除回归通过。[发布验收记录](validation/RELEASE-0.35.8.md)

## 待复现

原护卫舰模型中省略 `scope` 的零去料，在上述简化试件中未复现。原模型与完整切除请求尚未取得。Creo 9、Creo 12 和 WorkBuddy 黑盒未纳入本版验收。

## 附件

Release 地址：https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.35.8。

- `MCP_CREO_MechDog-0.35.8-source.zip`
- `MCP_CREO_MechDog-0.35.8-source.zip.sha256`
- `MCP_CREO_MechDog-0.35.8-seed-library.zip`
- `MCP_CREO_MechDog-0.35.8-seed-library.zip.sha256`

种子包 SHA256：`46afef284f90b01f76ab50152a2f428b16077561e64a3e8159f266721d397b12`（24 个文件、9 个种子）。源码包 SHA256 记录在同名 sidecar 中，格式为 `<64 位 SHA256>  文件名`。两份 sidecar 分别校验对应 ZIP。
