import type { V03LeaderboardArtifact } from '../types/v03';

export function parseV03Leaderboard(value: unknown): V03LeaderboardArtifact {
  if (!value || typeof value !== 'object') {
    throw new Error('v0.3 leaderboard payload must be an object');
  }
  const candidate = value as Partial<V03LeaderboardArtifact>;
  if (
    candidate.protocol !== 'aventine-multilingual-tournament-v0.3' ||
    candidate.score_version !== 'multilingual-pilot-v0.3-60soft-40hard' ||
    candidate.direction_count !== 18 ||
    !Array.isArray(candidate.profiles)
  ) {
    throw new Error('v0.3 leaderboard payload has an incompatible contract');
  }
  return candidate as V03LeaderboardArtifact;
}

export async function loadV03Leaderboard(
  signal?: AbortSignal,
): Promise<V03LeaderboardArtifact | null> {
  const url = `${import.meta.env.BASE_URL}data/v03-leaderboard.json`;
  const response = await fetch(url, { signal });
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`v0.3 leaderboard request failed: ${response.status}`);
  if ((response.headers.get('content-type') || '').includes('text/html')) return null;
  return parseV03Leaderboard(await response.json());
}
