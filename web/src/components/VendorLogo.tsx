import type { CSSProperties } from 'react';
import { getVendorBrand } from '../data/vendorBrands';

export function VendorLogo({
  signals,
  size = 20,
  fallback,
}: {
  signals: Array<string | null | undefined>;
  size?: number;
  fallback?: string;
}) {
  const brand = getVendorBrand(...signals);

  return (
    <span
      className="vendor-logo"
      aria-label={brand.label}
      title={brand.label}
      style={{ '--vendor-color': brand.color, width: size, height: size } as CSSProperties}
    >
      {brand.logo ? <img src={brand.logo} alt="" aria-hidden="true" /> : <span className="vendor-logo-fallback" aria-hidden="true">{fallback?.charAt(0).toUpperCase() ?? '·'}</span>}
    </span>
  );
}
