"use client";

import type { ReactNode } from "react";
import clsx from "clsx";

export interface TabItem {
  id: string;
  label: ReactNode;
  badge?: ReactNode;
}

export interface TabsProps {
  items: TabItem[];
  active: string;
  onChange: (id: string) => void;
  size?: "sm" | "md";
}

export function Tabs({ items, active, onChange, size = "md" }: TabsProps) {
  return (
    <div
      role="tablist"
      className="flex flex-wrap gap-1 rounded-lg border border-border bg-bg-subtle p-1"
    >
      {items.map((it) => {
        const isActive = it.id === active;
        return (
          <button
            key={it.id}
            role="tab"
            aria-selected={isActive}
            type="button"
            onClick={() => onChange(it.id)}
            className={clsx(
              "inline-flex items-center gap-2 rounded-md font-medium transition-colors",
              size === "sm" ? "px-3 py-1.5 text-xs" : "px-4 py-2 text-sm",
              isActive
                ? "bg-bg-card text-text-heading shadow-card"
                : "text-text-muted hover:text-text-body",
            )}
          >
            <span>{it.label}</span>
            {it.badge !== undefined && it.badge !== null && (
              <span
                className={clsx(
                  "inline-flex items-center justify-center rounded-full px-1.5 text-[10px] font-semibold",
                  isActive
                    ? "bg-accent-subtle text-accent-deep"
                    : "bg-border text-text-muted",
                )}
              >
                {it.badge}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
