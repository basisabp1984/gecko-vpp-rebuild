"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Factory, Building2, Battery, Code2, ShieldCheck, Home } from "lucide-react";
import clsx from "clsx";

const PERSONAS: Array<{
  href: string;
  label: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
  match: (path: string) => boolean;
}> = [
  { href: "/", label: "Огляд", icon: Home, match: (p) => p === "/" },
  {
    href: "/producer",
    label: "Виробник",
    icon: Factory,
    match: (p) => p.startsWith("/producer"),
  },
  {
    href: "/c-i",
    label: "C&I",
    icon: Building2,
    match: (p) => p.startsWith("/c-i"),
  },
  {
    href: "/storage",
    label: "УЗЕ",
    icon: Battery,
    match: (p) => p.startsWith("/storage"),
  },
  {
    href: "/developer",
    label: "Developer",
    icon: Code2,
    match: (p) => p.startsWith("/developer"),
  },
  {
    href: "/admin",
    label: "Admin",
    icon: ShieldCheck,
    match: (p) => p.startsWith("/admin"),
  },
];

export function PersonaSwitcher() {
  const pathname = usePathname() ?? "/";
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
            {p.label}
          </Link>
        );
      })}
    </nav>
  );
}
