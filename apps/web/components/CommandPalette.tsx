"use client";

import { Command } from "cmdk";
import { useRouter, usePathname } from "next/navigation";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  Home,
  Factory,
  Building2,
  Battery,
  Code2,
  ShieldCheck,
  Sun,
  Moon,
  Repeat,
  Zap,
  Send,
  MapPin,
  Bell,
  Activity,
  Search,
  type LucideIcon,
} from "lucide-react";
import { useTenantStore, useThemeStore } from "@/lib/store";
import { TENANTS } from "@/lib/tenants";

/* -------------------------------------------------------------------------- */
/* Context for opening the palette from any component                         */
/* -------------------------------------------------------------------------- */

interface CommandPaletteContextValue {
  open: boolean;
  setOpen: (v: boolean) => void;
  toggle: () => void;
}

const CommandPaletteContext = createContext<CommandPaletteContextValue | null>(
  null,
);

export function useCommandPalette(): CommandPaletteContextValue {
  const ctx = useContext(CommandPaletteContext);
  if (!ctx) {
    return {
      open: false,
      setOpen: () => {},
      toggle: () => {},
    };
  }
  return ctx;
}

/* -------------------------------------------------------------------------- */
/* Action model                                                                */
/* -------------------------------------------------------------------------- */

interface Action {
  id: string;
  label: string;
  hint?: string;
  group: string;
  keywords?: string[];
  icon: LucideIcon;
  run: (api: ActionAPI) => void;
}

interface ActionAPI {
  router: ReturnType<typeof useRouter>;
  setTenantId: (id: string) => void;
  setTheme: (t: "light" | "dark") => void;
  toggleTheme: () => void;
  close: () => void;
}

/* -------------------------------------------------------------------------- */
/* Action list — built once with stable IDs                                   */
/* -------------------------------------------------------------------------- */

const PERSONA_SUBPAGES: Record<string, Array<{ label: string; segment: string }>> = {
  producer: [
    { label: "Активи", segment: "aktyvy" },
    { label: "Прогнози", segment: "prognozy" },
    { label: "Диспетчеризація", segment: "dyspetcheryzatsiya" },
    { label: "Ринок", segment: "rynok" },
    { label: "УЗЕ", segment: "uze" },
    { label: "Сповіщення", segment: "spovishchennya" },
    { label: "Звіти", segment: "zvity" },
    { label: "Налаштування", segment: "nalashtuvannya" },
  ],
  "c-i": [
    { label: "Активи", segment: "aktyvy" },
    { label: "Прогнози", segment: "prognozy" },
    { label: "Ринок", segment: "rynok" },
    { label: "Звіти", segment: "zvity" },
  ],
  storage: [
    { label: "Активи", segment: "aktyvy" },
    { label: "УЗЕ", segment: "uze" },
    { label: "Ринок", segment: "rynok" },
    { label: "Звіти", segment: "zvity" },
  ],
};

function buildActions(currentPath: string): Action[] {
  const out: Action[] = [];

  // ---- Top-level navigation ----
  const navItems: Array<{
    href: string;
    label: string;
    icon: LucideIcon;
    keywords?: string[];
  }> = [
    { href: "/", label: "Перейти до Hero", icon: Home, keywords: ["home", "огляд", "головна"] },
    { href: "/producer", label: "Виробник", icon: Factory, keywords: ["producer", "сес", "поляна"] },
    { href: "/c-i", label: "Бізнес (C&I)", icon: Building2, keywords: ["ci", "industry", "завод"] },
    { href: "/storage", label: "Зберігання (УЗЕ)", icon: Battery, keywords: ["storage", "battery", "узе"] },
    { href: "/developer", label: "Розробники", icon: Code2, keywords: ["developer", "api", "sdk"] },
    { href: "/admin", label: "Admin", icon: ShieldCheck, keywords: ["admin", "operator", "console"] },
  ];
  for (const n of navItems) {
    out.push({
      id: `nav:${n.href}`,
      group: "Навігація",
      label: n.label,
      hint: n.href,
      icon: n.icon,
      keywords: n.keywords,
      run: ({ router, close }) => {
        router.push(n.href);
        close();
      },
    });
  }

  // ---- Persona sub-pages (only if currently inside that persona) ----
  const currentPersonaSegment = currentPath.split("/")[1];
  const personaSubs = PERSONA_SUBPAGES[currentPersonaSegment];
  if (personaSubs) {
    for (const sub of personaSubs) {
      const href = `/${currentPersonaSegment}/${sub.segment}`;
      out.push({
        id: `nav-sub:${href}`,
        group: `${currentPersonaSegment} — підрозділи`,
        label: sub.label,
        hint: href,
        icon: MapPin,
        run: ({ router, close }) => {
          router.push(href);
          close();
        },
      });
    }
  }

  // ---- Admin sub-tabs (always accessible) ----
  const adminTabs = [
    { href: "/admin/engage", label: "Admin · Engage" },
    { href: "/admin/operate", label: "Admin · Operate" },
    { href: "/admin/analyze", label: "Admin · Analyze" },
  ];
  for (const t of adminTabs) {
    out.push({
      id: `nav-admin:${t.href}`,
      group: "Admin",
      label: t.label,
      hint: t.href,
      icon: ShieldCheck,
      run: ({ router, close }) => {
        router.push(t.href);
        close();
      },
    });
  }

  // ---- Tenant switch ----
  const tenantItems: Array<{ kind: keyof typeof TENANTS; label: string; icon: LucideIcon }> = [
    { kind: "producer", label: "Перемкнути на producer (Поляна Енерго)", icon: Factory },
    { kind: "ci", label: "Перемкнути на c-i (Карпатський завод)", icon: Building2 },
    { kind: "storage", label: "Перемкнути на storage (БСЗ Захід-1)", icon: Battery },
  ];
  for (const t of tenantItems) {
    const tenant = TENANTS[t.kind];
    out.push({
      id: `tenant:${tenant.id}`,
      group: "Тенант",
      label: t.label,
      hint: tenant.id.slice(0, 8) + "…",
      icon: t.icon,
      keywords: ["tenant", "switch", tenant.name],
      run: ({ setTenantId, close }) => {
        setTenantId(tenant.id);
        close();
      },
    });
  }

  // ---- Theme ----
  out.push(
    {
      id: "theme:light",
      group: "Тема",
      label: "Світла тема",
      icon: Sun,
      keywords: ["theme", "light"],
      run: ({ setTheme, close }) => {
        setTheme("light");
        close();
      },
    },
    {
      id: "theme:dark",
      group: "Тема",
      label: "Темна тема",
      icon: Moon,
      keywords: ["theme", "dark"],
      run: ({ setTheme, close }) => {
        setTheme("dark");
        close();
      },
    },
    {
      id: "theme:toggle",
      group: "Тема",
      label: "Перемкнути тему",
      icon: Repeat,
      keywords: ["theme", "toggle"],
      run: ({ toggleTheme, close }) => {
        toggleTheme();
        close();
      },
    },
  );

  // ---- Quick actions ----
  out.push(
    {
      id: "qa:optimise",
      group: "Швидкі дії",
      label: "Запустити оптимізацію",
      hint: "/producer · сценарій arbitrage",
      icon: Zap,
      keywords: ["optimise", "оптимізація", "run"],
      run: ({ router, close }) => {
        router.push("/producer/dyspetcheryzatsiya");
        close();
      },
    },
    {
      id: "qa:submit-forecast",
      group: "Швидкі дії",
      label: "Подати прогноз",
      hint: "/producer/prognozy",
      icon: Send,
      keywords: ["forecast", "прогноз", "submit"],
      run: ({ router, close }) => {
        router.push("/producer/prognozy");
        close();
      },
    },
    {
      id: "qa:bid",
      group: "Швидкі дії",
      label: "Виставити заявку на ринок",
      hint: "/producer/rynok",
      icon: Activity,
      keywords: ["bid", "заявка", "market"],
      run: ({ router, close }) => {
        router.push("/producer/rynok");
        close();
      },
    },
    {
      id: "qa:alerts",
      group: "Швидкі дії",
      label: "Переглянути сповіщення",
      hint: "/producer/spovishchennya",
      icon: Bell,
      keywords: ["alerts", "events", "сповіщення"],
      run: ({ router, close }) => {
        router.push("/producer/spovishchennya");
        close();
      },
    },
    {
      id: "qa:api-explorer",
      group: "Швидкі дії",
      label: "Відкрити API Explorer",
      hint: "/developer/api/explorer",
      icon: Code2,
      keywords: ["api", "swagger", "scalar", "openapi"],
      run: ({ router, close }) => {
        router.push("/developer/api/explorer");
        close();
      },
    },
  );

  return out;
}

/* -------------------------------------------------------------------------- */
/* Provider + Modal                                                            */
/* -------------------------------------------------------------------------- */

export function CommandPaletteProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const toggle = useCallback(() => setOpen((v) => !v), []);

  // Global Ctrl+K / Cmd+K
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        toggle();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [toggle]);

  // Lock body scroll when open
  useEffect(() => {
    if (!open) return;
    const original = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = original;
    };
  }, [open]);

  return (
    <CommandPaletteContext.Provider value={{ open, setOpen, toggle }}>
      {children}
      {open && <CommandPaletteModal onClose={() => setOpen(false)} />}
    </CommandPaletteContext.Provider>
  );
}

function CommandPaletteModal({ onClose }: { onClose: () => void }) {
  const router = useRouter();
  const pathname = usePathname() ?? "/";
  const setTenantId = useTenantStore((s) => s.setTenantId);
  const setTheme = useThemeStore((s) => s.setTheme);
  const toggleTheme = useThemeStore((s) => s.toggleTheme);

  const actions = useMemo(() => buildActions(pathname), [pathname]);

  // Group actions in insertion order
  const grouped = useMemo(() => {
    const groups = new Map<string, Action[]>();
    for (const a of actions) {
      const arr = groups.get(a.group);
      if (arr) arr.push(a);
      else groups.set(a.group, [a]);
    }
    return Array.from(groups.entries());
  }, [actions]);

  function runAction(a: Action) {
    a.run({
      router,
      setTenantId,
      setTheme,
      toggleTheme,
      close: onClose,
    });
  }

  return (
    <div
      className="fixed inset-0 z-[200] flex items-start justify-center pt-[15vh] px-4"
      role="dialog"
      aria-modal="true"
      aria-label="Команд-палітра"
    >
      <button
        type="button"
        aria-label="Закрити команд-палітру"
        className="absolute inset-0 bg-black/40 backdrop-blur-sm cursor-default"
        onClick={onClose}
      />
      <div className="relative w-full max-w-xl rounded-xl border border-border bg-bg-card shadow-elevated overflow-hidden">
        <Command
          label="Команд-палітра"
          shouldFilter
          loop
          className="flex flex-col"
        >
          <div className="flex items-center gap-2 px-4 py-3 border-b border-border">
            <Search size={16} className="text-text-muted shrink-0" />
            <Command.Input
              autoFocus
              placeholder="Шукати дію або сторінку…"
              className="flex-1 bg-transparent outline-none text-sm text-text-body placeholder:text-text-muted"
              onKeyDown={(e) => {
                if (e.key === "Escape") {
                  e.preventDefault();
                  onClose();
                }
              }}
            />
            <kbd className="hidden sm:inline text-[10px] font-mono px-1.5 py-0.5 rounded border border-border bg-bg-subtle text-text-muted">
              Esc
            </kbd>
          </div>

          <Command.List className="max-h-[60vh] overflow-y-auto p-2 scrollbar-thin">
            <Command.Empty className="px-4 py-8 text-center text-sm text-text-muted">
              Нічого не знайдено.
            </Command.Empty>

            {grouped.map(([group, items]) => (
              <Command.Group
                key={group}
                heading={group}
                className="mb-2 [&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-[10px] [&_[cmdk-group-heading]]:font-semibold [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-wider [&_[cmdk-group-heading]]:text-text-muted"
              >
                {items.map((a) => {
                  const Icon = a.icon;
                  // Build a fuzzy-search value from label + keywords + hint
                  const value = [a.label, ...(a.keywords ?? []), a.hint ?? ""].join(" ");
                  return (
                    <Command.Item
                      key={a.id}
                      value={value}
                      onSelect={() => runAction(a)}
                      className="flex items-center gap-3 px-3 py-2 rounded-md text-sm cursor-pointer text-text-body data-[selected=true]:bg-accent-subtle data-[selected=true]:text-accent-deep"
                    >
                      <Icon size={14} className="shrink-0 opacity-80" />
                      <span className="flex-1 truncate">{a.label}</span>
                      {a.hint && (
                        <span className="text-[10px] font-mono text-text-muted truncate max-w-[180px]">
                          {a.hint}
                        </span>
                      )}
                    </Command.Item>
                  );
                })}
              </Command.Group>
            ))}
          </Command.List>

          <div className="border-t border-border px-3 py-2 text-[11px] text-text-muted flex items-center justify-between bg-bg-subtle">
            <span>↑↓ навігація · Enter обрати · Esc закрити</span>
            <span className="font-mono">{actions.length} дій</span>
          </div>
        </Command>
      </div>
    </div>
  );
}
