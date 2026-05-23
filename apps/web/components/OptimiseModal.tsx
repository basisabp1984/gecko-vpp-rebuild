"use client";

import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { X, Loader2, Zap } from "lucide-react";
import clsx from "clsx";
import { fetchAPI, ApiError } from "@/lib/api";
import { formatNumber } from "@/lib/format";

interface Recommendation {
  asset_id: string;
  hour: number;
  action: "charge" | "discharge" | "hold" | "sell" | string;
  mw: string | number;
}

interface OptimiseResult {
  run_id: number;
  scenario: string;
  recommendations: Recommendation[];
  expected_revenue_uah?: string | number;
}

interface OptimisePayload {
  scenario: string;
  date: string;
}

export function OptimiseModal({
  date,
  scenario = "arbitrage",
}: {
  date: string;
  scenario?: string;
}) {
  const [open, setOpen] = useState(false);

  const mut = useMutation<OptimiseResult, ApiError, OptimisePayload>({
    mutationFn: async (payload) => {
      const res = await fetchAPI<OptimiseResult>("/api/v1/ems/optimise", {
        method: "POST",
        body: payload,
      });
      return res.data;
    },
  });

  function handleRun() {
    setOpen(true);
    mut.mutate({ scenario, date });
  }

  return (
    <>
      <button
        type="button"
        onClick={handleRun}
        className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-accent text-text-inverse font-medium hover:bg-accent-deep transition-colors shadow-card"
      >
        <Zap size={16} />
        Запустити оптимізацію
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-black/40"
            onClick={() => setOpen(false)}
          />
          <div className="relative w-full max-w-2xl max-h-[80vh] overflow-hidden rounded-xl border border-border bg-bg-card shadow-elevated flex flex-col">
            <div className="flex items-center justify-between px-6 py-4 border-b border-border">
              <div>
                <h2 className="text-lg font-semibold text-text-heading">
                  Результати оптимізації
                </h2>
                <p className="text-xs text-text-muted">
                  Сценарій: {scenario} · {date}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="p-1 rounded hover:bg-bg-subtle"
                aria-label="Закрити"
              >
                <X size={18} />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-6 scrollbar-thin">
              {mut.isPending && (
                <div className="flex flex-col items-center justify-center py-12 gap-3 text-text-muted">
                  <Loader2 size={28} className="animate-spin text-accent" />
                  <span>Підбираємо оптимальну стратегію…</span>
                </div>
              )}

              {mut.isError && (
                <div className="rounded-lg border border-alert/50 bg-alert/10 p-4 text-sm text-alert">
                  <strong className="block mb-1">Не вдалося оптимізувати</strong>
                  {mut.error.message}
                </div>
              )}

              {mut.isSuccess && mut.data && (
                <RecommendationsTable result={mut.data} />
              )}
            </div>

            <div className="px-6 py-3 border-t border-border flex items-center justify-end gap-2 bg-bg-subtle">
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="px-4 py-1.5 rounded-lg border border-border bg-bg-card text-text-body hover:border-accent transition-colors text-sm"
              >
                Закрити
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function RecommendationsTable({ result }: { result: OptimiseResult }) {
  return (
    <div>
      <div className="mb-4 grid grid-cols-2 gap-4">
        <div className="rounded-lg border border-border bg-bg-page p-3">
          <div className="text-xs text-text-muted">Run ID</div>
          <div className="text-sm font-mono text-text-heading">
            #{result.run_id}
          </div>
        </div>
        <div className="rounded-lg border border-border bg-bg-page p-3">
          <div className="text-xs text-text-muted">Рекомендацій</div>
          <div className="text-sm font-semibold text-text-heading">
            {result.recommendations.length}
          </div>
        </div>
      </div>

      <div className="rounded-lg border border-border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-bg-subtle text-xs uppercase tracking-wide text-text-muted">
            <tr>
              <th className="px-3 py-2 text-left">Год</th>
              <th className="px-3 py-2 text-left">Дія</th>
              <th className="px-3 py-2 text-right">МВт</th>
            </tr>
          </thead>
          <tbody>
            {result.recommendations.slice(0, 24).map((r, i) => (
              <tr
                key={i}
                className={clsx(
                  "border-t border-border",
                  i % 2 === 1 && "bg-bg-subtle/40",
                )}
              >
                <td className="px-3 py-2 font-mono text-text-body">
                  {String(r.hour).padStart(2, "0")}:00
                </td>
                <td className="px-3 py-2">
                  <ActionBadge action={r.action} />
                </td>
                <td className="px-3 py-2 text-right font-mono text-text-body">
                  {formatNumber(r.mw, 2)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ActionBadge({ action }: { action: string }) {
  const labels: Record<string, string> = {
    charge: "Зарядка",
    discharge: "Розряд",
    hold: "Утримати",
    sell: "Продати",
  };
  const tone =
    action === "discharge" || action === "sell"
      ? "bg-success/15 text-success"
      : action === "charge"
        ? "bg-info/15 text-info"
        : "bg-bg-subtle text-text-muted";
  return (
    <span
      className={clsx(
        "inline-flex items-center px-2 py-0.5 rounded text-xs font-medium",
        tone,
      )}
    >
      {labels[action] ?? action}
    </span>
  );
}
