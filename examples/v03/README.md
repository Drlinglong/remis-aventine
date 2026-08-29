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

## 已发布的中英结果切片

当前 `2/18` 正式成果使用独立的紧凑契约：

- artifact：`web/public/data/v03-zh-en-results.json`
- protocol：`aventine-v0.3-zh-en-balanced-degree4-sample20-60soft-40hard`
- schema：`src/remis_aventine/schemas/v03-zh-en-public-result.schema.json`

该文件是已经完成的 `zh-CN->en` 与 `en->zh-CN` 结果切片，不是
`aventine-multilingual-tournament-v0.3` 完整 18 方向 artifact 的第二种形状。它保留扁平的
`telemetry.cost_usd`、`elapsed_seconds` 和 `total_tokens`，并通过自己的严格 JSON Schema
正式描述。完整锦标赛契约仍由 `v03-public-result.schema.json` 独立约束；不得使用
`oneOf` 将两种协议混为同一个宽松契约。

中英切片不声明季度 `anchors`，也不伪造尚未发布的完整 `judge_panel`。当前网站的
质量—成本、质量—耗时和质量—Token 前沿属于对已发布切片的确定性派生视图。将来发布
18/18 结果时，网站应切换到完整契约中预计算的 `pareto_frontiers`。
