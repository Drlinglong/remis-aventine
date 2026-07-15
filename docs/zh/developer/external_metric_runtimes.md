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
CC-BY-NC-SA-4.0；在把结果用于商业流程前需要单独检查许可边界。

## 已完成的 smoke

在 `examples/metrics/smoke-v1.json` 的完全匹配英德样例上，新 adapter 已真实跑通：

- MetricX-24 reference：`0.0`；
- xCOMET-XL：`1.0`。

这只能证明 runtime、权重、offline cache、adapter 与 schema 的端到端连通性，不代表模型已经
在 Aventine 的多语言难例上完成校准。下一步应在 48-case pack 的 reference-bearing 子集上比较
MetricX、xCOMET、LLM judge 与人工 gold 的一致和分歧。
