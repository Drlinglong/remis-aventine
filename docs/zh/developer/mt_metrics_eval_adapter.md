# mt-metrics-eval / WMT MQM adapter

## 目的

V2 adapter 把 Google Research `mt-metrics-eval` 的 `EvalSet`、系统译文和人工 MQM error span
转换为 Aventine Judge pack。它接入更多标准语料，但不改变信任关系：MQM annotation 是 human
gold，LLM Judge 仍然只是待校准的预测器。

adapter 不运行翻译模型、不计算 COMET，也不自动下载外部数据。官方完整数据包约为数 GB，必须
由使用者显式安装在仓外；Aventine 仓库及其 Git 历史不保存 WMT 原文、系统输出或生成结果。

## 准备官方工具与数据

`mtme` optional dependency 固定到核对过的官方 commit。官方 `setup.py` 在中文 Windows 上读取
README 时可能使用 GBK，因此安装前显式启用 Python UTF-8 mode：

```powershell
$env:PYTHONUTF8 = "1"
.\.venv\Scripts\python.exe -m pip install -e ".[mtme]"

.\.venv\Scripts\python.exe -m mt_metrics_eval.mtme --download
```

安装可能引入 `apache_beam`、NumPy 和 SciPy 等可选依赖，因此它没有进入 Aventine 的基础安装。
`--download` 是用户明确执行的外部动作；`aventine doctor` 和 adapter 本身都不会代为下载。

## 构建 bounded pack

需要明确给出 test set、language pair、准确的 rating set 名称，以及调用者声明的 dataset
revision。示例：

```powershell
aventine build-mtme-mqm-pack `
  wmt23 `
  en-de `
  mqm.merged `
  mt-metrics-eval-v2 `
  "$env:USERPROFILE\.cache\aventine\packs\wmt23-en-de-mqm-50.json" `
  --limit 50 `
  --json
```

不同数据版本的 rating 名可能不同。如果名称不匹配，命令会失败并列出该 EvalSet 实际可用的
rating set；不会静默选择另一个 gold。可重复使用 `--system NAME` 限定系统译文。数据不在官方
默认目录时，使用 `--data-root PATH` 指向包含 test-set 子目录的父目录。

## 转换合同

adapter：

- 通过 `EvalSet(..., read_stored_ratings=True)` 读取数据；
- 从 `Ratings(rating_set)` 取得每个 system/segment 的人工 error span；
- 跳过明确为 `None` 的未标注 segment，空 `errors` 则视为人工判定的 no-error；
- 保留 source、标准 reference、system output、rater、document、domain、span、category 和 severity；
- 将 MQM category 映射到 Aventine 的宽类别，但同时保留原始 category/span；
- 按 `critical -> major -> minor -> none` 轮询，并在每个桶内按内容 SHA-256 排序；
- 默认最多选择 50 条，记录候选总数、选择算法和最终内容 SHA-256；
- 对未知 severity、缺失 system output、长度错位和不完整 EvalSet 显式报错。

`dataset_revision` 是调用者声明的外部版本标识；最终 `content_sha256` 进一步锁定实际生成 pack。
两者必须一起保留。相同代码、数据、rating set、system filter 和 limit 应生成逐字节相同的 JSON。

## 接入现有 Judge

输出格式与现有 runner 兼容：

```powershell
aventine run-judge `
  "$env:USERPROFILE\.cache\aventine\packs\wmt23-en-de-mqm-50.json" `
  "$env:USERPROFILE\.cache\aventine\results\wmt23-en-de-deepseek.json" `
  --provider deepseek `
  --workers 4 `
  --max-calls 60 `
  --json

aventine summarize-calibration `
  "$env:USERPROFILE\.cache\aventine\results\wmt23-en-de-deepseek.json" `
  --json
```

这里不会产生 ACES A/B swap，因为这些是单候选 MQM case。Judge 输出解析失败仍计入总分母，
human gold 不会被模型输出覆盖。

## 当前边界

本阶段提供的是 WMT MQM 数据接入和 bounded sampling，不是完整 `mt-metrics-eval` metric
leaderboard，也没有下载整套数据进行真实大规模运行。下一阶段的 ACES/SPAN-ACES adapter 应沿用
相同原则：仓外数据、固定 revision、稳定选择、显式失败和可验证内容 hash。
