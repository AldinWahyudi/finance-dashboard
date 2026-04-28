export function fmtRp(n: number): string {
  const sign = n < 0 ? "-" : "";
  return `${sign}Rp ${Math.abs(Math.round(n)).toLocaleString("id-ID")}`;
}

export function fmtRpShort(n: number): string {
  const abs = Math.abs(n);
  const sign = n < 0 ? "-" : "";
  if (abs >= 1_000_000_000) return `${sign}Rp ${(abs / 1_000_000_000).toFixed(1)}B`;
  if (abs >= 1_000_000) return `${sign}Rp ${(abs / 1_000_000).toFixed(1)}M`;
  if (abs >= 1_000) return `${sign}Rp ${(abs / 1_000).toFixed(0)}K`;
  return `${sign}Rp ${abs}`;
}
