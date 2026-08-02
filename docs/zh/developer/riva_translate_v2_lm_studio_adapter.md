# Riva Translate 4B Instruct v2 · LM Studio adapter

`run-remis-riva-lm-studio` 让 Aventine 通过 LM Studio 的 OpenAI-compatible API 运行
NVIDIA `Riva-Translate-4B-Instruct-v2`，并输出 Remis 原始报告与 Aventine run artifact。

它不是把 Riva 当成普通聊天模型。官方模型卡要求 system message 使用语言方向代码，例如
`en-zh-cn`；user message 直接放待译文本。adapter 因此采用模型原生提示格式。

## Recipe 口径

- 每个字符串一次独立请求，避免要求专用 NMT 模型生成批量 JSON；
- adapter 把结果确定性封装为 `{"translations": [...]}`；
- Remis 词典条目转换为 user/assistant few-shot 对，策略标记为 `few_shot_priority`；
- repair 使用 `source_retranslation`：从源文重新生成最终译文；
- repair 仍接受 `must_remain_unchanged_indexes` 检验，不会因为重新翻译而自动得到修复分；
- reasoning 固定记录为 `none`；
- LM Studio loaded model metadata、实际 response model、量化、tokens、请求数、模型原生
  prompt hash 和 Remis checkout identity 都进入 artifact；
- endpoint 与本地模型路径不进入公开 artifact。

因此，Riva 的结构化输出成功率表示该完整 recipe 的可靠性，不应解释为“模型原生 JSON
instruction following”。网页或报告需要保留 `deterministic_adapter_json_wrapper` 标记。

## 准备 LM Studio

1. 下载并加载 Riva v2 的 GGUF 量化；
2. 把 context length 设为至少 8192；
3. 启用 Local Server，默认地址为 `http://127.0.0.1:1234/v1`；
4. 最好只加载一个模型，这样可以使用 `--model auto`；否则传入 loaded instance ID；
5. 记下实际量化，例如 `Q8_0`、`Q6_K` 或 `Q4_K_M`。

## 单题 smoke

```powershell
.\.venv\Scripts\aventine.exe run-remis-riva-lm-studio `
  J:\V3_Mod_Localization_Factory\tests\fixtures\translation_quality_benchmark_v1.json `
  benchmark_results\riva-v2-smoke.raw.json `
  benchmark_results\riva-v2-smoke.run.json `
  --remis-root J:\V3_Mod_Localization_Factory `
  --runtime-python J:\V3_Mod_Localization_Factory\.venv\Scripts\python.exe `
  --model auto `
  --quantization Q8_0 `
  --case-id stellaris_proclamation_style `
  --json
```

如果 Remis 使用 Conda，而不是仓库内 `.venv`，请把 `--runtime-python` 换成 Remis 实际
可导入依赖的 Python。命令不会自动下载或加载模型。

## 正式三轮

先完成单题 smoke，再把 `--case-id` 删除并运行三次。每轮使用不同输出文件，不要覆盖：

```powershell
.\.venv\Scripts\aventine.exe run-remis-riva-lm-studio `
  J:\V3_Mod_Localization_Factory\tests\fixtures\translation_quality_benchmark_v1.json `
  benchmark_results\riva-v2-repeat-01.raw.json `
  benchmark_results\riva-v2-repeat-01.run.json `
  --remis-root J:\V3_Mod_Localization_Factory `
  --runtime-python J:\V3_Mod_Localization_Factory\.venv\Scripts\python.exe `
  --model auto `
  --quantization Q8_0 `
  --track all `
  --recipe-id remis.lm-studio.riva-translate-4b-instruct-v2.q8-0 `
  --json
```

正式入榜前必须确认三轮使用同一模型文件、量化、LM Studio runtime 设置、Remis commit、
fixture hash 和 recipe id。

## 未来接入 Remis 产品

不要在 Remis 中仅用 `model_id == riva` 给现有通用 LLM prompt 加条件分支。更可维护的边界是
新增通用 `native_translation_model` capability：

1. model profile 声明语言方向 tag、batch 策略、glossary 策略和 repair 策略；
2. Native NMT executor 对每个字符串构造模型原生 messages；
3. executor 把逐条结果确定性装回 Remis 的 batch contract；
4. validator、post-process、任务进度与导出继续复用现有 Remis 工作流；
5. 不支持的能力必须显式降级或禁用，不能静默回到通用聊天 prompt。

Aventine 已把纯消息构造暴露为 `riva_language_pair()`、`riva_glossary_pairs()` 和
`build_riva_messages()`，并用 model-free tests 锁定行为。Remis 实装时应复用同一合同与测试
向量，但由 Remis 自己拥有产品 runtime，不让桌面应用反向依赖评测工具。

## 当前语言边界

Riva v2 支持英语与 36 种非英语语言之间的双向翻译。adapter 已覆盖官方语言标签，包括
简繁中文、日、韩、德、俄、法、西、葡、土等；不允许两个非英语语言之间直接互译。

官方资料：

- https://huggingface.co/nvidia/Riva-Translate-4B-Instruct-v2
- https://build.nvidia.com/nvidia/riva-translate-4b-instruct-v2/modelcard
