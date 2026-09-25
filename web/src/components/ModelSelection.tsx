import { useState } from 'react';
import { useI18n } from '../i18n/I18nProvider';
import { defaultModelIds } from '../data/modelSelection';
import { zhEnProfileName } from '../data/zhEnProfileName';
import type { ZhEnPreviewProfile } from '../types/zhEnPreview';
import { VendorLogo } from './VendorLogo';

export function ModelSelection({ profiles, selected, onChange }: {
  profiles: ZhEnPreviewProfile[]; selected: string[]; onChange: (ids: string[]) => void;
}) {
  const { locale } = useI18n();
  const zh = locale === 'zh-CN';
  const [query, setQuery] = useState('');
  const defaults = new Set(defaultModelIds(profiles));
  const visible = profiles.filter((p) => `${zhEnProfileName(p)} ${p.model_id}`.toLowerCase().includes(query.toLowerCase()));
  return <details className="model-selection">
    <summary>{zh ? `显示 ${selected.length} / ${profiles.length} 个模型` : `${selected.length} of ${profiles.length} models`} <span>＋ / −</span></summary>
    <div className="model-selection-panel">
      <input type="search" aria-label={zh ? '筛选模型' : 'Filter models'} placeholder={zh ? '搜索模型…' : 'Search models…'} value={query} onChange={(e) => setQuery(e.target.value)} />
      <div className="model-selection-actions">
        <button onClick={() => onChange(profiles.map((p) => p.model_id))}>{zh ? '全选' : 'Select all'}</button>
        <button onClick={() => onChange([])}>{zh ? '清空' : 'Clear'}</button>
        <button onClick={() => onChange([...defaults])}>{zh ? '恢复默认' : 'Reset to default'}</button>
      </div>
      <p>{zh ? '默认显示各产品线最新版本；可手动加入历史型号。' : 'Latest version of each product line by default. Add older models to compare.'}</p>
      <div className="model-selection-list">
        {visible.map((p) => <label key={p.model_id}>
          <input type="checkbox" checked={selected.includes(p.model_id)} onChange={(e) => onChange(e.target.checked ? [...selected, p.model_id] : selected.filter((id) => id !== p.model_id))} />
          <VendorLogo signals={[p.model_family, p.model_id]} size={20} fallback={zhEnProfileName(p)} />
          <span className="model-selection-name">{zhEnProfileName(p)}</span>
          {!defaults.has(p.model_id) && <small>{zh ? '上一代' : 'Previous'}</small>}
        </label>)}
        {visible.length === 0 && <p>{zh ? '没有匹配的模型。' : 'No matching models.'}</p>}
      </div>
    </div>
  </details>;
}
