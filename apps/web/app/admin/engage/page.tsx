"use client";

import Link from "next/link";
import { useMemo } from "react";
import { Factory, Building2, Battery, ArrowRight, AlertTriangle } from "lucide-react";
import { useAPI } from "@/lib/api";
import { ArchitectureDiagram } from "@/components/diagram/ArchitectureDiagram";
import { KPITile } from "@/components/KPITile";
import { formatUAHCompact, formatNumber } from "@/lib/format";

interface PortfolioRow {
  tenant_id: string;
  code: string;
  display_name: string;
  segment: "producer" | "c-i" | "storage";
  asset_count: number;
  capacity_mw: string;
  revenue_30d_uah: string;
}

interface PortfolioPayload {
  tenants: PortfolioRow[];
}

const SEGMENT_META: Record<
  PortfolioRow["segment"],
  {
    icon: React.ComponentType<{ size?: number; className?: string }>;
    href: string;
    label: string;
    accent: string;
  }
> = {
  producer: {
    icon: Factory,
    href: "/producer",
    label: "Виробник",
    accent: "text-accent-deep",
  },
  "c-i": {
    icon: Building2,
    href: "/c-i",
    label: "C&I",
    accent: "text-info",
  },
  storage: {
    icon: Battery,
    href: "/storage",
    label: "УЗЕ",
    accent: "text-success",
  },
};

export default function AdminEngagePage() {
  const portfolio = useAPI<PortfolioPayload>("/api/v1/admin/portfolio");

  const totals = useMemo(() => {
    const rows = portfolio.data?.data.tenants ?? [];
    return rows.reduce(
      (acc, r) => {
        acc.tenants += 1;
        acc.assets += r.asset_count;
        acc.capacityMw += parseFloat(r.capacity_mw);
        acc.revenue30dUah += parseFloat(r.revenue_30d_uah);
        return acc;
      },
      { tenants: 0, assets: 0, capacityMw: 0, revenue30dUah: 0 },
    );
  }, [portfolio.data]);

  const tenants = portfolio.data?.data.tenants ?? [];

  return (
    <div className="flex flex-col gap-6">
      <header>
        <h1 className="text-2xl sm:text-3xl font-bold text-text-heading">
          GECKO VPP · Operator Console / Engage
        </h1>
        <p className="text-sm text-text-muted">
          Крос-тенантна оглядова панель. Бачите тих самих учасників, що й на діаграмі головної.
        </p>
      </header>

      {/* Aggregate KPIs */}
      <section className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <KPITile
          label="Тенантів"
          value={portfolio.isLoading ? "—" : String(totals.tenants)}
          sublabel="у портфелі"
        />
        <KPITile
          label="Активів"
          value={portfolio.isLoading ? "—" : String(totals.assets)}
          sublabel="усього"
        />
        <KPITile
          label="Сум. потужність"
          value={
            portfolio.isLoading
              ? "—"
              : `${formatNumber(totals.capacityMw, 1)} МВт`
          }
          sublabel="вст. потужність"
        />
        <KPITile
          label="Виторг (30 діб)"
          value={
            portfolio.isLoading
              ? "—"
              : formatUAHCompact(totals.revenue30dUah)
          }
          sublabel="усі тенанти"
          tone="success"
        />
      </section>

      {/* Architecture diagram (operator mental model) */}
      <section className="rounded-xl border border-border bg-bg-card p-4 sm:p-6 shadow-card">
        <ArchitectureDiagram />
      </section>

      {/* Tenant cards */}
      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold text-text-heading">Тенанти</h2>
        {portfolio.isError ? (
          <div className="rounded-xl border border-alert/40 bg-alert/10 p-4 flex items-start gap-3">
            <AlertTriangle size={16} className="text-alert mt-0.5 shrink-0" />
            <div>
              <div className="text-sm font-semibold text-text-heading">
                Не вдалося завантажити портфель
              </div>
              <p className="text-sm text-text-muted">{portfolio.error.message}</p>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {(portfolio.isLoading
              ? [null, null, null]
              : tenants
            ).map((t, i) => {
              if (!t)
                return (
                  <div
                    key={i}
                    className="rounded-xl border border-border bg-bg-card p-5 shadow-card animate-pulse h-44"
                  />
                );
              const meta = SEGMENT_META[t.segment];
              const Icon = meta.icon;
              return (
                <Link
                  key={t.tenant_id}
                  href={meta.href}
                  className="rounded-xl border border-border bg-bg-card p-5 shadow-card hover:border-accent transition-colors group flex flex-col gap-3"
                >
                  <div className="flex items-center justify-between">
                    <span className={`inline-flex items-center justify-center w-9 h-9 rounded-lg bg-accent-subtle ${meta.accent}`}>
                      <Icon size={16} />
                    </span>
                    <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full border border-border bg-bg-subtle text-text-muted">
                      {meta.label}
                    </span>
                  </div>
                  <div>
                    <h3 className="text-base font-semibold text-text-heading leading-tight">
                      {t.display_name}
                    </h3>
                    <code className="text-[10px] text-text-muted block truncate font-mono">
                      {t.tenant_id}
                    </code>
                  </div>
                  <dl className="grid grid-cols-3 gap-2 text-xs">
                    <div>
                      <dt className="text-text-muted">Активи</dt>
                      <dd className="font-semibold text-text-heading">{t.asset_count}</dd>
                    </div>
                    <div>
                      <dt className="text-text-muted">МВт</dt>
                      <dd className="font-semibold text-text-heading">
                        {formatNumber(t.capacity_mw, 0)}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-text-muted">30 діб</dt>
                      <dd className="font-semibold text-text-heading">
                        {formatUAHCompact(t.revenue_30d_uah)}
                      </dd>
                    </div>
                  </dl>
                  <span className="inline-flex items-center gap-1 text-xs text-accent-deep group-hover:gap-2 transition-all">
                    Перейти до кабінету <ArrowRight size={12} />
                  </span>
                </Link>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
