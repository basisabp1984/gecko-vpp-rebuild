"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { BookOpen, ArrowLeft, ExternalLink } from "lucide-react";
import { useSyncExternalStore } from "react";
import { useThemeStore } from "@/lib/store";

// Scalar imports a ton of CSS + Vue runtime in a Vite-style bundle.
// Load it client-only via next/dynamic to keep the SSR-side bundle clean.
const ApiReferenceReact = dynamic(
  () =>
    import("@scalar/api-reference-react").then((m) => ({
      default: m.ApiReferenceReact,
    })),
  {
    ssr: false,
    loading: () => (
      <div className="h-[60vh] flex items-center justify-center text-sm text-text-muted">
        Завантаження Scalar API Reference…
      </div>
    ),
  },
);

// Stable hydrated signal so we can pick a Scalar theme matching app theme.
function subscribe() {
  return () => {};
}
function getClientSnapshot() {
  return true;
}
function getServerSnapshot() {
  return false;
}

export default function ApiExplorerPage() {
  const theme = useThemeStore((s) => s.theme);
  const hydrated = useSyncExternalStore(
    subscribe,
    getClientSnapshot,
    getServerSnapshot,
  );
  const isDark = hydrated && theme === "dark";

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <header className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 mb-1 text-xs text-text-muted">
            <Link
              href="/developer"
              className="inline-flex items-center gap-1 hover:text-accent-deep transition-colors"
            >
              <ArrowLeft size={12} /> Developer
            </Link>
            <span>/</span>
            <span>API Explorer</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-text-heading flex items-center gap-2">
            <BookOpen size={22} className="text-accent-deep" /> API Explorer
          </h1>
          <p className="text-sm text-text-muted">
            Інтерактивна документація OpenAPI 3.1 (Scalar). Спробуйте будь-який ендпоінт прямо у
            браузері.
          </p>
        </div>
        <a
          href="/api/openapi"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border bg-bg-card hover:border-accent text-sm font-medium text-text-body transition-colors self-start sm:self-auto"
        >
          openapi.json (raw) <ExternalLink size={13} />
        </a>
      </header>

      {/* Scalar embed */}
      <div className="rounded-xl border border-border bg-bg-card overflow-hidden shadow-card scalar-frame">
        <ApiReferenceReact
          configuration={{
            url: "/api/openapi",
            theme: "default",
            darkMode: isDark,
            hideClientButton: false,
            hideDarkModeToggle: false,
            layout: "modern",
            // Identify this instance to Scalar
            slug: "krytsia-api",
          }}
        />
      </div>
    </div>
  );
}
