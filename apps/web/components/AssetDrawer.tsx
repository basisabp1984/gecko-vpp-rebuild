"use client";

import { useEffect, useMemo } from "react";
import { X, MapPin, Zap, Battery, Calendar, Fingerprint } from "lucide-react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { useAPI } from "@/lib/api";
import { formatNumber, formatDate } from "@/lib/format";

export interface AssetSummary {
  id: string;
  display_name: string;
  asset_class: string;
  technology_type?: string;
  capacity_mw: string;
  storage_capacity_mwh?: string | null;
  region?: string;
  resource_eic: string;
  metering_eic?: string;
  commissioned_on?: string;
  status: string;
}

interface TelemetryRow {
  asset_id: string;
  date: string;
  hour: number;
  interval_start: string;
  active_power_mw: string;
  soc_pct?: string | null;
  availability_pct?: string | null;
  status: string;
}

function daysAgoISO(d: number): string {
  const date = new Date();
  date.setDate(date.getDate() - d);
  return date.toISOString().slice(0, 10);
}

export function AssetDrawer({
  asset,
  onClose,
}: {
  asset: AssetSummary | null;
  onClose: () => void;
}) {
  const open = Boolean(asset);

  // Block body scroll while open
  useEffect(() => {
    if (!open) return;
    const orig = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = orig;
    };
  }, [open]);

  // ESC closes
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  const date_start = useMemo(() => daysAgoISO(3), [asset?.id]);
  const date_end = useMemo(() => daysAgoISO(1), [asset?.id]);

  const tele = useAPI<TelemetryRow[]>(
    asset ? `/api/v1/assets/${asset.id}/telemetry` : null,
    { date_start, date_end },
  );

  const chartData = useMemo(() => {
    const rows = tele.data?.data ?? [];
    return rows.slice(0, 72).map((r) => {
      const d = new Date(r.interval_start);
      const label = `${String(d.getDate()).padStart(2, "0")}.${String(
        d.getMonth() + 1,
      ).padStart(2, "0")} ${String(d.getHours()).padStart(2, "0")}`;
      return {
        label,
        power: parseFloat(r.active_power_mw),
        soc: r.soc_pct ? parseFloat(r.soc_pct) : null,
      };
    });
  }, [tele.data]);

  if (!open || !asset) return null;

  return (
    <div className="fixed inset-0 z-50">
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />
      <aside
        role="dialog"
        aria-modal="true"
        aria-label={`Активи — ${asset.display_name}`}
        className="absolute right-0 top-0 h-full w-full sm:w-[480px] lg:w-[560px] bg-bg-card border-l border-border shadow-elevated flex flex-col"
      >
        <header className="flex items-start justify-between gap-3 p-5 border-b border-border">
          <div className="min-w-0">
            <div className="text-xs uppercase tracking-wide text-text-muted">
              {asset.asset_class} · {asset.region}
            </div>
            <h2 className="text-lg font-semibold text-text-heading mt-0.5 truncate">
              {asset.display_name}
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-md hover:bg-bg-subtle text-text-muted hover:text-text-body"
            aria-label="Закрити панель"
          >
            <X size={18} />
          </button>
        </header>

        <div className="flex-1 overflow-y-auto p-5 space-y-5">
          {/* Specs */}
          <section className="grid grid-cols-2 gap-3">
            <Spec
              icon={<Zap size={14} />}
              label="Потужність"
              value={`${formatNumber(asset.capacity_mw, 1)} МВт`}
            />
            {asset.storage_capacity_mwh && (
              <Spec
                icon={<Battery size={14} />}
                label="Ємність"
                value={`${formatNumber(asset.storage_capacity_mwh, 1)} МВт·год`}
              />
            )}
            <Spec
              icon={<MapPin size={14} />}
              label="Регіон"
              value={asset.region ?? "—"}
            />
            <Spec
              icon={<Calendar size={14} />}
              label="Введено в експлуатацію"
              value={
                asset.commissioned_on
                  ? formatDate(asset.commissioned_on)
                  : "—"
              }
            />
            <Spec
              icon={<Fingerprint size={14} />}
              label="Resource EIC"
              value={
                <span className="font-mono text-[11px]">
                  {asset.resource_eic}
                </span>
              }
            />
            <Spec
              label="Статус"
              value={
                <span
                  className={
                    asset.status === "active"
                      ? "text-success font-medium"
                      : "text-warning font-medium"
                  }
                >
                  {asset.status === "active" ? "активний" : asset.status}
                </span>
              }
            />
          </section>

          {/* Telemetry chart */}
          <section className="rounded-xl border border-border bg-bg-page p-4">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-semibold text-text-heading">
                Телеметрія — активна потужність
              </h3>
              <span className="text-xs text-text-muted">останні 3 дні</span>
            </div>
            {tele.isLoading ? (
              <div className="h-[200px] flex items-center justify-center text-sm text-text-muted">
                Завантаження телеметрії…
              </div>
            ) : tele.isError ? (
              <div className="h-[200px] flex items-center justify-center text-sm text-alert">
                {tele.error.message}
              </div>
            ) : chartData.length === 0 ? (
              <div className="h-[200px] flex items-center justify-center text-sm text-text-muted">
                Дані телеметрії відсутні.
              </div>
            ) : (
              <div style={{ width: "100%", height: 200 }}>
                <ResponsiveContainer>
                  <LineChart
                    data={chartData}
                    margin={{ top: 4, right: 8, left: -16, bottom: 4 }}
                  >
                    <CartesianGrid
                      stroke="var(--color-border)"
                      strokeDasharray="3 3"
                      vertical={false}
                    />
                    <XAxis
                      dataKey="label"
                      stroke="var(--color-text-muted)"
                      tick={{ fontSize: 10 }}
                      interval="preserveStartEnd"
                      minTickGap={28}
                    />
                    <YAxis
                      stroke="var(--color-text-muted)"
                      tick={{ fontSize: 10 }}
                    />
                    <Tooltip
                      contentStyle={{
                        background: "var(--color-bg-card)",
                        border: "1px solid var(--color-border)",
                        borderRadius: 8,
                        fontSize: 11,
                      }}
                      formatter={(v: number) => [
                        `${formatNumber(v, 2)} МВт`,
                        "потужність",
                      ]}
                    />
                    <Line
                      type="monotone"
                      dataKey="power"
                      stroke="var(--color-accent)"
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

        <footer className="border-t border-border p-4 bg-bg-subtle flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg border border-border bg-bg-card text-sm hover:border-accent"
          >
            Закрити
          </button>
        </footer>
      </aside>
    </div>
  );
}

function Spec({
  icon,
  label,
  value,
}: {
  icon?: React.ReactNode;
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border border-border bg-bg-card p-2.5">
      <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wide text-text-muted">
        {icon}
        {label}
      </div>
      <div className="text-sm text-text-heading font-medium mt-0.5 break-words">
        {value}
      </div>
    </div>
  );
}
