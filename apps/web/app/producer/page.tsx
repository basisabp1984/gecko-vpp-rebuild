"use client";

import { useMemo } from "react";
import {
  Coins,
  PiggyBank,
  Activity,
  Leaf,
  Cpu,
  Layers,
  AlertTriangle,
} from "lucide-react";
import { useAPI } from "@/lib/api";
import { KPITile } from "@/components/KPITile";
import { HourlyChart, type HourlyPoint } from "@/components/HourlyChart";
import { OptimiseModal } from "@/components/OptimiseModal";
import {
  formatUAHCompact,
  formatPercent,
  formatNumber,
  formatTonnes,
  formatDate,
} from "@/lib/format";

interface PortfolioKPI {
  range: string;
  grn_saved_uah: string;
  grn_earned_uah: string;
  revenue_uah: string;
  imbalance_mwh: string;
  co2_avoided_tn: string;
  availability_pct: string;
  asset_count: number;
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

interface RegulatoryEvent {
  id: number;
  issuer: string;
  act_type: string;
  act_number: string;
  issued_at: string;
  effective_at: string;
  title: string;
  category: string;
  severity: string;
  summary: string;
}

function daysAgoISO(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

export default function ProducerHomePage() {
  const date_start = useMemo(() => daysAgoISO(7), []);
  const date = useMemo(() => todayISO(), []);

  const kpi = useAPI<PortfolioKPI>("/api/v1/ems/kpi/portfolio", { range: "week" });
  const rdn = useAPI<RDNPoint[]>("/api/v1/market/rdn", { date_start });
  const events = useAPI<RegulatoryEvent[]>("/api/v1/regulatory/events");

  const chartData: HourlyPoint[] = useMemo(() => {
    const pts = rdn.data?.data ?? [];
    return pts.map((p) => {
      const d = new Date(p.interval_start);
      const label = `${String(d.getDate()).padStart(2, "0")}.${String(
        d.getMonth() + 1,
      ).padStart(2, "0")} ${String(d.getHours()).padStart(2, "0")}:00`;
      return {
        ts: p.interval_start,
        label,
        value: parseFloat(p.price_uah_mwh),
        is_capped: p.is_capped,
      };
    });
  }, [rdn.data]);

  const chartCap = useMemo(() => {
    const pts = rdn.data?.data ?? [];
    const cappedPoint = pts.find(
      (p) => p.is_capped && p.cap_uah_mwh,
    );
    if (cappedPoint?.cap_uah_mwh) return parseFloat(cappedPoint.cap_uah_mwh);
    // Fallback: max value when no explicit cap
    return null;
  }, [rdn.data]);

  const k = kpi.data?.data;
  const recent = events.data?.data?.slice(0, 5) ?? [];

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <header className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-text-heading">
            Кабінет виробника
          </h1>
          <p className="text-sm text-text-muted">
            Результати за тиждень · станом на {formatDate(new Date())}
          </p>
        </div>
        <OptimiseModal date={date} scenario="arbitrage" />
      </header>

      {/* KPI grid */}
      <section className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3">
        <KPITile
          label="Грн зароблено"
          value={formatUAHCompact(k?.grn_earned_uah)}
          icon={<Coins size={18} />}
          sublabel="тиждень"
          tone="success"
        />
        <KPITile
          label="Грн зекономлено"
          value={formatUAHCompact(k?.grn_saved_uah)}
          icon={<PiggyBank size={18} />}
          sublabel="тиждень"
        />
        <KPITile
          label="Небаланси"
          value={
            k ? `${formatNumber(k.imbalance_mwh, 1)} МВт·год` : "—"
          }
          icon={<Activity size={18} />}
          sublabel="чисті"
          tone={
            k && parseFloat(k.imbalance_mwh) >= 0 ? "success" : "warning"
          }
        />
        <KPITile
          label="CO₂ уникнено"
          value={formatTonnes(k?.co2_avoided_tn)}
          icon={<Leaf size={18} />}
          sublabel="тиждень"
          tone="success"
        />
        <KPITile
          label="Доступність"
          value={formatPercent(k?.availability_pct, 1)}
          icon={<Cpu size={18} />}
          sublabel="середня"
          tone={
            k && parseFloat(k.availability_pct) >= 95 ? "success" : "warning"
          }
        />
        <KPITile
          label="Активи"
          value={k ? k.asset_count : "—"}
          icon={<Layers size={18} />}
          sublabel="у портфелі"
        />
      </section>

      {/* Main chart + alerts */}
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 rounded-xl border border-border bg-bg-card p-4 shadow-card">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h2 className="text-base font-semibold text-text-heading">
                Ціна РДН — останні 7 днів
              </h2>
              <p className="text-xs text-text-muted">
                грн/МВт·год · червоні точки — годинні кепи
              </p>
            </div>
          </div>
          {rdn.isLoading ? (
            <div className="h-[280px] flex items-center justify-center text-sm text-text-muted">
              Завантаження даних РДН…
            </div>
          ) : rdn.isError ? (
            <div className="h-[280px] flex items-center justify-center text-sm text-alert">
              Помилка: {rdn.error.message}
            </div>
          ) : (
            <HourlyChart data={chartData} cap={chartCap} yLabel="грн/МВт·год" />
          )}
        </div>

        <aside className="rounded-xl border border-border bg-bg-card p-4 shadow-card">
          <h2 className="text-base font-semibold text-text-heading mb-3 flex items-center gap-2">
            <AlertTriangle size={16} className="text-warning" />
            Регуляторні події
          </h2>
          {events.isLoading ? (
            <div className="text-sm text-text-muted py-4 text-center">
              Завантаження…
            </div>
          ) : recent.length === 0 ? (
            <div className="text-sm text-text-muted py-4 text-center">
              Нових подій немає.
            </div>
          ) : (
            <ul className="space-y-3">
              {recent.map((e) => (
                <li
                  key={e.id}
                  className="border-l-2 border-accent pl-3 py-1"
                >
                  <div className="text-xs text-text-muted">
                    {e.issuer} · {e.act_type} {e.act_number}
                  </div>
                  <div className="text-sm font-medium text-text-heading leading-snug">
                    {e.title}
                  </div>
                  <div className="text-xs text-text-muted mt-1">
                    Чинно з {formatDate(e.effective_at)}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </aside>
      </section>
    </div>
  );
}
