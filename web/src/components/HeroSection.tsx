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
        {/* Seal watermark — sits behind text, never behind the benchmark card */}
        <svg className="hero-seal-bg" viewBox="0 0 1024 1024" aria-hidden="true">
          <circle cx="512" cy="512" r="455" fill="none" stroke="currentColor" strokeWidth="24" />
          <g fill="currentColor">
            <path d="M486 238 512 212 538 238 512 264Z" />
            <path d="M502 258H522V374H502Z" />
            <path d="M214 742 482 402Q512 364 542 402L810 742 764 779 512 461 260 779Z" />
          </g>
        </svg>
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

export function CredibilityStrip() {
  const { t } = useI18n();
  return (
    <section className="credo-strip">
      <div className="credo-item">
        <h3>{t('credo.hardTitle')}</h3>
        <p>{t('credo.hardBody')}</p>
      </div>
      <div className="credo-item">
        <h3>{t('credo.judgeTitle')}</h3>
        <p>{t('credo.judgeBody')}</p>
      </div>
      <div className="credo-item">
        <h3>{t('credo.evidenceTitle')}</h3>
        <p>{t('credo.evidenceBody')}</p>
      </div>
    </section>
  );
}