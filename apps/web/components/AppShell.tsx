"use client";

import type { ReactNode } from "react";
import { KrytsiaLogo } from "./KrytsiaLogo";
import { TenantSwitcher } from "./TenantSwitcher";
import { PersonaSwitcher } from "./PersonaSwitcher";
import { CommandPaletteTrigger } from "./CommandPaletteTrigger";
import { AlertsBell } from "./AlertsBell";
import { AgentChat } from "./AgentChat";
import { VoiceButton } from "./VoiceButton";
import { ThemeToggle } from "./ThemeToggle";

export function AppShell({ children }: { children: ReactNode }) {
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
            <AlertsBell />
            <AgentChat />
            <VoiceButton />
            <ThemeToggle />
          </div>
        </div>
      </header>

      <main className="flex-1 mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8 py-6">
        {children}
      </main>

      <footer className="border-t border-border bg-bg-card/50">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-4 flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-text-muted">
          <span>© 2026 Krytsia. Інтелектуальний шар для критичної енергетичної інфраструктури.</span>
          <div className="flex items-center gap-4">
            <a
              href="https://github.com/basisabp1984/agentic-dev-framework"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-accent-deep transition-colors"
            >
              GitHub
            </a>
            <a
              href="https://vpp.radai-1984.dev"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-accent-deep transition-colors"
            >
              v1 продакшен
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
