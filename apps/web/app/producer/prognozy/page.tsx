"use client";

import { useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
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
import { Send, Loader2, FileCheck2 } from "lucide-react";
import clsx from "clsx";
import { fetchAPI, useAPI, ApiError } from "@/lib/api";
import { Tabs } from "@/components/Tabs";
import { useToast } from "@/components/Toast";
import { formatNumber, formatDateTime } from "@/lib/format";

type ForecastKind = "solar" | "wind" | "load" | "price";

interface ForecastRow {
  id: number;
  asset_id: string;
  forecast_kind: string;
  forecast_type: string;
  issued_at: string;
  date: string;
  hour: number;
  interval_start: string;
  value_mwh: string;
  model_id: string;
}

interface ActualRow {
  asset_id: string;
  forecast_kind: string;
  date: string;
  hour: number;
  interval_start: string;
  actual_mwh: string;
}

interface SubmissionRow {
  id: number;
  submission_id: string;
  submitted_at: string;
  resource_eic: string;
  delivery_date: string;
  document_type: string;
  status: string;
  status_changed_at?: string;
  hourly_volumes_mwh?: string[];
}

interface SubmitResult {
  id?: number;
  submission_id?: string;
  status?: string;
  [k: string]: unknown;
}

const TABS: { id: ForecastKind; label: string }[] = [
  { id: "solar", label: "Сонячна генерація" },
  { id: "wind", label: "Вітрова" },
  { id: "load", label: "Споживання" },
  { id: "price", label: "Ціна" },
];

function daysAgoISO(d: number): string {
  const date = new Date();
  date.setDate(date.getDate() - d);
  return date.toISOString().slice(0, 10);
}

function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

export default function ProducerForecastsPage() {
  const toast = useToast();
  const qc = useQueryClient();
  const [active, setActive] = useState<ForecastKind>("solar");
  const date_start = useMemo(() => daysAgoISO(4), []);
  const date_end = useMemo(() => todayISO(), []);

  const forecasts = useAPI<ForecastRow[]>("/api/v1/ems/forecasts", {
    type: active,
    date_start,
    date_end,
  });

  const actuals = useAPI<ActualRow[]>("/api/v1/ems/forecasts/actuals", {
    type: active,
    date_start,
    date_end,
  });

  const submissions = useAPI<SubmissionRow[]>("/api/v1/regulatory/submissions");

  /* MAPE calculation (client-side, since API doesn't return it) */
  const chartData = useMemo(() => {
    const fc = forecasts.data?.data ?? [];
    const ac = actuals.data?.data ?? [];
    // Aggregate forecasts (refined) by interval_start
    const refMap = new Map<string, number>();
    const priMap = new Map<string, number>();
    const actMap = new Map<string, number>();
    for (const r of fc) {
      const key = r.interval_start;
      const val = parseFloat(r.value_mwh);
      if (r.forecast_type === "refined") {
        refMap.set(key, (refMap.get(key) ?? 0) + val);
      } else {
        priMap.set(key, (priMap.get(key) ?? 0) + val);
      }
    }
    for (const r of ac) {
      const key = r.interval_start;
      const val = parseFloat(r.actual_mwh);
      actMap.set(key, (actMap.get(key) ?? 0) + val);
    }
    const keys = Array.from(
      new Set([...refMap.keys(), ...priMap.keys(), ...actMap.keys()]),
    ).sort();
    return keys.map((k) => {
      const d = new Date(k);
      const label = `${String(d.getDate()).padStart(2, "0")}.${String(
        d.getMonth() + 1,
      ).padStart(2, "0")} ${String(d.getHours()).padStart(2, "0")}`;
      return {
        ts: k,
        label,
        refined: refMap.get(k) ?? null,
        primary: priMap.get(k) ?? null,
        actual: actMap.get(k) ?? null,
      };
    });
  }, [forecasts.data, actuals.data]);

  const mape = useMemo(() => {
    let errSum = 0;
    let actSum = 0;
    let n = 0;
    for (const p of chartData) {
      if (p.refined !== null && p.actual !== null && p.actual > 0) {
        errSum += Math.abs(p.refined - p.actual);
        actSum += p.actual;
        n++;
      }
    }
    if (n === 0 || actSum === 0) return null;
    return (errSum / actSum) * 100;
  }, [chartData]);

  const mut = useMutation<SubmitResult, ApiError, void>({
    mutationFn: async () => {
      // Synth a flat 24-hour submission for today using producer's first СЕС.
      const payload = {
        delivery_date: todayISO(),
        resource_eic: "10W-UA-ASSET-001",
        hourly_volumes_mwh: Array.from({ length: 24 }, (_, i) => {
          // gentle sinusoid centered on 4 MWh, daytime hump
          const t = i;
          const v = Math.max(
            0,
            5 *
              Math.sin(((t - 5) * Math.PI) / 12) *
              (t >= 6 && t <= 20 ? 1 : 0),
          );
          return Number(v.toFixed(3));
        }),
      };
      const res = await fetchAPI<SubmitResult>(
        "/api/v1/ems/forecasts/submit",
        { method: "POST", body: payload },
      );
      return res.data;
    },
    onSuccess: (d) => {
      toast.push({
        tone: "success",
        title: "Прогноз подано до ГП",
        description: `ID: ${d.submission_id ?? d.id ?? "—"} · статус ${d.status ?? "—"}`,
      });
      qc.invalidateQueries({
        predicate: (q) =>
          typeof q.queryKey?.[1] === "string" &&
          (q.queryKey[1] as string).startsWith("/api/v1/regulatory/submissions"),
      });
    },
    onError: (e) => {
      toast.push({
        tone: "alert",
        title: "Помилка подачі прогнозу",
        description: e.message,
      });
    },
  });

  const recentSubs = submissions.data?.data?.slice(0, 6) ?? [];

  return (
    <div className="flex flex-col gap-5">
      <header className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-text-heading">
            Прогнози генерації
          </h1>
          <p className="text-sm text-text-muted">
            Денний та внутрішньодобовий прогноз. Refined vs primary з фактом,
            подача до Гарантованого Покупця.
          </p>
        </div>
        <button
          type="button"
          onClick={() => mut.mutate()}
          disabled={mut.isPending}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-accent text-text-inverse font-medium hover:bg-accent-deep transition-colors shadow-card disabled:opacity-50"
        >
          {mut.isPending ? (
            <Loader2 size={16} className="animate-spin" />
          ) : (
            <Send size={16} />
          )}
          Подати прогноз
        </button>
      </header>

      <Tabs
        items={TABS.map((t) => ({ id: t.id, label: t.label }))}
        active={active}
        onChange={(id) => setActive(id as ForecastKind)}
      />

      <section className="rounded-xl border border-border bg-bg-card p-4 shadow-card">
        <div className="flex items-center justify-between mb-3 gap-3 flex-wrap">
          <div>
            <h2 className="text-base font-semibold text-text-heading">
              {TABS.find((t) => t.id === active)?.label} · прогноз vs факт
            </h2>
            <p className="text-xs text-text-muted">
              Refined уточнений · primary первинний · факт телеметрії
            </p>
          </div>
          {mape !== null && (
            <span
              className={clsx(
                "inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium",
                mape < 10
                  ? "bg-success/15 text-success"
                  : mape < 20
                    ? "bg-warning/15 text-warning"
                    : "bg-alert/15 text-alert",
              )}
            >
              MAPE {formatNumber(mape, 1)}%
            </span>
          )}
        </div>
        {forecasts.isLoading ? (
          <div className="h-[320px] flex items-center justify-center text-sm text-text-muted">
            Завантаження…
          </div>
        ) : forecasts.isError ? (
          <div className="h-[320px] flex items-center justify-center text-sm text-alert">
            {forecasts.error.message}
          </div>
        ) : chartData.length === 0 ? (
          <div className="h-[320px] flex items-center justify-center text-sm text-text-muted">
            Немає даних прогнозу для відображення.
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
                    if (v === null || v === undefined) return "—";
                    const n = typeof v === "number" ? v : parseFloat(String(v));
                    return Number.isFinite(n)
                      ? `${formatNumber(n, 2)} МВт·год`
                      : "—";
                  }}
                />
                <Legend
                  wrapperStyle={{ fontSize: 11, paddingTop: 8 }}
                  iconType="line"
                />
                <Line
                  type="monotone"
                  dataKey="actual"
                  name="Факт"
                  stroke="var(--color-accent-deep)"
                  strokeWidth={2.5}
                  dot={false}
                  isAnimationActive={false}
                  connectNulls
                />
                <Line
                  type="monotone"
                  dataKey="refined"
                  name="Refined"
                  stroke="var(--color-info)"
                  strokeWidth={1.8}
                  strokeDasharray="4 3"
                  dot={false}
                  isAnimationActive={false}
                  connectNulls
                />
                <Line
                  type="monotone"
                  dataKey="primary"
                  name="Primary"
                  stroke="var(--color-warning)"
                  strokeWidth={1.4}
                  strokeDasharray="2 4"
                  dot={false}
                  isAnimationActive={false}
                  connectNulls
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </section>

      {/* Recent submissions */}
      <section className="rounded-xl border border-border bg-bg-card shadow-card">
        <header className="flex items-center justify-between p-4 border-b border-border">
          <div className="flex items-center gap-2">
            <FileCheck2 size={16} className="text-accent" />
            <h2 className="text-base font-semibold text-text-heading">
              Останні подачі до ГП
            </h2>
          </div>
          <span className="text-xs text-text-muted">
            Кодекс комерційного обліку · CAdES-X-Long
          </span>
        </header>
        {submissions.isLoading ? (
          <div className="p-8 text-center text-sm text-text-muted">
            Завантаження…
          </div>
        ) : recentSubs.length === 0 ? (
          <div className="p-8 text-center text-sm text-text-muted">
            Поки що подач немає.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-bg-subtle text-xs uppercase tracking-wide text-text-muted">
                <tr>
                  <th className="px-4 py-2 text-left">Submission ID</th>
                  <th className="px-4 py-2 text-left">Доставка</th>
                  <th className="px-4 py-2 text-left">Resource EIC</th>
                  <th className="px-4 py-2 text-left">Подано</th>
                  <th className="px-4 py-2 text-left">Статус</th>
                </tr>
              </thead>
              <tbody>
                {recentSubs.map((s, i) => (
                  <tr
                    key={s.id}
                    className={clsx(
                      "border-t border-border",
                      i % 2 === 1 && "bg-bg-subtle/30",
                    )}
                  >
                    <td className="px-4 py-2 font-mono text-[11px] text-text-body">
                      {s.submission_id}
                    </td>
                    <td className="px-4 py-2 text-text-body">
                      {s.delivery_date}
                    </td>
                    <td className="px-4 py-2 font-mono text-[11px] text-text-muted">
                      {s.resource_eic}
                    </td>
                    <td className="px-4 py-2 text-text-muted text-xs">
                      {formatDateTime(s.submitted_at)}
                    </td>
                    <td className="px-4 py-2">
                      <SubmissionStatus status={s.status} />
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

function SubmissionStatus({ status }: { status: string }) {
  const map: Record<string, string> = {
    ACK: "bg-success/15 text-success",
    PENDING: "bg-warning/15 text-warning",
    REJECTED: "bg-alert/15 text-alert",
    SUBMITTED: "bg-info/15 text-info",
  };
  const tone = map[status] ?? "bg-bg-subtle text-text-muted";
  return (
    <span
      className={clsx(
        "inline-flex items-center px-2 py-0.5 rounded text-xs font-medium",
        tone,
      )}
    >
      {status}
    </span>
  );
}
