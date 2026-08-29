import { ArrowDown, ArrowUpRight } from 'lucide-react';
import type { V03Judge, V03LeaderboardArtifact } from '../types/v03';
import type { ZhEnPreviewArtifact } from '../types/zhEnPreview';

interface HeroSectionProps {
  onSelectTab: (tab: string) => void;
  artifact: V03LeaderboardArtifact | null;
  preview: ZhEnPreviewArtifact | null;
}

const EXPECTED_BENCHMARK = {
  directions: 18,
  repeats: 2,
  cases: 19,
  occurrences: 598,
  season: '2026-Q3',
};

function judgeLabel(judge: V03Judge): string {
  const model = judge.model_id
    .replace(/^[^/]+\//, '')
    .replace(/:batch$/, '')
    .replace(/-(high|medium|low)$/, '')
    .split('-')
    .map((token) => (/^\d/.test(token) ? token : token.charAt(0).toUpperCase() + token.slice(1)))
    .join(' ');
  return `${model} (${judge.qualification.status})`;
}

export function HeroSection({ onSelectTab, artifact, preview }: HeroSectionProps) {
  const benchmark = {
    directions: preview?.direction_count ?? artifact?.exam.direction_count ?? EXPECTED_BENCHMARK.directions,
    repeats: artifact?.exam.repeat_count ?? EXPECTED_BENCHMARK.repeats,
    cases: artifact?.exam.case_count ?? EXPECTED_BENCHMARK.cases,
    occurrences: artifact?.exam.item_occurrence_count ?? EXPECTED_BENCHMARK.occurrences,
    season: artifact?.publication.season ?? EXPECTED_BENCHMARK.season,
  };
  const status = preview ? 'Preview live' : artifact?.status === 'complete' ? 'Published' : artifact?.status === 'incomplete' ? 'Incomplete' : 'Preparing';
  const judges = artifact?.judge_panel.length
    ? artifact.judge_panel.map(judgeLabel).join(' + ')
    : 'Gemini 3.7 Flash (qualified) + GPT-5.6 Luna (pending)';

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
          <button className="hero-cta hero-cta-primary" onClick={() => onSelectTab('multilingual')}>
            Explore the leaderboard <ArrowDown size={16} />
          </button>
          <button className="hero-cta hero-cta-secondary" onClick={() => onSelectTab('calibration')}>
            Inspect the evidence <ArrowUpRight size={16} />
          </button>
        </div>
      </div>

      <aside className="benchmark-card" aria-label="Current benchmark">
        <div className="benchmark-card-header">
          <span>Current benchmark</span>
          <span className="benchmark-status"><i />{status}</span>
        </div>
        <div className="benchmark-card-rule" />
        <h2 className="display-serif">{preview ? 'ZH–EN Core Preview v0.3' : 'Multilingual Tournament v0.3'}</h2>
        <p className="benchmark-version">
          {preview ? '60% soft preference · 40% hard reliability' : `score_version ${artifact?.score_version ?? 'multilingual-pilot-v0.3-60soft-40hard'} · season ${benchmark.season}`}
        </p>
        <dl className="benchmark-facts">
          <div><dt>Directions</dt><dd>{preview ? `${benchmark.directions} / 18` : benchmark.directions}</dd></div>
          <div><dt>{preview ? 'Contestants' : 'Repeats'}</dt><dd>{preview ? preview.contestant_count : `${benchmark.repeats}×`}</dd></div>
          <div><dt>{preview ? 'Soft cases' : 'Cases'}</dt><dd>{preview?.soft_case_count ?? benchmark.cases ?? '—'}</dd></div>
          <div><dt>{preview ? 'Resolved' : 'Occurrences'}</dt><dd>{preview?.soft_resolved_count ?? benchmark.occurrences ?? '—'}</dd></div>
        </dl>
        <p className="benchmark-judges">
          <span>Judges:</span> {preview ? 'Luna + Gemini 3.7 Flash + DeepSeek V4 Flash' : judges} · family exclusion on
        </p>
      </aside>
    </section>
  );
}
