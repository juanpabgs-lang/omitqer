export function ars(n: number | null | undefined, digits = 0): string {
  if (n == null || Number.isNaN(n)) return "—";
  return new Intl.NumberFormat("es-AR", {
    style: "currency",
    currency: "ARS",
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  }).format(n);
}

export function usd(n: number): string {
  return new Intl.NumberFormat("es-AR", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 1,
    minimumFractionDigits: 1,
  }).format(n);
}

export function compact(n: number): string {
  if (Math.abs(n) >= 1e12) return `ARS ${(n / 1e12).toFixed(2)} B`;
  if (Math.abs(n) >= 1e9) return `ARS ${(n / 1e9).toFixed(2)} mil M`;
  if (Math.abs(n) >= 1e6) return `ARS ${(n / 1e6).toFixed(1)} M`;
  return ars(n);
}

export function pct(n: number): string {
  return `${(n * 100).toFixed(1)}%`;
}
