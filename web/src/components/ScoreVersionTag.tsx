import { useI18n } from '../i18n/I18nProvider';
import type { ZhEnPreviewProfile } from '../types/zhEnPreview';

export function ScoreVersionTag({ profile }: { profile: ZhEnPreviewProfile }) {
  const { locale } = useI18n();
  if (!profile.score_version) return null;
  const incremental = profile.score_version === 'v0.3-zh-en-anchors-20260925-v1';
  return <small title={profile.score_version} className={`badge ${incremental ? 'badge-gold' : 'badge-neutral'}`}>
    {locale === 'zh-CN' ? (incremental ? '增量 · 2026-09' : '原评测 · 2026-08') : (incremental ? 'Incremental · Sep 2026' : 'Original · Aug 2026')}
  </small>;
}
