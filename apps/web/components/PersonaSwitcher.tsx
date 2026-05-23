"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { Factory, Building2, Battery, ShieldCheck, Home } from "lucide-react";
import clsx from "clsx";

const PERSONAS: Array<{
  href: string;
  key: "overview" | "producer" | "ci" | "storage" | "admin";
  icon: React.ComponentType<{ size?: number; className?: string }>;
  match: (path: string) => boolean;
}> = [
  { href: "/", key: "overview", icon: Home, match: (p) => p === "/" },
  {
    href: "/producer",
    key: "producer",
    icon: Factory,
    match: (p) => p.startsWith("/producer"),
  },
  {
    href: "/c-i",
    key: "ci",
    icon: Building2,
    match: (p) => p.startsWith("/c-i"),
  },
  {
    href: "/storage",
    key: "storage",
    icon: Battery,
    match: (p) => p.startsWith("/storage"),
  },
  {
    href: "/admin",
    key: "admin",
    icon: ShieldCheck,
    match: (p) => p.startsWith("/admin"),
  },
];

export function PersonaSwitcher() {
  const pathname = usePathname() ?? "/";
  const t = useTranslations("nav");
  return (
    <nav className="hidden md:flex items-center gap-1">
      {PERSONAS.map((p) => {
        const active = p.match(pathname);
        const Icon = p.icon;
        return (
          <Link
            key={p.href}
            href={p.href}
            className={clsx(
              "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors",
              active
                ? "bg-accent-subtle text-accent-deep"
                : "text-text-muted hover:text-text-heading hover:bg-bg-subtle",
            )}
          >
            <Icon size={14} />
            {t(p.key)}
          </Link>
        );
      })}
    </nav>
  );
}
