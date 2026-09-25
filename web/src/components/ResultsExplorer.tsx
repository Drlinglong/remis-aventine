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
  const storageKey = `aventine-model-selection:${artifact.score_version}`;
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
      <div><strong>{artifact.anchor_panel ? (zh ? '固定锚点增量榜' : 'Fixed-anchor placements') : (zh ? '历史榜单' : 'Historical leaderboard')}</strong>
        <p>{artifact.anchor_panel ? (zh ? '同一锚点面板内比较；历史面板成绩另存，不混排。' : 'Compare within this frozen panel. Historical panel scores remain separate.') : (zh ? '保留原评分与裁判版本。' : 'Original scores and judge version preserved.')}</p>
        <small>{artifact.score_version}</small>
      </div>
      <ModelSelection profiles={artifact.profiles} selected={selected} onChange={setSelected} />
    </div>
    {shown.profiles.length ? <>
      <V03Visualizations key={selected.join('|')} artifact={shown} />
      <ZhEnPreviewLeaderboard artifact={shown} />
    </> : <div className="v03-panel empty-model-selection">{zh ? '当前未选择模型。请添加模型或恢复默认。' : 'No models selected. Add a model or reset to defaults.'}</div>}
  </>;
}
