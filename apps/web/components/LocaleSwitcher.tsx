"use client";

import { useLocale, useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useState, useRef, useEffect } from "react";
import { Globe, Check } from "lucide-react";
import clsx from "clsx";
import {
  LOCALE_COOKIE,
  LOCALE_META,
  locales,
  type Locale,
} from "@/i18n/config";

export function LocaleSwitcher() {
  const locale = useLocale() as Locale;
  const t = useTranslations("localeSwitcher");
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (!containerRef.current) return;
      if (!containerRef.current.contains(e.target as Node)) setOpen(false);
    }
    if (open) document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, [open]);

  function setLocale(next: Locale) {
    if (next === locale) {
      setOpen(false);
      return;
    }
    document.cookie = `${LOCALE_COOKIE}=${next}; path=/; max-age=${60 * 60 * 24 * 365}; SameSite=Lax`;
    setOpen(false);
    router.refresh();
  }

  const current = LOCALE_META[locale];

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label={t("label")}
        title={t("label")}
        aria-expanded={open}
        aria-haspopup="listbox"
        className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-border bg-bg-card hover:border-accent text-text-body text-sm font-medium transition-colors"
      >
        <Globe size={14} className="text-accent" />
        <span className="hidden sm:inline">{current.flag}</span>
        <span className="hidden md:inline">{locale.toUpperCase()}</span>
        <span className="inline sm:hidden">{current.flag}</span>
      </button>

      {open && (
        <ul
          role="listbox"
          aria-label={t("label")}
          className="absolute right-0 mt-1 z-50 min-w-[180px] rounded-xl border border-border bg-bg-card shadow-elevated overflow-hidden"
        >
          {locales.map((code) => {
            const meta = LOCALE_META[code];
            const active = code === locale;
            return (
              <li key={code} role="option" aria-selected={active}>
                <button
                  type="button"
                  onClick={() => setLocale(code)}
                  className={clsx(
                    "w-full flex items-center gap-2.5 px-3 py-2 text-sm hover:bg-bg-subtle text-left transition-colors",
                    active && "bg-accent-subtle text-accent-deep",
                  )}
                >
                  <span className="text-base leading-none">{meta.flag}</span>
                  <span className="flex-1">{meta.nativeLabel}</span>
                  {active && <Check size={14} className="text-accent-deep" />}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
