import { useMemo, useState, type CSSProperties } from 'react';
import { getVendorBrand } from '../data/vendorBrands';
import type { ZhEnDirection, ZhEnMeasure, ZhEnPreviewArtifact, ZhEnPreviewProfile } from '../types/zhEnPreview';
import { VendorLogo } from './VendorLogo';

type View = 'overall' | ZhEnDirection;

const VIEW_LABELS: Record<View, string> = {
  overall: 'ZH–EN Core',
  'zh-CN->en': '中文 → English',
  'en->zh-CN': 'English → 中文',
};

const DISPLAY_NAMES: Record<string, string> = {
  'openai/gpt-5.6-sol-pro': 'GPT-5.6 Sol Pro',
  'qwen/qwen3.8-max': 'Qwen 3.8 Max',
  'meituan/longcat-2.0': 'LongCat 2.0',
  'google/gemini-3.7-flash': 'Gemini 3.7 Flash',
  'deepseek/deepseek-v4-pro-0813': 'DeepSeek V4 Pro',
  'moonshotai/kimi-k3': 'Kimi K3',
  'openai/gpt-5.6-terra': 'GPT-5.6 Terra',
  'x-ai/grok-4.6': 'Grok 4.6',
  'tencent/hy3': 'HY3',
  'meta/muse-spark-1.2': 'Muse Spark 1.2',
  'minimax/minimax-m3': 'MiniMax M3',
  'openai/gpt-5.6-luna': 'GPT-5.6 Luna',
  'qwen/qwen3.8-27b': 'Qwen 3.8 27B',
  'deepseek/deepseek-v4-flash-0731': 'DeepSeek V4 Flash',
  'xiaomi/mimo-v2.5': 'MiMo V2.5',
  'upstage/solar-pro4': 'Solar Pro 4',
  'nvidia/nemotron-3.5-lightning': 'Nemotron 3.5 Lightning',
};

function name(profile: ZhEnPreviewProfile): string {
  return DISPLAY_NAMES[profile.model_id] ?? profile.model_id.split('/').pop() ?? profile.model_id;
}

function aggregateMeasure(profile: ZhEnPreviewProfile, kind: 'soft' | 'hard'): ZhEnMeasure {
  const measures = Object.values(profile.directions).map((direction) => direction[kind]);
  const total = measures.reduce((sum, item) => sum + item.total, 0);
  const resolved = measures.reduce((sum, item) => sum + item.resolved, 0);
  const points = measures.reduce((sum, item) => sum + item.points, 0);
  return {
    coverage: total === 0 ? 0 : resolved / total,
    points,
    resolved,
    score: measures.reduce((sum, item) => sum + item.score, 0) / measures.length,
    total,
  };
}

function metric(profile: ZhEnPreviewProfile, view: View) {
  if (view === 'overall') {
    return { score: profile.zh_en_score, soft: aggregateMeasure(profile, 'soft'), hard: aggregateMeasure(profile, 'hard') };
  }
  return profile.directions[view];
}

function percent(value: number): string {
  return `${value.toFixed(1)}%`;
}

export function ZhEnPreviewLeaderboard({ artifact }: { artifact: ZhEnPreviewArtifact }) {
  const [view, setView] = useState<View>('overall');
  const ranked = useMemo(() => [...artifact.profiles].sort((left, right) => metric(right, view).score - metric(left, view).score), [artifact.profiles, view]);
  const resolvedRate = artifact.soft_resolved_count / artifact.soft_case_count;

  return (
    <section className="zh-en-preview" style={{ marginTop: 24, marginBottom: 44 }}>
      <div className="section-title"><span>Live results · ZH–EN Core Preview</span></div>
      <div className="preview-disclosure">
        <div>
          <strong>Two measured directions, not the full 18-direction leaderboard.</strong>
          <p>Scores combine 60% sparse soft preference and 40% hard reliability. Unresolved judgments reduce coverage; they are not counted as failures.</p>
        </div>
        <span className="badge badge-gold">PREVIEW · 2026-08-30</span>
      </div>

      <div className="preview-kpis">
        <div className="v03-panel"><span>Contestants</span><strong>{artifact.contestant_count}</strong></div>
        <div className="v03-panel"><span>Directions completed</span><strong>{artifact.direction_count} / 18</strong></div>
        <div className="v03-panel"><span>Soft cases resolved</span><strong>{artifact.soft_resolved_count} / {artifact.soft_case_count}</strong><small>{(resolvedRate * 100).toFixed(1)}% coverage</small></div>
        <div className="v03-panel"><span>Current leader</span><strong>{name(ranked[0])}</strong><small>{metric(ranked[0], view).score.toFixed(2)}</small></div>
      </div>

      <div className="tab-group preview-tabs">
        {(Object.keys(VIEW_LABELS) as View[]).map((key) => (
          <button key={key} className={`tab-btn ${view === key ? 'active' : ''}`} onClick={() => setView(key)}>
            {VIEW_LABELS[key]}
          </button>
        ))}
      </div>

      <div className="v03-panel preview-table-wrap">
        <table className="preview-table">
          <thead>
            <tr>
              <th>#</th><th>Recipe</th><th>Score</th><th>Soft preference</th><th>Hard reliability</th><th>Coverage</th><th>Observed cost</th><th>Elapsed</th><th>Tokens</th>
            </tr>
          </thead>
          <tbody>
            {ranked.map((profile, index) => {
              const result = metric(profile, view);
              const brand = getVendorBrand(profile.model_family, profile.model_id);
              return (
                <tr key={profile.execution_identity_sha256}>
                  <td className="preview-rank">{index + 1}</td>
                  <td>
                    <div className="preview-model">
                      <VendorLogo signals={[profile.model_family, profile.model_id]} fallback={name(profile)} />
                      <div><strong>{name(profile)}</strong><small>{profile.model_id}</small></div>
                    </div>
                  </td>
                  <td>
                    <div className="preview-score" style={{ '--vendor-color': brand.color } as CSSProperties}>
                      <strong>{result.score.toFixed(2)}</strong><i style={{ width: `${Math.max(2, result.score)}%` }} />
                    </div>
                  </td>
                  <td>{percent(result.soft.score)}</td>
                  <td>{percent(result.hard.score)}</td>
                  <td><span>{result.soft.resolved}/{result.soft.total} soft</span><small>{result.hard.resolved}/{result.hard.total} hard</small></td>
                  <td>{profile.telemetry.cost_rank_eligible && profile.telemetry.cost_usd !== null ? `$${profile.telemetry.cost_usd.toFixed(3)}` : 'Not rankable'}</td>
                  <td>{(profile.telemetry.elapsed_seconds / 60).toFixed(1)} min</td>
                  <td>{profile.telemetry.total_tokens.toLocaleString()}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="preview-footnote">
        <span>Protocol: <code>{artifact.protocol}</code></span>
        <span>Judge cost: ${artifact.judge_cost_usd.toFixed(3)}</span>
        <a href={`${import.meta.env.BASE_URL}data/v03-zh-en-preview.json`} target="_blank" rel="noreferrer">Download sanitized result JSON ↗</a>
      </div>
    </section>
  );
}
