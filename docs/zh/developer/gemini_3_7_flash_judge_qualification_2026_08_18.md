# Gemini 3.7 Flash 裁判资格报告（2026-08-18）

## 结论

`google/gemini-3.7-flash` **有条件通过** Aventine 裁判资格测试。建议使用
`high` reasoning 的 seeded v2 profile，作为 pairwise Soft Preference 的异构第二裁判；它不能单独
承担历史术语放行闸门，也不能单独裁定所有 Structural Review。

推荐 profile：

`openrouter-gemini-3.7-flash-reasoning-high-structured-seeded-v2`

使用限制：

- Gemini 参赛时禁止自评，必须 leave-one-family-out；
- 确定性的变量、标签、容器和内部 key 损坏仍由 validator 直接判失败；
- 合法变量重组仍需双裁判同意；Gemini 只能提供其中一票；
- 历史术语、细微指代和天文概念不能因 Gemini 单独判 pass 而放行；
- provider、model response id、reasoning tokens 和 OpenRouter 实扣费用必须逐次保留。

## 固定配置

| 字段 | 值 |
| --- | --- |
| OpenRouter model | `google/gemini-3.7-flash` |
| 记录的 canonical model | `google/gemini-3.7-flash-20260813` |
| 实际 routed provider | 本次所有有效输出均为 `Google` |
| prompt | `translation-judge-v2` |
| output contract | strict JSON Schema |
| reasoning | `high`, `exclude: true` |
| seed | `20260818` |
| max tokens | 8,000 |
| provider fallback | disabled |
| web search | disabled |
| 标准价格快照 | input $0.375/M；cache read $0.0375/M；output（含 reasoning）$1.875/M |

OpenRouter 将 reasoning tokens 计入 completion/output tokens；成本估算不得再额外加一次 reasoning。
runner 优先记录 response `usage.cost`，并同时保留 token-price estimate 供核对。参见 OpenRouter 的
[usage accounting](https://openrouter.ai/docs/cookbook/administration/usage-accounting) 与
[reasoning token](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens) 说明。

## 公共 multilingual-48-v1

正式 seeded high v2 结果：

| 指标 | Gemini 3.7 Flash high v2 |
| --- | ---: |
| schema-valid base | 48/48 |
| base accuracy | 40/48（83.3%） |
| single / MQM | 7/12（58.3%） |
| pairwise（ACES + Remis synthetic） | 33/36（91.7%） |
| ACES base | 21/24（87.5%） |
| Remis synthetic | 12/12（100%） |
| major error recall | 82.9% |
| critical exact-severity recall | 33.3% |
| false-good | 44.4% |
| ACES swap | 21/24（87.5%） |
| position consistency | 24/24（100%） |
| HTTP attempts | 72，无重试 |
| exact cost | **$0.157880250** |
| 平均每个逻辑裁决 | $0.002192781 |
| input / output / reasoning tokens | 81,244 / 67,954 / 52,747 |

探索轮中，medium 得到 38/48，high 得到 41/48；high 对 single error detection 的提升足以覆盖
额外成本。最终 seeded high v2 回落到 40/48，说明不能把单轮 41/48 当成稳定能力上限。

与历史结果比较，最终 high v2 与 DeepSeek V4 Pro、Grok 4.5 low 都是 40/48。逐题互补性如下：

| 对照 | verdict agreement | Gemini 独对 | 对方独对 | 两者皆错 | oracle union |
| --- | ---: | ---: | ---: | ---: | ---: |
| DeepSeek V4 Pro | 42/48 | 3 | 3 | 5 | 43/48 |
| Grok 4.5 low | 40/48 | 4 | 4 | 4 | 44/48 |

这支持“异构双裁判”的价值，但 oracle union 不是可直接实现的线上得分；真实协议仍必须把分歧标为
补裁或 unresolved，不能事后挑正确答案。

## 重复运行与结构可靠性

两次 high 完整运行的 base verdict 一致 45/48，24 个 swap verdict 全部一致。固定 seed 进入了
configuration fingerprint，但 Google 后端仍不保证逐次完全确定，因此季度结果必须保存逐 case
裁决，不能只保存聚合分数。

探索 high v1 有 1 个 strict-schema 输出初次失败，重试后成功；正式 seeded high v2 为 72/72
首次成功。包括 smoke、探索轮与有效资格轮在内，共 265 个有效逻辑输出，只有这 1 次需要 schema
重试。

## Luna 困难锚点盲测

私密 audition pack 共 12 条。模型只看到来源、候选、参考译文和中性任务语境；人工预期与裁定理由
保存在模型不可见的 gold/provenance。早先一次把裁定理由误放进 input 的运行已标为无效诊断，完全
不计入下表。

| 指标 | medium v2 | high v2 |
| --- | ---: | ---: |
| 总正确 | 8/12（66.7%） | 9/12（75.0%） |
| 五个必须抓出项 | 1/5 | 2/5 |
| 七个克制/结构放行项 | 7/7 | 7/7 |
| exact cost | $0.026095875 | $0.044300250 |

high 抓出了：

- 明治奏请中的 `Your servant → 你的仆人`；
- `#italic` 标签数量合法但语义作用域搬错。

high 漏掉了：

- `home star → 母星`；
- `sidearm → 副武器`；
- `Sublime Porte → 崇高门`。

两种配置都正确放行：无 glossary 时 `Worm → 蠕虫`、`ojalateros → 但愿派`、两条中文合法变量
重组、书信换行改写、parser 已恢复的最终输出，以及只应报警的双层引号。这说明 Gemini 的优势是
克制和 pairwise 比较，弱点是细微历史术语与上下文多义词召回。

## 资格判定

最终采用 high，而不是 medium，原因是：

1. 公共包 base accuracy、single accuracy 和 position consistency 均更好；
2. 盲测多抓出一条 formatting-scope 语义错误；
3. 完整公共资格轮仍只需约 $0.16，成本远低于整体季度预算。

但 high 不是独立质量闸门。推荐默认组合是 Gemini high + 一个非 Google、历史术语召回更强的裁判；
两者意见不一致时依 v0.3 补裁，仍不一致则 unresolved。Gemini 自身作为参赛模型时，整个 Google
家族退出该 case 的裁判面板。

## 成本与产物

本次全部真实调用（包括 smoke、medium/high 探索、seeded 正式轮、一次已作废的泄漏诊断以及公平
重跑）合计 **$0.560463375**，低于 $2 资格测试闸门。作废诊断只计钱包支出，不计能力结论。

有效主要产物位于 Git-ignored 用户缓存：

- `high-seeded-v2-full.json` — SHA-256
  `92ccb0b277a6db2bcb94f40dd69e5374eb3735aa83e0d4bee1929be09bec5d7e`；
- `audition-medium-v2-blind.json` — SHA-256
  `db2dcbc2f447f469054e125daaaefe8eaa46e057d5375dc70fde4b6c2b08eb88e`；
- `audition-high-v2-blind.json` — SHA-256
  `ef63903d531cecb7fa228b64906d03f775b76f4ea7181dc6f39efeffadf2b2d2`。

路径：`%USERPROFILE%/.cache/aventine/results/gemini-3.7-flash-qualification-2026-08-18/`。
产物不保存 API key、Authorization header 或 reasoning 正文。
