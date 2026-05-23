"use client";

import { useState, useRef, useEffect } from "react";
import { ChevronDown, Building2, Factory, Battery } from "lucide-react";
import clsx from "clsx";
import { useTenantStore } from "@/lib/store";
import { TENANT_LIST, type TenantKind } from "@/lib/tenants";

const ICONS: Record<TenantKind, React.ComponentType<{ size?: number; className?: string }>> = {
  producer: Factory,
  ci: Building2,
  storage: Battery,
};

export function TenantSwitcher() {
  const currentId = useTenantStore((s) => s.currentTenantId);
  const setTenantId = useTenantStore((s) => s.setTenantId);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const current = TENANT_LIST.find((t) => t.id === currentId) ?? TENANT_LIST[0];
  const Icon = ICONS[current.kind];

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-border bg-bg-card hover:border-accent transition-colors text-sm"
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <Icon size={16} className="text-accent" />
        <span className="font-medium text-text-heading">{current.name}</span>
        <ChevronDown size={14} className="text-text-muted" />
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-72 rounded-lg border border-border bg-bg-card shadow-elevated z-50 overflow-hidden">
          {TENANT_LIST.map((t) => {
            const TIcon = ICONS[t.kind];
            const active = t.id === currentId;
            return (
              <button
                key={t.id}
                type="button"
                onClick={() => {
                  setTenantId(t.id);
                  setOpen(false);
                }}
                className={clsx(
                  "w-full flex items-start gap-3 px-3 py-2.5 text-left hover:bg-bg-subtle transition-colors",
                  active && "bg-accent-subtle",
                )}
              >
                <TIcon
                  size={18}
                  className={clsx(active ? "text-accent-deep" : "text-accent")}
                />
                <span className="flex-1 min-w-0">
                  <span className="block text-sm font-medium text-text-heading truncate">
                    {t.name}
                  </span>
                  <span className="block text-xs text-text-muted truncate">
                    {t.description}
                  </span>
                </span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
