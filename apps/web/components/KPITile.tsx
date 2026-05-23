"use client";

import type { ReactNode } from "react";
import clsx from "clsx";
import { TrendingDown, TrendingUp, Minus } from "lucide-react";

export interface KPITileProps {
  label: string;
  value: ReactNode;
  sublabel?: ReactNode;
  delta?: number | null; // percentage change
  deltaLabel?: string;
  icon?: ReactNode;
  tone?: "default" | "success" | "warning" | "alert" | "info";
}

const TONES: Record<NonNullable<KPITileProps["tone"]>, string> = {
  default: "text-accent-deep",
  success: "text-success",
  warning: "text-warning",
  alert: "text-alert",
  info: "text-info",
};

export function KPITile({
  label,
  value,
  sublabel,
  delta,
  deltaLabel,
  icon,
  tone = "default",
}: KPITileProps) {
  const dir =
    delta === null || delta === undefined || delta === 0
      ? "flat"
      : delta > 0
        ? "up"
        : "down";
  return (
    <div className="rounded-xl border border-border bg-bg-card p-4 shadow-card flex flex-col gap-2 min-h-[120px]">
      <div className="flex items-start justify-between gap-2">
        <span className="text-xs font-medium text-text-muted uppercase tracking-wide">
          {label}
        </span>
        {icon && <span className={clsx("opacity-80", TONES[tone])}>{icon}</span>}
      </div>
      <div className="flex items-baseline gap-2">
        <span className={clsx("text-2xl font-bold text-text-heading", TONES[tone])}>
          {value}
        </span>
      </div>
      <div className="flex items-center justify-between text-xs">
        <span className="text-text-muted">{sublabel}</span>
        {delta !== null && delta !== undefined && (
          <span
            className={clsx(
              "flex items-center gap-1 font-medium",
              dir === "up" && "text-success",
              dir === "down" && "text-alert",
              dir === "flat" && "text-text-muted",
            )}
          >
            {dir === "up" && <TrendingUp size={12} />}
            {dir === "down" && <TrendingDown size={12} />}
            {dir === "flat" && <Minus size={12} />}
            {Math.abs(delta).toFixed(1)}%{deltaLabel ? ` ${deltaLabel}` : ""}
          </span>
        )}
      </div>
    </div>
  );
}
