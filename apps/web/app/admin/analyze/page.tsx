"use client";

import { useMemo } from "react";
import {
  BarChart3,
  Leaf,
  Coins,
  Gauge,
  AlertTriangle,
} from "lucide-react";
import {
  Bar,
  BarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  CartesianGrid,
  Cell,
} from "recharts";
import { useAPI } from "@/lib/api";
import { KPITile } from "@/components/KPITile";
import { formatUAHCompact, formatNumber, formatTonnes } from "@/lib/format";
import clsx from "clsx";

interface AnalyticsRow {
  tenant_id: string;
  code: string;
  co2_avoided_tn_30d: string;
  grn_earned_uah_30d: string;
  opportunity_score_avg: string;
}

interface PortfolioRow {
  tenant_id: string;
  code: string;
  display_name: string;
  segment: string;
  capacity_mw: string;
  asset_count: number;
}

interface AnalyticsPayload {
  rows: AnalyticsRow[];
}
interface PortfolioPayload {
  tenants: PortfolioRow[];
}

const SEGMENT_COLOUR: Record<string, string> = {
  producer: "var(--color-accent)",
  "c-i": "var(--color-info)",
  storage: "var(--color-success)",
};

export default function AdminAnalyzePage() {
  const analytics = useAPI<AnalyticsPayload>("/api/v1/admin/analytics");
  const portfolio = useAPI<PortfolioPayload>("/api/v1/admin/portfolio");

  const merged = useMemo(() => {
    const aRows = analytics.data?.data.rows ?? [];
    const pRows = portfolio.data?.data.tenants ?? [];
    const map = new Map<string, PortfolioRow>();
    for (const p of pRows) map.set(p.tenant_id, p);
    return aRows.map((a) => {
      const p = map.get(a.tenant_id);
      return {
        tenant_id: a.tenant_id,
        code: a.code,
        display_name: p?.display_name ?? a.code,
        segment: p?.segment ?? "—",
        capacity_mw: parseFloat(p?.capacity_mw ?? "0"),
        asset_count: p?.asset_count ?? 0,
        co2: parseFloat(a.co2_avoided_tn_30d),
        revenue: parseFloat(a.grn_earned_uah_30d),
        opportunity: parseFloat(a.opportunity_score_avg),
      };
    });
  }, [analytics.data, portfolio.data]);

  const totals = useMemo(() => {
    return merged.reduce(
      (acc, r) => {
        acc.revenue += r.revenue;
        acc.co2 += r.co2;
        acc.capacity += r.capacity_mw;
        acc.opportunitySum += r.opportunity;
        return acc;
      },
      { revenue: 0, co2: 0, capacity: 0, opportunitySum: 0 },
    );
  }, [merged]);

  const avgOpp = merged.length > 0 ? totals.opportunitySum / merged.length : 0;

  // ---- Heatmap-like cells (tenant × metric) ----
  // Normalise each metric across tenants so colour intensity scales.
  const metrics: Array<{
    key: "revenue" | "co2" | "capacity_mw" | "opportunity";
    label: string;
    fmt: (v: number) => string;
  }> = [
    { key: "revenue", label: "Виторг 30 діб", fmt: (v) => formatUAHCompact(v) },
    { key: "co2", label: "CO₂ уникнено", fmt: (v) => formatTonnes(v) },
    {
      key: "capacity_mw",
      label: "Сум. потужність",
      fmt: (v) => `${formatNumber(v, 1)} МВт`,
    },
    {
      key: "opportunity",
      label: "Opportunity score",
      fmt: (v) => formatNumber(v, 1),
    },
  ];

  function intensity(key: typeof metrics[number]["key"], value: number): number {
    const all = merged.map((m) => m[key]);
    const max = Math.max(...all, 1);
    return Math.min(1, value / max);
  }

  const error = analytics.error ?? portfolio.error;
  const isLoading = analytics.isLoading || portfolio.isLoading;

  return (
    <div className="flex flex-col gap-6">
      <header>
        <h1 className="text-2xl sm:text-3xl font-bold text-text-heading flex items-center gap-2">
          <BarChart3 size={22} className="text-accent-deep" /> Analyze · крос-тенантний KPI dashboard
        </h1>
        <p className="text-sm text-text-muted">
          Зведений виторг, ESG і opportunity score за останні 30 діб по всіх тенантах.
        </p>
      </header>

      {/* Aggregate KPIs */}
      <section className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <KPITile
          label="Виторг 30 діб"
          value={isLoading ? "—" : formatUAHCompact(totals.revenue)}
          sublabel="усі тенанти"
          tone="success"
          icon={<Coins size={16} />}
        />
        <KPITile
          label="CO₂ уникнено"
          value={isLoading ? "—" : formatTonnes(totals.co2)}
          sublabel="30 діб"
          tone="success"
          icon={<Leaf size={16} />}
        />
        <KPITile
          label="Сум. потужність"
          value={isLoading ? "—" : `${formatNumber(totals.capacity, 1)} МВт`}
          sublabel="вст. потужність"
          icon={<Gauge size={16} />}
        />
        <KPITile
          label="Сер. opportunity"
          value={isLoading ? "—" : formatNumber(avgOpp, 1)}
          sublabel="індекс 0–100"
          tone={avgOpp >= 60 ? "success" : "warning"}
        />
      </section>

      {error && (
        <div className="rounded-xl border border-alert/40 bg-alert/10 p-4 flex items-start gap-3">
          <AlertTriangle size={16} className="text-alert mt-0.5 shrink-0" />
          <div>
            <div className="text-sm font-semibold text-text-heading">
              Помилка завантаження
            </div>
            <p className="text-sm text-text-muted">{error.message}</p>
          </div>
        </div>
      )}

      {/* Revenue by tenant */}
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="rounded-xl border border-border bg-bg-card p-5 shadow-card">
          <h2 className="text-base font-semibold text-text-heading mb-3">
            Виторг по тенантах (30 діб)
          </h2>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={merged} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
              <XAxis
                type="number"
                tickFormatter={(v) => formatUAHCompact(v)}
                stroke="var(--color-text-muted)"
                fontSize={11}
              />
              <YAxis
                dataKey="code"
                type="category"
                stroke="var(--color-text-muted)"
                fontSize={11}
                width={80}
              />
              <Tooltip
                cursor={{ fill: "var(--color-bg-subtle)" }}
                contentStyle={{
                  background: "var(--color-bg-card)",
                  border: "1px solid var(--color-border)",
                  borderRadius: 8,
                  fontSize: 12,
                }}
                formatter={(v: number | string) => formatUAHCompact(v)}
              />
              <Bar dataKey="revenue" radius={[0, 4, 4, 0]}>
                {merged.map((r) => (
                  <Cell
                    key={r.tenant_id}
                    fill={SEGMENT_COLOUR[r.segment] ?? "var(--color-accent)"}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* CO2 by tenant */}
        <div className="rounded-xl border border-border bg-bg-card p-5 shadow-card">
          <h2 className="text-base font-semibold text-text-heading mb-3">
            CO₂ уникнено (тонн, 30 діб)
          </h2>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={merged} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
              <XAxis
                type="number"
                stroke="var(--color-text-muted)"
                fontSize={11}
              />
              <YAxis
                dataKey="code"
                type="category"
                stroke="var(--color-text-muted)"
                fontSize={11}
                width={80}
              />
              <Tooltip
                cursor={{ fill: "var(--color-bg-subtle)" }}
                contentStyle={{
                  background: "var(--color-bg-card)",
                  border: "1px solid var(--color-border)",
                  borderRadius: 8,
                  fontSize: 12,
                }}
                formatter={(v: number | string) =>
                  `${formatNumber(v, 1)} т`
                }
              />
              <Bar dataKey="co2" fill="var(--color-success)" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>

      {/* Heatmap-like grid */}
      <section className="rounded-xl border border-border bg-bg-card shadow-card overflow-hidden">
        <div className="px-5 pt-4 pb-2">
          <h2 className="text-base font-semibold text-text-heading">
            Тенант × метрика
          </h2>
          <p className="text-xs text-text-muted">
            Колір клітинки відображає відносну величину метрики (макс по колонці = найбільша
            заливка).
          </p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-bg-subtle text-xs uppercase tracking-wide text-text-muted">
              <tr>
                <th className="px-4 py-2 text-left">Тенант</th>
                <th className="px-4 py-2 text-left">Сегмент</th>
                {metrics.map((m) => (
                  <th key={m.key} className="px-4 py-2 text-right">
                    {m.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {merged.map((r, i) => (
                <tr
                  key={r.tenant_id}
                  className={clsx(
                    "border-t border-border",
                    i % 2 === 1 && "bg-bg-subtle/30",
                  )}
                >
                  <td className="px-4 py-3 text-text-body">
                    <div className="font-medium text-text-heading">
                      {r.display_name}
                    </div>
                    <div className="text-[11px] text-text-muted">{r.code}</div>
                  </td>
                  <td className="px-4 py-3 text-text-muted text-xs uppercase tracking-wide">
                    {r.segment}
                  </td>
                  {metrics.map((m) => {
                    const v = r[m.key];
                    const t = intensity(m.key, v);
                    return (
                      <td
                        key={m.key}
                        className="px-4 py-3 text-right font-mono text-xs"
                        style={{
                          background: `rgba(50, 168, 138, ${0.05 + t * 0.35})`,
                        }}
                      >
                        {m.fmt(v)}
                      </td>
                    );
                  })}
                </tr>
              ))}
              {merged.length === 0 && !isLoading && (
                <tr>
                  <td
                    colSpan={2 + metrics.length}
                    className="px-4 py-6 text-center text-sm text-text-muted"
                  >
                    Немає даних.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
