# 0.25.0 发布记录

- 版本：`0.25.0`（MINOR）
- 日期：2026-11-15
- 版本说明：[RELEASE_NOTES_0.25.0](../RELEASE_NOTES_0.25.0.md)
- 主台账：[BACKLOG](../BACKLOG.md)
- 工作卡：[DEV-090](../work-items/DEV-090.md)
- 受测提交：`v0.25.0` 标签指向的 `main` 提交（标签对象与提交号在[POSTCHECK](../development/RELEASE-POSTCHECK-2026-11-07.md) 的 `## v0.25.0` 段登记）

## 包内容对照（相对 0.24.0）

| 项 | 0.24.0 | 0.25.0 | 说明 |
| --- | --- | --- | --- |
| 公开工具 | 107 | 108 | 新增 `creo_sheetmetal_base_flange` |
| 计划操作 | `import_geometry` 等 | 增加 `sheetmetal_base_flange`、`linear_pattern` | 组合钣金首壁与方向线阵 |
| 几何引用 | 特征/边 ID 与 `edge_geometry` | 增加 `geometry_selector`（边/面，含装配坐标空间） | 唯一命中否则拒绝 |
| 尺寸寻址 | `{id}` | 增加 `{feature,symbol}` | 0/多命中拒绝 |
| 装配约束 | `mate`/`align`/`insert`/`csys` 偏移被忽略 | 非零 `offset` 拒绝；新增 `coincident`/`concentric` | `mate_offset`/`align_offset` 继续承载偏移 |
| 倒角 | 等距 | 增加 `chamfer_type="distance_angle"` | `angle_deg` + `angle_reference` |
| 计划输入 | `operations` 内联 | 增加 `plan_file`（受控本地 JSON） | 互斥、只读一次、回显 SHA256 |
| 种子库 | 9 个种子 | 9 个种子 | `compatible_server_version=0.25.0` |

## 验证

- 环境：Windows x64、Python 3.12、Creo 12.4.0.0（`release_numeric=44`）与匹配 Toolkit SDK、MSVC x64。
- 离线：`tools/dev_check.py --work-item DEV-090` → `success=true`（`Ran 3655 tests`、`OK`；`lint_findings=0`、`unformatted_files=0`；受测源码指纹 `295767cd…`，基于 `9a7a3d9` 且发布文档提交前为 dirty）；`bridge.py build` 退出码 0（`build/creo_worker.exe`）；`tools/check_release_records.py --version 0.25.0` → exit 0；`tools/check_backlog_counts.py` → `consistent=true`（186 个 ID）。
- 合并基线：本版从已发布的 0.24.1（`e1ee731`）合入，包内含其启动参数、无图形容错、worker 回退与 toolkit 提示；该批实机证据见 [RELEASE-0.24.1](RELEASE-0.24.1.md)，本版未重复实测。
- 实机：组合首壁 job `f85ddda1…`（体积 770.185802 / 上界 770.185796 mm³、包络 `u 0…8 / v 0…20 / n −12…2`、`composed_features` = 49 + 104、保存重载通过）、几何选择器边/面与装配坐标、符号定位尺寸、`mate_offset=5` 残差 0.0 与随动、70° 角度倒角两例、方向线阵两例，均有成功与拒绝用例，逐条回执见 [DEV-090](../work-items/DEV-090.md)。
- 未测：T6c 区域切除、T7 弧端点与两阶段形状误差、`parallel`/`distance`、多约束求解与装配保存重载、Creo 9/10 实机、WorkBuddy 黑盒；组合首壁与反馈参照 792.323 mm³ 不等价（差约 22 mm³，中面加厚 vs 单侧加厚）。

## 逐 ID 状态核对

成员：本版只交付 [DEV-090](../work-items/DEV-090.md) 一项汇总卡，其 T1—T8 子项均在该卡内登记，不另拆台账行。该卡原以 DEV-089 登记，因与 0.24.1 已归档的 DEV-089（安装文档预检）编号冲突改为 DEV-090。0.24.1 自身的 [BUG-125](../work-items/BUG-125.md)—[BUG-128](../work-items/BUG-128.md) 已随 0.24.1 发布并归档，不重复列入本版交付。

| ID / 工作卡 | 技术状态 | 交付版本 | 剩余范围 | 卡首页 | 主台账 | 差异说明 | 版本说明 | 开发入口 | 实际 Release |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [DEV-090](../work-items/DEV-090.md) | 部分交付（T1/T2/T3 组合/T4/T5/T6a/T6b/T8 与 T7 诊断措辞已交付；T6c、T7 弧端点与两阶段形状误差、`parallel`/`distance`、多约束求解与装配保存重载未交付） | 0.25.0（子项） | T6c 区域切除、T7 弧端点与两阶段形状误差、`parallel`/`distance`、多约束求解、装配保存重载、Creo 10 与 WorkBuddy 黑盒 | 部分交付，剩余待验收 | 部分交付，剩余待验收 | 无 | 已列入 | 已列入 | `v0.25.0` |

## 未纳入本版

- T6c 区域切除：反馈报告只有摘要，缺 B-REGION 的名称/成员/输出侧，构造不出稳定签名。
- T3 的单特征基体法兰：本机三种候选元素树均未成立（创建返回 -1、再生失败或材料落入未联动新实体），只开放组合路线。
- 机械臂完整回放：原始 TXT、生成计划与原始回执未提供，不作验收声明。

## 发布核对

本版发布四个附件（逐个列出，不使用通配）：

- `MCP_CREO_MechDog-0.25.0-source.zip`
- `MCP_CREO_MechDog-0.25.0-source.zip.sha256`（源码包摘要记录在同名 sidecar 中，一行 `<64 位 SHA256>  文件名`）
- `MCP_CREO_MechDog-0.25.0-seed-library.zip`
- `MCP_CREO_MechDog-0.25.0-seed-library.zip.sha256`（种子包摘要同样在 sidecar 中）

- 种子包 SHA256：`f8cf62d21d8c9d513fe6335e8e82b8064f48be642ad6a009cd433aa3257705fc`（24 个文件、9 个种子，与 `docs/seed_package.json` 一致，重建一次摘要不变）。
- 源码包：由本次合入 `main` 的提交源码构建，`tools/package.py` 的四附件门禁与发布记录门禁均通过；字节数与 SHA256 见同名 sidecar，不写入包内。
- Release：<https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.25.0>，id `446058283`，非 draft、非 prerelease，`published_at=2026-11-15T12:51:01Z`，target `main`（`38bee48692d67d7f962d21ad713abbaa821c2fa7`，标签对象 `f617e5d26d326a0b51d52f298141e965a63d2041`）。
- 发布后核对：`tools/check_release_assets.py --tag v0.25.0` → exit 0，「v0.25.0: four assets downloaded and verified; both sidecars match」；实际 Release id、发布时间与附件摘要同步到 `main` 上的[POSTCHECK](../development/RELEASE-POSTCHECK-2026-11-07.md)，不回写已冻结的包内快照。远端 digest、本地重算与 sidecar 内容逐一致：

| 附件 | 字节 | SHA256 |
| --- | ---: | --- |
| `MCP_CREO_MechDog-0.25.0-source.zip` | 10 238 309 | `a1e949a302d1a0003dd9f98c0a44ec9e7096cda740fced526b09dec26f126d40` |
| `MCP_CREO_MechDog-0.25.0-source.zip.sha256` | 101 | `68486baf77050e947b00651003982926b47b193a1e5033fc35c1e449ee584174` |
| `MCP_CREO_MechDog-0.25.0-seed-library.zip` | 493 442 | `f8cf62d21d8c9d513fe6335e8e82b8064f48be642ad6a009cd433aa3257705fc` |
| `MCP_CREO_MechDog-0.25.0-seed-library.zip.sha256` | 107 | `a89288276cf7182dda630998da03130f544dfb2ddc5d7e4145b45f547d83864b` |

## 相对上一正式包核对（上一版本：0.24.0）

| 项目 | 上一版 | 本版 | 结论 / 注册影响 |
| --- | --- | --- | --- |
| native/third_party 原字节（含 json.hpp、第三方许可） | 未改 | 未改 | 无 |
| 回调指纹（sha256-repo-lf-v1） | 未改 | 未改 | 无 |
| loader DLL SHA256 | 未改 | 未改 | 无 |
| callback DLL SHA256 | 未改 | 未改 | 无 |
| worker SHA256 | 0.24.0 构建 | 本版新增/修改原生源码 | 必须重新编译 worker（`bridge.py build`） |
| protk.dat / 注册表路径 | 未改 | 未改 | 无需重新注册 |
| 实际注册影响（未变 / 需重新注册 / 需迁移 / 需重启） | — | — | 仅需重编译并重启 MCP 连接器 |
