"use client";

import { ShieldCheck } from "lucide-react";
import clsx from "clsx";

/**
 * КЕП-підпис із обов'язковою позначкою "ДЕМО".
 *
 * Архітектурний контракт §11.20: компонент завжди рендерить водяний знак
 * "ДЕМО" і `isDemo: true` обов'язковий пропс типу literal `true` —
 * це гарантує на рівні компіляції, що жоден виклик не може випадково
 * створити враження "справжнього" підпису.
 */
export interface KEPSignBadgeProps {
  /** Обов'язково `true`. Жодна реалізація не може передати інше значення. */
  isDemo: true;
  signerName: string;
  edrpou: string;
  signedAt: string | Date;
  hashShort?: string | null;
  position?: string | null;
  acskName?: string | null;
  className?: string;
}

export function KEPSignBadge({
  isDemo,
  signerName,
  edrpou,
  signedAt,
  hashShort,
  position,
  acskName,
  className,
}: KEPSignBadgeProps) {
  // Захист на рантаймі (типи це і так гарантують, але демонструємо намір).
  if (!isDemo) {
    throw new Error("KEPSignBadge: isDemo must be literal true");
  }

  const d =
    typeof signedAt === "string" ? new Date(signedAt) : signedAt;
  const dateStr = Number.isNaN(d.getTime())
    ? String(signedAt)
    : `${String(d.getDate()).padStart(2, "0")}.${String(
        d.getMonth() + 1,
      ).padStart(2, "0")}.${d.getFullYear()} ${String(d.getHours()).padStart(
        2,
        "0",
      )}:${String(d.getMinutes()).padStart(2, "0")}`;

  const shortHash =
    hashShort && hashShort.length > 8 ? hashShort.slice(0, 8) : hashShort;

  return (
    <div
      className={clsx(
        "relative overflow-hidden rounded-lg border border-success/40 bg-success/5 p-3 text-xs",
        className,
      )}
    >
      {/* Водяний знак "ДЕМО" — завжди видимий */}
      <span
        aria-hidden="true"
        className="pointer-events-none absolute -right-2 top-1/2 -translate-y-1/2 rotate-[-18deg] select-none text-[64px] font-black uppercase tracking-tighter text-warning/15"
      >
        ДЕМО
      </span>

      <div className="relative flex items-start gap-2">
        <ShieldCheck
          size={16}
          className="mt-0.5 shrink-0 text-success"
          aria-hidden="true"
        />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold text-text-heading">
              {signerName}
            </span>
            <span className="inline-flex items-center rounded bg-warning/20 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-warning">
              Демо-підпис
            </span>
          </div>
          {position && (
            <div className="text-text-muted">{position}</div>
          )}
          <div className="text-text-muted">
            ЄДРПОУ <span className="font-mono">{edrpou}</span>
            {acskName && (
              <>
                {" · АЦСК "}
                {acskName}
              </>
            )}
          </div>
          <div className="text-text-muted">
            Підписано {dateStr}
            {shortHash && (
              <>
                {" · хеш "}
                <span className="font-mono">{shortHash}…</span>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
