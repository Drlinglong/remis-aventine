import { ArrowLeft } from 'lucide-react';
import { observedThroughput } from '../data/v03VisualMetrics';
import { zhEnProfileName } from '../data/zhEnProfileName';
import { useI18n } from '../i18n/I18nProvider';
import type { ZhEnMeasure, ZhEnPreviewArtifact, ZhEnPreviewProfile } from '../types/zhEnPreview';
import { VendorLogo } from './VendorLogo';
import { modelDetailHref } from '../data/modelDetailUrl';
import { executionSettings, reasoningLabel } from '../data/executionSettings';

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
  versions = [],
}: {
  artifact: ZhEnPreviewArtifact;
  profile: ZhEnPreviewProfile;
  onBack: () => void;
  versions?: ZhEnPreviewArtifact[];
}) {
  const { t, locale } = useI18n();
  const verified = profile.telemetry.verified_cost;
  const name = zhEnProfileName(profile, locale === 'zh-CN');
  const settings = executionSettings(profile);

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
      {versions.length > 1 && <nav className="tab-group" aria-label={locale === 'zh-CN' ? '该模型的成绩版本' : 'Score versions for this model'}>
        {versions.map((version) => <a className={`tab-btn ${version.score_version === artifact.score_version ? 'active' : ''}`} key={version.score_version} href={modelDetailHref(profile.model_id, locale, undefined, undefined, version.score_version)}>
          {version.anchor_panel ? (locale === 'zh-CN' ? '本轮锚点复核' : 'Anchor recheck') : (locale === 'zh-CN' ? '原始成绩' : 'Original score')}
        </a>)}
      </nav>}
      <dl className="manifest-grid">
        <div><dt>{locale === 'zh-CN' ? '推理设置（请求值）' : 'Reasoning setting (requested)'}</dt><dd>{reasoningLabel(profile, locale === 'zh-CN')}</dd></div>
        <div><dt>{locale === 'zh-CN' ? '输出 token 上限' : 'Output token limit'}</dt><dd>{settings?.max_output_tokens.toLocaleString() ?? (locale === 'zh-CN' ? '未记录' : 'Unrecorded')}</dd></div>
        <div><dt>{locale === 'zh-CN' ? '评分版本' : 'Score version'}</dt><dd>{artifact.score_version}</dd></div>
        <div><dt>ZH→EN</dt><dd>{profile.directions['zh-CN->en'].score.toFixed(2)}</dd></div>
        <div><dt>EN→ZH</dt><dd>{profile.directions['en->zh-CN'].score.toFixed(2)}</dd></div>
        <div><dt>{t(profile.telemetry.generation_cost_upper_bound_usd === undefined ? (profile.telemetry.cost_source ? 'manifest.estimatedCost' : 'manifest.observedCost') : 'table.costUpperBound')}</dt><dd>{profile.telemetry.generation_cost_upper_bound_usd !== undefined ? `≤ $${profile.telemetry.generation_cost_upper_bound_usd.toFixed(4)}` : profile.telemetry.cost_usd === null ? t('common.notMeasured') : `$${profile.telemetry.cost_usd.toFixed(4)}`}</dd></div>
        <div><dt>{t('manifest.elapsed')}</dt><dd>{t('common.minutes', { value: (profile.telemetry.elapsed_seconds / 60).toFixed(1) })}</dd></div>
        <div><dt>{t('manifest.tokens')}</dt><dd>{profile.telemetry.total_tokens.toLocaleString()}</dd></div>
        <div><dt>{t('manifest.throughput')}</dt><dd>{observedThroughput(profile).toFixed(1)} tok/s</dd></div>
        <div><dt>{t('manifest.soft')}</dt><dd>{aggregate(profile, 'soft').score.toFixed(2)}</dd></div>
        <div><dt>{t('manifest.hard')}</dt><dd>{aggregate(profile, 'hard').score.toFixed(2)}</dd></div>
      </dl>
      {settings?.generation && <section className="manifest-note">
        <strong>{locale === 'zh-CN' ? '批量输出可靠性' : 'Batch output reliability'}</strong>
        <p>{locale === 'zh-CN'
          ? `${settings.generation.calls} 次调用 / ${settings.generation.entries} 条译文；原始格式通过 ${settings.generation.raw_contract_pass}/${settings.generation.calls}，现有解析与规范化后通过 ${settings.generation.final_contract_pass}/${settings.generation.calls}，空响应 ${settings.generation.empty_responses}。`
          : `${settings.generation.calls} calls / ${settings.generation.entries} translations; raw contract passed ${settings.generation.raw_contract_pass}/${settings.generation.calls}, after existing parsing and normalization ${settings.generation.final_contract_pass}/${settings.generation.calls}; empty responses ${settings.generation.empty_responses}.`}</p>
      </section>}
      <p className="manifest-disclosure">{locale === 'zh-CN' ? '推理设置来自该次运行身份记录。“默认配置”表示本次请求未显式设置推理参数，不代表关闭推理；供应商默认的具体强度未记录。' : 'Reasoning settings come from this execution identity. “Default” means the request omitted explicit reasoning controls, not that reasoning was disabled; the provider’s default effort was not recorded.'} <a href={`${import.meta.env.BASE_URL}data/v03-execution-settings.json`}>{locale === 'zh-CN' ? '查看参数记录' : 'Execution settings'}</a></p>
      {artifact.score_version === 'v0.3-zh-en-anchors-20261009-v1' && <section className="manifest-note">
        <strong>{locale === 'zh-CN' ? '本轮裁判与路由' : 'Judges and routes for this run'}</strong>
        <p>{profile.model_id.startsWith('anthropic/') ? (locale === 'zh-CN' ? '主审：GPT-6 Luna（high）＋DeepSeek V4.1 Flash（high）；缺失或分歧时由 Gemini 3.8 Flash（medium）补裁。' : 'Primary: GPT-6 Luna (high) + DeepSeek V4.1 Flash (high); Gemini 3.8 Flash (medium) handles missing or disputed votes.') : (locale === 'zh-CN' ? '裁判：DeepSeek V4.1 Flash（high）＋Gemini 3.8 Flash（medium）。Luna 同家族回避；MiMo 无通过速度预检的路由，启用 Gemini。' : 'Judges: DeepSeek V4.1 Flash (high) + Gemini 3.8 Flash (medium). Luna recuses by family; Gemini replaces MiMo because no tested MiMo route qualified.')}</p>
        <p>{locale === 'zh-CN' ? '固定通过 ≥30 output token/s 预检的端点，关闭供应商自动回退。运行中检测到低速或无法计量即隔离后续调用；预检不保证每次请求的速度。' : 'Routes are pinned after ≥30 output token/s preflight, with provider fallback disabled. Slow or unmeasurable live responses quarantine later calls; preflight is not a per-request speed guarantee.'} <a href={`${import.meta.env.BASE_URL}data/v03-judge-routes-20261009.json`}>{locale === 'zh-CN' ? '路由记录' : 'Route record'}</a></p>
        <p>{locale === 'zh-CN' ? 'DeepInfra 运行中出现约 29.4 token/s 后已隔离，未发送的任务改由通过检查的 Fireworks 完成。已完成裁决保留。' : 'DeepInfra was quarantined after a live response at about 29.4 token/s. Unsent work moved to qualified Fireworks; completed votes were retained.'}</p>
        {profile.model_id.startsWith('anthropic/') && <p>{locale === 'zh-CN' ? '切换时有 3 条补裁的结果与费用未能确认；未重复发出这些请求，裁判费用保留为已知下界。' : 'Three fallback calls at the transition have unconfirmed outcomes and fees. They were not reissued; judging cost remains a known lower bound.'}</p>}
      </section>}
      {artifact.score_version === 'v0.3-zh-en-anchors-local-20261001-v1' && (
        <section className="manifest-note">
          <strong>{locale === 'zh-CN' ? '本地评测配方' : 'Local evaluation recipe'}</strong>
          <p>{profile.model_id.startsWith('bilibili/')
            ? (locale === 'zh-CN' ? 'LM Studio · RTX 5090 · Q8_0 · temperature 0 · Thinking 关闭。' : 'LM Studio · RTX 5090 · Q8_0 · temperature 0 · thinking off.')
            : (locale === 'zh-CN' ? 'LM Studio · RTX 5090 · Q4_K_S · temperature 0.3 · Thinking 开启。' : 'LM Studio · RTX 5090 · Q4_K_S · temperature 0.3 · thinking on.')}</p>
          <p>{locale === 'zh-CN' ? '硬件与电费未计量，因此不参与成本排名；分数对应这一量化与推理配方。' : 'Hardware and electricity costs are unmeasured, so this recipe is excluded from cost ranking. Scores describe this quantization and decoding recipe.'}</p>
        </section>
      )}
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
