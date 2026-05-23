"use client";

import { useEffect, useMemo } from "react";
import clsx from "clsx";
import { useAPI } from "@/lib/api";
import { useTenantStore } from "@/lib/store";
import { TENANTS } from "@/lib/tenants";
import { HourlyChart, type HourlyPoint } from "@/components/HourlyChart";
import { Tabs } from "@/components/Tabs";
import { formatUAH, formatNumber } from "@/lib/format";

interface RDNPoint {
  date: string;
  hour: number;
  interval_start: string;
  price_uah_mwh: string;
  volume_mwh: string;
  is_capped: boolean;
  cap_uah_mwh: string | null;
}

interface SettlementRow {
  id: number;
  statement_no: string;
  counterparty: string;
  counterparty_edrpou: string;
  contract_no: string;
  period_year: number;
  period_month: number;
  period_start: string;
  period_end: string;
  volume_total_mwh: string;
  amount_net_uah: string;
  amount_vat_uah: string;
  amount_gross_uah: string;
  payment_due_date: string;
  status: string;
}

function daysAgoISO(d: number): string {
  const date = new Date();
  date.setDate(date.getDate() - d);
  return date.toISOString().slice(0, 10);
}

function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

export default function CIMarketPage() {
  useEffect(() => {
    const { currentTenantId, setTenantId } = useTenantStore.getState();
    if (currentTenantId === TENANTS.producer.id) {
      setTenantId(TENANTS.ci.id);
    }
  }, []);

  const date_start = useMemo(() => daysAgoISO(7), []);
  const date_end = useMemo(() => todayISO(), []);

  const rdn = useAPI<RDNPoint[]>("/api/v1/market/rdn", { date_start, date_end });
  const settlements = useAPI<SettlementRow[]>(
    "/api/v1/regulatory/settlements",
    { period: "monthly" },
  );

  const chartData: HourlyPoint[] = useMemo(() => {
    const rows = rdn.data?.data ?? [];
    return rows.map((r) => {
      const d = new Date(r.interval_start);
      const label = `${String(d.getDate()).padStart(2, "0")}.${String(
        d.getMonth() + 1,
      ).padStart(2, "0")} ${String(d.getHours()).padStart(2, "0")}`;
      return {
        ts: r.interval_start,
        label,
        value: parseFloat(r.price_uah_mwh),
        is_capped: r.is_capped,
      };
    });
  }, [rdn.data]);

  const cap = useMemo(() => {
    const rows = rdn.data?.data ?? [];
    const c = rows.find((r) => r.is_capped && r.cap_uah_mwh);
    return c?.cap_uah_mwh ? parseFloat(c.cap_uah_mwh) : null;
  }, [rdn.data]);

  /* Average + peak/off-peak split for buying perspective */
  const stats = useMemo(() => {
    const rows = rdn.data?.data ?? [];
    if (rows.length === 0) return null;
    let sum = 0;
    let peakSum = 0;
    let peakN = 0;
    let nightSum = 0;
    let nightN = 0;
    let max = -Infinity;
    let min = Infinity;
    for (const r of rows) {
      const p = parseFloat(r.price_uah_mwh);
      sum += p;
      if (p > max) max = p;
      if (p < min) min = p;
      const h = r.hour;
      if (h >= 9 && h <= 22) {
        peakSum += p;
        peakN++;
      } else {
        nightSum += p;
        nightN++;
      }
    }
    const avg = sum / rows.length;
    const peakAvg = peakN > 0 ? peakSum / peakN : 0;
    const nightAvg = nightN > 0 ? nightSum / nightN : 0;
    return { avg, peakAvg, nightAvg, max, min, n: rows.length };
  }, [rdn.data]);

  const settleRows = settlements.data?.data ?? [];

  return (
    <div className="flex flex-col gap-5">
      <header>
        <h1 className="text-2xl sm:text-3xl font-bold text-text-heading">
          Ринок · тарифи РДН
        </h1>
        <p className="text-sm text-text-muted">
          Денний ринок з боку покупця. Зсуньте енергоємні процеси на нічні
          години — заощаджуйте на дельті peak / off-peak.
        </p>
      </header>

      <Tabs
        items={[{ id: "rdn", label: "Тарифи" }]}
        active="rdn"
        onChange={() => undefined}
      />

      {stats && (
        <section className="grid grid-cols-2 lg:grid-cols-5 gap-3">
          <PriceTile label="Середня ціна" value={formatUAH(stats.avg)} />
          <PriceTile
            label="Пік 09:00–22:00"
            value={formatUAH(stats.peakAvg)}
            tone="alert"
          />
          <PriceTile
            label="Ніч 23:00–08:00"
            value={formatUAH(stats.nightAvg)}
            tone="success"
          />
          <PriceTile label="Макс." value={formatUAH(stats.max)} />
          <PriceTile label="Мін." value={formatUAH(stats.min)} />
        </section>
      )}

      <section className="rounded-xl border border-border bg-bg-card shadow-card p-4">
        <header className="flex items-center justify-between mb-3">
          <div>
            <h2 className="text-base font-semibold text-text-heading">
              РДН · 7-денна крива (грн/МВт·год)
            </h2>
            <p className="text-xs text-text-muted">
              Червоні точки — годинні кепи · нічні години дешевші
            </p>
          </div>
        </header>
        {rdn.isLoading ? (
          <div className="h-[320px] flex items-center justify-center text-sm text-text-muted">
            Завантаження…
          </div>
        ) : rdn.isError ? (
          <div className="h-[320px] flex items-center justify-center text-sm text-alert">
            {rdn.error.message}
          </div>
        ) : (
          <HourlyChart
            data={chartData}
            cap={cap}
            yLabel="грн/МВт·год"
            height={320}
          />
        )}
      </section>

      {/* Settlement preview */}
      <section className="rounded-xl border border-border bg-bg-card shadow-card overflow-hidden">
        <header className="p-4 border-b border-border">
          <h2 className="text-base font-semibold text-text-heading">
            Розрахункові акти за період
          </h2>
          <p className="text-xs text-text-muted">
            Поточні платежі за електроенергію (місячний період)
          </p>
        </header>
        {settlements.isLoading ? (
          <div className="p-8 text-center text-sm text-text-muted">
            Завантаження…
          </div>
        ) : settleRows.length === 0 ? (
          <div className="p-8 text-center text-sm text-text-muted">
            Актів не знайдено.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-bg-subtle text-xs uppercase tracking-wide text-text-muted">
                <tr>
                  <th className="px-4 py-2 text-left">Акт</th>
                  <th className="px-4 py-2 text-left">Контрагент</th>
                  <th className="px-4 py-2 text-left">Період</th>
                  <th className="px-4 py-2 text-right">Обсяг</th>
                  <th className="px-4 py-2 text-right">Сума (брутто)</th>
                  <th className="px-4 py-2 text-left">Статус</th>
                </tr>
              </thead>
              <tbody>
                {settleRows.slice(0, 12).map((r, i) => (
                  <tr
                    key={r.id}
                    className={clsx(
                      "border-t border-border",
                      i % 2 === 1 && "bg-bg-subtle/30",
                    )}
                  >
                    <td className="px-4 py-2 font-mono text-[11px] text-text-body">
                      {r.statement_no}
                    </td>
                    <td className="px-4 py-2 text-text-heading">
                      {r.counterparty}
                      <div className="text-[10px] text-text-muted">
                        ЄДРПОУ {r.counterparty_edrpou}
                      </div>
                    </td>
                    <td className="px-4 py-2 text-xs text-text-muted">
                      {r.period_year}-
                      {String(r.period_month).padStart(2, "0")}
                    </td>
                    <td className="px-4 py-2 text-right font-mono text-xs">
                      {formatNumber(r.volume_total_mwh, 1)}
                    </td>
                    <td className="px-4 py-2 text-right font-mono text-xs text-text-heading font-medium">
                      {formatUAH(r.amount_gross_uah)}
                    </td>
                    <td className="px-4 py-2">
                      <SettlementStatusBadge status={r.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

function PriceTile({
  label,
  value,
  tone = "default",
}: {
  label: string;
  value: string;
  tone?: "default" | "success" | "alert";
}) {
  const cls =
    tone === "success"
      ? "text-success"
      : tone === "alert"
        ? "text-alert"
        : "text-text-heading";
  return (
    <div className="rounded-xl border border-border bg-bg-card p-3 shadow-card">
      <div className="text-[10px] uppercase tracking-wide text-text-muted">
        {label}
      </div>
      <div className={clsx("mt-1 text-base font-bold font-mono", cls)}>
        {value}
      </div>
    </div>
  );
}

function SettlementStatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    SIGNED: "bg-success/15 text-success",
    PENDING: "bg-warning/15 text-warning",
    DRAFT: "bg-bg-subtle text-text-muted",
    PAID: "bg-success/15 text-success",
  };
  const tone = map[status] ?? "bg-bg-subtle text-text-muted";
  return (
    <span
      className={clsx(
        "inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium",
        tone,
      )}
    >
      {status}
    </span>
  );
}
