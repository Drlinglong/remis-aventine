# 多语言小样本与远程 Judge

## 目的

`multilingual-48-v1` 用少量、固定、可重建的样本校准 Judge，不把单一模型在中英方向的表现
外推到所有语言。它校准的是评测工具，不是直接回答“X 语言到 Y 语言推荐什么 recipe”。后者仍需
在对应语言方向运行真实 Remis recipe，并把证据标为 `direct | adjacent | unsupported`。

Native review 未来可以作为低置信度、Judge/metric 分歧和高影响失败的人工复核通道；当前里程碑
不依赖 GitHub 社区审核。

## 固定构成

- 12 个 WMT generalMT2022 MQM anchor：`en-de`、`zh-en`、`en-ru` 各 4 个；
- 24 个 ACES contrastive case：`en-es`、`es-fr`、`fr-ru`、`ru-de`、`de-ja`、`ja-ko`、
  `ko-zh`、`zh-en` 各 3 个；
- 12 个 Aventine 原创 Remis case：结构安全、术语/上下文和 repair over-editing 各 4 个；
- 由 case id 的 SHA-256 排序固定切分为 36 calibration + 12 holdout；
- 24 个 ACES case 额外交换 candidate A/B，用于测 position consistency。

真实 ACES 各语言方向的 phenomenon 分布并不均匀。例如 `fr-ru` 只有两个 commonsense ambiguity
类别。manifest 和每个 case 的 provenance 如实保留覆盖范围，不为了形式整齐伪造同构样本。

仓库只保存：

- `calibration-packs/multilingual-48-v1.manifest.json`；
- SHA-256、URL、许可证、选择算法和配额；
- Aventine 自己编写的 12 个 Remis case。

ACES/MQM 原文与 Judge 结果必须放在仓外缓存。ACES 保留其 `CC-BY-NC-SA-4.0` 条款，Google MQM
数据保留 `Apache-2.0` 条款。

## 构建

假设外部文件已经下载到 `%USERPROFILE%\.cache\aventine\sources`：

```powershell
aventine build-calibration-pack `
  "$env:USERPROFILE\.cache\aventine\sources" `
  "$env:USERPROFILE\.cache\aventine\packs\multilingual-48-v1.json" `
  --json
```

构建前会逐个校验固定 SHA-256。缺文件或 hash 漂移会直接失败，不会从“最新 upstream”静默抽取
另一批样本。

## Provider 配置与运行

复制 `.env.example` 为 `.env`，设置：

```dotenv
DEEPSEEK_API_KEY=your-key
XAI_API_KEY=your-key
GEMINI_API_KEY=your-key
```

`.env` 已被 Git 忽略。命令行不接受密钥参数，避免进入 shell history。runner 使用：

- DeepSeek：`deepseek-v4-pro`、thinking enabled、`reasoning_effort=high`、JSON Output；
- xAI：`grok-4.5`、`reasoning_effort=low`、严格 mode-specific JSON Schema；
- Google：`gemma-4-31b-it`、免费层、原生 `generateContent` + response JSON schema；
- prompt revision：`translation-judge-v2`；
- `max_tokens=4000`；
- server-owned case/model/prompt/calibration metadata；
- 默认 120 秒 timeout、最多 2 次有限重试；
- 可配置的总 HTTP request 硬上限。

```powershell
aventine run-judge `
  "$env:USERPROFILE\.cache\aventine\packs\multilingual-48-v1.json" `
  "$env:USERPROFILE\.cache\aventine\results\deepseek-v4-pro-multilingual-48-v1.json" `
  --provider deepseek `
  --workers 4 `
  --max-calls 100 `
  --json
```

4 workers 只并发远程 HTTP；不会加载本地模型或长期占用 GPU。runner 不保存 API key、Authorization
header 或 `reasoning_content`。可选字段返回 `null` 时会规范化为缺省；必填字段仍需通过
`judge-result.schema.json`。

xAI 对照运行只需改 provider 与输出路径：

```powershell
aventine run-judge `
  "$env:USERPROFILE\.cache\aventine\packs\multilingual-48-v1.json" `
  "$env:USERPROFILE\.cache\aventine\results\grok-4.5-low-multilingual-48-v1.json" `
  --provider xai `
  --workers 4 `
  --max-calls 90 `
  --json
```

xAI adapter 记录 API 返回的 `reasoning_tokens` 与 `cost_in_usd_ticks`。后者是实际扣费，优先级高于
根据公开 token 单价计算的估算。Grok 4.5 不能关闭 reasoning，但支持 `low | medium | high`；校准对照
默认使用 `low`，避免简单样本消耗不必要的思考 token。

Google-hosted Gemma 4 对照：

```powershell
aventine run-judge `
  "$env:USERPROFILE\.cache\aventine\packs\multilingual-48-v1.json" `
  "$env:USERPROFILE\.cache\aventine\results\gemma-4-31b-it-multilingual-48-v1.json" `
  --provider google `
  --workers 2 `
  --max-calls 90 `
  --json
```

Gemma 4 没有可调 reasoning effort；该 adapter 记录为 `reasoning_effort=none`，表示 API 没有独立的
思考预算参数，而不是证明模型内部没有推理。Gemma 4 Gemini API 当前只有免费层，输入、输出和缓存
均免费。Google 的免费层条款注明数据可能用于改进产品，因此这里只发送公开 MQM/ACES 与仓库原创
synthetic calibration case；未经明确批准，不应把用户私有 mod 内容路由到该 provider。

## 失败与断点续跑

空 JSON、截断、schema failure、HTTP failure 和请求预算耗尽都是显式 benchmark failure。不要把
它们从准确率分母中静默删除。

当前 `--max-calls` 同时参与逻辑输出规划检查并限制包含 retry 在内的 HTTP 请求总数。修复前，
该值必须高于计划逻辑输出数并留出足够的重试余量。请求预算耗尽属于 judge 基础设施失败，
不能记为候选翻译失败。首届 Remis pilot 的 40 个逻辑输出使用了 113 次 HTTP 请求，最终 32 个
有效；预算拆分、逐项 checkpoint、实时进度与 failure taxonomy 统一由
[issue #5](https://github.com/Drlinglong/remis-aventine/issues/5) 跟踪。

如果外部计费或服务中断，可在恢复后只重试失败项：

```powershell
aventine run-judge `
  "$env:USERPROFILE\.cache\aventine\packs\multilingual-48-v1.json" `
  "$env:USERPROFILE\.cache\aventine\results\deepseek-v4-pro-resumed.json" `
  --resume-from "$env:USERPROFILE\.cache\aventine\results\partial.json" `
  --workers 4 `
  --max-calls 40 `
  --json
```

续跑只复用 schema-valid 且 case id 一致的结果，并强制 model、profile、prompt revision、reasoning
effort 与 max tokens 完全一致。run metadata 同时记录新一段与累计成本。不同 provider 或不同结构化
输出 profile 不能混合续跑。

## 解读边界

Judge 校准至少同时看：

- valid judge rate 与失败类型；
- MQM major/critical recall、false-good 和 no-error false positive；
- ACES base/swap accuracy 与 position consistency；
- calibration/holdout 落差；
- language-pair 和 phenomenon 分解。

小样本只能发现明显弱点、验证回归合同和决定下一批该补什么，不能证明某个 Judge 对 146 个语言
方向普遍可靠。特别是 fluent-but-wrong 高召回与“对自然译文过度挑错”可以同时存在；任何单一综合
分数都会掩盖这种差异。
