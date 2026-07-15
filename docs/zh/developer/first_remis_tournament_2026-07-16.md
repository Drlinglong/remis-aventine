# 首届 Remis recipe pilot（2026-07-16）

## 结论

首届 Aventine Remis pilot 使用同一份 7-case frozen fixture，对四份已经由 Remis 生产路径生成的
本地 recipe artifact 做全循环比较。最终次序为：

1. **Qwen 3.6 27B Q4_K_M**；
2. **Gemma 4 31B QAT Q4_0**；
3. **TranslateGemma 27B Instruct Q6_K**；
4. **Nemotron Cascade 2 30B A3B Q4_K_M**。

这只是首轮工程 pilot，不是可外推到其他语言、mod 或模型版本的通用排行榜。

## 输入与裁决合同

- Fixture：Remis `translation_quality_benchmark_v1.json`，SHA-256
  `4fad788b58c9c48acbdb6a0d0d82563348e5e072b7dd20cfc9a45f6882a47335`；
- 5 个 translation case、2 个 repair case；方向为 `en -> zh-CN` 与 `zh-CN -> en`；
- 每份原始结果先经 `adapt-remis-result` 转为 schema-valid Aventine run artifact；
- execution failure、structured-output failure 和 hard-validator failure 先执行 veto；
- 只有双方都合格的 case 才发送给 DeepSeek V4 Pro；
- 每个软质量 case 同时运行 A/B 与 swap；位置不一致或缺失输出保持 unresolved；
- judge 只裁决软质量，不能推翻 hard validator。

## 总战绩

战绩同时包含 hard-validator 决定和 position-consistent judge 决定。每位选手参加 21 个
case-level head-to-head matchup。

| 排名 | Recipe | Hard pass | 胜 | 负 | 平 | 双方不合格 | Unresolved |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | Qwen 3.6 27B Q4_K_M | 7/7 | 15 | 1 | 2 | 0 | 3 |
| 2 | Gemma 4 31B QAT Q4_0 | 7/7 | 11 | 4 | 2 | 0 | 4 |
| 3 | TranslateGemma 27B Instruct Q6_K | 5/7 | 4 | 7 | 2 | 2 | 6 |
| 4 | Nemotron Cascade 2 30B A3B Q4_K_M | 1/7 | 0 | 18 | 0 | 2 | 1 |

## 两两结果

| 对局 | 左胜 | 右胜 | 平 | 双方不合格 | Unresolved |
|---|---:|---:|---:|---:|---:|
| Gemma 4 vs Qwen 3.6 | 1 | 4 | 1 | 0 | 1 |
| Gemma 4 vs TranslateGemma | 3 | 0 | 1 | 0 | 3 |
| Gemma 4 vs Nemotron | 7 | 0 | 0 | 0 | 0 |
| TranslateGemma vs Qwen 3.6 | 0 | 4 | 1 | 0 | 2 |
| TranslateGemma vs Nemotron | 4 | 0 | 0 | 2 | 1 |
| Qwen 3.6 vs Nemotron | 7 | 0 | 0 | 0 | 0 |

Gemma 4 vs Qwen 3.6 的最后一个 unresolved 是长篇
`stellaris_proclamation_style`，其 base 与 swap 均多次返回 malformed JSON。即使该 case 判给
Gemma，Qwen 仍以 4:2 领先，因此不再继续付费重试，冠军结论不受影响。

## Repair restraint

四个 recipe 在两个 repair case 上都保持了标记为已有效的条目，没有记录到 over-editing。
Gemma 4、Qwen 3.6 和 TranslateGemma 各有一个 reference exact match；Nemotron 没有 exact
match，且只有一个 repair case 通过最终 hard validation。

## Judge 运行质量与成本

- 逻辑 judge 输出目标：40；实际 HTTP 请求：113；
- 经过两轮有界续跑和一次只影响冠亚军的定点补判，最终 32/40 个 base/swap 输出有效；
- 六组报告共 42 个 case matchup：30 个明确胜负、3 个 tie、2 个 neither、7 个 unresolved；
- DeepSeek 估算总成本约 `2.513589 RMB`；
- 首轮把 `max-calls` 恰好设为逻辑任务数，暴露出它同时限制 HTTP retry 的易错语义；大量首轮
  failure 实际是请求预算被前序重试耗尽，而不是选手失败；
- 长文本在 V4 Pro high-thinking + 4000 max tokens 下仍频繁产生 malformed JSON。该 profile
  不适合作为大规模全循环默认裁判。

下一轮应把 logical-call cap 与 HTTP-attempt cap 分开，并为 runner 增加逐项 checkpoint/进度输出。
评测策略上，应先用 hard validator 和便宜的本地 metric/QE 初筛，再把高思考 judge 留给关键
对局、证据分歧和高影响失败。

## 当前状态与追踪

当前 runner 已支持有界 retry、兼容配置校验的失败项续跑和成本统计，但还没有独立的逻辑输出/
HTTP 尝试预算、逐项崩溃安全 checkpoint、实时进度，以及面向长文本的紧凑 verdict-first profile。
这些可靠性工作统一记录在
[issue #5](https://github.com/Drlinglong/remis-aventine/issues/5)。完成该项是扩大选手数量或样本规模
前的下一里程碑；在此之前，请把请求预算耗尽视为基础设施失败，而不是选手失败。

完整 adapted artifacts、judge outputs 和逐 case reports 位于 Git-ignored
`benchmark_results/remis-tournament-2026-07-16/`；仓库只提交聚合结果、hash 和方法说明。
