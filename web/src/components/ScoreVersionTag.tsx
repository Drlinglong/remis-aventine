import { useI18n } from '../i18n/I18nProvider';
import type { ZhEnPreviewProfile } from '../types/zhEnPreview';

export function ScoreVersionTag({ profile }: { profile: ZhEnPreviewProfile }) {
  const { locale } = useI18n();
  if (!profile.score_version) return null;
  const incremental = profile.score_version !== 'v0.3-zh-en-60soft-40hard';
  const november = profile.score_version === 'v0.3-zh-en-anchors-20261125-v1';
  const october = profile.score_version === 'v0.3-zh-en-anchors-20261009-v1';
  const local = profile.score_version === 'v0.3-zh-en-anchors-local-20261001-v1';
  return <small title={profile.score_version} className={`badge ${incremental ? 'badge-gold' : 'badge-neutral'}`}>
    {locale === 'zh-CN' ? (november ? '增量 · 2026-11-25' : local ? '本地增量 · 2026-10' : october ? '增量 · 2026-10-09' : incremental ? '增量 · 2026-09' : '原评测 · 2026-08') : (november ? 'Incremental · Nov 25, 2026' : local ? 'Local · Oct 2026' : october ? 'Incremental · Oct 9, 2026' : incremental ? 'Incremental · Sep 2026' : 'Original · Aug 2026')}
  </small>;
}
