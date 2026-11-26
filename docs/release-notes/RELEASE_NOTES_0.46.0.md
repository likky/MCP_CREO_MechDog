# MCP_CREO_MechDog 0.46.0 版本说明

2026-11-26 MINOR，公开工具数 111。上一版本：0.45.2（`v0.45.2`，提交 `77aaa85ed318208fef0e6628773a1cefd31ab4f7`）。

- **拔模方向说明与加/去料结论（[BUG-192](../work-items/BUG-192.md)）**：实机对照确认 Creo 10 上实体底面与 XY 基准平面作为中性面时拔模朝向相反，修正 `creo_draft` 与能力说明并解释 `direction_flip_code`；在 `draft` 操作结果（compact 与 full）新增由 `material_delta_mm3` 派生的 `material_effect`（`added` / `removed` / `unchanged` / `null`）。
- **近容差圆弧端点焊接与草图参数公开（[FEAT-090](../work-items/FEAT-090.md)）**：在 `creo_create_sketch` 与 `creo_update_sketch_geometry` 暴露 `snap_endpoints`、`endpoint_policy`、`max_endpoint_move_mm`、`closure_tolerance_mm`；`snap_endpoints=true` 支持 `1e-9 ~ 1e-4 mm` 微间隙与异心 `arc-arc` 对接（相交圆弧仅调角零半径漂移，微离无交点圆弧三点重算并汇报 `max_radius_delta_mm`）；原生残差测量扩展支持 `PRO_2D_ARC`。
- **放样运行时就绪披露与提交前预检（[BUG-193](../work-items/BUG-193.md)）**：`creo_capabilities`（含 compact 页）为 `loft` 与 `surface_loft` 统一输出 `runtime_ready`（纳入 callback 就绪态与 Creo 10 release 42 的 `element_tree` `-18` 限制）；`creo_loft` 与 `creo_surface_loft(creation_route="resident_panel")` 在 callback 为 `not_loaded`/`version_mismatch` 时于提交前（before-job）直接拒绝，不占用通道、不生成失败作业；前置说明 `accept_unverified_completion` 在 Creo 10 上不能保留几何。
- **能力页操作列表与区域拉伸文档（[DEV-102](../work-items/DEV-102.md)）**：`creo_capabilities` 新增 `registered_but_unavailable_operations` 与 `operations_note`（向后保留 `registered_operations`）；明确 `region.interior_point_yz_mm` 与 `signature_yz_mm` 均需显式 `line`/`arc`/`b_spline` 图元。
- 实机验证环境为 Windows x64 / Python 3.12.10 / Creo Parametric 10.0.0.0（`release_numeric=42`）及匹配 SDK：拔模 8/8 用例（含 `datum_plane` 与 `material_effect`）与 40 弧 10 轮廓微间隙吸附拉伸均保存重载通过。Creo 9 / Creo 12.4、外部原始 `gear10.json` 文件与 WorkBuddy 黑盒仍未验收。 [发布记录](../validation/RELEASE-0.46.0.md)

## 附件

- `MCP_CREO_MechDog-0.46.0-source.zip`
- `MCP_CREO_MechDog-0.46.0-source.zip.sha256`
- `MCP_CREO_MechDog-0.46.0-seed-library.zip`
- `MCP_CREO_MechDog-0.46.0-seed-library.zip.sha256`

种子包 SHA256 为 `7ccae6e93dd1d7ed413c796a605d1488901e42abe93e8edbeb4e0fb190446384`。两份同名 sidecar 分别记录各自 ZIP 的摘要。 [GitHub Release](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.46.0)
