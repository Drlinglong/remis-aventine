# 中英固定锚点增量评测：2026-10-09

本轮参赛配置为 OpenRouter `anthropic/claude-haiku-5.5`（high）和
`openai/gpt-6.1-sol`（medium）。每个模型完成相同的 44 次生成、76 条译文，
沿用密封试卷、提示词、两次重复与 32,768 输出 token 上限。未追加修复调用。
新评分版本为 `v0.3-zh-en-anchors-20261009-v1`。

原始 17 模型及 9 月、10 月 1 日的成绩文件保持不变。新结果追加至统一目录，
模型选择器默认采用同产品线的最新一代，仍允许手动添加旧版本。
跨评分版本的排序与帕累托图是探索性比较，尚未校准成共同分数尺度。

## 推理设置的证据

`web/public/data/v03-execution-settings.json` 按执行身份 SHA-256 保存配置，
由原始运行身份核对得到，不按模型名推测。GPT-6 Luna 的评测参数为 high。
历史请求没有设置推理参数的模型显示“默认配置”；这不表示关闭推理，
也不声称供应商当时的具体默认强度。显式开启、关闭与未记录分别显示。
表格、图表、搜索、模型选择器与详情页使用同一份参数记录。

本轮 Haiku 原始批量格式通过 7/44，经现有解析与规范化后通过 44/44；
Sol 原始与最终格式均通过 44/44。两者空响应均为 0，完成原因均为 stop。
原始格式失败与最终解析成功分别保留，不能把恢复后的成功率称为原始格式可靠性。

## 裁判与速度门槛

OpenRouter 的 `preferred_min_throughput` 是路由偏好，并非硬性速度下限。
本轮先以四个固定合约案例验证 JSON、明显对错与速度，再固定 `only`、`order`
并设置 `allow_fallbacks: false`；正式裁判不设置客户端输出 token 上限。
参考：[OpenRouter provider routing](https://openrouter.ai/docs/guides/routing/provider-selection)。

| 裁判 | 固定路由 | 四例预检最低输出速度 |
| --- | --- | ---: |
| GPT-6 Luna（high） | `openai` | 57.87 token/s |
| DeepSeek V4.1 Flash（high） | `deepinfra/fp8` | 42.58 token/s |
| Gemini 3.8 Flash（medium） | `google-ai-studio` | 54.76 token/s |

MiMo 的 Xiaomi 路由预检约 1–6 token/s；DeepInfra 有一次约 23.64 token/s；
GMICloud 已返回的请求约 5–11 token/s；Novita 对所需参数返回 404。
没有一个 MiMo 路由完整通过本轮门槛，因此本轮正式裁判不使用 MiMo。
这只描述这次路由预检，不是对模型能力或供应商长期速度的判断。

速度使用输出 token（含推理）除以供应商 generation time；元数据未可用时，
用输出 token 除以完整请求耗时作为保守下界。输入 token 不计入速度。
实际响应低于 30，或速度无法确认时，隔离该路由的后续调用；已经发出的调用
保留响应与费用，不重复发起。预检不保证未来每次请求速度。

Haiku 主审为 Luna＋DeepSeek，缺失或分歧时由 Gemini 补裁。
Sol 同家族排除 Luna，且 MiMo 不满足路由门槛，因此由 DeepSeek＋Gemini 审理。
必须有两张一致的有效票才裁定；分歧仍为未决。裁判版本为
`priority-mimo26-luna6-ds41-gemini38-20261009-routes30-v1`。
公开路由证据见 `web/public/data/v03-judge-routes-20261009.json`。

## 锚点与复现

复用 9 月冻结的 Qwen 3.8 Max、Muse Spark 1.2、Solar Pro 4 输出及已完成的
结构裁决，不重复支付锚点生成与审查费用。沿用每方向每锚点最多 10 例、
20% 交换顺序审计、相反主审顺序、60% 软偏好＋40% 硬可靠性与双方向等权。
未决项单列，软分按已裁定样本计算；每个锚点在两个方向都必须贡献已裁定证据。
小样本结果不构成统计显著性结论。

私有语料库的 `run_oct09_candidates.py`、`run_oct09_judges.py`、
`panel_20261009.py` 保留计划、请求身份、回执、吞吐记录与可恢复检查点。
`test_oct09_routes.py` 验证固定路由、禁用回退、低速隔离、离线恢复不联网与家族回避。
公开结果不包含密封题目、候选译文、原始回执或裁判理由。
