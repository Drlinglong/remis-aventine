import { useEffect, useState } from 'react';
import { useI18n } from '../i18n/I18nProvider';
import { restoreSelection } from '../data/modelSelection';
import type { ZhEnPreviewArtifact } from '../types/zhEnPreview';
import { ModelSelection } from './ModelSelection';
import { V03Visualizations } from './V03Visualizations';
import { ZhEnPreviewLeaderboard } from './ZhEnPreviewLeaderboard';

export function ResultsExplorer({ artifact }: { artifact: ZhEnPreviewArtifact }) {
  const { locale } = useI18n();
  const zh = locale === 'zh-CN';
  const storageKey = `aventine-model-selection:${artifact.catalog ? 'unified-catalog' : artifact.score_version}`;
  const [selected, setSelected] = useState(() => {
    try { return restoreSelection(localStorage.getItem(storageKey), artifact.profiles); }
    catch { return restoreSelection(null, artifact.profiles); }
  });
  useEffect(() => {
    try { localStorage.setItem(storageKey, JSON.stringify({ selected, known: artifact.profiles.map((p) => p.model_id) })); }
    catch { /* Selection still works when browser storage is unavailable. */ }
  }, [selected, storageKey, artifact.profiles]);
  const shown = { ...artifact, profiles: artifact.profiles.filter((p) => selected.includes(p.model_id)) };
  return <>
    <div className="comparison-controls">
      <div><strong>{artifact.catalog ? (zh ? '中英模型总榜 · 持续增量更新' : 'ZH–EN leaderboard · incremental updates') : artifact.anchor_panel ? (zh ? '固定锚点增量榜' : 'Fixed-anchor placements') : (zh ? '历史榜单' : 'Historical leaderboard')}</strong>
        <p>{artifact.catalog ? (zh ? `原有 ${artifact.catalog.original_count} 个模型 + ${artifact.catalog.added_count} 个新模型，统一选择与展示；历史成绩保留。` : `${artifact.catalog.original_count} original models + ${artifact.catalog.added_count} additions in one selectable view; historical scores retained.`) : artifact.anchor_panel ? (zh ? '固定锚点评测，保留评分与裁判版本。' : 'Fixed-anchor evaluation with score and judge versions retained.') : (zh ? '保留原评分与裁判版本。' : 'Original scores and judge version preserved.')}</p>
        <small>{artifact.catalog ? (zh ? '各行标注评分版本。增量分尚未与旧赛程校准，跨版本排序及前沿用于探索比较。' : 'Each row identifies its score version. Incremental scores are not calibrated to the old schedule; cross-version ordering and frontiers are exploratory.') : artifact.score_version}</small>
      </div>
      <ModelSelection profiles={artifact.profiles} selected={selected} onChange={setSelected} />
    </div>
    {shown.profiles.length ? <>
      <V03Visualizations key={selected.join('|')} artifact={shown} />
      <ZhEnPreviewLeaderboard artifact={shown} />
    </> : <div className="v03-panel empty-model-selection">{zh ? '当前未选择模型。请添加模型或恢复默认。' : 'No models selected. Add a model or reset to defaults.'}</div>}
  </>;
}
