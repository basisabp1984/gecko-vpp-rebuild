"use client";

import { useEffect, useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import clsx from "clsx";
import {
  Leaf,
  ScrollText,
  Cog,
  BadgeCheck,
  Loader2,
  Coins,
  PiggyBank,
} from "lucide-react";
import { useAPI, fetchAPI, ApiError } from "@/lib/api";
import { useTenantStore } from "@/lib/store";
import { TENANTS } from "@/lib/tenants";
import { Tabs } from "@/components/Tabs";
import { KPITile } from "@/components/KPITile";
import { KEPSignBadge } from "@/components/KEPSignBadge";
import { useToast } from "@/components/Toast";
import {
  formatUAH,
  formatUAHCompact,
  formatNumber,
  formatTonnes,
  formatPercent,
  formatDate,
} from "@/lib/format";

type ReportTab = "fin" | "tech" | "esg" | "reg";

interface SettlementRow {
  id: number;
  statement_no: string;
  counterparty: string;
  counterparty_edrpou: string;
  contract_no: string;
  period_year: number;
  period_month: number;
  period_start: string;
  period_end: string;
  volume_total_mwh: string;
  amount_net_uah: string;
  amount_vat_uah: string;
  amount_gross_uah: string;
  payment_due_date: string;
  status: string;
}

interface AssetMini {
  id: string;
  display_name: string;
  asset_class: string;
  capacity_mw: string;
}

interface KpiDaily {
  asset_id: string;
  date: string;
  grn_saved_uah: string;
  grn_earned_uah: string;
  imbalance_mwh: string;
  co2_avoided_tn: string;
  availability_pct: string;
  opportunity_score: number;
}

interface SignedDoc {
  id: number;
  document_type: string;
  document_ref_table: string;
  document_ref_id: number;
  signer_name: string;
  signer_position: string;
  signer_edrpou: string;
  acsk_name: string;
  signature_format: string;
  document_hash_sha256: string;
  signed_at: string;
  is_demo_stub: boolean;
  kep_badge_short: string;
}

const TABS: { id: ReportTab; label: string; icon: React.ReactNode }[] = [
  { id: "fin", label: "Платежі", icon: <Coins size={14} /> },
  { id: "tech", label: "Активи", icon: <Cog size={14} /> },
  { id: "esg", label: "ESG", icon: <Leaf size={14} /> },
  { id: "reg", label: "Документи", icon: <ScrollText size={14} /> },
];

export default function CIReportsPage() {
  useEffect(() => {
    const { currentTenantId, setTenantId } = useTenantStore.getState();
    if (currentTenantId === TENANTS.producer.id) {
      setTenantId(TENANTS.ci.id);
    }
  }, []);

  const [active, setActive] = useState<ReportTab>("fin");
  return (
    <div className="flex flex-col gap-5">
      <header>
        <h1 className="text-2xl sm:text-3xl font-bold text-text-heading">
          Звіти — Бізнес
        </h1>
        <p className="text-sm text-text-muted">
          Платежі за електроенергію, операційні показники активів, ESG-метрики
          та підписані документи КЕП (демо).
        </p>
      </header>

      <Tabs
        items={TABS.map((t) => ({
          id: t.id,
          label: (
            <span className="inline-flex items-center gap-1.5">
              {t.icon}
              {t.label}
            </span>
          ),
        }))}
        active={active}
        onChange={(id) => setActive(id as ReportTab)}
      />

      {active === "fin" && <FinancialTab />}
      {active === "tech" && <TechnicalTab />}
      {active === "esg" && <EsgTab />}
      {active === "reg" && <RegulatoryTab />}
    </div>
  );
}

function FinancialTab() {
  const settlements = useAPI<SettlementRow[]>(
    "/api/v1/regulatory/settlements",
    { period: "monthly" },
  );
  const rows = settlements.data?.data ?? [];

  const totals = useMemo(() => {
    let net = 0;
    let gross = 0;
    let vol = 0;
    for (const r of rows) {
      net += parseFloat(r.amount_net_uah);
      gross += parseFloat(r.amount_gross_uah);
      vol += parseFloat(r.volume_total_mwh);
    }
    return { net, gross, vol, count: rows.length };
  }, [rows]);

  return (
    <div className="flex flex-col gap-4">
      <section className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <KPITile
          label="Платежі (брутто)"
          value={formatUAHCompact(totals.gross)}
          icon={<Coins size={18} />}
          tone="warning"
          sublabel="за період"
        />
        <KPITile
          label="Платежі (нетто)"
          value={formatUAHCompact(totals.net)}
          icon={<PiggyBank size={18} />}
          sublabel="без ПДВ"
        />
        <KPITile
          label="Обсяг"
          value={`${formatNumber(totals.vol, 0)} МВт·год`}
          sublabel="спожито"
        />
        <KPITile
          label="Актів"
          value={String(totals.count)}
          sublabel="у періоді"
        />
      </section>

      <section className="rounded-xl border border-border bg-bg-card shadow-card overflow-hidden">
        <header className="p-4 border-b border-border">
          <h2 className="text-base font-semibold text-text-heading">
            Платежі за електроенергію
          </h2>
        </header>
        {settlements.isLoading ? (
          <div className="p-8 text-center text-sm text-text-muted">
            Завантаження…
          </div>
        ) : rows.length === 0 ? (
          <div className="p-8 text-center text-sm text-text-muted">
            Актів не знайдено.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-bg-subtle text-xs uppercase tracking-wide text-text-muted">
                <tr>
                  <th className="px-4 py-2 text-left">Акт</th>
                  <th className="px-4 py-2 text-left">Контрагент</th>
                  <th className="px-4 py-2 text-left">Період</th>
                  <th className="px-4 py-2 text-right">Обсяг</th>
                  <th className="px-4 py-2 text-right">Сума (брутто)</th>
                  <th className="px-4 py-2 text-left">Статус</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r, i) => (
                  <tr
                    key={r.id}
                    className={clsx(
                      "border-t border-border",
                      i % 2 === 1 && "bg-bg-subtle/30",
                    )}
                  >
                    <td className="px-4 py-2 font-mono text-[11px] text-text-body">
                      {r.statement_no}
                    </td>
                    <td className="px-4 py-2 text-text-heading">
                      {r.counterparty}
                      <div className="text-[10px] text-text-muted">
                        ЄДРПОУ {r.counterparty_edrpou}
                      </div>
                    </td>
                    <td className="px-4 py-2 text-xs text-text-muted">
                      {r.period_year}-
                      {String(r.period_month).padStart(2, "0")}
                    </td>
                    <td className="px-4 py-2 text-right font-mono text-xs">
                      {formatNumber(r.volume_total_mwh, 1)}
                    </td>
                    <td className="px-4 py-2 text-right font-mono text-xs text-text-heading font-medium">
                      {formatUAH(r.amount_gross_uah)}
                    </td>
                    <td className="px-4 py-2">
                      <SettlementStatusBadge status={r.status} />
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

function SettlementStatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    SIGNED: "bg-success/15 text-success",
    PENDING: "bg-warning/15 text-warning",
    DRAFT: "bg-bg-subtle text-text-muted",
    PAID: "bg-success/15 text-success",
  };
  const tone = map[status] ?? "bg-bg-subtle text-text-muted";
  return (
    <span
      className={clsx(
        "inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium",
        tone,
      )}
    >
      {status}
    </span>
  );
}

function TechnicalTab() {
  const date_start = useMemo(() => {
    const d = new Date();
    d.setDate(d.getDate() - 30);
    return d.toISOString().slice(0, 10);
  }, []);
  const date_end = new Date().toISOString().slice(0, 10);

  const assets = useAPI<AssetMini[]>("/api/v1/assets");
  const kpi = useAPI<KpiDaily[]>("/api/v1/ems/kpi/daily", {
    date_start,
    date_end,
  });

  const perAsset = useMemo(() => {
    const map = new Map<
      string,
      { availSum: number; n: number; savedSum: number }
    >();
    for (const r of kpi.data?.data ?? []) {
      const cur = map.get(r.asset_id) ?? {
        availSum: 0,
        n: 0,
        savedSum: 0,
      };
      cur.availSum += parseFloat(r.availability_pct);
      cur.savedSum += parseFloat(r.grn_saved_uah);
      cur.n += 1;
      map.set(r.asset_id, cur);
    }
    return (assets.data?.data ?? []).map((a) => {
      const v = map.get(a.id);
      const avg = v && v.n > 0 ? v.availSum / v.n : null;
      return {
        ...a,
        availability: avg,
        saved: v?.savedSum ?? 0,
        downtime: avg !== null ? ((100 - avg) / 100) * 24 * 30 : null,
      };
    });
  }, [kpi.data, assets.data]);

  return (
    <section className="rounded-xl border border-border bg-bg-card shadow-card overflow-hidden">
      <header className="p-4 border-b border-border">
        <h2 className="text-base font-semibold text-text-heading">
          Активи — операційні показники (30 днів)
        </h2>
      </header>
      {kpi.isLoading || assets.isLoading ? (
        <div className="p-8 text-center text-sm text-text-muted">
          Завантаження…
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-bg-subtle text-xs uppercase tracking-wide text-text-muted">
              <tr>
                <th className="px-4 py-2 text-left">Актив</th>
                <th className="px-4 py-2 text-left">Тип</th>
                <th className="px-4 py-2 text-right">Потужність</th>
                <th className="px-4 py-2 text-right">Доступність</th>
                <th className="px-4 py-2 text-right">Простої (год)</th>
                <th className="px-4 py-2 text-right">Зекономлено</th>
              </tr>
            </thead>
            <tbody>
              {perAsset.map((a, i) => (
                <tr
                  key={a.id}
                  className={clsx(
                    "border-t border-border",
                    i % 2 === 1 && "bg-bg-subtle/30",
                  )}
                >
                  <td className="px-4 py-2 text-text-heading">
                    {a.display_name}
                  </td>
                  <td className="px-4 py-2 text-text-body">{a.asset_class}</td>
                  <td className="px-4 py-2 text-right font-mono text-xs">
                    {formatNumber(a.capacity_mw, 1)} МВт
                  </td>
                  <td className="px-4 py-2 text-right">
                    <span
                      className={clsx(
                        "font-mono text-xs font-medium",
                        a.availability !== null && a.availability >= 95
                          ? "text-success"
                          : "text-warning",
                      )}
                    >
                      {formatPercent(a.availability, 1)}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-right font-mono text-xs">
                    {a.downtime === null ? "—" : formatNumber(a.downtime, 1)}
                  </td>
                  <td className="px-4 py-2 text-right font-mono text-xs text-text-heading">
                    {formatUAHCompact(a.saved)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function EsgTab() {
  const date_start = useMemo(() => {
    const d = new Date();
    d.setDate(d.getDate() - 30);
    return d.toISOString().slice(0, 10);
  }, []);
  const date_end = new Date().toISOString().slice(0, 10);

  const assets = useAPI<AssetMini[]>("/api/v1/assets");
  const kpi = useAPI<KpiDaily[]>("/api/v1/ems/kpi/daily", {
    date_start,
    date_end,
  });

  const perAsset = useMemo(() => {
    const map = new Map<string, number>();
    for (const r of kpi.data?.data ?? []) {
      map.set(
        r.asset_id,
        (map.get(r.asset_id) ?? 0) + parseFloat(r.co2_avoided_tn),
      );
    }
    return (assets.data?.data ?? [])
      .map((a) => ({ ...a, co2: map.get(a.id) ?? 0 }))
      .sort((a, b) => b.co2 - a.co2);
  }, [kpi.data, assets.data]);

  const total = perAsset.reduce((s, a) => s + a.co2, 0);

  return (
    <div className="flex flex-col gap-4">
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        <KPITile
          label="CO₂ уникнено"
          value={formatTonnes(total)}
          icon={<Leaf size={18} />}
          tone="success"
          sublabel="30 днів"
        />
        <KPITile
          label="Потенціал кредитів"
          value={formatUAHCompact(total * 1100)}
          sublabel="за €25/т"
          tone="info"
        />
        <KPITile
          label="Власна генерація активів"
          value={String(perAsset.filter((a) => a.asset_class === "СЕС").length)}
          sublabel="дах-СЕС"
        />
      </section>

      <section className="rounded-xl border border-border bg-bg-card shadow-card overflow-hidden">
        <header className="p-4 border-b border-border">
          <h2 className="text-base font-semibold text-text-heading">
            CO₂ уникнено на актив
          </h2>
        </header>
        <ul className="divide-y divide-border">
          {perAsset.map((a) => {
            const pct = total > 0 ? (a.co2 / total) * 100 : 0;
            return (
              <li key={a.id} className="p-4 flex items-center gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-medium text-text-heading truncate">
                      {a.display_name}
                    </span>
                    <span className="text-sm font-mono text-success">
                      {formatTonnes(a.co2)}
                    </span>
                  </div>
                  <div className="mt-1.5 h-2 rounded-full bg-bg-subtle overflow-hidden">
                    <div
                      className="h-full bg-success transition-all"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <div className="mt-1 text-xs text-text-muted">
                    {a.asset_class} · {formatNumber(pct, 1)}% від портфеля
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      </section>
    </div>
  );
}

function RegulatoryTab() {
  const toast = useToast();
  const qc = useQueryClient();
  const docs = useAPI<SignedDoc[]>("/api/v1/regulatory/documents");
  const rows = docs.data?.data ?? [];

  const signMut = useMutation<
    { signed_doc_id?: number; badge_text?: string; is_demo_stub?: boolean },
    ApiError,
    number
  >({
    mutationFn: async (refId) => {
      const res = await fetchAPI<{ signed_doc_id?: number }>(
        `/api/v1/regulatory/documents/${refId}/sign`,
        { method: "POST", body: {} },
      );
      return res.data;
    },
    onSuccess: (_d, refId) => {
      toast.push({
        tone: "success",
        title: `Документ #${refId} підписано КЕП`,
        description: "Демо-підпис, водяний знак ДЕМО",
      });
      qc.invalidateQueries({
        predicate: (q) =>
          typeof q.queryKey?.[1] === "string" &&
          (q.queryKey[1] as string).startsWith("/api/v1/regulatory/documents"),
      });
    },
    onError: (e) =>
      toast.push({
        tone: "alert",
        title: "Помилка підпису",
        description: e.message,
      }),
  });

  return (
    <section className="flex flex-col gap-3">
      <div className="rounded-xl border border-warning/40 bg-warning/10 p-3 text-xs text-warning flex items-start gap-2">
        <BadgeCheck size={16} className="shrink-0 mt-0.5" />
        <div>
          Усі підписи в системі є <strong>демонстраційними (ДЕМО)</strong> і не
          мають юридичної сили. Реальна інтеграція з АЦСК та КЕП-провайдером —
          частина продакшен-релізу.
        </div>
      </div>

      {docs.isLoading ? (
        <div className="p-8 text-center text-sm text-text-muted">
          Завантаження документів…
        </div>
      ) : rows.length === 0 ? (
        <div className="p-8 text-center text-sm text-text-muted">
          Документів немає.
        </div>
      ) : (
        <ul className="flex flex-col gap-3">
          {rows.slice(0, 12).map((d) => (
            <li
              key={d.id}
              className="rounded-xl border border-border bg-bg-card shadow-card p-4 flex flex-col lg:flex-row gap-4"
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-accent-subtle text-accent-deep">
                    {d.document_type}
                  </span>
                  <span className="text-xs text-text-muted">
                    {d.document_ref_table} #{d.document_ref_id}
                  </span>
                </div>
                <h3 className="text-sm font-semibold text-text-heading mt-1">
                  Документ #{d.id} — {d.document_type}
                </h3>
                <p className="text-xs text-text-muted">
                  Формат {d.signature_format} · АЦСК {d.acsk_name} · підписано{" "}
                  {formatDate(d.signed_at)}
                </p>
                <button
                  type="button"
                  onClick={() => signMut.mutate(d.document_ref_id)}
                  disabled={signMut.isPending}
                  className="mt-2 inline-flex items-center gap-1.5 px-3 py-1 rounded text-xs border border-accent text-accent hover:bg-accent hover:text-text-inverse disabled:opacity-50"
                >
                  {signMut.isPending &&
                  signMut.variables === d.document_ref_id ? (
                    <Loader2 size={11} className="animate-spin" />
                  ) : (
                    <BadgeCheck size={11} />
                  )}
                  Підписати через КЕП (демо)
                </button>
              </div>
              <div className="lg:w-80 shrink-0">
                <KEPSignBadge
                  isDemo={true}
                  signerName={d.signer_name}
                  position={d.signer_position}
                  edrpou={d.signer_edrpou}
                  acskName={d.acsk_name}
                  signedAt={d.signed_at}
                  hashShort={d.document_hash_sha256}
                />
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
