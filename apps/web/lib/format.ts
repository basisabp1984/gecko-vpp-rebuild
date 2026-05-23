/**
 * Ukrainian-locale formatters for the UI.
 * All money in грн (UAH), all energy in МВт·год.
 */

const UA = "uk-UA";

export function formatUAH(value: number | string | null | undefined): string {
  if (value === null || value === undefined) return "—";
  const n = typeof value === "string" ? parseFloat(value) : value;
  if (!Number.isFinite(n)) return "—";
  if (Math.abs(n) >= 1_000_000) {
    return new Intl.NumberFormat(UA, {
      style: "currency",
      currency: "UAH",
      maximumFractionDigits: 1,
      notation: "compact",
    }).format(n);
  }
  return new Intl.NumberFormat(UA, {
    style: "currency",
    currency: "UAH",
    maximumFractionDigits: 0,
  }).format(n);
}

export function formatNumber(
  value: number | string | null | undefined,
  digits = 1,
): string {
  if (value === null || value === undefined) return "—";
  const n = typeof value === "string" ? parseFloat(value) : value;
  if (!Number.isFinite(n)) return "—";
  return new Intl.NumberFormat(UA, {
    maximumFractionDigits: digits,
    minimumFractionDigits: 0,
  }).format(n);
}

export function formatPercent(
  value: number | string | null | undefined,
  digits = 1,
): string {
  if (value === null || value === undefined) return "—";
  const n = typeof value === "string" ? parseFloat(value) : value;
  if (!Number.isFinite(n)) return "—";
  return `${new Intl.NumberFormat(UA, { maximumFractionDigits: digits }).format(n)} %`;
}

export function formatMWh(
  value: number | string | null | undefined,
  digits = 1,
): string {
  if (value === null || value === undefined) return "—";
  const n = typeof value === "string" ? parseFloat(value) : value;
  if (!Number.isFinite(n)) return "—";
  return `${formatNumber(n, digits)} МВт·год`;
}

export function formatTonnes(
  value: number | string | null | undefined,
  digits = 0,
): string {
  if (value === null || value === undefined) return "—";
  const n = typeof value === "string" ? parseFloat(value) : value;
  if (!Number.isFinite(n)) return "—";
  return `${formatNumber(n, digits)} т`;
}

export function formatDate(value: string | Date | null | undefined): string {
  if (!value) return "—";
  const d = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(d.getTime())) return "—";
  return new Intl.DateTimeFormat(UA, {
    day: "2-digit",
    month: "long",
    year: "numeric",
  }).format(d);
}

export function formatDateTime(value: string | Date | null | undefined): string {
  if (!value) return "—";
  const d = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(d.getTime())) return "—";
  return new Intl.DateTimeFormat(UA, {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(d);
}

/** Compact UAH for KPI tiles — always K/M suffix style */
export function formatUAHCompact(
  value: number | string | null | undefined,
): string {
  if (value === null || value === undefined) return "—";
  const n = typeof value === "string" ? parseFloat(value) : value;
  if (!Number.isFinite(n)) return "—";
  return new Intl.NumberFormat(UA, {
    style: "currency",
    currency: "UAH",
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(n);
}
