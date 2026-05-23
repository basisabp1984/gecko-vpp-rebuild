"use client";

import type { ReactNode } from "react";
import { useTranslations } from "next-intl";
import { KrytsiaLogo } from "./KrytsiaLogo";
import { TenantSwitcher } from "./TenantSwitcher";
import { PersonaSwitcher } from "./PersonaSwitcher";
import { CommandPaletteTrigger } from "./CommandPaletteTrigger";
import { AlertsBell } from "./AlertsBell";
import { AgentChat } from "./AgentChat";
import { VoiceButton } from "./VoiceButton";
import { ThemeToggle } from "./ThemeToggle";
import { LocaleSwitcher } from "./LocaleSwitcher";

export function AppShell({ children }: { children: ReactNode }) {
  const t = useTranslations("footer");
  return (
    <div className="min-h-screen flex flex-col">
      <header className="sticky top-0 z-40 border-b border-border bg-bg-card/90 backdrop-blur">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 h-16 flex items-center gap-4">
          <KrytsiaLogo />
          <div className="hidden lg:block w-px h-6 bg-border" />
          <PersonaSwitcher />
          <div className="flex-1" />
          <CommandPaletteTrigger />
          <TenantSwitcher />
          <div className="flex items-center gap-1">
            <LocaleSwitcher />
            <AlertsBell />
            <VoiceButton />
            <ThemeToggle />
          </div>
        </div>
      </header>

      <main className="flex-1 mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8 py-6">
        {children}
      </main>

      {/* AgentChat is mounted globally so its FAB is reachable from any page */}
      <AgentChat />

      <footer className="border-t border-border bg-bg-card/50">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-4 flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-text-muted">
          <span>{t("tagline")}</span>
          <div className="flex items-center gap-4">
            <a
              href="https://github.com/basisabp1984/gecko-vpp-rebuild"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-accent-deep transition-colors"
            >
              {t("github")}
            </a>
            <a
              href="/developer"
              className="hover:text-accent-deep transition-colors"
            >
              {t("developers")}
            </a>
            <a
              href="https://vpp.radai-1984.dev"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-accent-deep transition-colors"
            >
              {t("v1")}
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
