# Google AI Studio contestant adapter

`run-remis-google-ai-studio` 是 Aventine core 的受控执行 adapter。它复用指定 Remis checkout
中的冻结样本、生产 prompt、词典注入、结构化解析、硬校验与 repair 工作流，但由 Aventine 直接
调用 Google AI Studio。这样不需要把 Gemini benchmark 配置塞进 Remis 的普通用户 provider
默认值，也不会经过 OpenRouter。

## Recipe 边界

每次运行必须显式指定：

- Google API model id；
- `minimal | low | medium | high` reasoning effort；
- max output tokens；
- Remis checkout、冻结 fixture 和可选 case/track；
- raw Remis artifact 与已验证 Aventine run artifact 的输出位置。

adapter 使用 `generateContent`、`application/json` 响应模式，并设置
`includeThoughts=false`。reasoning effort 是请求上限而不是 effective effort；报告保留
`reasoning_tokens`，但不保存思维摘要。Google 官方当前列出 `gemini-3.6-flash` 与
`gemini-3.5-flash-lite` 均支持 `minimal/low/medium/high`，正式运行前仍应重新核对模型元数据。

## 凭据与隐私

adapter 按以下来源查找 `GEMINI_API_KEY`：

1. Remis 开发用户数据中 provider id 为 `gemini` 的 API key；
2. 当前进程环境变量；
3. 显式 `--env-file`（默认 Aventine 根目录 `.env`）。

key 只进入 `x-goog-api-key` 请求头，不写入 raw artifact、Aventine artifact、recipe hash、日志或
CLI 输出。当前 adapter 没有客户端自动重试；一次 HTTP 请求就是一次可审计尝试。

## Smoke 示例

```powershell
.\.venv\Scripts\aventine.exe run-remis-google-ai-studio `
  J:\V3_Mod_Localization_Factory-worktrees\openrouter-benchmark-provider\tests\fixtures\translation_quality_benchmark_v1.json `
  benchmark_results\gemini-smoke\gemini-3.6-flash.raw.json `
  benchmark_results\gemini-smoke\gemini-3.6-flash.run.json `
  --remis-root J:\V3_Mod_Localization_Factory-worktrees\openrouter-benchmark-provider `
  --runtime-python K:\MiniConda\python.exe `
  --model gemini-3.6-flash `
  --reasoning-effort high `
  --max-output-tokens 16000 `
  --case-id stellaris_missing_color_tags `
  --json
```

正式榜单应从空输出路径开始连续运行三次，并让每次运行拥有独立 artifact。切换模型、effort、
输出预算、Remis checkout/fixture 或 provider 后均形成新 recipe，不得混入同一三轮统计。

`--runtime-python` 必须指向能够运行该 Remis checkout 的 Python。Aventine 通过 stdin 传递不含
秘密的 worker 配置，并用临时 `PYTHONPATH` 暴露双方源码；它不会要求 Aventine 的轻量环境安装
Remis 的 SQLAlchemy、数据库和产品依赖，也不会把 API key 放进进程参数。

## 输出

- `raw_output`：Remis benchmark schema v1，包含逐题译文、硬校验、usage 和 sanitized request
  profile；
- `run_output`：由 `remis-translation-quality-v3` compatibility adapter 立即转换并通过
  `run-result.schema.json` 验证的 Aventine artifact。

若 Google 返回 `MAX_TOKENS`、无 candidate、无最终文本、HTTP 错误或 malformed JSON，本次调用
显式失败。thought parts 不会被拼进要求严格 JSON 的最终译文。
