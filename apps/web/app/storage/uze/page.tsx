"use client";

import { useEffect, useMemo, useState } from "react";
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
import { Battery, Repeat, TrendingUp, Coins, Clock } from "lucide-react";
import { useAPI } from "@/lib/api";
import { useTenantStore } from "@/lib/store";
import { TENANTS } from "@/lib/tenants";
import { formatNumber } from "@/lib/format";

interface AssetMini {
  id: string;
  display_name: string;
  asset_class: string;
  capacity_mw: string;
  storage_capacity_mwh: string | null;
  region: string;
}

interface TelemetryRow {
  asset_id: string;
  date: string;
  hour: number;
  interval_start: string;
  active_power_mw: string;
  soc_pct?: string | null;
  status: string;
}

interface SetpointRow {
  id: number;
  asset_id: string;
  issued_at: string;
  effective_from: string;
  effective_to: string;
  target_power_mw: string;
  target_soc_pct?: string | null;
  reason: string;
  issued_by: string;
  state: string;
}

function daysAgoISO(d: number): string {
  const date = new Date();
  date.setDate(date.getDate() - d);
  return date.toISOString().slice(0, 10);
}

function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

export default function StorageUzePage() {
  useEffect(() => {
    const { currentTenantId, setTenantId } = useTenantStore.getState();
    if (currentTenantId === TENANTS.producer.id) {
      setTenantId(TENANTS.storage.id);
    }
  }, []);

  const assets = useAPI<AssetMini[]>("/api/v1/assets");

  const uzeAssets = useMemo(
    () => (assets.data?.data ?? []).filter((a) => a.asset_class === "УЗЕ"),
    [assets.data],
  );

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const current = selectedId
    ? uzeAssets.find((a) => a.id === selectedId)
    : uzeAssets[0];

  const date_start = useMemo(() => daysAgoISO(2), []);
  const date_end = useMemo(() => todayISO(), []);

  const tele = useAPI<TelemetryRow[]>(
    current ? `/api/v1/assets/${current.id}/telemetry` : null,
    { date_start, date_end },
  );

  const setpoints = useAPI<SetpointRow[]>(
    current ? "/api/v1/dispatch/setpoints" : null,
    current ? { asset_id: current.id } : undefined,
  );

  const rows = tele.data?.data ?? [];

  const latestSoc = useMemo(() => {
    for (let i = rows.length - 1; i >= 0; i--) {
      if (rows[i].soc_pct) {
        return parseFloat(rows[i].soc_pct!);
      }
    }
    return null;
  }, [rows]);

  const scheduleData = useMemo(() => {
    return rows.slice(-24).map((r) => {
      const d = new Date(r.interval_start);
      return {
        label: `${String(d.getHours()).padStart(2, "0")}:00`,
        power: parseFloat(r.active_power_mw),
        soc: r.soc_pct ? parseFloat(r.soc_pct) : null,
      };
    });
  }, [rows]);

  const cycles = useMemo(() => {
    let prev = 0;
    let cyc = 0;
    for (const r of rows) {
      const p = parseFloat(r.active_power_mw);
      if (prev <= 0 && p > 0) cyc += 0.5;
      if (prev >= 0 && p < 0) cyc += 0.5;
      prev = p;
    }
    return cyc;
  }, [rows]);

  const arbitrage = useMemo(() => {
    const dischargeMWh = rows
      .filter((r) => parseFloat(r.active_power_mw) > 0)
      .reduce((s, r) => s + parseFloat(r.active_power_mw), 0);
    const chargeMWh = rows
      .filter((r) => parseFloat(r.active_power_mw) < 0)
      .reduce((s, r) => s + Math.abs(parseFloat(r.active_power_mw)), 0);
    const grnEarned = (dischargeMWh - chargeMWh) * 3500;
    return { dischargeMWh, chargeMWh, grnEarned, windows: Math.floor(cycles) };
  }, [rows, cycles]);

  /* Upcoming schedule from setpoints (sorted by effective_from) */
  const upcoming = useMemo(() => {
    const rows = setpoints.data?.data ?? [];
    return [...rows]
      .sort((a, b) =>
        a.effective_from.localeCompare(b.effective_from),
      )
      .slice(-24)
      .map((r) => {
        const d = new Date(r.effective_from);
        return {
          ts: r.effective_from,
          time: `${String(d.getHours()).padStart(2, "0")}:00`,
          date: `${String(d.getDate()).padStart(2, "0")}.${String(
            d.getMonth() + 1,
          ).padStart(2, "0")}`,
          power: parseFloat(r.target_power_mw),
          state: r.state,
          reason: r.reason,
        };
      });
  }, [setpoints.data]);

  return (
    <div className="flex flex-col gap-5">
      <header>
        <h1 className="text-2xl sm:text-3xl font-bold text-text-heading">
          УЗЕ · операції зі зберіганням
        </h1>
        <p className="text-sm text-text-muted">
          SOC (State of Charge), цикли заряд/розряд, арбітражний P&L, наступні
          вікна диспетчеризації.
        </p>
      </header>

      {assets.isLoading ? (
        <div className="p-8 text-center text-sm text-text-muted">
          Завантаження активів…
        </div>
      ) : uzeAssets.length === 0 ? (
        <div className="rounded-xl border border-border bg-bg-card p-10 text-center">
          <Battery size={36} className="mx-auto mb-3 text-text-muted" />
          <h2 className="text-lg font-semibold text-text-heading">
            УЗЕ-активи відсутні
          </h2>
          <p className="text-sm text-text-muted mt-1">
            У портфелі немає установок зберігання енергії.
          </p>
        </div>
      ) : (
        <>
          {/* Asset picker */}
          <div className="flex flex-wrap gap-2">
            {uzeAssets.map((a) => {
              const isActive = (current?.id ?? uzeAssets[0]?.id) === a.id;
              return (
                <button
                  key={a.id}
                  type="button"
                  onClick={() => setSelectedId(a.id)}
                  className={clsx(
                    "px-3 py-1.5 rounded-full text-xs font-medium border transition-colors",
                    isActive
                      ? "border-accent bg-accent text-text-inverse"
                      : "border-border bg-bg-card text-text-muted hover:border-accent",
                  )}
                >
                  {a.display_name}
                </button>
              );
            })}
          </div>

          {!current ? (
            <div className="p-8 text-center text-sm text-text-muted">
              Оберіть актив.
            </div>
          ) : (
            <>
              {/* Hero */}
              <section className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                <div className="lg:col-span-1 rounded-xl border border-border bg-bg-card shadow-card p-5 flex flex-col items-center justify-center">
                  <SOCArc value={latestSoc ?? 0} />
                  <h3 className="mt-4 text-base font-semibold text-text-heading text-center">
                    {current.display_name}
                  </h3>
                  <p className="text-xs text-text-muted text-center">
                    {current.capacity_mw} МВт ·{" "}
                    {current.storage_capacity_mwh ?? "—"} МВт·год ·{" "}
                    {current.region}
                  </p>
                </div>

                <div className="lg:col-span-2 grid grid-cols-1 sm:grid-cols-2 gap-3 content-start">
                  <StatCard
                    icon={<Repeat size={18} />}
                    label="Циклів (вікно)"
                    value={formatNumber(cycles, 1)}
                    hint="зарядка↔розряд"
                  />
                  <StatCard
                    icon={<TrendingUp size={18} />}
                    label="Розряджено"
                    value={`${formatNumber(arbitrage.dischargeMWh, 1)} МВт·год`}
                    hint="за період"
                  />
                  <StatCard
                    icon={<Battery size={18} />}
                    label="Заряджено"
                    value={`${formatNumber(arbitrage.chargeMWh, 1)} МВт·год`}
                    hint="за період"
                  />
                  <StatCard
                    icon={<Coins size={18} />}
                    label="Арбітражний P&L"
                    value={`${formatNumber(arbitrage.grnEarned, 0)} грн`}
                    hint={`${arbitrage.windows} вікон`}
                    tone={arbitrage.grnEarned >= 0 ? "success" : "alert"}
                  />
                </div>
              </section>

              {/* Schedule chart */}
              <section className="rounded-xl border border-border bg-bg-card shadow-card p-4">
                <header className="flex items-center justify-between mb-3">
                  <h2 className="text-base font-semibold text-text-heading">
                    Графік заряд/розряд · 24 години
                  </h2>
                  <span className="text-xs text-text-muted">
                    + розряд (продаж) · − заряд (купівля)
                  </span>
                </header>
                {tele.isLoading ? (
                  <div className="h-[320px] flex items-center justify-center text-sm text-text-muted">
                    Завантаження телеметрії…
                  </div>
                ) : scheduleData.length === 0 ? (
                  <div className="h-[320px] flex items-center justify-center text-sm text-text-muted">
                    Немає даних.
                  </div>
                ) : (
                  <div style={{ width: "100%", height: 320 }}>
                    <ResponsiveContainer>
                      <BarChart
                        data={scheduleData}
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
                          formatter={(v, name) => {
                            const n =
                              typeof v === "number"
                                ? v
                                : parseFloat(String(v));
                            if (name === "power")
                              return [`${formatNumber(n, 2)} МВт`, "потужність"];
                            if (name === "soc")
                              return [`${formatNumber(n, 1)}%`, "SOC"];
                            return [v, name];
                          }}
                        />
                        <Bar dataKey="power" isAnimationActive={false}>
                          {scheduleData.map((d, i) => (
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

              {/* Upcoming dispatch windows */}
              <section className="rounded-xl border border-border bg-bg-card shadow-card overflow-hidden">
                <header className="p-4 border-b border-border flex items-center gap-2">
                  <Clock size={16} className="text-accent" />
                  <h2 className="text-base font-semibold text-text-heading">
                    Найближчі 24 години — вікна заряд/розряд
                  </h2>
                </header>
                {setpoints.isLoading ? (
                  <div className="p-8 text-center text-sm text-text-muted">
                    Завантаження…
                  </div>
                ) : upcoming.length === 0 ? (
                  <div className="p-8 text-center text-sm text-text-muted">
                    Запланованих setpoint-ів немає.
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead className="bg-bg-subtle text-xs uppercase tracking-wide text-text-muted">
                        <tr>
                          <th className="px-4 py-2 text-left">Час</th>
                          <th className="px-4 py-2 text-left">Дія</th>
                          <th className="px-4 py-2 text-right">Потужність</th>
                          <th className="px-4 py-2 text-left">Причина</th>
                          <th className="px-4 py-2 text-left">Стан</th>
                        </tr>
                      </thead>
                      <tbody>
                        {upcoming.map((u, i) => (
                          <tr
                            key={`${u.ts}-${i}`}
                            className={clsx(
                              "border-t border-border",
                              i % 2 === 1 && "bg-bg-subtle/30",
                            )}
                          >
                            <td className="px-4 py-2 font-mono text-xs text-text-body">
                              {u.date} · {u.time}
                            </td>
                            <td className="px-4 py-2">
                              <ActionBadge power={u.power} />
                            </td>
                            <td className="px-4 py-2 text-right font-mono text-xs text-text-body">
                              {formatNumber(Math.abs(u.power), 2)} МВт
                            </td>
                            <td className="px-4 py-2 text-text-muted text-xs">
                              {u.reason}
                            </td>
                            <td className="px-4 py-2 text-text-muted text-xs">
                              {u.state}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </section>
            </>
          )}
        </>
      )}
    </div>
  );
}

function SOCArc({ value }: { value: number }) {
  const pct = Math.max(0, Math.min(100, value));
  const radius = 70;
  const stroke = 12;
  const norm = radius - stroke / 2;
  const circumference = 2 * Math.PI * norm;
  const arcLen = (circumference * 3) / 4;
  const offset = arcLen - (pct / 100) * arcLen;

  const tone =
    pct < 20
      ? "var(--color-alert)"
      : pct < 50
        ? "var(--color-warning)"
        : "var(--color-success)";

  return (
    <div className="relative">
      <svg
        width={radius * 2 + stroke}
        height={radius * 2 + stroke}
        viewBox={`0 0 ${radius * 2 + stroke} ${radius * 2 + stroke}`}
        style={{ transform: "rotate(135deg)" }}
        aria-label="SOC"
      >
        <circle
          cx={radius + stroke / 2}
          cy={radius + stroke / 2}
          r={norm}
          fill="none"
          stroke="var(--color-border)"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${arcLen} ${circumference}`}
        />
        <circle
          cx={radius + stroke / 2}
          cy={radius + stroke / 2}
          r={norm}
          fill="none"
          stroke={tone}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${arcLen} ${circumference}`}
          strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 600ms ease" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-[10px] uppercase tracking-wide text-text-muted">
          SOC
        </span>
        <span className="text-3xl font-bold text-text-heading">
          {formatNumber(pct, 0)}
          <span className="text-base">%</span>
        </span>
      </div>
    </div>
  );
}

function StatCard({
  icon,
  label,
  value,
  hint,
  tone = "default",
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  hint?: string;
  tone?: "default" | "success" | "alert";
}) {
  const toneCls =
    tone === "success"
      ? "text-success"
      : tone === "alert"
        ? "text-alert"
        : "text-text-heading";
  return (
    <div className="rounded-xl border border-border bg-bg-card p-4 shadow-card">
      <div className="flex items-center justify-between text-text-muted text-xs uppercase tracking-wide">
        <span>{label}</span>
        <span className="text-accent-deep">{icon}</span>
      </div>
      <div className={clsx("mt-1.5 text-xl font-bold", toneCls)}>{value}</div>
      {hint && <div className="text-xs text-text-muted mt-0.5">{hint}</div>}
    </div>
  );
}

function ActionBadge({ power }: { power: number }) {
  if (power > 0.05) {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-success/15 text-success">
        Розряд
      </span>
    );
  }
  if (power < -0.05) {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-info/15 text-info">
        Заряд
      </span>
    );
  }
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-bg-subtle text-text-muted">
      Утримання
    </span>
  );
}
