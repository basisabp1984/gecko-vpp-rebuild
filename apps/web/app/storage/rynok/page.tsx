"use client";

import { Suspense, useEffect, useMemo } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import clsx from "clsx";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Zap, Coins } from "lucide-react";
import { useAPI } from "@/lib/api";
import { useTenantStore } from "@/lib/store";
import { TENANTS } from "@/lib/tenants";
import { Tabs } from "@/components/Tabs";
import { HourlyChart, type HourlyPoint } from "@/components/HourlyChart";
import {
  formatUAH,
  formatUAHCompact,
  formatNumber,
  formatDateTime,
} from "@/lib/format";

type MarketTab = "anc" | "arb";

interface AncillaryRow {
  id: number;
  asset_id: string;
  service: string;
  started_at: string;
  ended_at: string;
  avg_power_mw: string;
  energy_mwh: string;
  energy_price_uah_mwh: string;
  revenue_energy_uah: string;
}

interface RDNPoint {
  date: string;
  hour: number;
  interval_start: string;
  price_uah_mwh: string;
  volume_mwh: string;
  is_capped: boolean;
  cap_uah_mwh: string | null;
}

interface AssetMini {
  id: string;
  display_name: string;
  asset_class: string;
}

interface TelemetryRow {
  asset_id: string;
  interval_start: string;
  active_power_mw: string;
}

const TABS: { id: MarketTab; label: string }[] = [
  { id: "anc", label: "Допоміжні послуги" },
  { id: "arb", label: "Арбітраж" },
];

function daysAgoISO(d: number): string {
  const date = new Date();
  date.setDate(date.getDate() - d);
  return date.toISOString().slice(0, 10);
}

function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

export default function StorageMarketPage() {
  return (
    <Suspense
      fallback={
        <div className="p-8 text-center text-sm text-text-muted">
          Завантаження ринкової секції…
        </div>
      }
    >
      <Content />
    </Suspense>
  );
}

function Content() {
  useEffect(() => {
    const { currentTenantId, setTenantId } = useTenantStore.getState();
    if (currentTenantId === TENANTS.producer.id) {
      setTenantId(TENANTS.storage.id);
    }
  }, []);

  const router = useRouter();
  const params = useSearchParams();
  const active = (params.get("market") as MarketTab) || "anc";

  function setTab(id: string) {
    const sp = new URLSearchParams(params.toString());
    sp.set("market", id);
    router.replace(`?${sp.toString()}`);
  }

  const date_start = useMemo(() => daysAgoISO(7), []);
  const date_end = useMemo(() => todayISO(), []);

  return (
    <div className="flex flex-col gap-5">
      <header>
        <h1 className="text-2xl sm:text-3xl font-bold text-text-heading">
          Ринок · допоміжні послуги та арбітраж
        </h1>
        <p className="text-sm text-text-muted">
          aFRR / mFRR / РВЧ — оплачуваний резерв та активації. РДН — оптимізація
          циклу заряд/розряд за день уперед.
        </p>
      </header>

      <Tabs
        items={TABS.map((t) => ({ id: t.id, label: t.label }))}
        active={active}
        onChange={setTab}
      />

      {active === "anc" && (
        <AncillaryView date_start={date_start} date_end={date_end} />
      )}
      {active === "arb" && (
        <ArbitrageView date_start={date_start} date_end={date_end} />
      )}
    </div>
  );
}

function AncillaryView({
  date_start,
  date_end,
}: {
  date_start: string;
  date_end: string;
}) {
  const anc = useAPI<AncillaryRow[]>("/api/v1/market/ancillary", {
    date_start,
    date_end,
  });
  const rows = anc.data?.data ?? [];

  /* aggregate by service */
  const byService = useMemo(() => {
    const m = new Map<string, { count: number; mwh: number; revenue: number }>();
    for (const r of rows) {
      const cur = m.get(r.service) ?? { count: 0, mwh: 0, revenue: 0 };
      cur.count += 1;
      cur.mwh += parseFloat(r.energy_mwh);
      cur.revenue += parseFloat(r.revenue_energy_uah);
      m.set(r.service, cur);
    }
    return Array.from(m.entries())
      .map(([service, v]) => ({ service, ...v }))
      .sort((a, b) => b.revenue - a.revenue);
  }, [rows]);

  const totalRevenue = byService.reduce((s, x) => s + x.revenue, 0);
  const totalMwh = byService.reduce((s, x) => s + x.mwh, 0);

  return (
    <div className="flex flex-col gap-5">
      <section className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <SummaryTile
          label="Виторг (7 днів)"
          value={formatUAHCompact(totalRevenue)}
          tone="success"
        />
        <SummaryTile
          label="Активацій"
          value={String(rows.length)}
          sub="aFRR/mFRR/РВЧ"
        />
        <SummaryTile
          label="Енергії передано"
          value={`${formatNumber(totalMwh, 2)} МВт·год`}
        />
        <SummaryTile
          label="Видів послуг"
          value={String(byService.length)}
        />
      </section>

      {/* Per-service summary */}
      <section className="rounded-xl border border-border bg-bg-card shadow-card p-4">
        <header className="mb-3 flex items-center gap-2">
          <Zap size={16} className="text-accent" />
          <h2 className="text-base font-semibold text-text-heading">
            Виторг за послугами
          </h2>
        </header>
        {byService.length === 0 ? (
          <div className="py-8 text-center text-sm text-text-muted">
            Активацій не зафіксовано.
          </div>
        ) : (
          <ul className="divide-y divide-border">
            {byService.map((s) => {
              const pct = totalRevenue > 0 ? (s.revenue / totalRevenue) * 100 : 0;
              return (
                <li key={s.service} className="py-3 flex items-center gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm font-medium text-text-heading">
                        {s.service}
                      </span>
                      <span className="text-sm font-mono text-success">
                        {formatUAH(s.revenue)}
                      </span>
                    </div>
                    <div className="mt-1.5 h-2 rounded-full bg-bg-subtle overflow-hidden">
                      <div
                        className="h-full bg-info transition-all"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <div className="mt-1 text-xs text-text-muted">
                      {s.count} активацій · {formatNumber(s.mwh, 2)} МВт·год
                      · {formatNumber(pct, 1)}% від портфеля
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      {/* Recent activations table */}
      <section className="rounded-xl border border-border bg-bg-card shadow-card overflow-hidden">
        <header className="p-4 border-b border-border">
          <h2 className="text-base font-semibold text-text-heading">
            Останні активації
          </h2>
        </header>
        {anc.isLoading ? (
          <div className="p-8 text-center text-sm text-text-muted">
            Завантаження…
          </div>
        ) : rows.length === 0 ? (
          <div className="p-8 text-center text-sm text-text-muted">
            Активацій немає.
          </div>
        ) : (
          <div className="overflow-x-auto max-h-96 overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="bg-bg-subtle text-xs uppercase tracking-wide text-text-muted sticky top-0">
                <tr>
                  <th className="px-3 py-2 text-left">Початок</th>
                  <th className="px-3 py-2 text-left">Послуга</th>
                  <th className="px-3 py-2 text-right">Потужність</th>
                  <th className="px-3 py-2 text-right">Енергія</th>
                  <th className="px-3 py-2 text-right">Ціна</th>
                  <th className="px-3 py-2 text-right">Виторг</th>
                </tr>
              </thead>
              <tbody>
                {rows.slice(0, 60).map((r, i) => (
                  <tr
                    key={r.id}
                    className={clsx(
                      "border-t border-border",
                      i % 2 === 1 && "bg-bg-subtle/30",
                    )}
                  >
                    <td className="px-3 py-1.5 text-text-body text-xs">
                      {formatDateTime(r.started_at)}
                    </td>
                    <td className="px-3 py-1.5">
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-info/15 text-info">
                        {r.service}
                      </span>
                    </td>
                    <td className="px-3 py-1.5 text-right font-mono text-xs">
                      {formatNumber(r.avg_power_mw, 2)} МВт
                    </td>
                    <td className="px-3 py-1.5 text-right font-mono text-xs">
                      {formatNumber(r.energy_mwh, 3)}
                    </td>
                    <td className="px-3 py-1.5 text-right font-mono text-xs">
                      {formatUAH(r.energy_price_uah_mwh)}
                    </td>
                    <td className="px-3 py-1.5 text-right font-mono text-xs text-text-heading font-medium">
                      {formatUAH(r.revenue_energy_uah)}
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

function ArbitrageView({
  date_start,
  date_end,
}: {
  date_start: string;
  date_end: string;
}) {
  const rdn = useAPI<RDNPoint[]>("/api/v1/market/rdn", {
    date_start,
    date_end,
  });
  const assets = useAPI<AssetMini[]>("/api/v1/assets");
  const uzeAssets = useMemo(
    () => (assets.data?.data ?? []).filter((a) => a.asset_class === "УЗЕ"),
    [assets.data],
  );

  /* fetch telemetry for first УЗЕ (proxy for fleet dispatch curve) */
  const firstUze = uzeAssets[0];
  const tele = useAPI<TelemetryRow[]>(
    firstUze ? "/api/v1/dispatch/telemetry" : null,
    firstUze
      ? { asset_id: firstUze.id, date_start: daysAgoISO(2), date_end }
      : undefined,
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

  /* battery dispatch overlay — last 24h */
  const dispatchData = useMemo(() => {
    return (tele.data?.data ?? []).slice(-24).map((r) => {
      const d = new Date(r.interval_start);
      return {
        label: `${String(d.getHours()).padStart(2, "0")}:00`,
        power: parseFloat(r.active_power_mw),
      };
    });
  }, [tele.data]);

  /* P&L estimate */
  const arb = useMemo(() => {
    const tRows = tele.data?.data ?? [];
    const rRows = rdn.data?.data ?? [];
    const priceMap = new Map<string, number>();
    for (const p of rRows) {
      priceMap.set(p.interval_start, parseFloat(p.price_uah_mwh));
    }
    let revenue = 0;
    let cost = 0;
    let mwhSold = 0;
    let mwhBought = 0;
    for (const r of tRows) {
      const p = parseFloat(r.active_power_mw);
      const price = priceMap.get(r.interval_start);
      if (price === undefined) continue;
      if (p > 0) {
        revenue += p * price;
        mwhSold += p;
      } else if (p < 0) {
        cost += -p * price;
        mwhBought += -p;
      }
    }
    return {
      revenue,
      cost,
      net: revenue - cost,
      mwhSold,
      mwhBought,
    };
  }, [tele.data, rdn.data]);

  return (
    <div className="flex flex-col gap-5">
      <section className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <SummaryTile
          label="Виторг від продажу"
          value={formatUAHCompact(arb.revenue)}
          tone="success"
          sub="розряд → РДН"
        />
        <SummaryTile
          label="Витрати на закупівлю"
          value={formatUAHCompact(arb.cost)}
          sub="заряд ← РДН"
        />
        <SummaryTile
          label="Чистий P&L"
          value={formatUAHCompact(arb.net)}
          tone={arb.net >= 0 ? "success" : "alert"}
          sub={`${formatNumber(arb.mwhSold, 1)} / ${formatNumber(arb.mwhBought, 1)} МВт·год`}
        />
        <SummaryTile
          label="Цикл-маржа"
          value={
            arb.mwhBought > 0
              ? formatUAH(arb.net / arb.mwhBought)
              : "—"
          }
          sub="P&L / закуплена МВт·год"
        />
      </section>

      <section className="rounded-xl border border-border bg-bg-card shadow-card p-4">
        <header className="mb-3">
          <h2 className="text-base font-semibold text-text-heading">
            РДН · ціна за останні 7 днів
          </h2>
          <p className="text-xs text-text-muted">
            Червоні точки — годинні кепи. Дешева ніч + дорогий пік = арбітраж.
          </p>
        </header>
        {rdn.isLoading ? (
          <div className="h-[260px] flex items-center justify-center text-sm text-text-muted">
            Завантаження…
          </div>
        ) : (
          <HourlyChart
            data={chartData}
            cap={cap}
            yLabel="грн/МВт·год"
            height={260}
          />
        )}
      </section>

      <section className="rounded-xl border border-border bg-bg-card shadow-card p-4">
        <header className="mb-3 flex items-center gap-2">
          <Coins size={16} className="text-accent" />
          <h2 className="text-base font-semibold text-text-heading">
            Диспетчеризація батареї · 24 год ·{" "}
            {firstUze?.display_name ?? "—"}
          </h2>
        </header>
        {tele.isLoading ? (
          <div className="h-[260px] flex items-center justify-center text-sm text-text-muted">
            Завантаження…
          </div>
        ) : dispatchData.length === 0 ? (
          <div className="h-[260px] flex items-center justify-center text-sm text-text-muted">
            Дані телеметрії відсутні.
          </div>
        ) : (
          <div style={{ width: "100%", height: 260 }}>
            <ResponsiveContainer>
              <BarChart
                data={dispatchData}
                margin={{ top: 10, right: 16, left: 0, bottom: 8 }}
              >
                <CartesianGrid
                  stroke="var(--color-border)"
                  strokeDasharray="3 3"
                  vertical={false}
                />
                <XAxis
                  dataKey="label"
                  stroke="var(--color-text-muted)"
                  tick={{ fontSize: 11 }}
                />
                <YAxis
                  stroke="var(--color-text-muted)"
                  tick={{ fontSize: 11 }}
                />
                <Tooltip
                  contentStyle={{
                    background: "var(--color-bg-card)",
                    border: "1px solid var(--color-border)",
                    borderRadius: 8,
                    fontSize: 11,
                  }}
                  formatter={(v) => {
                    const n = typeof v === "number" ? v : parseFloat(String(v));
                    return [`${formatNumber(n, 2)} МВт`, "потужність"];
                  }}
                />
                <Bar dataKey="power" isAnimationActive={false}>
                  {dispatchData.map((d, i) => (
                    <Cell
                      key={i}
                      fill={
                        d.power >= 0
                          ? "var(--color-success)"
                          : "var(--color-info)"
                      }
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </section>
    </div>
  );
}

function SummaryTile({
  label,
  value,
  sub,
  tone = "default",
}: {
  label: string;
  value: string;
  sub?: string;
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
      <div className={clsx("mt-1 text-lg font-bold", cls)}>{value}</div>
      {sub && <div className="text-[11px] text-text-muted mt-0.5">{sub}</div>}
    </div>
  );
}
