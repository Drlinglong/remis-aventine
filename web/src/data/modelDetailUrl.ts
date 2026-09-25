import type { Locale } from '../i18n/I18nProvider';

export function modelDetailHref(
  modelId: string,
  locale: Locale,
  baseUrl = import.meta.env.BASE_URL,
  currentPath = typeof window === 'undefined' ? '/' : window.location.pathname,
  scoreVersion = typeof window === 'undefined' ? null : new URLSearchParams(window.location.search).get('score_version'),
): string {
  const pageUrl = new URL(currentPath, 'https://aventine.local');
  const url = new URL(baseUrl, pageUrl);
  url.searchParams.set('lang', locale);
  url.searchParams.set('model', modelId);
  if (scoreVersion) url.searchParams.set('score_version', scoreVersion);
  return `${url.pathname}${url.search}`;
}
