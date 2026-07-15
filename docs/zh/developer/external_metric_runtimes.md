# MetricX / xCOMET 隔离 runtime

## “隔离 runtime”是什么

这里的 runtime 不是虚拟机，也不是再复制一份模型。它是一套只服务于某个自动 metric 的
Python 解释器和固定依赖：MetricX、xCOMET 各用一个环境，模型权重仍只在
`J:\AI_Models` 保存一份。

这样做是为了解决真实的依赖冲突。MetricX-24 官方代码固定在较旧的
`transformers==4.30.2` 和 `sentencepiece==0.1.99`；xCOMET 的 COMET 运行栈则需要更新的
SentencePiece、Lightning 和 TorchMetrics。把二者硬塞进 Aventine `.venv` 或 Remis Conda
环境，会使一次无关升级同时破坏三个项目。

Aventine core 因此只做四件事：

1. 用 `metric-pack.schema.json` 校验有界输入；
2. 用无 shell 的参数列表启动指定 Python；
3. 重新计算并核对权重 SHA-256，再记录 model id、哈希、包版本和 GPU；
4. 用 `metric-result.schema.json` 校验结果后落盘。

核心进程不会 import `torch`、`transformers` 或 `comet`，worker 也被强制使用本地模型文件。
哈希检查会增加一次顺序读取权重文件的时间，但避免“命令行写着固定 SHA，实际跑了另一份权重”。
xCOMET 还会进入 Hugging Face offline mode，不会在一次 benchmark 中悄悄下载或改变权重。

## 当前已验证配置

2026-07-15 在 RTX 5090 上验证的两个环境位于：

```text
J:\AI_Models\runtimes\metricx-24
J:\AI_Models\runtimes\xcomet-xl
```

两者均使用 Python 3.11、PyTorch 2.10.0 + CUDA 12.8。完整的关键 pin 位于
`runtimes/metricx-24-cu128.txt` 与 `runtimes/xcomet-xl-cu128.txt`。重建示例：

```powershell
conda create --prefix J:\AI_Models\runtimes\metricx-24 python=3.11 pip -y
J:\AI_Models\runtimes\metricx-24\python.exe -m pip install -r runtimes\metricx-24-cu128.txt

conda create --prefix J:\AI_Models\runtimes\xcomet-xl python=3.11 pip -y
J:\AI_Models\runtimes\xcomet-xl\python.exe -m pip install -r runtimes\xcomet-xl-cu128.txt
```

这些文件只锁定已经验证过的关键兼容边界，不把数 GB 权重、Conda 环境或 Hugging Face cache
提交进 Git。

## 输入合同

`run-metric` 接受明确的 metric pack，而不是猜测任意 benchmark 文件的字段：

```json
{
  "schema_version": 1,
  "id": "my-pack-v1",
  "suite": "remis",
  "cases": [
    {
      "id": "case-1",
      "source": "Hello world",
      "hypothesis": "Hallo Welt",
      "reference": "Hallo Welt"
    }
  ]
}
```

MetricX-24 hybrid 支持 `reference` 和无参考的 `qe` 模式。xCOMET-XL 当前只接受
`source + hypothesis + reference`；Aventine 不会为缺少 reference 的 Remis translation case
编造一个 reference。

## 运行 MetricX-24

```powershell
.\.venv\Scripts\aventine.exe run-metric examples\metrics\smoke-v1.json metricx.json `
  --metric metricx-24 `
  --runtime-python J:\AI_Models\runtimes\metricx-24\python.exe `
  --model-path J:\AI_Models\MetricX-24-Hybrid-XL-v2p6-bfloat16 `
  --model-id google/metricx-24-hybrid-xl-v2p6-bfloat16 `
  --model-sha256 f6fce442b0235b8d8dd9391214063c9ad48a3e90961218183aeca15a51c58d6f `
  --mode reference `
  --tokenizer-path J:\AI_Models\MetricX-24-Hybrid-XL-v2p6-bfloat16\tokenizer `
  --metricx-source J:\AI_Models\MetricX-24-Hybrid-XL-v2p6-bfloat16\metricx-source
```

MetricX 输出范围为 0–25，`lower_is_better`。同一个 hybrid checkpoint 在 `qe` 模式可以跳过
reference；这尤其适合 Remis 现有的 translation benchmark。

## 运行 xCOMET

```powershell
.\.venv\Scripts\aventine.exe run-metric examples\metrics\smoke-v1.json xcomet.json `
  --metric xcomet `
  --runtime-python J:\AI_Models\runtimes\xcomet-xl\python.exe `
  --model-path J:\AI_Models\XCOMET-XL\checkpoints\model.ckpt `
  --model-id Unbabel/XCOMET-XL `
  --model-sha256 b644a48a1163ca7f8d3bcf237816eea7ecf368ecdbd6eb16ea27fef218fcd716 `
  --mode reference `
  --hf-home J:\AI_Models\XCOMET-XL\hf-cache
```

xCOMET 分数是 `higher_is_better`，并在模型提供时保留 error spans。其模型卡使用
CC-BY-NC-SA-4.0；用户已在 gated model 页面手动同意访问，这只解决权重访问，不等于额外取得
商业授权。在把模型或结果用于商业流程前仍需重新检查许可边界；当前本地研发与校准继续进行。

## 已完成的 smoke

在 `examples/metrics/smoke-v1.json` 的完全匹配英德样例上，新 adapter 已真实跑通：

- MetricX-24 reference：`0.0`；
- xCOMET-XL：`1.0`。

这只能证明 runtime、权重、offline cache、adapter 与 schema 的端到端连通性，不代表模型已经
在 Aventine 的多语言难例上完成校准。下一步应在 48-case pack 的 reference-bearing 子集上比较
MetricX、xCOMET、LLM judge 与人工 gold 的一致和分歧。

## Calibration pack 接入

`build-metric-pack` 接受现有 MQM/ACES calibration pack：single case 生成一个 hypothesis，
pairwise case 生成 `candidate_a`、`candidate_b` 两个 hypothesis。没有 reference 的 Remis case
会被明确计入 `skipped_case_counts`，不会编造 reference。

```powershell
aventine build-metric-pack source-pack.json metric-pack.json --json
aventine run-metric metric-pack.json xcomet.json <上述 xCOMET runtime 参数>
aventine report-metric-calibration metric-pack.json xcomet.json report.json report.md --json
```

报告对 single case 给出按 gold verdict/severity 的分数分布，以及不依赖阈值的 pass/fail、
severity 排序准确率；对 pairwise case 直接比较两个分数的 winner 与 gold winner，并按语言方向和
phenomenon 分组。不要从单条语言方向样本推导该语言的稳定模型排名。

## 2026-07-15 本地 xCOMET 校准

本地 RTX 5090 对两份已下载 pack 完成真实运行：

- WMT23 `en-de` MQM：50 条；none/minor/major 均分为
  `0.9507 / 0.8953 / 0.8468`；pass/fail 排序准确率 `76.10%`；severity 排序准确率
  `72.75%`。
- ACES global：50 个 pairwise case、100 个 hypothesis、40 个语言方向；winner 命中
  `38/50 = 76%`，无平局。

这说明 xCOMET 能提供独立且有方向性的证据，但 24% ACES winner 失败足以否定“让 metric 单独
终审”。它应与 hard validator、校准后的 LLM judge 和可用的人类 gold 并列，而不是取代它们。
仓库只保存无原文的 `calibration-packs/xcomet-local-v1.manifest.json`；完整 pack、逐 case 分数和
报告留在 Git-ignored `benchmark_results/xcomet-calibration-2026-07-15/`。

Transformers 4.57.6 会对本地 XLM-R tokenizer 误报 Mistral regex 警告；Transformers 官方已将
这一行为记录为 non-Mistral tokenizer 的误报。不要对 XLM-R 强设 `fix_mistral_regex=True`，该
参数会破坏其 Metaspace pre-tokenizer。

## Gold / Judge / Metric 对齐结果

相同 50 条 WMT23 `en-de` MQM 与 50 对 ACES 已使用 DeepSeek V4 Pro 重新判断，并通过
`report-evidence-alignment` 与 xCOMET 逐 case 对齐：

- MQM：Judge verdict accuracy `56%`，major recall `82.35%`，false-good `50%`；主要问题是
  minor/no-error 边界，而不是 major 完全失明。xCOMET 在 Judge 判对/判错两组的均分分别约
  `0.8830 / 0.9138`，说明二者失败并非简单同向。
- ACES：Judge base accuracy `84%`，swap accuracy `88%`，position consistency `86%`；只有
  position-consistent verdict 才进入严格对齐，此时 43 对中双方都对 34、仅 Judge 对 7、仅
  xCOMET 对 0、双方都错 2。两者任一命中的 oracle union 为 `95.35%`，它是互补性上限，不是
  可直接部署的 ensemble 准确率。

完整逐 case 结果保存在 Git-ignored
`benchmark_results/evidence-alignment-2026-07-15/`。16 个 ACES case 进入 review queue，原因包括
位置不一致、Judge/xCOMET 分歧或双方共同失败。这个结果支持下一阶段使用 hard validator 先 veto、
自动 metric 提供证据、LLM Judge 处理软质量与争议，而不是让任一模型独自终审。
