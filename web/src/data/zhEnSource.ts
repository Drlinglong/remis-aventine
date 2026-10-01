import type { ZhEnPreviewArtifact } from '../types/zhEnPreview';

export function zhEnSource(artifact?: ZhEnPreviewArtifact | null) {
  switch (artifact?.score_version) {
    case 'v0.3-zh-en-anchors-local-20261001-v1':
      return { filename: 'v03-zh-en-anchors-local-20261001.json', date: '2026-10-01' };
    case 'v0.3-zh-en-anchors-20260925-v1':
      return { filename: 'v03-zh-en-anchors-20260925.json', date: '2026-09-25' };
    default:
      return { filename: 'v03-zh-en-results.json', date: '2026-08-30' };
  }
}
