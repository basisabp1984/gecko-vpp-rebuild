"use client";

import { useEffect, useMemo, useState } from "react";
import clsx from "clsx";
import { Sun, Battery, Factory, Search, Plug } from "lucide-react";
import { useAPI } from "@/lib/api";
import { useTenantStore } from "@/lib/store";
import { TENANTS } from "@/lib/tenants";
import { AssetDrawer, type AssetSummary } from "@/components/AssetDrawer";
import { formatNumber } from "@/lib/format";

type AssetClass = "all" | "СЕС" | "УЗЕ" | "Споживач" | "АктСпож";

const FILTERS: { id: AssetClass; label: string; icon?: React.ReactNode }[] = [
  { id: "all", label: "Всі" },
  { id: "Споживач", label: "Споживання", icon: <Plug size={14} /> },
  { id: "АктСпож", label: "Гнучке навант.", icon: <Factory size={14} /> },
  { id: "СЕС", label: "Дах-СЕС", icon: <Sun size={14} /> },
  { id: "УЗЕ", label: "УЗЕ", icon: <Battery size={14} /> },
];

export default function CIAssetsPage() {
  useEffect(() => {
    const { currentTenantId, setTenantId } = useTenantStore.getState();
    if (currentTenantId === TENANTS.producer.id) {
      setTenantId(TENANTS.ci.id);
    }
  }, []);

  const [filter, setFilter] = useState<AssetClass>("all");
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<AssetSummary | null>(null);

  const assets = useAPI<AssetSummary[]>("/api/v1/assets");
  const rows = assets.data?.data ?? [];

  const filtered = useMemo(() => {
    return rows
      .filter((a) => (filter === "all" ? true : a.asset_class === filter))
      .filter((a) => {
        if (!query.trim()) return true;
        const q = query.toLowerCase();
        return (
          a.display_name.toLowerCase().includes(q) ||
          (a.region ?? "").toLowerCase().includes(q) ||
          a.resource_eic.toLowerCase().includes(q)
        );
      });
  }, [rows, filter, query]);

  return (
    <div className="flex flex-col gap-5">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl sm:text-3xl font-bold text-text-heading">
          Активи — Бізнес
        </h1>
        <p className="text-sm text-text-muted">
          Точки споживання, гнучкі навантаження та власна генерація. Натисніть
          рядок для деталей та телеметрії.
        </p>
      </header>

      <section className="flex flex-col lg:flex-row gap-3 items-stretch lg:items-center">
        <div className="flex flex-wrap gap-1.5">
          {FILTERS.map((f) => {
            const isActive = filter === f.id;
            const count =
              f.id === "all"
                ? rows.length
                : rows.filter((a) => a.asset_class === f.id).length;
            return (
              <button
                key={f.id}
                type="button"
                onClick={() => setFilter(f.id)}
                className={clsx(
                  "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border transition-colors",
                  isActive
                    ? "border-accent bg-accent text-text-inverse"
                    : "border-border bg-bg-card text-text-muted hover:border-accent",
                )}
              >
                {f.icon}
                {f.label}
                <span
                  className={clsx(
                    "ml-0.5 inline-flex items-center justify-center min-w-[18px] h-[18px] rounded-full px-1 text-[10px]",
                    isActive
                      ? "bg-accent-deep/40 text-text-inverse"
                      : "bg-bg-subtle text-text-muted",
                  )}
                >
                  {count}
                </span>
              </button>
            );
          })}
        </div>
        <div className="relative lg:ml-auto lg:w-64">
          <Search
            size={14}
            className="absolute left-2.5 top-1/2 -translate-y-1/2 text-text-muted"
          />
          <input
            type="search"
            placeholder="Назва, EIC, регіон…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 rounded-md border border-border bg-bg-card text-sm"
          />
        </div>
      </section>

      <section className="rounded-xl border border-border bg-bg-card overflow-hidden shadow-card">
        {assets.isLoading ? (
          <div className="p-10 text-center text-sm text-text-muted">
            Завантаження активів…
          </div>
        ) : assets.isError ? (
          <div className="p-10 text-center text-sm text-alert">
            Помилка: {assets.error.message}
          </div>
        ) : filtered.length === 0 ? (
          <div className="p-10 text-center">
            <p className="text-sm text-text-muted">
              Активів за вказаним фільтром не знайдено.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-bg-subtle text-xs uppercase tracking-wide text-text-muted">
                <tr>
                  <th className="px-4 py-2.5 text-left">Назва</th>
                  <th className="px-4 py-2.5 text-left">Тип</th>
                  <th className="px-4 py-2.5 text-right">Потужність</th>
                  <th className="px-4 py-2.5 text-left">Регіон</th>
                  <th className="px-4 py-2.5 text-left">EIC</th>
                  <th className="px-4 py-2.5 text-left">Статус</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((a, i) => (
                  <tr
                    key={a.id}
                    onClick={() => setSelected(a)}
                    className={clsx(
                      "border-t border-border cursor-pointer hover:bg-accent-subtle/30 transition-colors",
                      i % 2 === 1 && "bg-bg-subtle/30",
                    )}
                  >
                    <td className="px-4 py-3 text-text-heading font-medium">
                      {a.display_name}
                    </td>
                    <td className="px-4 py-3">
                      <ClassBadge cls={a.asset_class} />
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-text-body">
                      {formatNumber(a.capacity_mw, 1)} МВт
                    </td>
                    <td className="px-4 py-3 text-text-body">
                      {a.region ?? "—"}
                    </td>
                    <td className="px-4 py-3 font-mono text-[11px] text-text-muted">
                      {a.resource_eic}
                    </td>
                    <td className="px-4 py-3">
                      <StatusPill status={a.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <AssetDrawer asset={selected} onClose={() => setSelected(null)} />
    </div>
  );
}

function ClassBadge({ cls }: { cls: string }) {
  const map: Record<string, { label: string; tone: string }> = {
    СЕС: { label: "СЕС", tone: "bg-warning/15 text-warning" },
    УЗЕ: { label: "УЗЕ", tone: "bg-accent-subtle text-accent-deep" },
    Споживач: { label: "Споживач", tone: "bg-info/15 text-info" },
    АктСпож: { label: "Гнучке навант.", tone: "bg-success/15 text-success" },
  };
  const v = map[cls] ?? { label: cls, tone: "bg-bg-subtle text-text-muted" };
  return (
    <span
      className={clsx(
        "inline-flex items-center px-2 py-0.5 rounded text-xs font-medium",
        v.tone,
      )}
    >
      {v.label}
    </span>
  );
}

function StatusPill({ status }: { status: string }) {
  const isActive = status === "active";
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 text-xs",
        isActive ? "text-success" : "text-warning",
      )}
    >
      <span
        className={clsx(
          "w-1.5 h-1.5 rounded-full",
          isActive ? "bg-success" : "bg-warning",
        )}
      />
      {isActive ? "активний" : status}
    </span>
  );
}
