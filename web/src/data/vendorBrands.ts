export type VendorBrandId =
  | 'google'
  | 'openai'
  | 'deepseek'
  | 'moonshot'
  | 'tencent'
  | 'longcat'
  | 'upstage'
  | 'nvidia'
  | 'alibaba'
  | 'inclusionai'
  | 'xiaomi'
  | 'anthropic'
  | 'meta'
  | 'minimax'
  | 'xai'
  | 'neutral';

export interface VendorBrand {
  id: VendorBrandId;
  label: string;
  logo: string | null;
  color: string;
}

const BRAND_DEFINITIONS: Record<VendorBrandId, Omit<VendorBrand, 'id'>> = {
  google: { label: 'Google', logo: 'google.png', color: 'var(--vendor-google)' },
  openai: { label: 'OpenAI', logo: 'openai.png', color: 'var(--vendor-openai)' },
  deepseek: { label: 'DeepSeek', logo: 'deepseek.png', color: 'var(--vendor-deepseek)' },
  moonshot: { label: 'Moonshot AI', logo: 'moonshot-ai.png', color: 'var(--vendor-moonshot)' },
  tencent: { label: 'Tencent', logo: 'tencent.png', color: 'var(--vendor-tencent)' },
  longcat: { label: 'LongCat / Meituan', logo: 'longcat.svg', color: 'var(--vendor-longcat)' },
  upstage: { label: 'Upstage', logo: 'upstage.png', color: 'var(--vendor-upstage)' },
  nvidia: { label: 'NVIDIA', logo: 'nvidia.png', color: 'var(--vendor-nvidia)' },
  alibaba: { label: 'Alibaba / Qwen', logo: 'alibaba.png', color: 'var(--vendor-alibaba)' },
  inclusionai: { label: 'InclusionAI / Ling', logo: 'inclusionai.png', color: 'var(--vendor-alibaba)' },
  xiaomi: { label: 'Xiaomi / MiMo', logo: 'xiaomi.png', color: 'var(--vendor-xiaomi)' },
  anthropic: { label: 'Anthropic / Claude', logo: 'anthropic.svg', color: 'var(--vendor-anthropic)' },
  meta: { label: 'Meta', logo: 'meta.png', color: 'var(--vendor-meta)' },
  minimax: { label: 'MiniMax', logo: 'minimax.png', color: 'var(--vendor-minimax)' },
  xai: { label: 'xAI', logo: 'xai.svg', color: 'var(--vendor-xai)' },
  neutral: { label: 'Other', logo: null, color: 'var(--vendor-neutral)' },
};

export function vendorAsset(file: string): string {
  return `${import.meta.env.BASE_URL}vendors/${file}`;
}

export function getVendorBrand(...signals: Array<string | null | undefined>): VendorBrand {
  const value = signals.filter(Boolean).join(' ').toLowerCase();
  let id: VendorBrandId = 'neutral';

  if (value.includes('gemini') || value.includes('gemma') || value.includes('google')) id = 'google';
  else if (value.includes('openai') || value.includes('gpt-')) id = 'openai';
  else if (value.includes('deepseek')) id = 'deepseek';
  else if (value.includes('tencent') || value.includes('hy3')) id = 'tencent';
  else if (value.includes('moonshot') || value.includes('kimi')) id = 'moonshot';
  else if (value.includes('longcat') || value.includes('meituan')) id = 'longcat';
  else if (value.includes('upstage') || value.includes('solar')) id = 'upstage';
  else if (value.includes('nvidia') || value.includes('nemotron')) id = 'nvidia';
  else if (value.includes('qwen') || value.includes('alibaba')) id = 'alibaba';
  else if (value.includes('ling') || value.includes('inclusionai')) id = 'inclusionai';
  else if (value.includes('xiaomi') || value.includes('mimo')) id = 'xiaomi';
  else if (value.includes('anthropic') || value.includes('claude')) id = 'anthropic';
  else if (value.includes('meta') || value.includes('muse-spark')) id = 'meta';
  else if (value.includes('minimax')) id = 'minimax';
  else if (value.includes('x-ai') || value.includes('xai') || value.includes('grok')) id = 'xai';

  const definition = BRAND_DEFINITIONS[id];
  return {
    id,
    ...definition,
    logo: definition.logo ? vendorAsset(definition.logo) : null,
  };
}
