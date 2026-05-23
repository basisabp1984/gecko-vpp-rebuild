"use client";

import { Moon, Sun } from "lucide-react";
import { useSyncExternalStore } from "react";
import { useThemeStore } from "@/lib/store";

// Subscribe to nothing — we only need a stable "is hydrated" signal.
// Server snapshot returns `false`, client snapshot returns `true`.
function subscribe() {
  return () => {};
}
function getClientSnapshot() {
  return true;
}
function getServerSnapshot() {
  return false;
}

export function ThemeToggle() {
  const theme = useThemeStore((s) => s.theme);
  const toggle = useThemeStore((s) => s.toggleTheme);
  const hydrated = useSyncExternalStore(
    subscribe,
    getClientSnapshot,
    getServerSnapshot,
  );

  const isDark = hydrated && theme === "dark";

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={isDark ? "Світла тема" : "Темна тема"}
      title={isDark ? "Світла тема" : "Темна тема"}
      className="p-2 rounded-lg border border-border bg-bg-card hover:border-accent transition-colors text-text-body"
    >
      {isDark ? <Sun size={16} /> : <Moon size={16} />}
    </button>
  );
}
