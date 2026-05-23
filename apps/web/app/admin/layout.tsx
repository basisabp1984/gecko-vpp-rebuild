"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ShieldCheck, Eye, Cpu, BarChart3 } from "lucide-react";
import clsx from "clsx";
import type { ReactNode } from "react";

const TABS = [
  { href: "/admin/engage", label: "Engage", icon: Eye },
  { href: "/admin/operate", label: "Operate", icon: Cpu },
  { href: "/admin/analyze", label: "Analyze", icon: BarChart3 },
];

export default function AdminLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname() ?? "";

  return (
    <div className="flex flex-col gap-5">
      <header className="flex flex-col gap-3">
        <div className="flex items-center gap-2 text-sm text-text-muted">
          <ShieldCheck size={14} className="text-accent-deep" />
          <span className="font-semibold text-text-heading">Operator Console</span>
          <span className="text-text-muted">/ cross-tenant</span>
        </div>
        <nav className="inline-flex rounded-lg border border-border bg-bg-card p-1 self-start shadow-card">
          {TABS.map((t) => {
            const active =
              pathname === t.href ||
              (pathname === "/admin" && t.href === "/admin/engage");
            const Icon = t.icon;
            return (
              <Link
                key={t.href}
                href={t.href}
                className={clsx(
                  "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors",
                  active
                    ? "bg-accent text-text-inverse"
                    : "text-text-muted hover:text-text-heading hover:bg-bg-subtle",
                )}
              >
                <Icon size={14} />
                {t.label}
              </Link>
            );
          })}
        </nav>
      </header>

      <div>{children}</div>
    </div>
  );
}
