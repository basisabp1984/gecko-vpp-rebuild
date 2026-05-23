"use client";

import { useMemo, useState } from "react";
import clsx from "clsx";
import {
  AlertTriangle,
  Info,
  AlertOctagon,
  Bell,
  CheckCheck,
} from "lucide-react";
import { useAPI } from "@/lib/api";
import { formatDate } from "@/lib/format";

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
  affected_entities?: string[];
  source_url?: string | null;
}

type SeverityFilter = "all" | "INFO" | "NOTICE" | "WARN" | "CRITICAL";

const SEVERITY_FILTERS: { id: SeverityFilter; label: string }[] = [
  { id: "all", label: "Всі" },
  { id: "INFO", label: "Інфо" },
  { id: "NOTICE", label: "Повідомлення" },
  { id: "WARN", label: "Попередження" },
  { id: "CRITICAL", label: "Критичні" },
];

function daysAgoISO(d: number): string {
  const date = new Date();
  date.setDate(date.getDate() - d);
  return date.toISOString().slice(0, 10);
}

function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

export default function ProducerNotificationsPage() {
  const date_start = useMemo(() => daysAgoISO(30), []);
  const date_end = useMemo(() => todayISO(), []);
  const events = useAPI<RegulatoryEvent[]>("/api/v1/regulatory/events", {
    date_start,
    date_end,
  });

  const [severity, setSeverity] = useState<SeverityFilter>("all");
  const [issuer, setIssuer] = useState<string>("all");
  const [readIds, setReadIds] = useState<Set<number>>(new Set());

  const rows = events.data?.data ?? [];

  const issuers = useMemo(() => {
    const s = new Set<string>();
    rows.forEach((e) => s.add(e.issuer));
    return ["all", ...Array.from(s)];
  }, [rows]);

  const filtered = useMemo(() => {
    return rows.filter((e) => {
      if (severity !== "all" && e.severity !== severity) return false;
      if (issuer !== "all" && e.issuer !== issuer) return false;
      return true;
    });
  }, [rows, severity, issuer]);

  function markRead(id: number) {
    setReadIds((s) => new Set([...s, id]));
  }
  function markAllRead() {
    setReadIds(new Set(filtered.map((e) => e.id)));
  }

  return (
    <div className="flex flex-col gap-5">
      <header className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-text-heading">
            Сповіщення та події
          </h1>
          <p className="text-sm text-text-muted">
            Регуляторні зміни від НКРЕКП, ОРЕЕ, Укренерго та ГП. Підтверджуйте
            ознайомлення для аудиту.
          </p>
        </div>
        <button
          type="button"
          onClick={markAllRead}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-border bg-bg-card text-sm hover:border-accent"
        >
          <CheckCheck size={14} />
          Прочитати всі
        </button>
      </header>

      {/* Filters */}
      <section className="flex flex-col lg:flex-row gap-3 lg:items-center">
        <div className="flex flex-wrap gap-1.5">
          {SEVERITY_FILTERS.map((f) => (
            <button
              key={f.id}
              type="button"
              onClick={() => setSeverity(f.id)}
              className={clsx(
                "px-3 py-1.5 rounded-full text-xs font-medium border transition-colors",
                severity === f.id
                  ? "border-accent bg-accent text-text-inverse"
                  : "border-border bg-bg-card text-text-muted hover:border-accent",
              )}
            >
              {f.label}
            </button>
          ))}
        </div>
        <div className="lg:ml-auto flex items-center gap-2">
          <span className="text-xs text-text-muted">Видавець:</span>
          <select
            value={issuer}
            onChange={(e) => setIssuer(e.target.value)}
            className="rounded-md border border-border bg-bg-card px-2 py-1 text-sm"
          >
            {issuers.map((i) => (
              <option key={i} value={i}>
                {i === "all" ? "Всі" : i}
              </option>
            ))}
          </select>
        </div>
      </section>

      {/* Events list */}
      <section className="flex flex-col gap-3">
        {events.isLoading ? (
          <div className="p-8 text-center text-sm text-text-muted">
            Завантаження подій…
          </div>
        ) : events.isError ? (
          <div className="p-8 text-center text-sm text-alert">
            {events.error.message}
          </div>
        ) : filtered.length === 0 ? (
          <div className="p-10 text-center rounded-xl border border-dashed border-border">
            <Bell size={28} className="mx-auto mb-2 text-text-muted" />
            <p className="text-sm text-text-muted">
              За цими фільтрами подій немає.
            </p>
          </div>
        ) : (
          filtered.map((e) => (
            <EventCard
              key={e.id}
              event={e}
              isRead={readIds.has(e.id)}
              onMarkRead={() => markRead(e.id)}
            />
          ))
        )}
      </section>
    </div>
  );
}

function EventCard({
  event,
  isRead,
  onMarkRead,
}: {
  event: RegulatoryEvent;
  isRead: boolean;
  onMarkRead: () => void;
}) {
  const sev = sevMeta(event.severity);
  return (
    <article
      className={clsx(
        "rounded-xl border bg-bg-card p-4 shadow-card transition-opacity",
        isRead ? "opacity-60" : "opacity-100",
        sev.borderCls,
      )}
    >
      <div className="flex items-start gap-3">
        <div className={clsx("shrink-0 mt-0.5", sev.iconCls)}>{sev.icon}</div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span
              className={clsx(
                "inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide",
                sev.badgeCls,
              )}
            >
              {sev.label}
            </span>
            <span className="text-xs text-text-muted">
              {event.issuer} · {event.act_type} {event.act_number}
            </span>
            <span className="text-xs text-text-muted ml-auto">
              {formatDate(event.issued_at)}
            </span>
          </div>
          <h3 className="text-sm sm:text-base font-semibold text-text-heading mt-1 leading-snug">
            {event.title}
          </h3>
          <p className="text-sm text-text-body mt-1">{event.summary}</p>
          <div className="flex items-center justify-between mt-2 gap-2 flex-wrap">
            <span className="text-xs text-text-muted">
              Чинно з {formatDate(event.effective_at)}
              {event.category && ` · ${event.category}`}
            </span>
            {!isRead && (
              <button
                type="button"
                onClick={onMarkRead}
                className="inline-flex items-center gap-1 px-2 py-1 rounded text-xs border border-border bg-bg-card hover:border-accent"
              >
                <CheckCheck size={12} />
                Позначити прочитаним
              </button>
            )}
            {isRead && (
              <span className="inline-flex items-center gap-1 text-xs text-success">
                <CheckCheck size={12} />
                Прочитано
              </span>
            )}
          </div>
        </div>
      </div>
    </article>
  );
}

function sevMeta(sev: string): {
  label: string;
  icon: React.ReactNode;
  badgeCls: string;
  borderCls: string;
  iconCls: string;
} {
  switch (sev) {
    case "CRITICAL":
      return {
        label: "Критично",
        icon: <AlertOctagon size={20} />,
        badgeCls: "bg-alert text-text-inverse",
        borderCls: "border-alert/40",
        iconCls: "text-alert",
      };
    case "WARN":
      return {
        label: "Попередження",
        icon: <AlertTriangle size={20} />,
        badgeCls: "bg-warning/20 text-warning",
        borderCls: "border-warning/40",
        iconCls: "text-warning",
      };
    case "NOTICE":
      return {
        label: "Повідомлення",
        icon: <Info size={20} />,
        badgeCls: "bg-info/15 text-info",
        borderCls: "border-info/30",
        iconCls: "text-info",
      };
    case "INFO":
    default:
      return {
        label: "Інфо",
        icon: <Info size={20} />,
        badgeCls: "bg-bg-subtle text-text-muted",
        borderCls: "border-border",
        iconCls: "text-text-muted",
      };
  }
}
