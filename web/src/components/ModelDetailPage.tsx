import { ArrowLeft } from 'lucide-react';
import { observedThroughput } from '../data/v03VisualMetrics';
import { zhEnProfileName } from '../data/zhEnProfileName';
import { useI18n } from '../i18n/I18nProvider';
import type { ZhEnMeasure, ZhEnPreviewArtifact, ZhEnPreviewProfile } from '../types/zhEnPreview';
import { VendorLogo } from './VendorLogo';

function aggregate(profile: ZhEnPreviewProfile, kind: 'soft' | 'hard'): ZhEnMeasure {
  const values = Object.values(profile.directions).map((direction) => direction[kind]);
  const total = values.reduce((sum, value) => sum + value.total, 0);
  const resolved = values.reduce((sum, value) => sum + value.resolved, 0);
  return {
    coverage: resolved / total,
    points: values.reduce((sum, value) => sum + value.points, 0),
    resolved,
    score: values.reduce((sum, value) => sum + value.score, 0) / values.length,
    total,
  };
}

export function ModelDetailPage({
  artifact,
  profile,
  onBack,
}: {
  artifact: ZhEnPreviewArtifact;
  profile: ZhEnPreviewProfile;
  onBack: () => void;
}) {
  const { t } = useI18n();
  const verified = profile.telemetry.verified_cost;
  const name = zhEnProfileName(profile);

  return (
    <article className="model-detail-page animate-fade-in">
      <button className="model-detail-back" onClick={onBack}>
        <ArrowLeft size={15} /> {t('manifest.back')}
      </button>
      <header className="model-detail-header">
        <VendorLogo signals={[profile.model_family, profile.model_id]} size={48} fallback={name} />
        <div>
          <span className="eyebrow">{t('manifest.eyebrow')}</span>
          <h1>{name}</h1>
          <code>{profile.model_id}</code>
        </div>
      </header>
      <div className="manifest-score">
        <span>{t('manifest.zhEnScore')}</span>
        <strong>{profile.zh_en_score.toFixed(2)}</strong>
      </div>
      <dl className="manifest-grid">
        <div><dt>ZH→EN</dt><dd>{profile.directions['zh-CN->en'].score.toFixed(2)}</dd></div>
        <div><dt>EN→ZH</dt><dd>{profile.directions['en->zh-CN'].score.toFixed(2)}</dd></div>
        <div><dt>{t('manifest.observedCost')}</dt><dd>{profile.telemetry.cost_usd === null ? t('common.notMeasured') : `$${profile.telemetry.cost_usd.toFixed(4)}`}</dd></div>
        <div><dt>{t('manifest.elapsed')}</dt><dd>{t('common.minutes', { value: (profile.telemetry.elapsed_seconds / 60).toFixed(1) })}</dd></div>
        <div><dt>{t('manifest.tokens')}</dt><dd>{profile.telemetry.total_tokens.toLocaleString()}</dd></div>
        <div><dt>{t('manifest.throughput')}</dt><dd>{observedThroughput(profile).toFixed(1)} tok/s</dd></div>
        <div><dt>{t('manifest.soft')}</dt><dd>{aggregate(profile, 'soft').score.toFixed(2)}</dd></div>
        <div><dt>{t('manifest.hard')}</dt><dd>{aggregate(profile, 'hard').score.toFixed(2)}</dd></div>
      </dl>
      {verified && (
        <section className="manifest-note">
          <strong>{t('manifest.verified')}</strong>
          <p>{t('manifest.verifiedCopy', { amount: verified.amount.toFixed(2), rate: verified.cny_per_usd, date: verified.converted_on })}</p>
        </section>
      )}
      <section className="manifest-identity">
        <h2>{t('manifest.repro')}</h2>
        <dl>
          <div><dt>{t('manifest.source')}</dt><dd><code>{artifact.source_commit}</code></dd></div>
          <div><dt>{t('manifest.identity')}</dt><dd><code>{profile.execution_identity_sha256}</code></dd></div>
          <div><dt>{t('manifest.directions')}</dt><dd>zh-CN→en · en→zh-CN</dd></div>
        </dl>
      </section>
      <p className="manifest-disclosure">{t('manifest.disclosure')}</p>
    </article>
  );
}
