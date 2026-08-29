import type { Locale } from '../i18n/I18nProvider';

export function modelDetailHref(
  modelId: string,
  locale: Locale,
  baseUrl = import.meta.env.BASE_URL,
  currentPath = typeof window === 'undefined' ? '/' : window.location.pathname,
): string {
  const pageUrl = new URL(currentPath, 'https://aventine.local');
  const url = new URL(baseUrl, pageUrl);
  url.searchParams.set('lang', locale);
  url.searchParams.set('model', modelId);
  return `${url.pathname}${url.search}`;
}
