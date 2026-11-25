# OpenAI 直连评测的生成费用估算

以后 OpenAI 参赛模型默认走官方 Responses API。每轮保存每次生成的模型、实际服务档位、token 用量与费率快照。按请求核对长上下文门槛、服务档位和适用的地区附加费。汇总只计本轮执行的生成调用，裁判费单独记录。

按响应的 `usage` 拆分普通输入、缓存读取、30 分钟缓存写入、12 小时缓存写入和输出。普通输入为 `input_tokens` 扣除 `input_tokens_details.cached_tokens` 及 `cache_write_tokens_details.ttl_30m_tokens`、`ttl_12h_tokens`。校验分项非负，另在返回写入总量时检查两种 TTL 分项之和。输出使用 `output_tokens`，其中已含推理 token。各项乘以该模型的对应每百万 token 费率并除以一百万，然后汇总。只有总写入量时，按已记录且唯一的 TTL 归类。若缺少足以确定档位或缓存分项的证据，应标注估算假设或单列上界。

公开结果将可核算的估算写入 `telemetry.cost_usd`，标记 `cost_source: openai-token-estimate` 和 `cost_rank_eligible: true`。榜单、模型详情和成本图标为估算。账户额度抵扣不计入配方生成成本。

2026-11-25 使用 Standard 短上下文费率。单位为美元／百万 token。

| 模型 | 普通输入 | 缓存读取 | 30 分钟写入 | 12 小时写入 | 输出 | 44 次生成估算 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| GPT-6.1 Terra | 1 | 0.05 | 1.25 | 2.50 | 5 | 0.1371266 |
| GPT-6.2 Sol | 2 | 0.10 | 2.50 | 5 | 10 | 0.2454442 |
| GPT-6.2 Astra | 8 | 0.40 | 10 | 20 | 40 | 0.8977368 |

[OpenAI API 定价](https://developers.openai.com/api/docs/pricing) · [Prompt caching 用量与计费](https://developers.openai.com/api/docs/guides/prompt-caching)
