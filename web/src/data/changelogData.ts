import type { ChangelogItem } from '../types/benchmark';

export const CHANGELOG_DATA: ChangelogItem[] = [
  {
    id: 'ch-2026-08-02-anchored',
    date: '02 Aug 2026',
    title: 'Anchored Panel Benchmark v0.2: Qwen 3.7 Plus & TranslateGemma Placement',
    category: 'Tournaments',
    summary: 'Evaluated Qwen 3.7 Plus (high reasoning) and TranslateGemma 27B IT (local Q6_K) against the 3-model anchor panel under pilot-score-v0.2-anchored policy.',
    model_tag: 'Qwen 3.7 Plus',
    provider: 'OpenRouter',
    pilot_score: 71.12,
    highlights: [
      'Qwen 3.7 Plus achieved 71.12 score with 57.1% soft preference and 92.1% hard reliability.',
      'TranslateGemma 27B IT achieved 39.29 score running on local consumer hardware (<24GB VRAM).',
      'Anchor panel consists of Gemini 3.6 Flash, Gemini 3.5 Flash Lite, and MiMo V2.5.',
    ],
  },
  {
    id: 'ch-2026-08-01-nine-pilot',
    date: '01 Aug 2026',
    title: 'Nine-Model Frontier Pilot: Gemini 3.6 Flash Wins Tournament',
    category: 'Tournaments',
    summary: 'Published the first comprehensive 9-model automated round-robin tournament (36 pairs, 21 cases each, 3 repeats) with complete token telemetry and cost accounting.',
    model_tag: 'Gemini 3.6 Flash',
    provider: 'Google AI Studio',
    pilot_score: 84.21,
    highlights: [
      'Gemini 3.6 Flash (high) takes #1 with 84.21 Pilot Score (73.7% soft win rate, 100% hard pass).',
      'HY3 ranks #2 with 79.71 score and 72.5% soft win rate, but requires 9.6x higher latency and 98.9k reasoning tokens.',
      'GPT-5.6 Luna demonstrates highest reasoning token efficiency (174.3s total time, 10.9k reasoning tokens) tied with DeepSeek V4 Flash at 72.8 points.',
      'Total participant inference cost across 6 paid models: $0.65199.',
    ],
  },
  {
    id: 'ch-2026-07-16-first-tournament',
    date: '16 Jul 2026',
    title: 'First Remis Four-Recipe Tournament',
    category: 'Tournaments',
    summary: 'Completed first 4-recipe round-robin pilot using frozen 7-case fixtures with DeepSeek V4 Pro judge.',
    model_tag: 'Qwen 3.6 27B',
    provider: 'Local / Remis',
    pilot_score: 81.5,
    highlights: [
      'Qwen 3.6 27B Q4_K_M finished 1st (15-1-2 record, 7/7 hard pass).',
      'Gemma 4 31B finished 2nd (11-4-2 record, 7/7 hard pass).',
      'Validated hard validator veto power against soft preference.',
    ],
  },
  {
    id: 'ch-2026-07-15-evidence-alignment',
    date: '15 Jul 2026',
    title: 'Judge Calibration & Baseline Evidence Alignment',
    category: 'Calibration',
    summary: 'Aligned DeepSeek V4 judge against WMT23 MQM human gold annotations and ACES contrastive challenge sets.',
    highlights: [
      'Achieved 94.4% severe error recall and 5.6% false-good rate on WMT MQM EN->DE.',
      'Calibrated against ACES phenomena: negation, numerical, entity substitution, and omission.',
      'Integrated isolated MetricX-24 and xCOMET external evaluation baselines.',
    ],
  },
  {
    id: 'ch-2026-07-14-schema-contracts',
    date: '14 Jul 2026',
    title: 'Versioned JSON Schema Contracts & Multi-Provider Judge Adapters',
    category: 'Infrastructure',
    summary: 'Released formal schemas for recipe manifests, run results, judge verdicts, metric packs, and tournament aggregates.',
    highlights: [
      'Schema validation via jsonschema with strict trust boundaries.',
      'Added multi-provider judge runners supporting DeepSeek, xAI Grok, Gemini, and OpenRouter.',
      'Enforced hard validator veto precedence over judge outputs.',
    ],
  },
];
