# Judge 校准、Summary Metrics 与 Remis 兼容层

## 当前交付切片

第一阶段先让评测合同和失败传播运转起来：

1. `judge-result.schema.json` 锁定结构化 Judge 输出；
2. 两组纯合成 MQM/ACES fixture 提供可重复输入；
3. `calibration.py` 计算确定性汇总指标；
4. `adapters/remis.py` 把 Remis 当前 benchmark artifact 转成 Aventine run result。

后续切片已经增加仓外真实小样本构建器与 DeepSeek V4 Pro runner，详见
[`multilingual_calibration.md`](multilingual_calibration.md)。Fake fixture 仍保留，用于零成本测试失败合同；
它不再代表当前能力上限。

这些 fixture 故意包含 false-good、选错 pairwise winner、JSON parse failure 和 schema failure。
校准工具如果只能在“所有输出都完美”时运行，就无法证明失败合同有效。

## Judge Result Schema

Judge 输出分两种模式：

- `single`：`pass | fail | uncertain`；
- `pairwise`：`candidate_a | candidate_b | tie | neither | uncertain`。

每个结果必须记录：

- judge profile、真实 model id、prompt revision 和 calibration revision；
- 置信度；
- 结构化错误列表；
- rationale 与 limitations。

每条错误必须指向候选、MQM 风格类别和 `minor | major | critical` 严重度。`single` 模式只能
引用 `candidate`，`pairwise` 模式只能引用 `candidate_a` 或 `candidate_b`。`fail` 结果至少需要
一条错误，避免模型只输出无法审计的否定结论。

维度分数是可选证据，不存在一个可以覆盖 hard validator 的“综合 Judge 总分”。

## Fake Calibration Fixtures

```text
examples/calibration/fake-mqm-v1.json
examples/calibration/fake-aces-v1.json
```

它们是仓库原创的极小合成样本，不来自 WMT/ACES 原始数据，因此可以安全进入 Git。未来接入真实
MQM/ACES 数据时，应继续使用仓外数据目录并保留 upstream license/citation metadata。

Fixture envelope 当前包含：

- `input`：供人类理解的 source/candidate；
- `gold`：人工 anchor 的 mode、verdict、最大严重度、主类别和 phenomenon；
- `judge_output`：结构化对象，或用于测试失败传播的原始字符串/非法对象。

## Summary Metrics

```powershell
aventine summarize-calibration examples/calibration/fake-mqm-v1.json --json
aventine summarize-calibration examples/calibration/fake-aces-v1.json --json
```

当前输出：

- `valid_judge_rate`、JSON parse/schema failure count；
- 总体、single 和 pairwise verdict accuracy；
- major/critical error recall、major false-negative rate；
- ACES 风格 bad-candidate detection accuracy；
- false-good rate；
- low-confidence rate；
- source-evidence coverage；
- phenomenon accuracy；
- category/severity confusion counts。

准确率和 recall 的分母包含非法 Judge 输出，因此 parse/schema failure 不会被从难例里静默删除。
`false_good_rate` 只统计明确把 gold fail 判成 pass 的情况；非法输出单独报告，不伪装成 false-good。

这些指标校准的是 Judge，不是翻译模型。Fake fixture 的具体数值没有产品意义，它们只验证计算和
失败传播。

## Remis 复用策略

近期不在 Aventine 重写 Remis 已验证的轮子。以下实现继续留在 Remis，并可由 compatibility
adapter 或后续受控 execution adapter 直接复用：

- Provider factory 与本地/云端调用路径；
- 生产翻译 Prompt、格式 Prompt 和 Glossary 注入；
- `PostProcessValidator` 与游戏专用规则；
- `TranslationFixerAgent`；
- `scripts/developer_tools/evaluate_translation_quality.py`。

当前 adapter 是只读 artifact adapter：

```powershell
aventine adapt-remis-result `
  J:\V3_Mod_Localization_Factory\benchmark_results\REMIS_RESULT.json `
  .\aventine-result.json `
  --json
```

它会：

1. 区分 `completed`、`execution_failure` 和 `structured_output_failure`；
2. 把 Remis hard check 和 findings 映射到 Aventine envelope；
3. 保留候选输出与必要 hash/运行指标；
4. 丢弃 `raw_response`，减少 provider 内部信息和无关 reasoning 泄漏；
5. 用 provider/model/track/prompt/fixture/policy 生成稳定 compatibility snapshot hash；
6. 在写出前用 `run-result.schema.json` 验证结果。

因为旧 Remis artifact 没有原生 Aventine recipe manifest，这个 hash 明确标记为
`provenance=compatibility_snapshot`，不能伪装成 manifest hash。

## 依赖反转原则

当前允许 Aventine 依赖 Remis checkout，是为了尽快验证真实流水线而不是重造生产代码。未来只有
以下内容适合进入 Aventine core：

- 已稳定的通用 schema；
- 与具体游戏/provider 无关的 calibration/aggregation；
- 可复现 artifact 与报告协议；
- 不依赖 Remis 全局状态的纯函数。

Remis 特定的执行、副作用和 UI 继续留在 Remis。这个边界可以逐步反转，但不要求现在提前完成。
