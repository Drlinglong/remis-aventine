import { useMemo, useState, type CSSProperties } from 'react';
import { getVendorBrand } from '../data/vendorBrands';
import { zhEnProfileName } from '../data/zhEnProfileName';
import type { ZhEnDirection, ZhEnMeasure, ZhEnPreviewArtifact, ZhEnPreviewProfile } from '../types/zhEnPreview';
import { VendorLogo } from './VendorLogo';
import { useI18n } from '../i18n/I18nProvider';

type View = 'overall' | ZhEnDirection;

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
  const { t } = useI18n();
  const [view, setView] = useState<View>('overall');
  const viewLabels: Record<View, string> = { overall: t('leader.overall'), 'zh-CN->en': t('leader.zhEn'), 'en->zh-CN': t('leader.enZh') };
  const ranked = useMemo(() => [...artifact.profiles].sort((left, right) => metric(right, view).score - metric(left, view).score), [artifact.profiles, view]);
  const resolvedRate = artifact.soft_resolved_count / artifact.soft_case_count;

  return (
    <section className="zh-en-preview" style={{ marginTop: 24, marginBottom: 44 }}>
      <div className="section-title"><span>{t('leader.title')}</span></div>
      <div className="preview-disclosure">
        <div>
          <strong>{t('leader.scope')}</strong>
          <p>{t('leader.policy')}</p>
        </div>
        <span className="badge badge-gold">{t('leader.date')}</span>
      </div>

      <div className="preview-kpis">
        <div className="v03-panel"><span>{t('benchmark.contestants')}</span><strong>{artifact.contestant_count}</strong></div>
        <div className="v03-panel"><span>{t('leader.completed')}</span><strong>{artifact.direction_count} / 18</strong></div>
        <div className="v03-panel"><span>{t('leader.resolved')}</span><strong>{artifact.soft_resolved_count} / {artifact.soft_case_count}</strong><small>{t('leader.coverage', { value: (resolvedRate * 100).toFixed(1) })}</small></div>
        <div className="v03-panel"><span>{t('leader.current')}</span><strong>{zhEnProfileName(ranked[0])}</strong><small>{metric(ranked[0], view).score.toFixed(2)}</small></div>
      </div>

      <div className="tab-group preview-tabs">
        {(Object.keys(viewLabels) as View[]).map((key) => (
          <button key={key} className={`tab-btn ${view === key ? 'active' : ''}`} onClick={() => setView(key)}>
            {viewLabels[key]}
          </button>
        ))}
      </div>

      <div className="v03-panel preview-table-wrap">
        <table className="preview-table">
          <thead>
            <tr>
              <th>#</th><th>{t('table.recipe')}</th><th>{t('table.score')}</th><th>{t('table.soft')}</th><th>{t('table.hard')}</th><th>{t('table.coverage')}</th><th>{t('table.cost')}</th><th>{t('table.elapsed')}</th><th>{t('table.tokens')}</th>
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
                      <VendorLogo signals={[profile.model_family, profile.model_id]} fallback={zhEnProfileName(profile)} />
                      <div><strong>{zhEnProfileName(profile)}</strong><small>{profile.model_id}</small></div>
                    </div>
                  </td>
                  <td>
                    <div className="preview-score" style={{ '--vendor-color': brand.color } as CSSProperties}>
                      <strong>{result.score.toFixed(2)}</strong><i style={{ width: `${Math.max(2, result.score)}%` }} />
                    </div>
                  </td>
                  <td>{percent(result.soft.score)}</td>
                  <td>{percent(result.hard.score)}</td>
                  <td><span>{result.soft.resolved}/{result.soft.total} {t('table.softShort')}</span><small>{result.hard.resolved}/{result.hard.total} {t('table.hardShort')}</small></td>
                  <td>
                    {profile.telemetry.cost_rank_eligible && profile.telemetry.cost_usd !== null
                      ? profile.telemetry.verified_cost
                        ? <><span>${profile.telemetry.cost_usd.toFixed(3)}</span><small style={{ display: 'block' }}>¥{profile.telemetry.verified_cost.amount.toFixed(2)} {t('table.verified')}</small></>
                        : `$${profile.telemetry.cost_usd.toFixed(3)}`
                      : profile.telemetry.verified_cost
                        ? <><span>¥{profile.telemetry.verified_cost.amount.toFixed(2)} CNY</span><small>{t('table.providerVerified')}</small></>
                        : t('table.notRankable')}
                  </td>
                  <td>{t('common.minutes', { value: (profile.telemetry.elapsed_seconds / 60).toFixed(1) })}</td>
                  <td>{profile.telemetry.total_tokens.toLocaleString()}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="preview-footnote">
        <span>{t('leader.source')} <code>{artifact.source_commit}</code></span>
        <span>{t('leader.judgeCost')} ${artifact.judge_cost_usd.toFixed(3)}</span>
        <a href={`${import.meta.env.BASE_URL}data/v03-zh-en-results.json`} target="_blank" rel="noreferrer">{t('leader.download')}</a>
      </div>
    </section>
  );
}
