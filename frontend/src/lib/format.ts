export function inr(value: number | string | null | undefined): string {
  const n = Number(value || 0);
  const abs = Math.abs(n);
  const formatted = abs.toLocaleString('en-IN', { maximumFractionDigits: 0 });
  return n < 0 ? `-₹${formatted}` : `₹${formatted}`;
}

export function inrCompact(value: number | string | null | undefined): string {
  const n = Number(value || 0);
  const abs = Math.abs(n);
  let s = '';
  if (abs >= 1e7) s = `₹${(abs / 1e7).toFixed(2)} Cr`;
  else if (abs >= 1e5) s = `₹${(abs / 1e5).toFixed(2)} L`;
  else s = `₹${abs.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
  return n < 0 ? `-${s}` : s;
}

export function pct(value: number | string | null | undefined): string {
  return `${Number(value || 0).toFixed(2)}%`;
}
