import { describe, expect, it } from 'vitest';
import { normalizeLocale, translate } from './I18nProvider';

describe('Aventine i18n', () => {
  it('normalizes supported browser locales', () => {
    expect(normalizeLocale('zh-Hans-CN')).toBe('zh-CN');
    expect(normalizeLocale('en-AU')).toBe('en');
    expect(normalizeLocale('ja-JP')).toBeNull();
  });

  it('translates and interpolates interface copy', () => {
    expect(translate('zh-CN', 'leader.coverage', { value: '94.5' })).toBe('覆盖率 94.5%');
    expect(translate('en', 'leader.coverage', { value: '94.5' })).toBe('94.5% coverage');
  });
});
