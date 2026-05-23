"use client";

import { useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import clsx from "clsx";
import {
  Loader2,
  Zap,
  CheckCircle2,
  Inbox,
  ListChecks,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import { useAPI, fetchAPI, ApiError } from "@/lib/api";
import { useToast } from "@/components/Toast";
import { formatNumber, formatDateTime } from "@/lib/format";

interface Setpoint {
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

interface Instruction {
  id: number;
  setpoint_id: number;
  asset_id: string;
  instruction_kind: string;
  payload: Record<string, unknown>;
  queued_at: string;
  dispatched_at?: string | null;
  priority: number;
  ack_status?: string | null;
}

interface OptimiseResult {
  run_id: number;
  scenario: string;
  recommendations: { asset_id: string; hour: number; action: string; mw: string }[];
  expected_uplift_uah?: string;
  uplift_uah?: string;
  confidence_pct?: string;
  confidence?: string;
  risk_flags?: string[] | string | null;
  duration_ms?: number;
  inputs_hash?: string;
}

interface AssetMini {
  id: string;
  display_name: string;
  asset_class: string;
}

function daysAgoISO(d: number): string {
  const date = new Date();
  date.setDate(date.getDate() - d);
  return date.toISOString().slice(0, 10);
}

function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

export default function ProducerDispatchPage() {
  const toast = useToast();
  const qc = useQueryClient();
  const date_start = useMemo(() => daysAgoISO(2), []);
  const date_end = useMemo(() => todayISO(), []);

  const setpoints = useAPI<Setpoint[]>("/api/v1/dispatch/setpoints", {
    date_start,
    date_end,
  });
  const instructions = useAPI<Instruction[]>("/api/v1/dispatch/instructions", {
    date_start,
    date_end,
  });
  const assets = useAPI<AssetMini[]>("/api/v1/assets");

  const assetName = useMemo(() => {
    const m = new Map<string, string>();
    (assets.data?.data ?? []).forEach((a) =>
      m.set(a.id, `${a.display_name} · ${a.asset_class}`),
    );
    return m;
  }, [assets.data]);

  const optimise = useMutation<OptimiseResult, ApiError, void>({
    mutationFn: async () => {
      const res = await fetchAPI<OptimiseResult>("/api/v1/ems/optimise", {
        method: "POST",
        body: { scenario: "day_ahead", date: todayISO() },
      });
      return res.data;
    },
    onSuccess: (d) => {
      toast.push({
        tone: "success",
        title: "Оптимізацію виконано",
        description: `Run #${d.run_id} · uplift ${d.expected_uplift_uah ?? d.uplift_uah ?? "—"} грн`,
      });
    },
    onError: (e) =>
      toast.push({
        tone: "alert",
        title: "Помилка оптимізації",
        description: e.message,
      }),
  });

  const ackMut = useMutation<unknown, ApiError, number>({
    mutationFn: async (id) => {
      const res = await fetchAPI(
        `/api/v1/dispatch/instructions/${id}/ack`,
        { method: "POST", body: { ack_status: "ack" } },
      );
      return res.data;
    },
    onSuccess: (_d, id) => {
      toast.push({
        tone: "success",
        title: `Підтверджено інструкцію #${id}`,
      });
      qc.invalidateQueries({
        predicate: (q) =>
          typeof q.queryKey?.[1] === "string" &&
          (q.queryKey[1] as string).startsWith("/api/v1/dispatch/instructions"),
      });
    },
    onError: (e) =>
      toast.push({
        tone: "alert",
        title: "Помилка підтвердження",
        description: e.message,
      }),
  });

  const setpointRows = setpoints.data?.data?.slice(0, 24) ?? [];
  const instructionRows = instructions.data?.data?.slice(0, 24) ?? [];

  const result = optimise.data;
  const recs = result?.recommendations ?? [];
  const riskFlags = Array.isArray(result?.risk_flags)
    ? result?.risk_flags
    : typeof result?.risk_flags === "string"
      ? [result.risk_flags]
      : [];

  return (
    <div className="flex flex-col gap-5">
      <header className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-text-heading">
            Диспетчеризація
          </h1>
          <p className="text-sm text-text-muted">
            Черга сетпойнтів та інструкцій. Оптимізатор підбирає денний план.
          </p>
        </div>
        <button
          type="button"
          onClick={() => optimise.mutate()}
          disabled={optimise.isPending}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-accent text-text-inverse font-semibold hover:bg-accent-deep transition-colors shadow-card disabled:opacity-50"
        >
          {optimise.isPending ? (
            <Loader2 size={16} className="animate-spin" />
          ) : (
            <Zap size={16} />
          )}
          Запустити оптимізацію
        </button>
      </header>

      {/* Optimisation result */}
      {result && (
        <section className="rounded-xl border border-accent bg-accent-subtle p-5">
          <div className="flex items-start justify-between flex-wrap gap-3 mb-3">
            <div>
              <h2 className="text-base font-semibold text-text-heading flex items-center gap-2">
                <Sparkles size={16} className="text-accent-deep" />
                Результати оптимізації · run #{result.run_id}
              </h2>
              <p className="text-xs text-text-muted">
                сценарій {result.scenario}
                {result.duration_ms && ` · ${result.duration_ms} мс`}
                {result.inputs_hash && ` · hash ${result.inputs_hash.slice(0, 8)}`}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Metric
                label="Uplift"
                value={
                  result.expected_uplift_uah ??
                  result.uplift_uah ??
                  "—"
                }
                suffix="грн"
              />
              <Metric
                label="Впевненість"
                value={
                  result.confidence_pct ??
                  (result.confidence
                    ? `${formatNumber(parseFloat(result.confidence) * 100, 0)}`
                    : "—")
                }
                suffix="%"
              />
              <Metric label="Рекомендацій" value={recs.length} />
            </div>
          </div>
          {riskFlags.length > 0 && (
            <div className="rounded-md bg-warning/10 border border-warning/40 p-2.5 mb-3 flex items-start gap-2 text-xs text-warning">
              <ShieldAlert size={14} className="shrink-0 mt-0.5" />
              <div>
                <strong>Ризики:</strong>{" "}
                {riskFlags.join(", ")}
              </div>
            </div>
          )}
          <div className="rounded-lg border border-border bg-bg-card overflow-hidden max-h-80 overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="bg-bg-subtle text-xs uppercase tracking-wide text-text-muted sticky top-0">
                <tr>
                  <th className="px-3 py-2 text-left">Год</th>
                  <th className="px-3 py-2 text-left">Актив</th>
                  <th className="px-3 py-2 text-left">Дія</th>
                  <th className="px-3 py-2 text-right">МВт</th>
                </tr>
              </thead>
              <tbody>
                {recs.slice(0, 50).map((r, i) => (
                  <tr
                    key={i}
                    className={clsx(
                      "border-t border-border",
                      i % 2 === 1 && "bg-bg-subtle/30",
                    )}
                  >
                    <td className="px-3 py-1.5 font-mono text-xs">
                      {String(r.hour).padStart(2, "0")}:00
                    </td>
                    <td className="px-3 py-1.5 text-xs text-text-muted">
                      {assetName.get(r.asset_id) ?? r.asset_id.slice(0, 8)}
                    </td>
                    <td className="px-3 py-1.5">
                      <ActionPill action={r.action} />
                    </td>
                    <td className="px-3 py-1.5 text-right font-mono text-xs">
                      {formatNumber(r.mw, 2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Two-column: setpoints + instructions */}
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="rounded-xl border border-border bg-bg-card shadow-card overflow-hidden">
          <header className="flex items-center justify-between p-4 border-b border-border">
            <h2 className="text-base font-semibold text-text-heading flex items-center gap-2">
              <Inbox size={16} className="text-accent" />
              Сетпойнти
            </h2>
            <span className="text-xs text-text-muted">
              {setpointRows.length} останніх
            </span>
          </header>
          {setpoints.isLoading ? (
            <div className="p-8 text-center text-sm text-text-muted">
              Завантаження…
            </div>
          ) : setpointRows.length === 0 ? (
            <div className="p-8 text-center text-sm text-text-muted">
              Сетпойнтів поки немає.
            </div>
          ) : (
            <ul className="divide-y divide-border max-h-[500px] overflow-y-auto">
              {setpointRows.map((sp) => (
                <li key={sp.id} className="p-3 text-sm">
                  <div className="flex items-center justify-between gap-2">
                    <div className="font-medium text-text-heading text-xs">
                      {assetName.get(sp.asset_id) ?? sp.asset_id.slice(0, 8)}
                    </div>
                    <SetpointStateBadge state={sp.state} />
                  </div>
                  <div className="mt-1 text-xs text-text-muted">
                    {formatDateTime(sp.effective_from)} →{" "}
                    {formatDateTime(sp.effective_to)}
                  </div>
                  <div className="mt-1 flex items-center gap-3 text-xs">
                    <span className="font-mono text-text-body">
                      {formatNumber(sp.target_power_mw, 2)} МВт
                    </span>
                    {sp.target_soc_pct && (
                      <span className="font-mono text-text-body">
                        SOC {formatNumber(sp.target_soc_pct, 1)}%
                      </span>
                    )}
                    <span className="text-text-muted">
                      причина: {sp.reason}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="rounded-xl border border-border bg-bg-card shadow-card overflow-hidden">
          <header className="flex items-center justify-between p-4 border-b border-border">
            <h2 className="text-base font-semibold text-text-heading flex items-center gap-2">
              <ListChecks size={16} className="text-accent" />
              Інструкції диспетчера
            </h2>
            <span className="text-xs text-text-muted">
              {instructionRows.length} останніх
            </span>
          </header>
          {instructions.isLoading ? (
            <div className="p-8 text-center text-sm text-text-muted">
              Завантаження…
            </div>
          ) : instructionRows.length === 0 ? (
            <div className="p-8 text-center text-sm text-text-muted">
              Активних інструкцій немає.
            </div>
          ) : (
            <ul className="divide-y divide-border max-h-[500px] overflow-y-auto">
              {instructionRows.map((it) => {
                const target =
                  (it.payload as { target_mw?: number })?.target_mw ?? null;
                return (
                  <li key={it.id} className="p-3 text-sm">
                    <div className="flex items-center justify-between gap-2">
                      <div className="font-medium text-text-heading text-xs">
                        #{it.id} ·{" "}
                        {assetName.get(it.asset_id) ?? it.asset_id.slice(0, 8)}
                      </div>
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-accent-subtle text-accent-deep">
                        {it.instruction_kind}
                      </span>
                    </div>
                    <div className="mt-1 text-xs text-text-muted">
                      Черга: {formatDateTime(it.queued_at)}
                      {it.dispatched_at &&
                        ` · диспетч: ${formatDateTime(it.dispatched_at)}`}
                    </div>
                    <div className="mt-1 flex items-center justify-between gap-2">
                      <span className="font-mono text-xs text-text-body">
                        {target !== null
                          ? `${formatNumber(target, 2)} МВт`
                          : JSON.stringify(it.payload)}
                      </span>
                      <button
                        type="button"
                        onClick={() => ackMut.mutate(it.id)}
                        disabled={ackMut.isPending}
                        className="inline-flex items-center gap-1 px-2 py-1 rounded text-xs border border-success/40 text-success hover:bg-success/10 disabled:opacity-50"
                      >
                        {ackMut.isPending && ackMut.variables === it.id ? (
                          <Loader2 size={11} className="animate-spin" />
                        ) : (
                          <CheckCircle2 size={11} />
                        )}
                        Підтвердити
                      </button>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </section>
    </div>
  );
}

function Metric({
  label,
  value,
  suffix,
}: {
  label: string;
  value: string | number;
  suffix?: string;
}) {
  return (
    <div className="rounded-md bg-bg-card border border-border px-3 py-1.5 text-right">
      <div className="text-[10px] uppercase tracking-wide text-text-muted">
        {label}
      </div>
      <div className="text-sm font-semibold text-text-heading">
        {typeof value === "string" ? value : formatNumber(value, 0)}
        {suffix && <span className="text-xs text-text-muted ml-1">{suffix}</span>}
      </div>
    </div>
  );
}

function ActionPill({ action }: { action: string }) {
  const map: Record<string, { label: string; tone: string }> = {
    charge: { label: "Зарядка", tone: "bg-info/15 text-info" },
    discharge: { label: "Розряд", tone: "bg-success/15 text-success" },
    hold: { label: "Утримати", tone: "bg-bg-subtle text-text-muted" },
    sell: { label: "Продати", tone: "bg-success/15 text-success" },
    curtail: { label: "Curtail", tone: "bg-warning/15 text-warning" },
  };
  const v = map[action] ?? { label: action, tone: "bg-bg-subtle text-text-muted" };
  return (
    <span
      className={clsx(
        "inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium",
        v.tone,
      )}
    >
      {v.label}
    </span>
  );
}

function SetpointStateBadge({ state }: { state: string }) {
  const map: Record<string, string> = {
    done: "bg-success/15 text-success",
    active: "bg-info/15 text-info",
    pending: "bg-warning/15 text-warning",
    cancelled: "bg-bg-subtle text-text-muted",
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
