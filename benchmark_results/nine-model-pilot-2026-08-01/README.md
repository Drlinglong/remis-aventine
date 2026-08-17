# 九模型 Pilot Score v0.1 校准报告（2026-08-01）

这是 Aventine 第一份由真实 artifacts 自动生成的九模型综合分。它仍标记为 `PREVIEW`：目的
是先检查公式输出是否符合直觉，再决定是否替换网页手填数字。

## 排名

| 排名 | Recipe | Pilot Score | Soft Preference | Hard Reliability | W-L-T | 覆盖率 | 三轮耗时 | 三轮选手成本（USD） |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | Gemini 3.6 Flash (`high`) | 84.21 | 73.7% | 100.0% | 23-5-10 | 67.9% | 251.1 s | $0.41429 |
| 2 | HY3 (`high`) | 79.71 | 72.5% | 90.5% | 24-6-10 | 71.4% | 2,421.6 s | $0.05295 |
| 3 | DeepSeek V4 Flash (`high`) | 73.05 | 59.3% | 93.7% | 20-12-11 | 76.8% | 1,034.0 s | $0.02630 |
| 4 | GPT-5.6 Luna (`high`) | 72.79 | 61.0% | 90.5% | 21-12-8 | 73.2% | 174.3 s | $0.01066 |
| 5 | Gemini 3.5 Flash Lite (`high`) | 70.39 | 59.1% | 87.3% | 21-13-10 | 78.6% | 158.5 s | $0.13985 |
| 6 | Gemma 4 31B (`reasoning`) | 62.67 | 37.8% | 100.0% | 11-22-12 | 80.4% | 1,105.6 s | 免费 |
| 7 | Nemotron 3 Ultra 550B A55B (`high`) | 59.79 | 33.0% | 100.0% | 12-28-7 | 83.9% | 586.1 s | 免费 |
| 8 | Ling 3.0 Flash (`reasoning`) | 57.60 | 31.4% | 96.9% | 7-20-8 | 62.5% | 218.1 s | 免费 |
| 9 | MiMo V2.5 (`reasoning`) | 55.34 | 27.7% | 96.9% | 9-30-8 | 83.9% | 445.5 s | $0.00795 |

### 费用口径

- 表中是每位参赛模型完成三轮、共 21 道硬指标样本的推理费用，不包含后续 DeepSeek 裁判费用。
- OpenRouter 付费模型按 2026-08-01 模型目录中的美元单价和 artifacts 记录的输入/输出 tokens 估算；
  OpenRouter 已经以美元报价，因此 HY3、DeepSeek 与 MiMo 不再重复进行人民币换算。
- Google 直连模型按同日 Gemini Developer API Standard 公开价估算；Google 将 thinking tokens 计入输出价格。
  由于 artifact 无法证明 API key 最终落在哪个结算层级，这里记录可复现的标准价等值，而不是声称已核对账单扣款。
- `免费` 表示本轮使用了服务商当时提供的免费端点或免费额度：Gemma 4 走 Google AI Studio 免费路径，
  Nemotron 与 Ling 走 OpenRouter `:free` 端点。它不表示模型推理不存在基础设施成本，也不承诺该福利长期存在。
- 本轮六个付费选手的三轮参赛成本合计约 **$0.65199**。价格来源：
  [OpenRouter Models API](https://openrouter.ai/api/v1/models)、
  [Gemini Developer API pricing](https://ai.google.dev/gemini-api/docs/pricing)。

## 如何读这张表

`pilot-score-v0.1 = 100 × (0.60 × Soft Preference + 0.40 × Hard Reliability)`。

- Hard Reliability 使用每个 recipe 三轮、每轮七题，共 21 个样本。
- 翻译阶段可恢复的硬失败计 0.67；条目错位、空响应、执行失败和 repair 失败计 0。
- Soft Preference 使用 Repeat 01 的九模型完整 round-robin；每题交换 A/B 顺序。
- 只有两次位置交换结论一致的 judge 结果才进入胜负平；未决和硬门槛直接决定不进入软偏好。
- coverage 下降不会直接扣模型分，但必须与分数一起展示。

## 主要发现

### Gemini 3.6 是当前最完整的质量冠军

它同时得到最高 Soft Preference（73.7%）和三轮 21/21 的硬可靠性，且三轮只用 251 秒。
在当前冻结小样本中，84.21 分不是靠单一长板堆出来的。

### HY3 的第二名成立，但不是“最佳部署选择”

HY3 对其余八位的盲裁几乎场场占优；对 Gemini 3.6 的原始对局为 2 胜、2 负、2 平、1 未决。
它的 72.5% Soft Preference 因此不是单场爆冷。

但 HY3 三轮硬通过率为 `6/7 → 4/7 → 7/7`，总耗时 2,421.6 秒，约为 Gemini 3.6
的 9.6 倍、Luna 的 13.9 倍。这个分数只表示当前质量/可靠性公式下的第二名，不表示速度、
价格或综合部署价值第二。实测端到端延迟属于 recipe 事实；模型计算与 OpenRouter 单供应商排队
各自贡献多少，本轮无法拆分。

### DeepSeek 与 Luna 实际处于同一梯队

两者只差 0.26 分。DeepSeek 的硬可靠性更高，Luna 的软偏好更高；以当前单轮盲裁和覆盖率，
不应把第三、第四名解读成稳定的能力鸿沟。Luna 三轮耗时仅 174.3 秒，效率优势非常明显。

### 硬指标全满不等于语言质量好

Gemma 4 和 Nemotron 都是 21/21 硬通过，但 Soft Preference 分别只有 37.8% 和 33.0%。
这再次验证了保留“工程安全”和“文体/语义偏好”两根独立轴的必要性。

## Tokens 与推理效率

下表原样汇总 provider telemetry。部分供应商的 `output_tokens` 已包含或以不同方式核算隐藏
推理，因此 `reasoning_tokens` 不应再次机械加到 total 或用于跨厂商精确计费。

| Recipe | 输入 | 最终输出 | provider-reported reasoning | provider total | 三轮耗时 |
|---|---:|---:|---:|---:|---:|
| Gemini 3.6 | 14,811 | 4,016 | 48,260 | 67,087 | 251.1 s |
| HY3 | 14,694 | 96,607 | 98,958 | 111,301 | 2,421.6 s |
| DeepSeek V4 Flash | 15,309 | 86,279 | 88,329 | 101,588 | 1,034.0 s |
| Luna | 14,997 | 15,269 | 10,907 | 30,266 | 174.3 s |
| Gemini 3.5 Flash Lite | 14,811 | 4,011 | 50,151 | 68,973 | 158.5 s |
| Gemma 4 | 14,811 | 3,914 | 34,987 | 53,712 | 1,105.6 s |
| Nemotron | 16,095 | 26,616 | 21,970 | 42,711 | 586.1 s |
| Ling | 15,105 | 81,720 | 84,530 | 96,825 | 218.1 s |
| MiMo | 14,604 | 21,082 | 20,103 | 35,686 | 445.5 s |

Luna 仍是本轮最清晰的“适度推理”样本：质量分处于第一梯队，同时 provider total 只有
30,266 tokens。HY3 与 DeepSeek 的输出/推理量和耗时则高出一个量级。

## 裁判与覆盖率

- 裁判：DeepSeek 官方 API，`deepseek-v4-flash-thinking-low-8k`。
- Prompt：`translation-judge-v2`；所有输入隐藏参赛模型身份。
- 36 份 pairwise reports，508 次 HTTP 尝试，4 个最终失败结果。
- 裁判估算总成本：**$0.59572**（原始记录 ¥4.114365；按 2026-07-31 最近交易日
  [USD/CNY 参考汇率](https://www.poundsterlinglive.com/bank-of-england-spot/historical-spot-exchange-rates/usd/USD-to-CNY-2026)
  `1 USD ≈ 6.9065 CNY` 粗略换算）。
- 最终失败和 position-inconsistent 样本进入 unresolved，只降低 coverage，不直接算参赛模型输。

参赛模型与裁判合计估算成本约 **$1.24772**；免费端点不以 `$0` 展示，以免把阶段性服务商福利
误读为永久零成本推理。

## 对网页的建议

玲珑已确认本轮分数基本符合预期，且九位选手形成了清晰梯度；这说明 `pilot-score-v0.1` 已通过
第一轮直觉校准。当前排序也暴露了命名风险：它是质量/可靠性综合分，
没有把耗时和价格混入同一个数字。若网页把它写成“Overall Best”，HY3 第二名会掩盖其极端
延迟；更准确的首屏名称是 `Pilot Quality Score`，同时保留 Speed、Cost、Token Efficiency
badges。公式现已通过首轮直觉校准；网页手填 PREVIEW 分数可在下一次网站数据接入任务中替换。
