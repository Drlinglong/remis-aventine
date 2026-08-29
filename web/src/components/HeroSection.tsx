import { ArrowDown, ArrowUpRight } from 'lucide-react';
import type { ZhEnPreviewArtifact } from '../types/zhEnPreview';

interface HeroSectionProps {
  onSelectTab: (tab: string) => void;
  result: ZhEnPreviewArtifact | null;
}

export function HeroSection({ onSelectTab, result }: HeroSectionProps) {
  return (
    <section className="hero-editorial">
      <div className="hero-copy-column">
        <p className="hero-kicker">Aventine · AI-native translation benchmark</p>
        <h1 className="display-serif hero-title">
          Toward a world <em>without language barriers</em>.
        </h1>
        <p className="hero-vision">
          Aventine is the AI-native translation leaderboard. We benchmark complete translation recipes — model, prompt, glossary, validation, repair — because knowing how to make AI translate best means measuring the whole system, not just the model.
        </p>
        <div className="hero-actions">
          <button className="hero-cta hero-cta-primary" onClick={() => onSelectTab('results')}>
            Explore the leaderboard <ArrowDown size={16} />
          </button>
          <a className="hero-cta hero-cta-secondary" href={`${import.meta.env.BASE_URL}data/v03-zh-en-results.json`} target="_blank" rel="noreferrer">
            Download the results <ArrowUpRight size={16} />
          </a>
        </div>
      </div>

      <aside className="benchmark-card" aria-label="Current benchmark">
        <div className="benchmark-card-header">
          <span>Current benchmark</span>
          <span className="benchmark-status"><i />Published</span>
        </div>
        <div className="benchmark-card-rule" />
        <h2 className="display-serif">ZH–EN Core Results v0.3</h2>
        <p className="benchmark-version">
          60% soft preference · 40% hard reliability
        </p>
        <dl className="benchmark-facts">
          <div><dt>Directions</dt><dd>{result ? `${result.direction_count} / 18` : '2 / 18'}</dd></div>
          <div><dt>Contestants</dt><dd>{result?.contestant_count ?? 17}</dd></div>
          <div><dt>Soft cases</dt><dd>{result?.soft_case_count ?? 677}</dd></div>
          <div><dt>Resolved</dt><dd>{result?.soft_resolved_count ?? 640}</dd></div>
        </dl>
        <p className="benchmark-judges">
          <span>Judges:</span> Luna + Gemini 3.7 Flash + DeepSeek V4 Flash · family exclusion on
        </p>
      </aside>
    </section>
  );
}
