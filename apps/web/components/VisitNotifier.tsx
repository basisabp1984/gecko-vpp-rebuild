"use client";

import { useEffect } from "react";
import { usePathname, useSearchParams } from "next/navigation";

const ADMIN_KEY = "krytsia-admin";

export function VisitNotifier() {
  const pathname = usePathname();
  const params = useSearchParams();

  useEffect(() => {
    if (typeof window === "undefined") return;

    // Visiting with ?admin=1 marks this device as admin — no notifications hereafter.
    if (params.get("admin") === "1") {
      try {
        localStorage.setItem(ADMIN_KEY, "1");
      } catch {
        // ignore — localStorage may be blocked, in which case admin flag won't persist
      }
      return;
    }

    let isAdmin = false;
    try {
      isAdmin = localStorage.getItem(ADMIN_KEY) === "1";
    } catch {
      // ignore
    }
    if (isAdmin) return;

    fetch("/api/notify-visit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: pathname, referrer: document.referrer }),
      keepalive: true,
    }).catch(() => {
      // swallow — visit notification is best-effort
    });
  }, [pathname, params]);

  return null;
}
