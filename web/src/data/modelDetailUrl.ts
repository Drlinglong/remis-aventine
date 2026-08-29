import type { Locale } from '../i18n/I18nProvider';

export function modelDetailHref(modelId: string, locale: Locale, baseUrl = import.meta.env.BASE_URL): string {
  const url = new URL(baseUrl, 'https://aventine.local');
  url.searchParams.set('lang', locale);
  url.searchParams.set('model', modelId);
  return `${url.pathname}${url.search}`;
}
