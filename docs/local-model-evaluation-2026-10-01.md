# 本地模型中英增量评测（2026-10-01）

本轮在原有 21 模型统一目录中追加两个本地配方，共 23 个模型；默认选择 21 个，两个旧产品线型号仍可手动选择。原始 17 模型与上一轮增量的成绩 JSON 保持原样。

评分版本：`v0.3-zh-en-anchors-local-20261001-v1`。裁判版本：`priority-mimo26-luna6-ds41-gemini38-20260925-v1`。

## 结果与覆盖

| 本地配方 | 中英综合 | 中→英 | 英→中 | 软评测已决/总数 | 裁判已观测 USD | 费用待核实调用 |
| --- | ---: | ---: | ---: | --- | ---: | ---: |
| `bilibili/index-translate-9b-q8_0` | 44.07 | 43.07 | 45.08 | 55/60 | 0.365544 | 0 |
| `xiaomi/mimo-v2.6-distill-qwen-9b-q4_k_s` | 27.25 | 15.94 | 38.56 | 53/54 | 0.462920 | 2 |

## 配方与格式可靠性

两者均在 RTX 5090 32GB 上，通过 LM Studio 原生 `/api/v1/chat` 运行。同一 system prompt 与全部 44 个 user prompt 的哈希均匹配封存基线，双向各重复两次；不执行模型修复。

| 配方 | 量化 | temperature | Thinking | 上下文 | 原始 JSON 合格 | 解析后合格 | 返回/预期条目 | 推理总耗时秒 |
| --- | --- | ---: | --- | ---: | --- | --- | --- | ---: |
| `bilibili/index-translate-9b-q8_0` | Q8_0 | 0.0 | off | 44800 | 8/44 | 22/44 | 54/76 | 91.834 |
| `xiaomi/mimo-v2.6-distill-qwen-9b-q4_k_s` | Q4_K_S | 0.3 | on | 24576 | 25/44 | 37/44 | 53/76 | 227.579 |

解析后合格使用封存 Remis 解析器。未返回的条目由封存 densify 规则计为硬失败，不补做模型调用，不把缺失算成通过。原始响应、解析后的译文与逐条校验分别保留在私有运行记录。本轮衡量 Remis 的 JSON 批处理翻译配方，不能把分数直接解释为普通单段文本翻译能力。

Index 按[官方翻译设置](https://github.com/bilibili/Index-Translate#default-inference-settings)关闭 Thinking、temperature 0；MiMo 显式开启 Thinking、temperature 0.3。两者量化、上下文与推理设置不同，因此这是完整配方比较。未显式指定的采样器设置继承本地运行时；候选请求输出上限 32768，实际受已加载上下文限制；裁判不设客户端输出 token 上限。

本地翻译没有远程 API 账单；硬件与电费未计量，公开成本为 null，且不参与成本排名。裁判费用仅计本轮新增调用，不重复计入复用锚点的历史费用；费用缺失保留为待核实。

## 封存协议

沿用 Qwen 3.8 Max、Muse Spark 1.2、Solar Pro 4 的封存译文与已完成结构判定；种子 20260925，每方向每锚点最多 10 个结构合格案例。双裁判首轮相反顺序，20% 案例交换位置复核；两个有效同票才能裁定，位置不一致或无共识维持未决。

Index 优先使用 MiMo V2.6 Pro 与 GPT-6 Luna；MiMo 蒸馏候选排除 MiMo 家族，优先使用 GPT-6 Luna 与 DeepSeek V4.1 Flash。Gemini 3.8 仅补裁，Grok 不进入本轮。两者均有 Qwen 基础架构来源，裁判池没有 Qwen 家族。

每方向 60% 已决软偏好 + 40% 已决硬可靠性，两方向等权。软偏好池化已决案例，覆盖率差异会改变三个锚点的有效权重。未决项在覆盖率中单列；这是小样本固定锚点定位，不构成显著性证明，也不把跨赛程排序视为已校准。

父锚点清单哈希：`55b8cc1ab8a3d13022f1083ea00db6f1d1b9737e1b6100225b4609b48fae4a3a`。本轮清单哈希：`34236fa200f81c7f23e6c24e4054fc078c550721b72eb8c3c17c5bcfb7d42819`。

试卷哈希：`7b62edfd33d350743ba957f9117d7f7c7ac15fbd7066711cd5125719b5459294`。执行计划哈希：`65801eafc5b4aca7d1974364454604c68333763356864db21810b8f43866bd69`。

## 可复现证据

私有 corpus 运行目录：`runs/v0.3-zh-en-preview/local-panel-20261001/`。其中保存原始响应、标准化条目、裁判计划/收据、运行时元数据、源文件快照及 `invariant-audit.json`。公开 JSON 和本报告只包含聚合数据、配方与哈希，不含试题、译文或裁判理由。

- `bilibili/index-translate-9b-q8_0` 执行身份：`56eb544ee0a00a0268864051d0f3ceb0381f134b65f0548de9f79b6f4716cb42`。
- `xiaomi/mimo-v2.6-distill-qwen-9b-q4_k_s` 执行身份：`d95ed0a76f4a6a402f82c59e33df0b99e938d4b471460727c90cfbe834da8ab2`。

## 裁判耗时与运行控制

GPT-6 Luna 与 DeepSeek 裁判沿用 high reasoning，MiMo 裁判开启 Thinking，Gemini 补裁为 medium；不设置客户端输出 token 上限。结构阶段初始与 Index 软比较为 4 并发，MiMo 结构缺票恢复为 8 并发，MiMo 软比较为 24 并发。运行器的 180 秒是网络读取超时，不是整次调用的总时限；持续收到数据的请求可能等待更久。

初始 DS 调用未指定供应商；已完成结构响应的供应商均为 OpenInference。节点实测低吞吐且部分请求长时间等待，之后停止本地等待并保留两个未知在途调用，不重复提交收费请求，按原协议由 Gemini 补裁。服务端是否继续生成和实际账单仍待核实。MiMo 软比较显式固定 DeepInfra，禁止供应商回退和 OpenInference；模型 ID、high 推理与裁判评分规则保持不变。

[OpenRouter 路由文档](https://openrouter.ai/docs/guides/routing/provider-selection)说明默认以价格优先负载均衡，固定供应商须显式指定 provider 配置。路由修正通过单独的 transport 记录和每阶段请求指纹保留；不把供应商变化说成经过人类标注校准。

合成路由烟测中，DeepInfra 返回有效判定耗时 18.369 秒、874 输出 token；Fireworks 耗时 11.539 秒、568 输出 token，已观测费用合计 $0.00102092，另列于本轮裁判费用之外。输出长度不同，单案例不足以证明哪家全面更快。烟测使用 180 秒总时限，仅测试接口，不参与分数。早期探测因脚本字段冲突返回 HTTP 404，修正后的收据单独封存；未把 404 当作供应商故障或完成的模型调用。

| 裁判 | 调用数 | 无有效判定 | 耗时缺失 | 已测平均秒 | 已测最长秒 | 最长输出 token |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| ds41 | 85 | 6 | 2 | 252.1 | 3120.4 | 31011 |
| gemini38-fallback | 34 | 0 | 0 | 13.4 | 58.1 | 3890 |
| luna6 | 170 | 0 | 0 | 23.5 | 77.4 | 4161 |
| mimo26 | 85 | 1 | 0 | 58.3 | 260.7 | 10277 |

运行脚本：私有 corpus 中 `scripts/run_local_candidates_20261001.py`、`scripts/local_panel_20261001.py` 与 `scripts/report_local_evaluation_20261001.py`。

模型来源：[Index 9B Q8_0](https://huggingface.co/shoutmon/Index-Translate-9B-Q8_0-GGUF)、[MiMo GGUF](https://huggingface.co/bartowski/MiMo-V2.6-Distill-Qwen-9B-GGUF)。

## 发布前验证与前端维护性

隔离发布快照通过 368 项 Python 测试，覆盖率 90.06%，Ruff lint 和 format 通过。前端 30 项测试、lint 和构建通过。浏览器验证统一目录 23 个模型、默认选择 21 个，清空、仅选两个新模型、刷新保持选择、恢复默认、统一搜索，以及两者的评分版本、量化、Thinking 和成本说明。

App 的 state 从 8 个变为 9 个；effect 保持 2 个。既有加载 effect 读取第三个静态数据源，解析、目录合并和版本下载映射分别保留在 data 模块中，展示组件消费聚合结果。没有新增工作流或 API 状态职责。

`localCatalog.test.ts` 使用实际公开产物，覆盖 23 模型组成、旧行保留、保存选择与新模型加入、版本映射和未计量成本排除。已有 `zhEnCatalog.test.ts` 继续覆盖来源不可变与重复模型不可覆盖。模型选择由现有控制器处理，无新控制器或 hook 需要抽取；全部变更生产组件均低于 500 行。

| 生产文件 | 变更前行数 | 变更后行数 |
| --- | ---: | ---: |
| `web/src/App.tsx` | 169 | 174 |
| `web/src/components/Footer.tsx` | 116 | 117 |
| `web/src/components/HeroSection.tsx` | 85 | 87 |
| `web/src/components/MethodologyView.tsx` | 197 | 204 |
| `web/src/components/ModelDetailPage.tsx` | 87 | 96 |
| `web/src/components/ScoreVersionTag.tsx` | 11 | 12 |
| `web/src/components/ZhEnPreviewLeaderboard.tsx` | 148 | 149 |
| `web/src/data/changelogData.ts` | 112 | 124 |
| `web/src/data/vendorBrands.ts` | 75 | 78 |
| `web/src/data/zhEnCatalog.ts` | 26 | 29 |
| `web/src/data/zhEnPreview.ts` | 159 | 162 |
| `web/src/data/zhEnProfileName.ts` | 30 | 32 |
| `web/src/types/zhEnPreview.ts` | 63 | 63 |
| `web/src/data/zhEnSource.ts` | 0 | 12 |
