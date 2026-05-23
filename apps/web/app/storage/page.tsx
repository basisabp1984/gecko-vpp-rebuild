"use client";

import { useEffect, useMemo } from "react";
import {
  Battery,
  Coins,
  Cpu,
  Repeat,
  Zap,
  ShieldAlert,
  Lightbulb,
  Activity,
} from "lucide-react";
import { useAPI } from "@/lib/api";
import { useTenantStore } from "@/lib/store";
import { TENANTS } from "@/lib/tenants";
import { KPITile } from "@/components/KPITile";
import { ScenarioCard } from "@/components/ScenarioCard";
import { PersonaAIHelper } from "@/components/PersonaAIHelper";
import {
  formatUAHCompact,
  formatPercent,
  formatNumber,
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

interface AssetMini {
  id: string;
  display_name: string;
  asset_class: string;
  capacity_mw: string;
  storage_capacity_mwh: string | null;
  region?: string;
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

function daysAgoISO(d: number): string {
  const date = new Date();
  date.setDate(date.getDate() - d);
  return date.toISOString().slice(0, 10);
}

function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

export default function StorageHomePage() {
  useEffect(() => {
    const { currentTenantId, setTenantId } = useTenantStore.getState();
    if (currentTenantId === TENANTS.producer.id) {
      setTenantId(TENANTS.storage.id);
    }
  }, []);

  const date_start = useMemo(() => daysAgoISO(7), []);
  const date_end = useMemo(() => todayISO(), []);

  const kpi = useAPI<PortfolioKPI>("/api/v1/ems/kpi/portfolio", {
    range: "week",
  });
  const assets = useAPI<AssetMini[]>("/api/v1/assets");
  const tele = useAPI<TelemetryRow[]>("/api/v1/dispatch/telemetry", {
    date_start: daysAgoISO(2),
    date_end,
  });
  const ancillary = useAPI<AncillaryRow[]>("/api/v1/market/ancillary", {
    date_start,
    date_end,
  });

  const uzeAssets = useMemo(
    () => (assets.data?.data ?? []).filter((a) => a.asset_class === "УЗЕ"),
    [assets.data],
  );

  /* Latest SOC per УЗЕ asset */
  const latestSocByAsset = useMemo(() => {
    const map = new Map<string, { soc: number; ts: string }>();
    for (const r of tele.data?.data ?? []) {
      if (!r.soc_pct) continue;
      const cur = map.get(r.asset_id);
      if (!cur || r.interval_start > cur.ts) {
        map.set(r.asset_id, {
          soc: parseFloat(r.soc_pct),
          ts: r.interval_start,
        });
      }
    }
    return map;
  }, [tele.data]);

  /* Estimate cycles across all УЗЕ assets in the 2-day window */
  const cyclesTotal = useMemo(() => {
    const byAsset = new Map<string, TelemetryRow[]>();
    for (const r of tele.data?.data ?? []) {
      const arr = byAsset.get(r.asset_id) ?? [];
      arr.push(r);
      byAsset.set(r.asset_id, arr);
    }
    let total = 0;
    for (const [, arr] of byAsset) {
      arr.sort((a, b) => a.interval_start.localeCompare(b.interval_start));
      let prev = 0;
      for (const r of arr) {
        const p = parseFloat(r.active_power_mw);
        if (prev <= 0 && p > 0) total += 0.5;
        if (prev >= 0 && p < 0) total += 0.5;
        prev = p;
      }
    }
    return total;
  }, [tele.data]);

  /* Ancillary revenue (sum) */
  const ancRevenue = useMemo(() => {
    return (ancillary.data?.data ?? []).reduce(
      (s, r) => s + parseFloat(r.revenue_energy_uah),
      0,
    );
  }, [ancillary.data]);

  const k = kpi.data?.data;

  return (
    <div className="flex flex-col gap-6">
      <header>
        <h1 className="text-2xl sm:text-3xl font-bold text-text-heading">
          Результати — Зберігання
        </h1>
        <p className="text-sm text-text-muted">
          ТОВ &laquo;Запоріжжя Сторідж&raquo; · станом на {formatDate(new Date())}
        </p>
      </header>

      <PersonaAIHelper persona="battery_coach" />

      {/* KPI grid */}
      <section className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-3">
        <KPITile
          label="Циклів (48 год)"
          value={formatNumber(cyclesTotal, 1)}
          icon={<Repeat size={18} />}
          sublabel={`по ${uzeAssets.length} УЗЕ`}
        />
        <KPITile
          label="Грн зароблено (арбітраж)"
          value={formatUAHCompact(k?.grn_earned_uah)}
          icon={<Coins size={18} />}
          sublabel="тиждень"
          tone="success"
        />
        <KPITile
          label="Грн з допослуг"
          value={formatUAHCompact(ancRevenue)}
          icon={<Zap size={18} />}
          sublabel="aFRR / mFRR · тиждень"
          tone="info"
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
          label="Кількість УЗЕ"
          value={String(uzeAssets.length)}
          icon={<Battery size={18} />}
          sublabel="у портфелі"
        />
      </section>

      {/* SOC grid */}
      <section className="rounded-xl border border-border bg-bg-card p-4 shadow-card">
        <header className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-base font-semibold text-text-heading">
              SOC — стан заряду по батареях
            </h2>
            <p className="text-xs text-text-muted">
              State of Charge у % від ємності МВт·год · останнє значення
              телеметрії
            </p>
          </div>
        </header>
        {assets.isLoading ? (
          <div className="h-[180px] flex items-center justify-center text-sm text-text-muted">
            Завантаження активів…
          </div>
        ) : uzeAssets.length === 0 ? (
          <div className="h-[180px] flex items-center justify-center text-sm text-text-muted">
            Активів УЗЕ немає.
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {uzeAssets.map((a) => {
              const v = latestSocByAsset.get(a.id);
              const soc = v?.soc ?? 0;
              return (
                <div
                  key={a.id}
                  className="flex flex-col items-center text-center gap-2 p-3 rounded-lg border border-border bg-bg-page"
                >
                  <MiniSOCArc value={soc} />
                  <div className="min-w-0 w-full">
                    <div className="text-sm font-medium text-text-heading truncate">
                      {a.display_name}
                    </div>
                    <div className="text-[11px] text-text-muted">
                      {a.capacity_mw} МВт · {a.storage_capacity_mwh ?? "—"}{" "}
                      МВт·год
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* Scenario cards */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <ScenarioCard
          title="Захист від відключення"
          description="УЗЕ перемикається на острівний режим за <100 мс. Резерв 30 хв при 80% SOC."
          icon={<ShieldAlert size={20} />}
          cta="Налаштувати схему"
          href="/storage/uze/"
        />
        <ScenarioCard
          title="Арбітражна можливість"
          description="Зарядка вночі (РДН 1200 грн/МВт·год) — розряд у пік (4500+ грн/МВт·год). 2-3 цикли на день."
          icon={<Lightbulb size={20} />}
          cta="Подивитись РДН"
          href="/storage/rynok/?market=arb"
        />
        <ScenarioCard
          title="Допоміжні послуги"
          description="aFRR/mFRR/РВЧ — оплачуваний резерв потужності + плата за активацію. Готовність вимагає 20% SOC headroom."
          icon={<Zap size={20} />}
          cta="Подати заявку на резерв"
          href="/storage/rynok/"
          tone="accent"
        />
      </section>
    </div>
  );
}

function MiniSOCArc({ value }: { value: number }) {
  const pct = Math.max(0, Math.min(100, value));
  const radius = 36;
  const stroke = 8;
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
        <span className="text-lg font-bold text-text-heading leading-none">
          {Math.round(pct)}
        </span>
        <span className="text-[9px] text-text-muted uppercase tracking-wide">
          %
        </span>
      </div>
    </div>
  );
}
