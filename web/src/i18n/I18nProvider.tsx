/* oxlint-disable react/only-export-components -- the locale registry, pure translator, provider, and hook form one public i18n module. */
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';

export const LOCALES = [
  { code: 'en', label: 'English', shortLabel: 'EN', aliases: ['en'] },
  { code: 'zh-CN', label: '简体中文', shortLabel: '中', aliases: ['zh', 'zh-cn', 'zh-hans', 'zh-hans-cn'] },
] as const;

export type Locale = (typeof LOCALES)[number]['code'];

const en = {
  'nav.overview': 'Overview', 'nav.results': 'ZH–EN Results', 'nav.arena': '9×9 Arena', 'nav.methodology': 'Methodology', 'nav.changelog': 'Changelog', 'nav.language': 'Language',
  'a11y.theme': 'Toggle theme', 'a11y.github': 'GitHub Repository', 'a11y.closeManifest': 'Close recipe manifest',
  'common.published': 'Published', 'common.top9': 'Top 9', 'common.score': 'Score', 'common.minutes': '{value} min', 'common.notMeasured': 'Not measured',
  'hero.kicker': 'Aventine · AI-native translation benchmark', 'hero.titleBefore': 'Toward a world ', 'hero.titleEm': 'without language barriers', 'hero.period': '.',
  'hero.vision': 'Aventine is the AI-native translation leaderboard. We benchmark complete translation recipes — model, prompt, glossary, validation, repair — because knowing how to make AI translate best means measuring the whole system, not just the model.',
  'hero.explore': 'Explore the leaderboard', 'hero.download': 'Download the results',
  'benchmark.current': 'Current benchmark', 'benchmark.title': 'ZH–EN Core Results', 'benchmark.version': '60% soft preference · 40% hard reliability',
  'benchmark.softDefinition': 'Language quality judged by model reviewers: meaning, fluency, terminology, and style.',
  'benchmark.hardDefinition': 'Deterministic checks for format, placeholders, structure, and other non-negotiable requirements.',
  'benchmark.directions': 'Published language pairs', 'benchmark.contestants': 'Models evaluated', 'benchmark.lastUpdated': 'Last updated', 'benchmark.framework': 'Evaluation framework',
  'benchmark.updatedDate': '30 Aug 2026', 'benchmark.scope': 'ZH–EN · Published',
  'benchmark.judges': 'Judges:', 'benchmark.judgeNames': 'Luna + Gemini 3.7 Flash + DeepSeek V4 Flash · family exclusion on',
  'credo.hardTitle': 'Hard validators hold veto', 'credo.hardBody': 'Format, placeholder and structure failures zero out before any language judgment. Soft judges can never override a hard failure.',
  'credo.judgeTitle': 'Position-swapped blind judging', 'credo.judgeBody': 'Every scorable pair is judged A/B and B/A; only double-order-consistent verdicts count. Unresolved lowers coverage, never the score.',
  'credo.evidenceTitle': 'Every number links to artifacts', 'credo.evidenceBody': 'Versioned public aggregates only — score_version, execution identity, coverage and unresolved counts. No hand-maintained numbers.',
  'results.badge': 'PUBLISHED · 2 OF 18 LANGUAGE PAIRS', 'results.title': 'ZH–EN Core Results',
  'results.description': 'Official results for zh-CN→en and en→zh-CN. The other 16 directions are omitted until they have measured results of their own.',
  'results.unavailable': 'ZH–EN results are temporarily unavailable.',
  'arena.badge': 'ROUND-ROBIN TOURNAMENT', 'arena.title': '9×9 Head-to-Head Arena Matrix',
  'arena.description': 'Inspect every pairwise matchup across all 36 candidate pairs. Double-order swap consistency ensures robust, position-unbiased decisions.',
  'analysis.title': 'Published analysis · ZH–EN only',
  'highlight.score': 'ZH–EN Score', 'highlight.scoreSub': 'Published score · Higher is better',
  'highlight.throughput': 'Throughput Speed', 'highlight.throughputSub': 'Observed tokens per second · Higher is better',
  'highlight.cost': 'Observed Recipe Cost', 'highlight.costSub': 'Measured inference cost (USD) · Lower is better',
  'pareto.eyebrow': 'Efficiency frontier', 'pareto.title': 'Quality–efficiency Pareto frontier',
  'pareto.subtitle': 'Higher quality and lower resource use are better. Gold points define the current frontier.',
  'pareto.cost': 'Cost', 'pareto.elapsed': 'Elapsed time', 'pareto.tokens': 'Token load',
  'pareto.costAxis': 'Observed recipe cost (USD)', 'pareto.elapsedAxis': 'Elapsed benchmark time (minutes)', 'pareto.tokensAxis': 'Observed total tokens',
  'pareto.scoreAxis': 'ZH–EN score', 'pareto.log': 'log scale',
  'pareto.inspect': 'Hover over points to inspect metrics, or click to open full recipe details.', 'pareto.current': 'All values are current published measurements.',
  'pareto.open': 'Open recipe manifest.',
  'softhard.title': 'Soft preference vs Hard reliability', 'softhard.subtitle': 'Each point is an evaluated model. Models nearer the upper-right perform well on both language quality and deterministic checks.',
  'softhard.xAxis': 'Hard reliability (%)', 'softhard.yAxis': 'Soft preference (%)',
  'softhard.iso': 'equal final-score lines', 'softhard.isoFormula': 'Final score = 60% soft + 40% hard',
  'softhard.inspect': 'Hover over a point to compare its two score components. Click for full details.',
  'softhard.better': 'Better language quality ↑', 'softhard.reliable': 'More reliable →',
  'manifest.eyebrow': 'Published recipe details', 'manifest.back': 'Back to benchmark', 'manifest.zhEnScore': 'ZH–EN score', 'manifest.observedCost': 'Observed cost',
  'manifest.elapsed': 'Elapsed time', 'manifest.tokens': 'Total tokens', 'manifest.throughput': 'Throughput', 'manifest.soft': 'Soft score', 'manifest.hard': 'Hard score',
  'manifest.verified': 'Provider-verified cost', 'manifest.verifiedCopy': '¥{amount} CNY, converted at {rate} CNY/USD on {date}. Source: provider dashboard.',
  'manifest.repro': 'Reproducibility', 'manifest.protocol': 'Protocol', 'manifest.source': 'Result source', 'manifest.identity': 'Execution identity', 'manifest.directions': 'Directions',
  'manifest.disclosure': 'This is the complete public manifest for the published result. Sealed exam content, prompts, and candidate outputs are intentionally excluded.',
  'leader.title': 'Published results · ZH–EN Core', 'leader.scope': 'Officially published scope: zh-CN→en and en→zh-CN.',
  'leader.policy': 'Scores combine 60% sparse soft preference and 40% hard reliability. Unresolved judgments reduce coverage; they are not counted as failures.',
  'leader.date': 'PUBLISHED · 2026-08-30', 'leader.completed': 'Directions completed', 'leader.resolved': 'Soft cases resolved', 'leader.current': 'Current leader', 'leader.coverage': '{value}% coverage',
  'leader.overall': 'ZH–EN Core', 'leader.zhEn': '中文 → English', 'leader.enZh': 'English → 中文',
  'table.recipe': 'Recipe', 'table.score': 'Score', 'table.soft': 'Soft preference', 'table.hard': 'Hard reliability', 'table.coverage': 'Coverage',
  'table.cost': 'Observed cost', 'table.elapsed': 'Elapsed', 'table.tokens': 'Tokens', 'table.softShort': 'soft', 'table.hardShort': 'hard',
  'table.verified': 'verified', 'table.providerVerified': 'provider verified', 'table.notRankable': 'Not rankable',
  'leader.protocol': 'Protocol:', 'leader.source': 'Source:', 'leader.judgeCost': 'Judge cost:', 'leader.download': 'Download published result JSON ↗',
  'footer.status': 'ZH–EN · PUBLISHED', 'footer.about': 'A reproducible evaluation ground for translation recipes, born from {remis}. Evaluating complete translation pipelines, not isolated model names.',
  'footer.schema': 'JSON Schema Bound', 'footer.principles': 'The 4 Hard Principles',
  'footer.p1': '1. Hard validators have veto power', 'footer.p2': '2. Judge evaluates soft quality', 'footer.p3': '3. Output is structured data', 'footer.p4': '4. External datasets stay external',
  'footer.quick': 'Quick Links', 'footer.overview': '🏆 Overview', 'footer.results': '🌐 ZH–EN Results (2/18)', 'footer.json': '📦 Published result JSON',
  'footer.ecosystem': 'Ecosystem & Code', 'footer.repo': 'GitHub Repository', 'footer.issue': 'Issue #6: 18-Lang Frontier Benchmark', 'footer.contracts': 'JSON Schema Contracts', 'footer.reference': 'Aesthetics Reference: Artificial Analysis',
  'footer.copyright': '© 2026 Aventine Project. Released under AGPL-3.0 License. All evaluation artifacts are cryptographic SHA-256 bound.', 'footer.source': 'Published result source:',
} as const;

type TranslationKey = keyof typeof en;
const zh: Record<TranslationKey, string> = {
  'nav.overview': '概览', 'nav.results': '中英结果', 'nav.arena': '9×9 对战矩阵', 'nav.methodology': '方法论', 'nav.changelog': '更新日志', 'nav.language': '语言',
  'a11y.theme': '切换明暗主题', 'a11y.github': 'GitHub 代码仓库', 'a11y.closeManifest': '关闭翻译配方清单',
  'common.published': '已发布', 'common.top9': '前 9 名', 'common.score': '得分', 'common.minutes': '{value} 分钟', 'common.notMeasured': '未测量',
  'hero.kicker': 'Aventine · AI 原生翻译基准', 'hero.titleBefore': '迈向一个', 'hero.titleEm': '没有语言壁垒的世界', 'hero.period': '。',
  'hero.vision': 'Aventine 是面向 AI 原生翻译的排行榜。我们评测完整的翻译配方——模型、提示词、术语表、校验与修复——因为要知道怎样让 AI 翻译得最好，就必须衡量整个系统，而不只是模型本身。',
  'hero.explore': '查看排行榜', 'hero.download': '下载结果',
  'benchmark.current': '当前基准', 'benchmark.title': '中英核心结果', 'benchmark.version': '60% 软偏好 · 40% 硬可靠性',
  'benchmark.softDefinition': '由评审模型判断译文的含义、流畅度、术语与风格等语言质量。',
  'benchmark.hardDefinition': '通过确定性规则检查格式、占位符、结构以及其他不可妥协的要求。',
  'benchmark.directions': '已发布语言方向', 'benchmark.contestants': '已评测模型', 'benchmark.lastUpdated': '最后更新时间', 'benchmark.framework': '测评框架',
  'benchmark.updatedDate': '2026-08-30', 'benchmark.scope': '中英 · 已发布',
  'benchmark.judges': '评审模型：', 'benchmark.judgeNames': 'Luna + Gemini 3.7 Flash + DeepSeek V4 Flash · 已启用模型家族排除',
  'credo.hardTitle': '硬校验器拥有否决权', 'credo.hardBody': '格式、占位符与结构失败在语言评判之前直接归零。软评审永远无法推翻硬失败。',
  'credo.judgeTitle': '换位盲评', 'credo.judgeBody': '每个可计分对局都以 A/B 与 B/A 双顺序裁决，仅一致性裁决计入；未决只降低覆盖率，不扣分数。',
  'credo.evidenceTitle': '每个数字都可溯源', 'credo.evidenceBody': '网站只消费版本化公开聚合产物——score_version、执行身份哈希、覆盖率与未决计数齐备，没有手工维护的分数。',
  'results.badge': '已发布 · 18 个语言方向中的 2 个', 'results.title': '中英核心结果',
  'results.description': 'zh-CN→en 与 en→zh-CN 的正式结果。其余 16 个方向在产生各自的实测结果前暂不展示。',
  'results.unavailable': '中英结果暂时无法加载。',
  'arena.badge': '循环赛', 'arena.title': '9×9 两两对战矩阵',
  'arena.description': '检查全部 36 个候选配对的每一场对决。双顺序换位裁决保证位置无偏、结果稳健。',
  'analysis.title': '已发布分析 · 仅中英方向',
  'highlight.score': '中英综合得分', 'highlight.scoreSub': '已发布得分 · 越高越好',
  'highlight.throughput': '吞吐速度', 'highlight.throughputSub': '实测每秒 Token 数 · 越高越好',
  'highlight.cost': '翻译配方实测成本', 'highlight.costSub': '推理成本（美元）· 越低越好',
  'pareto.eyebrow': '效率前沿', 'pareto.title': '质量—效率帕累托前沿',
  'pareto.subtitle': '质量越高、资源消耗越低越好；金色点构成当前前沿。',
  'pareto.cost': '成本', 'pareto.elapsed': '耗时', 'pareto.tokens': 'Token 用量',
  'pareto.costAxis': '翻译配方实测成本（美元）', 'pareto.elapsedAxis': '基准测试耗时（分钟）', 'pareto.tokensAxis': '实测 Token 总量',
  'pareto.scoreAxis': '中英得分', 'pareto.log': '对数刻度',
  'pareto.inspect': '悬停在点位上查看指标，或点击打开完整的翻译配方详情。', 'pareto.current': '所有数值均来自当前已发布的实测结果。',
  'pareto.open': '打开翻译配方清单。',
  'softhard.title': '软偏好 × 硬可靠性', 'softhard.subtitle': '每个点代表一个已评测模型。越靠近右上角，说明语言质量和确定性校验表现越均衡。',
  'softhard.xAxis': '硬可靠性（%）', 'softhard.yAxis': '软偏好（%）',
  'softhard.iso': '相同总分线', 'softhard.isoFormula': '总分 = 60% 软偏好 + 40% 硬可靠性',
  'softhard.inspect': '悬停在点位上比较两项得分；点击可查看完整详情。',
  'softhard.better': '语言质量更好 ↑', 'softhard.reliable': '可靠性更高 →',
  'manifest.eyebrow': '已发布翻译配方详情', 'manifest.back': '返回基准结果', 'manifest.zhEnScore': '中英得分', 'manifest.observedCost': '实测成本',
  'manifest.elapsed': '总耗时', 'manifest.tokens': 'Token 总量', 'manifest.throughput': '吞吐速度', 'manifest.soft': '软偏好得分', 'manifest.hard': '硬可靠性得分',
  'manifest.verified': '厂商后台核验成本', 'manifest.verifiedCopy': '¥{amount} CNY，按 {rate} CNY/USD 于 {date} 换算。来源：厂商后台。',
  'manifest.repro': '可复现信息', 'manifest.protocol': '评测协议', 'manifest.source': '结果来源', 'manifest.identity': '执行身份哈希', 'manifest.directions': '翻译方向',
  'manifest.disclosure': '这里展示已发布结果的完整公开清单。密封试题、提示词和候选输出按设计不对外公开。',
  'leader.title': '已发布结果 · 中英核心', 'leader.scope': '正式发布范围：zh-CN→en 与 en→zh-CN。',
  'leader.policy': '总分由 60% 稀疏软偏好和 40% 硬可靠性组成。未决评审会降低覆盖率，但不会被视为失败。',
  'leader.date': '已发布 · 2026-08-30', 'leader.completed': '已完成方向', 'leader.resolved': '已判定软评测', 'leader.current': '当前第一名', 'leader.coverage': '覆盖率 {value}%',
  'leader.overall': '中英综合', 'leader.zhEn': '中文 → English', 'leader.enZh': 'English → 中文',
  'table.recipe': '翻译配方', 'table.score': '得分', 'table.soft': '软偏好', 'table.hard': '硬可靠性', 'table.coverage': '覆盖率',
  'table.cost': '实测成本', 'table.elapsed': '耗时', 'table.tokens': 'Token 数', 'table.softShort': '软评测', 'table.hardShort': '硬评测',
  'table.verified': '已核验', 'table.providerVerified': '厂商已核验', 'table.notRankable': '不参与成本排名',
  'leader.protocol': '评测协议：', 'leader.source': '来源提交：', 'leader.judgeCost': '评审成本：', 'leader.download': '下载已发布结果 JSON ↗',
  'footer.status': '中英 · 已发布', 'footer.about': '源自 {remis}、面向完整翻译配方的可复现评测场。我们评测完整翻译流水线，而不是孤立的模型名称。',
  'footer.schema': 'JSON Schema 约束', 'footer.principles': '四项硬原则',
  'footer.p1': '1. 硬校验器拥有否决权', 'footer.p2': '2. 评审模型只评价软质量', 'footer.p3': '3. 输出必须是结构化数据', 'footer.p4': '4. 外部数据集始终保持外部引用',
  'footer.quick': '快捷入口', 'footer.overview': '🏆 概览', 'footer.results': '🌐 中英结果（2/18）', 'footer.json': '📦 已发布结果 JSON',
  'footer.ecosystem': '生态与代码', 'footer.repo': 'GitHub 代码仓库', 'footer.issue': 'Issue #6：18 语言方向前沿基准', 'footer.contracts': 'JSON Schema 契约', 'footer.reference': '视觉参考：Artificial Analysis',
  'footer.copyright': '© 2026 Aventine Project。基于 AGPL-3.0 许可证发布。所有评测产物均通过 SHA-256 加密哈希绑定。', 'footer.source': '已发布结果来源：',
};

export function normalizeLocale(value: string | null | undefined): Locale | null {
  if (!value) return null;
  const normalized = value.toLowerCase();
  const match = LOCALES.find((locale) => locale.aliases.some((alias) => normalized === alias || normalized.startsWith(`${alias}-`)));
  if (match) return match.code;
  return null;
}

function initialLocale(): Locale {
  if (typeof window === 'undefined') return 'en';
  const fromUrl = normalizeLocale(new URLSearchParams(window.location.search).get('lang'));
  const fromStorage = normalizeLocale(window.localStorage.getItem('aventine-locale'));
  const fromBrowser = navigator.languages.map(normalizeLocale).find(Boolean) ?? normalizeLocale(navigator.language);
  return fromUrl ?? fromStorage ?? fromBrowser ?? 'en';
}

export function translate(locale: Locale, key: TranslationKey, values: Record<string, string | number> = {}): string {
  const dictionaries: Record<Locale, Partial<Record<TranslationKey, string>>> = { en, 'zh-CN': zh };
  const template = dictionaries[locale][key] ?? en[key];
  return Object.entries(values).reduce((result, [name, value]) => result.replaceAll(`{${name}}`, String(value)), template);
}

interface I18nValue { locale: Locale; setLocale: (locale: Locale) => void; t: (key: TranslationKey, values?: Record<string, string | number>) => string; }
const I18nContext = createContext<I18nValue | null>(null);

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocale] = useState<Locale>(initialLocale);
  useEffect(() => {
    document.documentElement.lang = locale;
    window.localStorage.setItem('aventine-locale', locale);
    const url = new URL(window.location.href);
    url.searchParams.set('lang', locale);
    window.history.replaceState({}, '', url);
  }, [locale]);
  const value = useMemo<I18nValue>(() => ({ locale, setLocale, t: (key, values) => translate(locale, key, values) }), [locale]);
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nValue {
  const context = useContext(I18nContext);
  if (!context) throw new Error('useI18n must be used inside I18nProvider');
  return context;
}
