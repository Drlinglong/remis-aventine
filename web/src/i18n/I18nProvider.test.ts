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

  it('describes the published evaluation protocol accurately in both locales', () => {
    expect(translate('en', 'credo.hardTitle')).toBe('Hard reliability is scored separately');
    expect(translate('en', 'credo.judgeTitle')).toBe('Adaptive blind judging');
    expect(translate('en', 'credo.evidenceTitle')).toBe('Results are contract-driven');
    expect(translate('en', 'credo.hardBody')).toContain('avoiding double penalties');
    expect(translate('en', 'credo.judgeBody')).toContain('unresolved cases reduce coverage');
    expect(translate('en', 'credo.evidenceBody')).toContain('Sealed exam content and candidate outputs remain private');
    expect(translate('zh-CN', 'credo.hardTitle')).toBe('硬可靠性独立计分');
    expect(translate('zh-CN', 'credo.judgeTitle')).toBe('自适应盲评');
    expect(translate('zh-CN', 'credo.evidenceTitle')).toBe('结果由公开契约驱动');
    expect(translate('zh-CN', 'credo.hardBody')).toContain('避免重复扣分');
    expect(translate('zh-CN', 'credo.judgeBody')).toContain('未决并降低覆盖率');
    expect(translate('zh-CN', 'credo.evidenceBody')).toContain('密封试题和候选输出按设计不公开');
  });
});
