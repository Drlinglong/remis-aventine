import { ArrowDown, ArrowUpRight } from 'lucide-react';
import type { ZhEnPreviewArtifact } from '../types/zhEnPreview';
import { useI18n } from '../i18n/I18nProvider';

interface HeroSectionProps {
  onSelectTab: (tab: string) => void;
  result: ZhEnPreviewArtifact | null;
}

export function HeroSection({ onSelectTab, result }: HeroSectionProps) {
  const { t } = useI18n();
  return (
    <section className="hero-editorial">
      <div className="hero-copy-column">
        <p className="hero-kicker">{t('hero.kicker')}</p>
        <h1 className="display-serif hero-title">
          {t('hero.titleBefore')}<em>{t('hero.titleEm')}</em>{t('hero.period')}
        </h1>
        <p className="hero-vision">
          {t('hero.vision')}
        </p>
        <div className="hero-actions">
          <button className="hero-cta hero-cta-primary" onClick={() => onSelectTab('results')}>
            {t('hero.explore')} <ArrowDown size={16} />
          </button>
          <a className="hero-cta hero-cta-secondary" href={`${import.meta.env.BASE_URL}data/v03-zh-en-results.json`} target="_blank" rel="noreferrer">
            {t('hero.download')} <ArrowUpRight size={16} />
          </a>
        </div>
      </div>

      <aside className="benchmark-card" aria-label={t('benchmark.current')}>
        <div className="benchmark-card-header">
          <span>{t('benchmark.current')}</span>
          <span className="benchmark-status"><i />{t('common.published')}</span>
        </div>
        <div className="benchmark-card-rule" />
        <h2 className="display-serif">{t('benchmark.title')}</h2>
        <p className="benchmark-version">
          {t('benchmark.version')}
        </p>
        <dl className="benchmark-facts">
          <div><dt>{t('benchmark.directions')}</dt><dd>{result ? `${result.direction_count} / 18` : '2 / 18'}</dd></div>
          <div><dt>{t('benchmark.contestants')}</dt><dd>{result?.contestant_count ?? 17}</dd></div>
          <div><dt>{t('benchmark.softCases')}</dt><dd>{result?.soft_case_count ?? 677}</dd></div>
          <div><dt>{t('benchmark.resolved')}</dt><dd>{result?.soft_resolved_count ?? 640}</dd></div>
        </dl>
        <p className="benchmark-judges">
          <span>{t('benchmark.judges')}</span> {t('benchmark.judgeNames')}
        </p>
      </aside>
    </section>
  );
}
