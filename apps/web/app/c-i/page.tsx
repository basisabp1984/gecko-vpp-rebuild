"use client";

import { useEffect, useMemo } from "react";
import {
  PiggyBank,
  Sun,
  Activity,
  Leaf,
  Cpu,
  ShieldAlert,
  Scale,
  Lightbulb,
} from "lucide-react";
import { useAPI } from "@/lib/api";
import { useTenantStore } from "@/lib/store";
import { TENANTS } from "@/lib/tenants";
import { KPITile } from "@/components/KPITile";
import { ScenarioCard } from "@/components/ScenarioCard";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
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

interface AssetMini {
  id: string;
  display_name: string;
  asset_class: string;
  capacity_mw: string;
  region?: string;
}

interface TelemetryRow {
  asset_id: string;
  date: string;
  hour: number;
  interval_start: string;
  active_power_mw: string;
  status: string;
}

function daysAgoISO(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

export default function CIHomePage() {
  /* ----- auto-bind tenant to C&I unless user already chose a non-producer one ----- */
  useEffect(() => {
    const { currentTenantId, setTenantId } = useTenantStore.getState();
    if (currentTenantId === TENANTS.producer.id) {
      setTenantId(TENANTS.ci.id);
    }
  }, []);

  const date_start = useMemo(() => daysAgoISO(7), []);
  const date_end = useMemo(() => todayISO(), []);

  const kpi = useAPI<PortfolioKPI>("/api/v1/ems/kpi/portfolio", {
    range: "week",
  });
  const assets = useAPI<AssetMini[]>("/api/v1/assets");

  /* identify the C&I consumer + on-site СЕС asset ids */
  const consumerAsset = useMemo(
    () =>
      (assets.data?.data ?? []).find(
        (a) => a.asset_class === "Споживач" || a.asset_class === "АктСпож",
      ),
    [assets.data],
  );
  const sesAsset = useMemo(
    () => (assets.data?.data ?? []).find((a) => a.asset_class === "СЕС"),
    [assets.data],
  );

  const consumption = useAPI<TelemetryRow[]>(
    consumerAsset ? "/api/v1/dispatch/telemetry" : null,
    consumerAsset
      ? { asset_id: consumerAsset.id, date_start, date_end }
      : undefined,
  );
  const ownGen = useAPI<TelemetryRow[]>(
    sesAsset ? "/api/v1/dispatch/telemetry" : null,
    sesAsset ? { asset_id: sesAsset.id, date_start, date_end } : undefined,
  );

  /* aggregate hourly consumption (abs of negative power) and own-gen (positive СЕС) */
  const chartData = useMemo(() => {
    const map = new Map<
      string,
      { ts: string; label: string; consumption: number; ownGen: number }
    >();
    for (const r of consumption.data?.data ?? []) {
      const key = r.interval_start;
      const d = new Date(r.interval_start);
      const label = `${String(d.getDate()).padStart(2, "0")}.${String(
        d.getMonth() + 1,
      ).padStart(2, "0")} ${String(d.getHours()).padStart(2, "0")}`;
      const v = Math.abs(parseFloat(r.active_power_mw));
      const cur = map.get(key) ?? {
        ts: key,
        label,
        consumption: 0,
        ownGen: 0,
      };
      cur.consumption = v;
      map.set(key, cur);
    }
    for (const r of ownGen.data?.data ?? []) {
      const key = r.interval_start;
      const d = new Date(r.interval_start);
      const label = `${String(d.getDate()).padStart(2, "0")}.${String(
        d.getMonth() + 1,
      ).padStart(2, "0")} ${String(d.getHours()).padStart(2, "0")}`;
      const v = Math.max(0, parseFloat(r.active_power_mw));
      const cur = map.get(key) ?? {
        ts: key,
        label,
        consumption: 0,
        ownGen: 0,
      };
      cur.ownGen = v;
      map.set(key, cur);
    }
    return Array.from(map.values()).sort((a, b) =>
      a.ts.localeCompare(b.ts),
    );
  }, [consumption.data, ownGen.data]);

  /* own-generation share — own / consumption (clamped) */
  const ownShare = useMemo(() => {
    const totalCons = chartData.reduce((s, p) => s + p.consumption, 0);
    const totalGen = chartData.reduce((s, p) => s + p.ownGen, 0);
    if (totalCons <= 0) return null;
    return Math.min(100, (totalGen / totalCons) * 100);
  }, [chartData]);

  /* sum consumption as "managed load" proxy (МВт·год) */
  const managedLoadMWh = useMemo(
    () => chartData.reduce((s, p) => s + p.consumption, 0),
    [chartData],
  );

  const k = kpi.data?.data;

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <header className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-text-heading">
            Результати — Бізнес
          </h1>
          <p className="text-sm text-text-muted">
            ПАТ &laquo;Дніпровий Завод&raquo; · тиждень до{" "}
            {formatDate(new Date())}
          </p>
        </div>
      </header>

      {/* KPI grid — C&I-tuned */}
      <section className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-3">
        <KPITile
          label="Грн зекономлено"
          value={formatUAHCompact(k?.grn_saved_uah)}
          icon={<PiggyBank size={18} />}
          sublabel="тиждень"
          tone="success"
        />
        <KPITile
          label="Своя генерація"
          value={ownShare !== null ? formatPercent(ownShare, 1) : "—"}
          icon={<Sun size={18} />}
          sublabel="дах-СЕС / попит"
          tone={
            ownShare !== null && ownShare >= 20 ? "success" : "warning"
          }
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
          label="CO₂ уникнено"
          value={formatTonnes(k?.co2_avoided_tn)}
          icon={<Leaf size={18} />}
          sublabel="тиждень"
          tone="success"
        />
        <KPITile
          label="Навантаження керовано"
          value={`${formatNumber(managedLoadMWh, 1)} МВт·год`}
          icon={<Activity size={18} />}
          sublabel="спожито"
        />
      </section>

      {/* Scenario cards */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <ScenarioCard
          title="Захист від відключення"
          description="Резервна СЕС + УЗЕ дозволяють витримати знеструмлення зовнішньої мережі без зупинки виробництва."
          icon={<ShieldAlert size={20} />}
          cta="Підготувати план"
          href="/c-i/aktyvy/"
        />
        <ScenarioCard
          title="Захист від небалансу"
          description="Утримання заявок у межах ±5% від факту — БР-штрафи не виникають. Уточнюйте прогноз споживання щогодини."
          icon={<Scale size={20} />}
          cta="Налаштувати прогноз"
          href="/c-i/prognozy/"
        />
        <ScenarioCard
          title="Арбітражна можливість"
          description="Перенесіть енергоємні процеси на нічні години — економія на тарифі за період пікового РДН."
          icon={<Lightbulb size={20} />}
          cta="Подивитись РДН"
          href="/c-i/rynok/"
          tone="accent"
        />
      </section>

      {/* Consumption + own-gen chart */}
      <section className="rounded-xl border border-border bg-bg-card p-4 shadow-card">
        <header className="flex items-center justify-between mb-3">
          <div>
            <h2 className="text-base font-semibold text-text-heading">
              Споживання та своя генерація — 7 днів
            </h2>
            <p className="text-xs text-text-muted">
              МВт за годину · {consumerAsset?.display_name ?? "споживач"} проти
              {" "}
              {sesAsset?.display_name ?? "дах-СЕС"}
            </p>
          </div>
        </header>
        {consumption.isLoading || ownGen.isLoading ? (
          <div className="h-[320px] flex items-center justify-center text-sm text-text-muted">
            Завантаження телеметрії…
          </div>
        ) : chartData.length === 0 ? (
          <div className="h-[320px] flex items-center justify-center text-sm text-text-muted">
            Немає даних за вибраний період.
          </div>
        ) : (
          <div style={{ width: "100%", height: 320 }}>
            <ResponsiveContainer>
              <LineChart
                data={chartData}
                margin={{ top: 10, right: 24, left: 0, bottom: 8 }}
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
                  interval="preserveStartEnd"
                  minTickGap={32}
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
                    fontSize: 12,
                  }}
                  formatter={(v) => {
                    const n =
                      typeof v === "number" ? v : parseFloat(String(v));
                    return Number.isFinite(n)
                      ? `${formatNumber(n, 2)} МВт`
                      : "—";
                  }}
                />
                <Legend
                  wrapperStyle={{ fontSize: 11, paddingTop: 8 }}
                  iconType="line"
                />
                <Line
                  type="monotone"
                  dataKey="consumption"
                  name="Споживання"
                  stroke="var(--color-info)"
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive={false}
                />
                <Line
                  type="monotone"
                  dataKey="ownGen"
                  name="Своя генерація"
                  stroke="var(--color-success)"
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </section>
    </div>
  );
}
