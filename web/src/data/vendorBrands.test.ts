import { describe, expect, it } from 'vitest';
import { getVendorBrand } from './vendorBrands';

describe('vendor brand recognition', () => {
  it('keeps Tencent HY3 separate from Moonshot Kimi', () => {
    expect(getVendorBrand('tencent-hy3', 'tencent/hy3').id).toBe('tencent');
    expect(getVendorBrand('moonshot-kimi', 'moonshotai/kimi-k3').id).toBe('moonshot');
  });

  it('recognizes official LongCat and Upstage families', () => {
    expect(getVendorBrand('meituan-longcat', 'meituan/longcat-2.0').id).toBe('longcat');
    expect(getVendorBrand('upstage-solar', 'upstage/solar-pro4').id).toBe('upstage');
  });
});
