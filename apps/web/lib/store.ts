"use client";

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import { DEFAULT_TENANT_ID } from "./tenants";

/* -------------------------------------------------------------------------- */
/* Tenant store                                                                */
/* -------------------------------------------------------------------------- */

interface TenantState {
  currentTenantId: string;
  setTenantId: (id: string) => void;
}

export const useTenantStore = create<TenantState>()(
  persist(
    (set) => ({
      currentTenantId: DEFAULT_TENANT_ID,
      setTenantId: (id) => set({ currentTenantId: id }),
    }),
    {
      name: "gecko-tenant",
      storage: createJSONStorage(() => localStorage),
    },
  ),
);

/* -------------------------------------------------------------------------- */
/* Theme store                                                                 */
/* -------------------------------------------------------------------------- */

export type Theme = "light" | "dark";

interface ThemeState {
  theme: Theme;
  setTheme: (t: Theme) => void;
  toggleTheme: () => void;
}

function applyTheme(t: Theme) {
  if (typeof document === "undefined") return;
  if (t === "dark") document.documentElement.setAttribute("data-theme", "dark");
  else document.documentElement.removeAttribute("data-theme");
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set, get) => ({
      theme: "light",
      setTheme: (t) => {
        applyTheme(t);
        set({ theme: t });
      },
      toggleTheme: () => {
        const next = get().theme === "light" ? "dark" : "light";
        applyTheme(next);
        set({ theme: next });
      },
    }),
    {
      name: "gecko-theme",
      storage: createJSONStorage(() => localStorage),
      onRehydrateStorage: () => (state) => {
        if (state) applyTheme(state.theme);
      },
    },
  ),
);
