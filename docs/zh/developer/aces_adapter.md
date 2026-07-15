# ACES / SPAN-ACES adapter

## 目的

V3 adapter 把完整 ACES 或 SPAN-ACES JSONL 转成 Aventine pairwise Judge pack。ACES 提供一条
相对更好的译文和一条包含指定 accuracy phenomenon 的错误译文；SPAN-ACES 在相同 36,476 条
case 上增加错误 span annotation。

它们测试的是 Judge 能否选出相对更好的候选，不意味着 `good-translation` 在所有维度上绝对无错。
因此 gold verdict 是 pairwise winner，不应改写成单候选 pass/fail 金标。

## 数据与许可证

官方数据位于 `nikitam/ACES`，包含：

- `challenge_set.jsonl`：36,476 条、146 个语言方向、68 个 phenomena；
- `span_aces.jsonl`：相同 case 加 span 字段；
- 许可证：`CC-BY-NC-SA-4.0`。

数据保存在仓外。adapter 要求调用者同时给出 dataset revision 和预期 SHA-256，hash 不匹配时
直接退出。仓库不自动下载，也不把生成 pack 加入 Git。

## 构建 ACES pack

```powershell
aventine build-aces-pack `
  "J:\AI_Models\ACES-SPAN-ACES-b497a645\challenge_set.jsonl" `
  "$env:USERPROFILE\.cache\aventine\packs\aces-global-50.json" `
  --kind aces `
  --dataset-revision b497a6456957a5660ac20b8cac5b5222eb9b669c `
  --expected-sha256 f4dc0df4f8ade8e94adf691f78f3cba62a266515aded09f1e53e433943c1dd93 `
  --limit 50 `
  --json
```

SPAN-ACES 只需切换输入、kind 和 hash：

```powershell
aventine build-aces-pack `
  "J:\AI_Models\ACES-SPAN-ACES-b497a645\span_aces.jsonl" `
  "$env:USERPROFILE\.cache\aventine\packs\span-aces-global-50.json" `
  --kind span-aces `
  --dataset-revision b497a6456957a5660ac20b8cac5b5222eb9b669c `
  --expected-sha256 6fab3d87afc610981bd767b6b67fe503380c5b65d17f20ff2838f2df1af5b235 `
  --limit 50 `
  --json
```

可重复使用 `--language-pair ja-ko` 或 `--phenomenon omission` 缩小范围。filter 没有匹配项时
显式失败。

## 稳定选择与 A/B

adapter 按 `(language_pair, phenomenon)` 分组，在组内按完整 upstream row 的 SHA-256 排序，
再跨组 round-robin，优先提高小 pack 的语言和现象覆盖。candidate A/B 由同一 row hash 的奇偶
稳定决定。相同数据、revision、filter 和 limit 会生成相同 JSON。

所有 case 都标为 `origin_suite=aces`，现有 Judge runner 会额外生成 A/B swap，用于计算 position
consistency。Hard validator 与 Judge 的信任边界不变。

## SPAN-ACES 边界

`incorrect-translation-annotated` 是 human gold，绝不能放入 Judge 的 `input`，否则等于泄题。
adapter 把它保存在 `gold.span_annotation`，并解析 `<v>...</v>` 为字符 offset。

官方数据中部分 annotated text 去掉标记后仍不与 `incorrect-translation` 逐字相同。因此 adapter
同时保留：

- 原始 annotated translation；
- 去标记文本；
- 相对于去标记文本的 spans；
- `aligned_to_incorrect_translation` 标志。

不对齐时不能把 offset 假装成 candidate offset。没有 `<v>` marker 的官方记录保留为空 span，
而不是伪造范围；嵌套或不成对 marker 则视为数据合同失败。

## 接入 Judge

生成 pack 可直接传给 `run-judge`。每个 base case 会产生一次正常判定和一次 A/B swap，因此 50 条
pack 最多计划 100 个逻辑 Judge 输出；`--max-calls` 还需给有限重试留出余量。
