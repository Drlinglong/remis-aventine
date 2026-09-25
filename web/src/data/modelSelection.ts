import type { ZhEnPreviewProfile } from '../types/zhEnPreview';

// Only known product naming schemes group generations. Unknown names coexist.
// Keep tiers distinct: a vendor's Pro, Flash and small models are not substitutes.
function generation(modelId: string): [string, number[]] {
  for (const pattern of [
    /^(openai\/gpt)-(\d+(?:\.\d+)*)-(luna|terra|sol|sol-pro|astra)(?:-\d{8})?$/,
    /^(deepseek\/deepseek)-v(\d+(?:\.\d+)*)-(flash|pro)(?:-\d{4,8})?$/,
    /^(xiaomi\/mimo)-v(\d+(?:\.\d+)*)(-pro)?$/,
  ]) {
    const match = modelId.match(pattern);
    if (match) return [`${match[1]}:${match[3] ?? 'base'}`, match[2].split('.').map(Number)];
  }
  return [modelId, [0]];
}

function newer(left: number[], right: number[]): boolean {
  for (let i = 0; i < Math.max(left.length, right.length); i++) {
    if ((left[i] ?? 0) !== (right[i] ?? 0)) return (left[i] ?? 0) > (right[i] ?? 0);
  }
  return false;
}

export function defaultModelIds(profiles: ZhEnPreviewProfile[]): string[] {
  const latest = new Map<string, { id: string; generation: number[] }>();
  for (const p of profiles) {
    const [series, version] = generation(p.model_id);
    const previous = latest.get(series);
    if (!previous || newer(version, previous.generation)) latest.set(series, { id: p.model_id, generation: version });
  }
  return [...latest.values()].map((entry) => entry.id);
}

export function restoreSelection(raw: string | null, profiles: ZhEnPreviewProfile[]): string[] {
  const defaults = defaultModelIds(profiles);
  if (!raw) return defaults;
  try {
    const stored = JSON.parse(raw);
    if (!Array.isArray(stored.selected) || !Array.isArray(stored.known)) return defaults;
    const previousDefaults = defaultModelIds(profiles.filter((p) => stored.known.includes(p.model_id)));
    if (stored.selected.length === previousDefaults.length && previousDefaults.every((id) => stored.selected.includes(id))) return defaults;
    const available = new Set(profiles.map((p) => p.model_id));
    return [...new Set<string>([
      ...stored.selected.filter((id: unknown) => typeof id === 'string' && available.has(id)),
      ...defaults.filter((id) => !stored.known.includes(id)),
    ])];
  } catch { return defaults; }
}
