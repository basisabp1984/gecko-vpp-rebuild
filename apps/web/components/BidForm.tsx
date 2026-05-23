"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { X, Loader2, Send } from "lucide-react";
import { fetchAPI, ApiError } from "@/lib/api";
import { useToast } from "@/components/Toast";

interface BidSubmitIn {
  market: string;
  delivery_date: string;
  hour: number;
  side: string;
  bid_type?: string;
  volume_mwh: number;
  price_uah_mwh: number;
  resource_eic?: string;
  participant_eic?: string;
}

interface BidSubmitResult {
  id?: number;
  bid_id?: string;
  state?: string;
  [k: string]: unknown;
}

const MARKETS = ["RDN", "VDR", "BR"] as const;
const SIDES = ["SELL", "BUY"] as const;

export function BidForm({
  open,
  onClose,
  defaultMarket = "RDN",
}: {
  open: boolean;
  onClose: () => void;
  defaultMarket?: string;
}) {
  const toast = useToast();
  const qc = useQueryClient();

  const today = new Date().toISOString().slice(0, 10);

  const [market, setMarket] = useState(defaultMarket);
  const [deliveryDate, setDeliveryDate] = useState(today);
  const [hour, setHour] = useState(12);
  const [side, setSide] = useState<string>("SELL");
  const [volume, setVolume] = useState("5");
  const [price, setPrice] = useState("3500");
  const [resourceEic, setResourceEic] = useState("10W-UA-ASSET-001");

  const mut = useMutation<BidSubmitResult, ApiError, BidSubmitIn>({
    mutationFn: async (payload) => {
      const res = await fetchAPI<BidSubmitResult>("/api/v1/market/bids", {
        method: "POST",
        body: payload,
      });
      return res.data;
    },
    onSuccess: (data) => {
      toast.push({
        tone: "success",
        title: "Заявку подано",
        description: `ID: ${data.bid_id ?? data.id ?? "—"} · стан: ${data.state ?? "ACTIVE"}`,
      });
      qc.invalidateQueries({
        predicate: (q) => {
          const key = q.queryKey?.[1];
          return typeof key === "string" && key.startsWith("/api/v1/market/bids");
        },
      });
      onClose();
    },
    onError: (err) => {
      toast.push({
        tone: "alert",
        title: "Не вдалося подати заявку",
        description: err.message,
      });
    },
  });

  function submit(e: React.FormEvent) {
    e.preventDefault();
    mut.mutate({
      market,
      delivery_date: deliveryDate,
      hour,
      side,
      bid_type: "SIMPLE",
      volume_mwh: parseFloat(volume),
      price_uah_mwh: parseFloat(price),
      resource_eic: resourceEic || undefined,
    });
  }

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-black/40"
        onClick={onClose}
        aria-hidden="true"
      />
      <div className="relative w-full max-w-lg rounded-xl border border-border bg-bg-card shadow-elevated">
        <header className="flex items-center justify-between px-5 py-4 border-b border-border">
          <div>
            <h2 className="text-lg font-semibold text-text-heading">
              Подати заявку на ринок
            </h2>
            <p className="text-xs text-text-muted">
              POST /api/v1/market/bids
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded hover:bg-bg-subtle"
            aria-label="Закрити"
          >
            <X size={18} />
          </button>
        </header>

        <form onSubmit={submit} className="p-5 space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <Field label="Ринок">
              <select
                value={market}
                onChange={(e) => setMarket(e.target.value)}
                className="w-full rounded-md border border-border bg-bg-page px-3 py-2 text-sm"
              >
                {MARKETS.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Сторона">
              <select
                value={side}
                onChange={(e) => setSide(e.target.value)}
                className="w-full rounded-md border border-border bg-bg-page px-3 py-2 text-sm"
              >
                {SIDES.map((s) => (
                  <option key={s} value={s}>
                    {s === "SELL" ? "Продаж (SELL)" : "Купівля (BUY)"}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Дата постачання">
              <input
                type="date"
                value={deliveryDate}
                onChange={(e) => setDeliveryDate(e.target.value)}
                className="w-full rounded-md border border-border bg-bg-page px-3 py-2 text-sm"
              />
            </Field>
            <Field label="Година (1-24)">
              <input
                type="number"
                min={1}
                max={24}
                value={hour}
                onChange={(e) => setHour(parseInt(e.target.value, 10) || 1)}
                className="w-full rounded-md border border-border bg-bg-page px-3 py-2 text-sm"
              />
            </Field>
            <Field label="Обсяг (МВт·год)">
              <input
                type="number"
                step="0.1"
                min={0}
                value={volume}
                onChange={(e) => setVolume(e.target.value)}
                className="w-full rounded-md border border-border bg-bg-page px-3 py-2 text-sm"
              />
            </Field>
            <Field label="Ціна (грн/МВт·год)">
              <input
                type="number"
                step="0.01"
                value={price}
                onChange={(e) => setPrice(e.target.value)}
                className="w-full rounded-md border border-border bg-bg-page px-3 py-2 text-sm"
              />
            </Field>
            <Field label="Resource EIC" full>
              <input
                type="text"
                value={resourceEic}
                onChange={(e) => setResourceEic(e.target.value)}
                placeholder="10W-UA-ASSET-001"
                className="w-full rounded-md border border-border bg-bg-page px-3 py-2 text-sm font-mono"
              />
            </Field>
          </div>

          <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-1.5 rounded-lg border border-border bg-bg-card text-sm hover:border-accent"
            >
              Скасувати
            </button>
            <button
              type="submit"
              disabled={mut.isPending}
              className="inline-flex items-center gap-2 px-4 py-1.5 rounded-lg bg-accent text-text-inverse text-sm font-medium hover:bg-accent-deep disabled:opacity-50"
            >
              {mut.isPending ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <Send size={14} />
              )}
              Подати заявку
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function Field({
  label,
  children,
  full,
}: {
  label: string;
  children: React.ReactNode;
  full?: boolean;
}) {
  return (
    <label className={full ? "col-span-2 block" : "block"}>
      <span className="block text-xs uppercase tracking-wide text-text-muted mb-1">
        {label}
      </span>
      {children}
    </label>
  );
}
