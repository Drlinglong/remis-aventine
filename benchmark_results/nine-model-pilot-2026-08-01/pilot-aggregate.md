# remis-nine-model-pilot-2026-08-01

PREVIEW aggregate · `pilot-score-v0.1` · abb729a7322d

| Rank | Recipe | Score | Soft | Hard | W-L-T | Coverage | Time |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | Gemini 3.6 Flash (high) | 84.21 | 73.7% | 100.0% | 23-5-10 | 67.9% | 251.1s |
| 2 | HY3 (high) | 79.71 | 72.5% | 90.5% | 24-6-10 | 71.4% | 2421.6s |
| 3 | DeepSeek V4 Flash (high) | 73.05 | 59.3% | 93.7% | 20-12-11 | 76.8% | 1034.0s |
| 4 | GPT-5.6 Luna (high) | 72.79 | 61.0% | 90.5% | 21-12-8 | 73.2% | 174.3s |
| 5 | Gemini 3.5 Flash Lite (high) | 70.39 | 59.1% | 87.3% | 21-13-10 | 78.6% | 158.5s |
| 6 | Gemma 4 31B (reasoning) | 62.67 | 37.8% | 100.0% | 11-22-12 | 80.4% | 1105.6s |
| 7 | Nemotron 3 Ultra 550B A55B (high) | 59.79 | 33.0% | 100.0% | 12-28-7 | 83.9% | 586.1s |
| 8 | Ling 3.0 Flash (reasoning) | 57.60 | 31.4% | 96.9% | 7-20-8 | 62.5% | 218.1s |
| 9 | MiMo V2.5 (reasoning) | 55.34 | 27.7% | 96.9% | 9-30-8 | 83.9% | 445.5s |

Soft Preference 只计入双顺序一致的盲化裁决；硬门槛直接判定与未决样本不混入语言偏好。
Hard Reliability 使用三轮结果：翻译阶段可恢复的硬校验或结构化失败计 0.67，修复阶段失败计 0。
