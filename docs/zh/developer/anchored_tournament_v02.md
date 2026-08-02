# Anchored sparse tournament v0.2

## 为什么新增这一模式

`pilot-score-v0.1` 要求所有 recipe 完整 round-robin。它适合小规模 pilot，但模型数量为
`M`、题目数量为 `C` 时，完整双顺序软裁决最多需要 `C × M × (M - 1)` 次 judge 输出。

`pilot-score-v0.2-anchored` 不修改 v0.1，而是给持续加入的新选手提供固定赛程：每位 challenger
只与同一个高位、中位和低位锚点比较。旧选手之间的历史对局不重跑，单个新选手最多需要
`3 × C × 2` 次 judge 输出。

## 冻结合同

- manifest 显式设置 `selection_policy.mode = "anchor-panel"`；
- `selection_policy.revision` 标识锚点组合，锚点变化必须使用新 revision；
- `selection_policy.anchors` 必须恰好包含三个已声明 profile id；
- 其余 profile 都是 challenger；
- 每个 challenger 必须分别提供与三个锚点的 pairwise report；
- report 只能连接一个 anchor 和一个 challenger；
- 每个 challenger 仍提供三轮 run artifact，Hard Reliability 仍使用三轮；
- 每个 anchor 只提供与 pairwise report 对应的冻结 Repeat 01 run artifact；
- Soft Preference 仍只使用 Repeat 01，并要求匿名 A/B 与 B/A 位置一致；
- hard validator 已经决定的 case 不调用 judge；
- aggregate 只为 challenger 生成 v0.2 entry，不重写 v0.1 历史排名。

同一 anchor panel 下，所有 challenger 面对相同对手，因此软分仍使用：

`(wins + 0.5 × ties) / resolved decisions`

综合分公式保持 `60% Soft Preference + 40% Hard Reliability`，但 score version 改为
`pilot-score-v0.2-anchored`，不得与 v0.1 数字冒充同一量尺。

## Manifest 示例

```json
{
  "schema_version": 1,
  "aggregate_id": "remis-anchor-panel-example",
  "expected_run_count": 3,
  "selection_policy": {
    "mode": "anchor-panel",
    "revision": "three-tier-2026-08-v1",
    "anchors": ["high", "middle", "low"]
  },
  "profiles": [
    {"id": "high", "runs": ["high-01.json"]},
    {"id": "middle", "runs": ["middle-01.json"]},
    {"id": "low", "runs": ["low-01.json"]},
    {
      "id": "challenger",
      "runs": ["challenger-01.json", "challenger-02.json", "challenger-03.json"]
    }
  ],
  "pairwise_reports": [
    "challenger-vs-high.json",
    "challenger-vs-middle.json",
    "challenger-vs-low.json"
  ]
}
```

仍使用现有命令生成 aggregate：

```powershell
aventine build-pilot-aggregate manifest.json aggregate.json aggregate.md --json
```

输出额外记录 anchor recipe id/hash、锚点 revision、challenger 对手列表、有效裁决覆盖率、
95% Wilson 区间和 `complete | provisional` 状态。表内 `rank` 只表示同一批 challengers
的 placement 顺序，不是全榜单名次。裁判经过 checkpoint/resume 时，成本与 HTTP attempts
优先读取累计字段，避免只报告补跑阶段的增量消耗。

## 边界

- v0.2 是固定锚点面板分，不是完整 round-robin 胜率；
- 锚点 recipe、fixture、judge profile 或 prompt revision 变化后，必须新开 panel revision；
- coverage 不足只会标记 provisional，不得假装确定排名；
- 冲击榜首、置信区间重叠或锚点漂移时，可以另做定点补赛或 top-K 审计；
- 人类模型竞技场结果是独立证据，不自动覆盖冻结 judge 结果。
