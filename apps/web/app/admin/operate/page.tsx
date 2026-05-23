"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  Cpu,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  Activity,
  Zap,
} from "lucide-react";
import { fetchAPI, ApiError } from "@/lib/api";
import { KPITile } from "@/components/KPITile";
import { TENANT_LIST, type Tenant } from "@/lib/tenants";
import { formatNumber } from "@/lib/format";

interface OperationsRow {
  tenant_id: string;
  code: string;
  setpoints_24h: number;
  telemetry_rows_24h: number;
  avg_availability_pct: string;
}

interface OperationsPayload {
  rows: OperationsRow[];
}

interface SetpointRow {
  id: number;
  asset_id?: number;
  asset_code?: string;
  effective_from: string;
  effective_to?: string | null;
  target_power_mw: string;
  target_soc_pct?: string | null;
  reason?: string | null;
  state?: string | null;
}

interface OptimiseResult {
  run_id: number;
  scenario: string;
  recommendations: Array<{ asset_id?: string | number; hour: number; action: string; mw: string | number }>;
  uplift_uah?: string | number;
  confidence?: number | string;
}

function todayISO() {
  return new Date().toISOString().slice(0, 10);
}

export default function AdminOperatePage() {
  const ops = useQuery<{ data: OperationsPayload }, ApiError>({
    queryKey: ["admin", "operations"],
    queryFn: () => fetchAPI<OperationsPayload>("/api/v1/admin/operations"),
    staleTime: 30_000,
  });

  // Fetch recent setpoints per tenant (we add tenantId override per request)
  const setpoints = useQuery<
    Array<{ tenant: Tenant; rows: SetpointRow[] }>,
    ApiError
  >({
    queryKey: ["admin", "recent-setpoints"],
    queryFn: async () => {
      const results = await Promise.all(
        TENANT_LIST.map(async (t) => {
          try {
            const res = await fetchAPI<SetpointRow[]>(
              "/api/v1/dispatch/setpoints",
              { tenantId: t.id, query: { limit: 50 } },
            );
            return { tenant: t, rows: res.data ?? [] };
          } catch {
            return { tenant: t, rows: [] };
          }
        }),
      );
      return results;
    },
    staleTime: 30_000,
  });

  const allSetpoints = useMemo(() => {
    const flat: Array<SetpointRow & { tenant: Tenant }> = [];
    for (const block of setpoints.data ?? []) {
      for (const r of block.rows.slice(0, 20)) {
        flat.push({ ...r, tenant: block.tenant });
      }
    }
    flat.sort(
      (a, b) =>
        new Date(b.effective_from).getTime() -
        new Date(a.effective_from).getTime(),
    );
    return flat.slice(0, 30);
  }, [setpoints.data]);

  const totals = useMemo(() => {
    const rows = ops.data?.data.rows ?? [];
    return rows.reduce(
      (acc, r) => {
        acc.setpoints += r.setpoints_24h;
        acc.telemetry += r.telemetry_rows_24h;
        acc.availabilitySum += parseFloat(r.avg_availability_pct);
        acc.tenantCount += 1;
        return acc;
      },
      { setpoints: 0, telemetry: 0, availabilitySum: 0, tenantCount: 0 },
    );
  }, [ops.data]);

  const avgAvail =
    totals.tenantCount > 0 ? totals.availabilitySum / totals.tenantCount : 0;

  const [runLog, setRunLog] = useState<
    Array<{
      tenant: Tenant;
      status: "running" | "ok" | "fail";
      message: string;
    }>
  >([]);

  const portfolioRun = useMutation<
    Array<{ tenant: Tenant; result?: OptimiseResult; error?: string }>,
    Error,
    void
  >({
    mutationFn: async () => {
      const date = todayISO();
      setRunLog(
        TENANT_LIST.map((t) => ({
          tenant: t,
          status: "running",
          message: "Запит надіслано…",
        })),
      );
      const results = await Promise.all(
        TENANT_LIST.map(async (t) => {
          try {
            const res = await fetchAPI<OptimiseResult>(
              "/api/v1/ems/optimise",
              {
                method: "POST",
                body: { scenario: "day_ahead", date },
                tenantId: t.id,
              },
            );
            return { tenant: t, result: res.data };
          } catch (err) {
            return {
              tenant: t,
              error: err instanceof Error ? err.message : String(err),
            };
          }
        }),
      );
      setRunLog(
        results.map((r) => ({
          tenant: r.tenant,
          status: r.error ? "fail" : "ok",
          message: r.error
            ? r.error
            : `Run #${r.result?.run_id} · ${r.result?.recommendations.length ?? 0} рекомендацій`,
        })),
      );
      return results;
    },
  });

  return (
    <div className="flex flex-col gap-6">
      <header>
        <h1 className="text-2xl sm:text-3xl font-bold text-text-heading flex items-center gap-2">
          <Cpu size={22} className="text-accent-deep" /> Operate · крос-тенантний диспетч
        </h1>
        <p className="text-sm text-text-muted">
          Зведений стан останніх 24 годин і пакетна оптимізація портфеля.
        </p>
      </header>

      {/* KPI */}
      <section className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <KPITile
          label="Setpoints 24h"
          value={ops.isLoading ? "—" : totals.setpoints}
          sublabel="усього виписано"
          icon={<Zap size={16} />}
        />
        <KPITile
          label="Телеметрія 24h"
          value={ops.isLoading ? "—" : totals.telemetry}
          sublabel="точок"
          icon={<Activity size={16} />}
        />
        <KPITile
          label="Сер. доступність"
          value={ops.isLoading ? "—" : `${formatNumber(avgAvail, 1)}%`}
          sublabel="по тенантах"
          tone={avgAvail >= 95 ? "success" : "warning"}
        />
        <KPITile
          label="Тенантів on-line"
          value={ops.isLoading ? "—" : totals.tenantCount}
          sublabel="у відстеженні"
        />
      </section>

      {/* Portfolio-wide optimisation */}
      <section className="rounded-xl border border-border bg-bg-card p-5 shadow-card">
        <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3 mb-4">
          <div>
            <h2 className="text-base font-semibold text-text-heading">
              Portfolio-wide optimisation
            </h2>
            <p className="text-sm text-text-muted">
              Запускає <code className="text-xs font-mono px-1 py-0.5 rounded bg-bg-subtle">POST /api/v1/ems/optimise</code>{" "}
              для кожного тенанта зі сценарієм <code className="text-xs font-mono px-1 py-0.5 rounded bg-bg-subtle">day_ahead</code>.
            </p>
          </div>
          <button
            type="button"
            onClick={() => portfolioRun.mutate()}
            disabled={portfolioRun.isPending}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-accent text-text-inverse text-sm font-semibold hover:bg-accent-deep transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {portfolioRun.isPending ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <Zap size={14} />
            )}
            Запустити для всього портфеля
          </button>
        </div>

        {runLog.length > 0 && (
          <ul className="flex flex-col gap-2">
            {runLog.map((r) => (
              <li
                key={r.tenant.id}
                className="flex items-center justify-between gap-3 rounded-lg border border-border bg-bg-subtle p-2.5 text-sm"
              >
                <div className="flex items-center gap-2">
                  {r.status === "running" && (
                    <Loader2 size={14} className="animate-spin text-accent" />
                  )}
                  {r.status === "ok" && (
                    <CheckCircle2 size={14} className="text-success" />
                  )}
                  {r.status === "fail" && (
                    <AlertTriangle size={14} className="text-alert" />
                  )}
                  <span className="font-medium text-text-heading">
                    {r.tenant.name}
                  </span>
                </div>
                <span
                  className={
                    r.status === "fail"
                      ? "text-alert text-xs"
                      : "text-text-muted text-xs"
                  }
                >
                  {r.message}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* Operations per tenant */}
      <section className="rounded-xl border border-border bg-bg-card shadow-card overflow-hidden">
        <div className="px-5 pt-4 pb-2">
          <h2 className="text-base font-semibold text-text-heading">
            Стан операцій (24h)
          </h2>
          <p className="text-xs text-text-muted">
            Джерело: <code className="text-xs font-mono">/api/v1/admin/operations</code>
          </p>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-bg-subtle text-xs uppercase tracking-wide text-text-muted">
            <tr>
              <th className="px-4 py-2 text-left">Тенант</th>
              <th className="px-4 py-2 text-right">Setpoints</th>
              <th className="px-4 py-2 text-right">Телеметрія</th>
              <th className="px-4 py-2 text-right">Доступність</th>
            </tr>
          </thead>
          <tbody>
            {(ops.data?.data.rows ?? []).map((r, i) => (
              <tr
                key={r.tenant_id}
                className={
                  i % 2 === 1
                    ? "bg-bg-subtle/30 border-t border-border"
                    : "border-t border-border"
                }
              >
                <td className="px-4 py-2 text-text-body">
                  <div className="font-medium text-text-heading">{r.code}</div>
                  <code className="text-[10px] text-text-muted font-mono">
                    {r.tenant_id}
                  </code>
                </td>
                <td className="px-4 py-2 text-right font-mono text-text-body">
                  {r.setpoints_24h}
                </td>
                <td className="px-4 py-2 text-right font-mono text-text-body">
                  {r.telemetry_rows_24h}
                </td>
                <td className="px-4 py-2 text-right font-mono text-text-body">
                  {formatNumber(r.avg_availability_pct, 1)}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {/* Recent setpoints across tenants */}
      <section className="rounded-xl border border-border bg-bg-card shadow-card overflow-hidden">
        <div className="px-5 pt-4 pb-2">
          <h2 className="text-base font-semibold text-text-heading">
            Останні setpoints — усі тенанти
          </h2>
          <p className="text-xs text-text-muted">
            Останні 30 команд по всіх тенантах, відсортовано за{" "}
            <code className="text-xs font-mono">effective_from</code> ↓
          </p>
        </div>
        {setpoints.isLoading ? (
          <div className="p-6 text-sm text-text-muted text-center">
            Завантаження…
          </div>
        ) : allSetpoints.length === 0 ? (
          <div className="p-6 text-sm text-text-muted text-center">
            Немає даних.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-bg-subtle text-xs uppercase tracking-wide text-text-muted">
                <tr>
                  <th className="px-4 py-2 text-left">Час (effective_from)</th>
                  <th className="px-4 py-2 text-left">Тенант</th>
                  <th className="px-4 py-2 text-right">МВт</th>
                  <th className="px-4 py-2 text-left">Причина</th>
                  <th className="px-4 py-2 text-left">Стан</th>
                </tr>
              </thead>
              <tbody>
                {allSetpoints.map((r, i) => (
                  <tr
                    key={`${r.tenant.id}-${r.id}`}
                    className={
                      i % 2 === 1
                        ? "bg-bg-subtle/30 border-t border-border"
                        : "border-t border-border"
                    }
                  >
                    <td className="px-4 py-2 font-mono text-xs text-text-body">
                      {new Date(r.effective_from).toLocaleString("uk-UA", {
                        dateStyle: "short",
                        timeStyle: "short",
                      })}
                    </td>
                    <td className="px-4 py-2 text-text-body">
                      {r.tenant.name}
                    </td>
                    <td className="px-4 py-2 text-right font-mono text-text-body">
                      {formatNumber(r.target_power_mw, 2)}
                    </td>
                    <td className="px-4 py-2 text-text-muted text-xs">
                      {r.reason ?? "—"}
                    </td>
                    <td className="px-4 py-2 text-text-muted text-xs">
                      {r.state ?? "—"}
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
