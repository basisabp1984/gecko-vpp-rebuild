"use client";

import { Search } from "lucide-react";
import { useCommandPalette } from "./CommandPalette";

export function CommandPaletteTrigger() {
  const { toggle } = useCommandPalette();

  return (
    <button
      type="button"
      onClick={toggle}
      className="hidden lg:flex items-center gap-2 px-3 py-1.5 rounded-lg border border-border bg-bg-subtle hover:border-accent transition-colors text-sm text-text-muted min-w-[220px]"
      aria-label="Відкрити команд-палітру"
    >
      <Search size={14} />
      <span className="flex-1 text-left">Пошук та команди…</span>
      <kbd className="font-mono text-xs px-1.5 py-0.5 rounded border border-border bg-bg-card">
        Ctrl K
      </kbd>
    </button>
  );
}
