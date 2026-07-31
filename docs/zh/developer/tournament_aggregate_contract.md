# Tournament aggregate contract

`src/remis_aventine/schemas/tournament-aggregate.schema.json` 定义 Stream A 的生成物合同。
它描述一个 recipe 在固定 benchmark pack 上的版本化聚合结果：

- `schema_version` 管理 JSON 结构；`score_version` 管理分数政策。benchmark pack 和 recipe
  都必须带可复核的 SHA-256；
- overall、component、regional score 以及 Remis workflow signal 都必须同时记录样本量、裁决量、
  coverage 和状态；未测项使用 `null` + `insufficient_data`/`failed`，不能用 0 冒充结果；
- regional score 还保留逐语言的 score、sample count、decision count 和 coverage；components 支持
  semantic fidelity、constraint integrity、cross-context consistency、repair precision、style/voice
  和 repeatability 等计划中的维度；
- stage failure counts/multipliers、延迟与吞吐、token/cost、峰值 VRAM/RAM、context budget、
  batch size、glossary provenance 和生成环境属于结果证据的一部分。成本记录 source、effective_at
  以及 estimated/observed 状态；未测 telemetry 可使用 `null`；
- 固定字段和嵌套对象拒绝未知属性。未来实验字段只能放进命名空间化的 `extensions.x-*`，稳定
  合同字段应通过新的 `schema_version` 演进。

这是聚合器生成的 JSON artifact，不是网页手填数据，也不是网页展示层的事实来源替代品。网页只有
在读取并验证该 artifact 后才能消费其中的分数。

验证仍复用现有入口：

```python
from pathlib import Path

from remis_aventine.validation import validate_document

validate_document(
    Path("path/to/tournament.aggregate.json"),
    "tournament-aggregate.schema.json",
)
```
