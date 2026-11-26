# 0.45.1 外部验收反馈映射（2026-11-26）

原件：[draft-flip-loft-arc-weld.md](originals/draft-flip-loft-arc-weld.md)（SHA256 `98ebb66c3ccc0716f775bbb37dda1f70b2ba2469982c07b9031acfc1750bcbc9`，11872 字节）。

| 原件章节 | 问题摘要 | 对应台账条目 | 处理方向 |
| --- | --- | --- | --- |
| §1 (P1) | `draft` 使用 XY 基准面中性面时 `flip=false` 加料、`flip=true` 去料，与工具说明相反；缺加/去料结论字段 | [BUG-192](../../work-items/BUG-192.md)（关联 [BUG-102](../../work-items/BUG-102.md)） | 实机对照实体底面与基准平面法向/拔模朝向，修正文档或 `applied_pull_vector`，新增 `material_effect` |
| §2 (P1) | 近容差端点焊接不支持 40 段异心圆弧（`gear10.json`），且公开草图工具未暴露 `snap_endpoints` / `endpoint_policy` | [FEAT-090](../../work-items/FEAT-090.md)（关联 FEAT-039 / BUG-101 / BUG-159） | 暴露草图焊接参数，扩展 `snap_endpoints` 支持 `arc-arc` 交点调角与容差内三点重算，原生补全圆弧残差测量 |
| §3 (P1) + §4 (P2) | `surface_loft` 与 `creo_loft` 在 Creo 10 上未启动 callback 时开箱不可用，但能力页显示 `enabled=true`，且提交时占通道建 job 后才失败 | [BUG-193](../../work-items/BUG-193.md)（关联 [BUG-135](../../work-items/BUG-135.md) / BUG-120 / FEAT-074） | 能力页拆分 `enabled` 与 `runtime_ready`（纳入 callback 就绪与已知 Creo 10 `-18` 边界）；before-job callback 预检拦截；前置 `accept_unverified_completion` 限制说明 |
| §5 (P2) + §6 附注 | `registered_operations` 包含 4 个不可用操作易误导；`region.interior_point_yz_mm` 未写明不支持 `rectangle`/`circle`/`ellipse` primitive | [DEV-102](../../work-items/DEV-102.md) | 能力页新增 `registered_but_unavailable_operations` 并明晰口径；补全 `interior_point_yz_mm` 文档 |
| §6 回归通过项 | `extrude add`、bbox、`dimensioning:auto` 挪圆心、`datum_plane` 角度符号、region extrude、会话探针均未复现 | 保留既有修复 | 纳入本批离线与实机回归保护 |
