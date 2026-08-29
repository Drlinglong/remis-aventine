# v0.3 前端结果模板

`v03-public-result.template.json` 是给网站使用的公共、脱敏 view model。它故意只展开：

- 1 名示例选手（Solar Pro 4）；
- 1 个语言方向（`en->ko`）；
- 1 个单语言分数（`ko`）。

正式生成器按相同结构重复 `profiles`、`directions`、`per_extended_language` 和
`direction_scores`，不会把私密考题、原文、候选译文或 raw response 写入网站 artifact。

前端处理规则：

1. `null` 表示尚未测量或不可排名，不得显示为 `0`。
2. 只有 `status=complete` 且对应 measure 完整时才显示正式名次。
3. `coverage`、`judge_agreement` 和 `unresolved` 必须与质量分同时展示。
4. 参赛者固定为 `service_tier=default`；裁判固定为 `service_tier=batch`。
5. `cost.rank_eligible=false` 的免费促销或未知本地成本不进入成本帕累托前沿。
6. 三个季度锚点由 `anchors` 表达；未选定时保持 `pending_selection`。
7. 网站三个二维前沿直接读取 `pareto_frontiers` 中的 `profile_id`，不自行猜测缺失成本。

正式网站文件建议放在 `web/public/data/v03-public-result.json`。结构约束位于
`src/remis_aventine/schemas/v03-public-result.schema.json`。
