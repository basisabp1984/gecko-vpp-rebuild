"use client";

import { Suspense, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
  Cell,
} from "recharts";
import { Coins, FilePlus } from "lucide-react";
import clsx from "clsx";
import { useAPI } from "@/lib/api";
import { Tabs } from "@/components/Tabs";
import { HourlyChart, type HourlyPoint } from "@/components/HourlyChart";
import { BidForm } from "@/components/BidForm";
import { formatUAH, formatNumber, formatUAHCompact } from "@/lib/format";

type MarketTab = "rdn" | "vdr" | "br" | "dd";

interface RDNPoint {
  date: string;
  hour: number;
  interval_start: string;
  price_uah_mwh: string;
  volume_mwh: string;
  is_capped: boolean;
  cap_uah_mwh: string | null;
}

interface VDRTrade {
  trade_id: string;
  executed_at: string;
  delivery_date: string;
  delivery_hour: number;
  interval_start: string;
  volume_mwh: string;
  price_uah_mwh: string;
  side: string;
  counterparty_code: string;
}

interface BRRow {
  date: string;
  hour: number;
  interval_start: string;
  price_short_uah_mwh: string;
  price_long_uah_mwh: string;
  system_direction: string;
  our_imbalance_mwh: string;
  settlement_uah: string;
}

interface DDContract {
  id: number;
  contract_no: string;
  counterparty_name: string;
  counterparty_edrpou: string;
  profile_type: string;
  start_date: string;
  end_date: string;
  price_uah_mwh: string | null;
  price_formula: string | null;
  total_volume_mwh: string;
  status: string;
}

interface BidRow {
  id: number;
  bid_id: string;
  market: string;
  delivery_date: string;
  hour: number;
  side: string;
  volume_mwh: string;
  price_uah_mwh: string;
  state: string;
  accepted_volume_mwh?: string | null;
  clearing_price?: string | null;
}

interface RevenueData {
  rdn_uah: string;
  vdr_uah: string;
  br_uah: string;
  dd_uah: string;
  ancillary_uah: string;
  green_tariff_uah: string;
  total_uah: string;
  by_channel: { channel: string; revenue_uah: string; share_pct: number }[];
}

const TABS: { id: MarketTab; label: string }[] = [
  { id: "rdn", label: "РДН" },
  { id: "vdr", label: "ВДР" },
  { id: "br", label: "БР" },
  { id: "dd", label: "ДД" },
];

function daysAgoISO(d: number): string {
  const date = new Date();
  date.setDate(date.getDate() - d);
  return date.toISOString().slice(0, 10);
}

function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

export default function ProducerMarketPage() {
  return (
    <Suspense
      fallback={
        <div className="p-8 text-center text-sm text-text-muted">
          Завантаження ринкової секції…
        </div>
      }
    >
      <MarketContent />
    </Suspense>
  );
}

function MarketContent() {
  const router = useRouter();
  const params = useSearchParams();
  const active = (params.get("market") as MarketTab) || "rdn";
  const [bidOpen, setBidOpen] = useState(false);

  const date_start = useMemo(() => daysAgoISO(7), []);
  const date_end = useMemo(() => todayISO(), []);

  function setTab(id: string) {
    const sp = new URLSearchParams(params.toString());
    sp.set("market", id);
    router.replace(`?${sp.toString()}`);
  }

  const revenue = useAPI<RevenueData>("/api/v1/market/revenue");
  const bids = useAPI<BidRow[]>("/api/v1/market/bids", { date_start, date_end });

  return (
    <div className="flex flex-col gap-5">
      <header className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-text-heading">
            Ринок · РДН / ВДР / БР / ДД
          </h1>
          <p className="text-sm text-text-muted">
            Заявки, історія угод, кеп-оверлей, ребра доходу.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setBidOpen(true)}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-accent text-text-inverse font-medium hover:bg-accent-deep transition-colors shadow-card"
        >
          <FilePlus size={16} />
          Подати заявку
        </button>
      </header>

      {/* Revenue summary */}
      <section className="rounded-xl border border-border bg-bg-card shadow-card p-4">
        <header className="flex items-center justify-between mb-3">
          <h2 className="text-base font-semibold text-text-heading flex items-center gap-2">
            <Coins size={16} className="text-accent" />
            Виторг за каналами
          </h2>
          {revenue.data && (
            <span className="text-sm font-semibold text-text-heading">
              Разом: {formatUAH(revenue.data.data.total_uah)}
            </span>
          )}
        </header>
        {revenue.isLoading ? (
          <div className="py-6 text-center text-sm text-text-muted">
            Завантаження…
          </div>
        ) : revenue.isError ? (
          <div className="py-6 text-center text-sm text-alert">
            {revenue.error.message}
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
            {revenue.data?.data.by_channel.map((c) => (
              <RevenueTile
                key={c.channel}
                channel={c.channel}
                revenue={c.revenue_uah}
                share={c.share_pct}
              />
            ))}
            <RevenueTile
              channel="ЗТ"
              revenue={revenue.data?.data.green_tariff_uah ?? "0"}
              share={null}
            />
          </div>
        )}
      </section>

      <Tabs
        items={TABS.map((t) => ({ id: t.id, label: t.label }))}
        active={active}
        onChange={setTab}
      />

      {active === "rdn" && <RDNView date_start={date_start} date_end={date_end} />}
      {active === "vdr" && <VDRView date_start={date_start} date_end={date_end} />}
      {active === "br" && <BRView date_start={date_start} date_end={date_end} />}
      {active === "dd" && <DDView date_start={date_start} date_end={date_end} />}

      {/* Bids table */}
      <section className="rounded-xl border border-border bg-bg-card shadow-card overflow-hidden">
        <header className="flex items-center justify-between p-4 border-b border-border">
          <h2 className="text-base font-semibold text-text-heading">
            Історія заявок
          </h2>
          <span className="text-xs text-text-muted">
            {bids.data?.data?.length ?? 0} за період
          </span>
        </header>
        {bids.isLoading ? (
          <div className="p-6 text-center text-sm text-text-muted">
            Завантаження…
          </div>
        ) : (bids.data?.data?.length ?? 0) === 0 ? (
          <div className="p-6 text-center text-sm text-text-muted">
            Заявок поки немає.
          </div>
        ) : (
          <div className="overflow-x-auto max-h-96 overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="bg-bg-subtle text-xs uppercase tracking-wide text-text-muted sticky top-0">
                <tr>
                  <th className="px-3 py-2 text-left">ID</th>
                  <th className="px-3 py-2 text-left">Ринок</th>
                  <th className="px-3 py-2 text-left">Дата · год</th>
                  <th className="px-3 py-2 text-left">Сторона</th>
                  <th className="px-3 py-2 text-right">Обсяг</th>
                  <th className="px-3 py-2 text-right">Ціна</th>
                  <th className="px-3 py-2 text-left">Стан</th>
                </tr>
              </thead>
              <tbody>
                {(bids.data?.data ?? []).slice(0, 50).map((b, i) => (
                  <tr
                    key={b.id}
                    className={clsx(
                      "border-t border-border",
                      i % 2 === 1 && "bg-bg-subtle/30",
                    )}
                  >
                    <td className="px-3 py-1.5 font-mono text-[11px] text-text-muted">
                      {b.bid_id}
                    </td>
                    <td className="px-3 py-1.5 text-text-body">{b.market}</td>
                    <td className="px-3 py-1.5 text-text-body">
                      {b.delivery_date} · {String(b.hour).padStart(2, "0")}:00
                    </td>
                    <td className="px-3 py-1.5">
                      <span
                        className={clsx(
                          "inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium",
                          b.side === "SELL"
                            ? "bg-success/15 text-success"
                            : "bg-info/15 text-info",
                        )}
                      >
                        {b.side}
                      </span>
                    </td>
                    <td className="px-3 py-1.5 text-right font-mono text-xs">
                      {formatNumber(b.volume_mwh, 2)}
                    </td>
                    <td className="px-3 py-1.5 text-right font-mono text-xs">
                      {formatUAH(b.price_uah_mwh)}
                    </td>
                    <td className="px-3 py-1.5">
                      <BidStateBadge state={b.state} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <BidForm
        open={bidOpen}
        onClose={() => setBidOpen(false)}
        defaultMarket={active.toUpperCase()}
      />
    </div>
  );
}

function RevenueTile({
  channel,
  revenue,
  share,
}: {
  channel: string;
  revenue: string;
  share: number | null;
}) {
  const n = parseFloat(revenue);
  const isNeg = n < 0;
  return (
    <div className="rounded-lg border border-border bg-bg-page p-2.5">
      <div className="text-[10px] uppercase tracking-wide text-text-muted">
        {channel}
      </div>
      <div
        className={clsx(
          "text-sm font-semibold",
          isNeg ? "text-alert" : "text-text-heading",
        )}
      >
        {formatUAHCompact(revenue)}
      </div>
      {share !== null && (
        <div className="text-[10px] text-text-muted">
          {formatNumber(share, 1)}%
        </div>
      )}
    </div>
  );
}

function BidStateBadge({ state }: { state: string }) {
  const map: Record<string, string> = {
    ACCEPTED: "bg-success/15 text-success",
    ACTIVE: "bg-info/15 text-info",
    REJECTED: "bg-alert/15 text-alert",
    CANCELLED: "bg-bg-subtle text-text-muted",
    EXPIRED: "bg-bg-subtle text-text-muted",
  };
  const tone = map[state] ?? "bg-bg-subtle text-text-muted";
  return (
    <span
      className={clsx(
        "inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium",
        tone,
      )}
    >
      {state}
    </span>
  );
}

/* ---------------- RDN view ---------------- */

function RDNView({
  date_start,
  date_end,
}: {
  date_start: string;
  date_end: string;
}) {
  const rdn = useAPI<RDNPoint[]>("/api/v1/market/rdn", { date_start, date_end });

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

  return (
    <section className="rounded-xl border border-border bg-bg-card shadow-card p-4">
      <h2 className="text-base font-semibold text-text-heading mb-3">
        РДН · ціна за останні 7 днів
      </h2>
      {rdn.isLoading ? (
        <div className="h-[320px] flex items-center justify-center text-sm text-text-muted">
          Завантаження…
        </div>
      ) : rdn.isError ? (
        <div className="h-[320px] flex items-center justify-center text-sm text-alert">
          {rdn.error.message}
        </div>
      ) : (
        <HourlyChart data={chartData} cap={cap} yLabel="грн/МВт·год" height={320} />
      )}
    </section>
  );
}

/* ---------------- VDR view ---------------- */

function VDRView({
  date_start,
  date_end,
}: {
  date_start: string;
  date_end: string;
}) {
  const vdr = useAPI<VDRTrade[]>("/api/v1/market/vdr", { date_start, date_end });
  const rows = vdr.data?.data ?? [];

  const points = useMemo(() => {
    return rows.slice(0, 200).map((t) => {
      const d = new Date(t.interval_start);
      return {
        x: d.getTime(),
        y: parseFloat(t.price_uah_mwh),
        z: parseFloat(t.volume_mwh),
        side: t.side,
        label: `${String(d.getDate()).padStart(2, "0")}.${String(
          d.getMonth() + 1,
        ).padStart(2, "0")} ${String(d.getHours()).padStart(2, "0")}:00`,
        counterparty: t.counterparty_code,
      };
    });
  }, [vdr.data]);

  const sellPts = points.filter((p) => p.side === "SELL");
  const buyPts = points.filter((p) => p.side === "BUY");

  return (
    <section className="rounded-xl border border-border bg-bg-card shadow-card p-4">
      <h2 className="text-base font-semibold text-text-heading mb-3">
        ВДР · угоди (розмір кулі ~ обсяг)
      </h2>
      {vdr.isLoading ? (
        <div className="h-[320px] flex items-center justify-center text-sm text-text-muted">
          Завантаження…
        </div>
      ) : rows.length === 0 ? (
        <div className="h-[320px] flex items-center justify-center text-sm text-text-muted">
          Угод не знайдено.
        </div>
      ) : (
        <div style={{ width: "100%", height: 320 }}>
          <ResponsiveContainer>
            <ScatterChart margin={{ top: 10, right: 16, left: 0, bottom: 8 }}>
              <CartesianGrid
                stroke="var(--color-border)"
                strokeDasharray="3 3"
              />
              <XAxis
                type="number"
                dataKey="x"
                domain={["dataMin", "dataMax"]}
                tickFormatter={(t) => {
                  const d = new Date(t);
                  return `${String(d.getDate()).padStart(2, "0")}.${String(
                    d.getMonth() + 1,
                  ).padStart(2, "0")}`;
                }}
                stroke="var(--color-text-muted)"
                tick={{ fontSize: 11 }}
              />
              <YAxis
                type="number"
                dataKey="y"
                name="ціна"
                stroke="var(--color-text-muted)"
                tick={{ fontSize: 11 }}
              />
              <ZAxis type="number" dataKey="z" range={[40, 280]} />
              <Tooltip
                cursor={{ strokeDasharray: "3 3" }}
                contentStyle={{
                  background: "var(--color-bg-card)",
                  border: "1px solid var(--color-border)",
                  borderRadius: 8,
                  fontSize: 11,
                }}
                formatter={(v: number, name: string) => {
                  if (name === "y") return [`${formatUAH(v)}`, "ціна"];
                  if (name === "z") return [`${formatNumber(v, 2)} МВт·год`, "обсяг"];
                  return [v, name];
                }}
                labelFormatter={() => ""}
              />
              <Scatter name="SELL" data={sellPts}>
                {sellPts.map((_, i) => (
                  <Cell key={i} fill="var(--color-success)" fillOpacity={0.6} />
                ))}
              </Scatter>
              <Scatter name="BUY" data={buyPts}>
                {buyPts.map((_, i) => (
                  <Cell key={i} fill="var(--color-info)" fillOpacity={0.6} />
                ))}
              </Scatter>
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  );
}

/* ---------------- BR view ---------------- */

function BRView({
  date_start,
  date_end,
}: {
  date_start: string;
  date_end: string;
}) {
  const br = useAPI<BRRow[]>("/api/v1/market/br", { date_start, date_end });
  const rows = br.data?.data ?? [];

  const aggregated = useMemo(() => {
    const m = new Map<string, number>();
    for (const r of rows) {
      const day = r.date;
      m.set(day, (m.get(day) ?? 0) + parseFloat(r.settlement_uah));
    }
    return Array.from(m.entries())
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([day, val]) => ({
        day: day.slice(5),
        settlement: val,
      }));
  }, [rows]);

  return (
    <section className="rounded-xl border border-border bg-bg-card shadow-card p-4">
      <h2 className="text-base font-semibold text-text-heading mb-3">
        Балансуючий ринок · щоденне сальдо
      </h2>
      {br.isLoading ? (
        <div className="h-[320px] flex items-center justify-center text-sm text-text-muted">
          Завантаження…
        </div>
      ) : aggregated.length === 0 ? (
        <div className="h-[320px] flex items-center justify-center text-sm text-text-muted">
          Немає даних балансування.
        </div>
      ) : (
        <div style={{ width: "100%", height: 320 }}>
          <ResponsiveContainer>
            <BarChart
              data={aggregated}
              margin={{ top: 10, right: 16, left: 0, bottom: 8 }}
            >
              <CartesianGrid
                stroke="var(--color-border)"
                strokeDasharray="3 3"
                vertical={false}
              />
              <XAxis
                dataKey="day"
                stroke="var(--color-text-muted)"
                tick={{ fontSize: 11 }}
              />
              <YAxis
                stroke="var(--color-text-muted)"
                tick={{ fontSize: 11 }}
                tickFormatter={(v) => formatUAHCompact(v)}
              />
              <Tooltip
                contentStyle={{
                  background: "var(--color-bg-card)",
                  border: "1px solid var(--color-border)",
                  borderRadius: 8,
                  fontSize: 11,
                }}
                formatter={(v: number) => [formatUAH(v), "сальдо"]}
              />
              <Bar dataKey="settlement" isAnimationActive={false}>
                {aggregated.map((d, i) => (
                  <Cell
                    key={i}
                    fill={
                      d.settlement >= 0
                        ? "var(--color-success)"
                        : "var(--color-alert)"
                    }
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  );
}

/* ---------------- DD view ---------------- */

function DDView({
  date_start,
  date_end,
}: {
  date_start: string;
  date_end: string;
}) {
  const dd = useAPI<DDContract[]>("/api/v1/market/dd", { date_start, date_end });
  const rows = dd.data?.data ?? [];

  return (
    <section className="rounded-xl border border-border bg-bg-card shadow-card overflow-hidden">
      <header className="p-4 border-b border-border">
        <h2 className="text-base font-semibold text-text-heading">
          Двосторонні договори
        </h2>
        <p className="text-xs text-text-muted">
          Активні контракти на двосторонньому ринку (ДД)
        </p>
      </header>
      {dd.isLoading ? (
        <div className="p-8 text-center text-sm text-text-muted">
          Завантаження…
        </div>
      ) : rows.length === 0 ? (
        <div className="p-8 text-center text-sm text-text-muted">
          Контрактів не знайдено.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-bg-subtle text-xs uppercase tracking-wide text-text-muted">
              <tr>
                <th className="px-4 py-2 text-left">№ контракту</th>
                <th className="px-4 py-2 text-left">Контрагент</th>
                <th className="px-4 py-2 text-left">Профіль</th>
                <th className="px-4 py-2 text-left">Період</th>
                <th className="px-4 py-2 text-right">Ціна</th>
                <th className="px-4 py-2 text-right">Обсяг</th>
                <th className="px-4 py-2 text-left">Статус</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((c, i) => (
                <tr
                  key={c.id}
                  className={clsx(
                    "border-t border-border",
                    i % 2 === 1 && "bg-bg-subtle/30",
                  )}
                >
                  <td className="px-4 py-2 font-mono text-[11px] text-text-body">
                    {c.contract_no}
                  </td>
                  <td className="px-4 py-2 text-text-heading">
                    {c.counterparty_name}
                    <div className="text-[10px] text-text-muted">
                      ЄДРПОУ {c.counterparty_edrpou}
                    </div>
                  </td>
                  <td className="px-4 py-2 text-text-body">{c.profile_type}</td>
                  <td className="px-4 py-2 text-xs text-text-muted">
                    {c.start_date} → {c.end_date}
                  </td>
                  <td className="px-4 py-2 text-right font-mono text-xs">
                    {c.price_uah_mwh
                      ? formatUAH(c.price_uah_mwh)
                      : c.price_formula ?? "—"}
                  </td>
                  <td className="px-4 py-2 text-right font-mono text-xs">
                    {formatNumber(c.total_volume_mwh, 1)} МВт·год
                  </td>
                  <td className="px-4 py-2">
                    <span
                      className={clsx(
                        "inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium",
                        c.status === "ACTIVE"
                          ? "bg-success/15 text-success"
                          : "bg-bg-subtle text-text-muted",
                      )}
                    >
                      {c.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
