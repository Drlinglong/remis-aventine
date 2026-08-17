# Aventine v0.3 多语言执行与裁判协议

## 固定拓扑

v0.3 使用 18 个方向：中英互译 2 个，中文或英文到日、韩、德、俄、法、西、巴葡、土耳其语
各 8 个。不做小语种之间互译。综合智力是 18 个方向的等权平均；缺失方向使结果不完整，绝不把
剩余方向重新归一化。

东亚分数先分别计算中文源与英文源到日/韩的平均，再合并两个源语言组；欧陆分数同理，目标为
德/俄/法/西/巴葡/土。单语言能力是中文和英文到该语言的平均。中英互译、Hard Format 与 Soft
Preference 独立报告。

## 参赛 recipe 执行

`exam_execution.py` 把私密冻结卷展开为内容寻址的 job plan：

- 默认两次 repeat；
- 一个 execution pack 对应一次参赛模型调用；
- plan、exam 和每个 checkpoint 都有 SHA-256 身份；
- 每次响应后原子保存，恢复时不会重复已经付费的调用；
- 调用前以 reserve cost 做保守预算闸门，调用后记录 observed provider cost；
- 完整考卷内容不进入公共仓库，公共层只拥有中立调度协议。

## Hard Format 路由

`structural_validation.py` 不再把“token 数量不同”直接等同于翻译失败：

1. `raw_contract_pass` 记录模型是否一次遵守响应契约；
2. `normalization_operations` 记录 Remis parser/护栏做过什么；
3. `final_contract_pass` 记录 recipe 最终交付是否可用；
4. 未闭合标签、非法概念语法等确定性损坏直接 hard fail；
5. 最终语法合法、但变量出现次数变化的结果交给两名独立结构裁判；
6. 两名结构裁判同意“符合目标语言行文”才通过，同意“变量丢失/新增”才失败，分歧则 unresolved；
7. 引号混用、反斜杠加弯引号等只产生 punctuation warning。

这意味着 parser 修好 `[[ *QT*]]` 属于完整 recipe 的成功交付，同时保留模型原始 contract
violation，不会把两件事混成一个 Hard Reliability 数字。

## 自适应双裁判

`dual_judge.py` 使用固定 seed 决定初始顺序：一名裁判看 A/B，另一名看 B/A。两者映射回真实候选
后一致即 resolved；不一致时，两名裁判各补看缺失顺序。另固定抽取每个分层中 20% 的样本，无条件
做完整四裁审计。

有双顺序证据时，每位裁判必须自身 position-consistent，且两名裁判仍须一致；否则结果是
unresolved，只降低 coverage。报告必须包括 resolved coverage、unresolved、position consistency、
observed cost 和 cost per resolved decision。两个裁判必须来自不同模型家族，而且任一参赛候选的
模型家族都被禁止自判。

Gemini 3.7 Flash high 已通过资格测试，但其历史术语细错召回不足，因此默认只能与非 Google、召回
侧更强的裁判组成异构面板；Gemini/Google recipe 参赛时，Google 家族整组退出。

## 聚合边界

`multilingual_scoring.py` 只聚合已经 resolved 的方向证据，并让 coverage 与质量分开。网站的质量—
金钱、质量—速度和质量—token 散点图必须使用 observed telemetry；未知本地成本不得伪装成 `$0`，
unresolved 也不得伪装成参赛模型失败。
