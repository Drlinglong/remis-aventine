# Judge Provider 小样本对照（2026-07-15）

本报告比较同一份 `multilingual-48-v1` 校准包在三个远程 Judge 上的表现。它回答的是
“Judge 能否识别这批已知正确/错误译文”，不是“哪个模型最适合任意 X→Y 翻译方向”。样本量仍小，
结果用于发现明显弱点和建立回归基线，不用于宣称普遍语言能力。

## 配置

| Provider | 模型 | 推理配置 | 结构化输出 | 本轮费用 |
| --- | --- | --- | --- | ---: |
| DeepSeek | `deepseek-v4-pro` | high thinking | JSON Output | ¥1.056608 |
| xAI | `grok-4.5` | `reasoning_effort=low` | strict JSON Schema | $0.479668 |
| Google | `gemma-4-31b-it` | API 无独立 reasoning effort | response JSON schema | $0 |

费用只比较本次完整主运行。额外 smoke、诊断和失败重试不计入表中。

## 结果

| 指标 | DeepSeek V4 Pro | Grok 4.5 low | Gemma 4 31B |
| --- | ---: | ---: | ---: |
| 有效 base 输出 | 48/48 | 48/48 | 47/48 |
| base 总正确 | 40/48 (83.3%) | 40/48 (83.3%) | 35/48 (72.9%) |
| MQM | 7/12 | 8/12 | 4/12 |
| ACES base | 21/24 | 20/24 | 19/24 |
| Remis synthetic | 12/12 | 12/12 | 12/12 |
| calibration split | 31/36 | 31/36 | 27/36 |
| holdout split | 9/12 | 9/12 | 8/12 |
| 全部 pairwise | 33/36 (91.7%) | 32/36 (88.9%) | 31/36 (86.1%) |
| ACES swap | 21/24 (87.5%) | 20/24 (83.3%) | 18/24 (75.0%) |
| position consistency | 23/24 (95.8%) | 24/24 (100%) | 19/23 (82.6%) |
| false-good | 22.2% | 11.1% | 77.8% |
| 有效 base 中 high confidence | 48/48 | 48/48 | 47/47 |

Gemma 的一次 base 输出持续失败：`aces-de-ja-01-009c93d8ee`。响应以合法 JSON 开始，随后追加
Markdown code fence，因而违反结构化输出合同。runner 没有擅自截断或修复，按 benchmark failure
保留在分母中。

## 结论

- DeepSeek 与 Grok 总正确数相同，逐题比较为 39 题共同正确、7 题共同错误、各自独占 1 题；目前
  没有证据证明更昂贵的 Grok 在这个任务上形成决定性优势。
- Grok 的 false-good 最低且位置一致性最好，但同一条德语 no-error case 三次运行出现一次 pass、
  两次 fail，而且都自报 high confidence，说明模型内在波动仍不可忽略。
- Gemma 免费、满模型且 Remis synthetic 全对，适合廉价 smoke/baseline；但 MQM 仅 4/12、
  false-good 达 77.8%，当前不适合作为默认质量闸门。它仍抓住了两个旗舰 Judge 都漏掉的一条
  critical untranslated case，因此可作为异构复核信号。
- 三个模型几乎总报 high confidence。该字段尚未校准，不能当作人工复核路由的可靠概率。
- 当前默认可继续使用 DeepSeek；Grok 保留作高价值对照，Gemma 保留作免费回归基线。下一阶段应
  扩充 major/critical 与 fluent-but-wrong 样本，再决定是否需要 ensemble 或 native review。

## 可复现产物

结果保存在仓外，避免提交第三方样本与模型输出：

- `deepseek-v4-pro-multilingual-48-v1-resumed.json` —
  SHA-256 `ee3c49a7688002f251e49ab23d5ebfcb1fbfc691e87005caf77453fc393467a5`
- `grok-4.5-low-multilingual-48-v1.json` —
  SHA-256 `5dba2d03ce7cb78b9bae2132ed20efda4ebe437c4c3d99bffb44a8a7b0cb009d`
- `gemma-4-31b-it-multilingual-48-v1-resumed.json` —
  SHA-256 `f9c3bc5408d57e984946e1a6a20ff16d5e58c4a3765db9cd42941a7d59139c12`

三个产物均已检查：不包含 API key、认证 header 或隐藏 reasoning 内容。

## 数据边界

Google AI Studio / Gemini API 免费层可能使用提交内容改进产品。本轮只发送公开 MQM/ACES 与
Aventine 原创 synthetic case；未经明确批准，不应把私有 mod 原文送入该 provider。
