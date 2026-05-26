"use client";

import { GraduationCap } from "lucide-react";
import { usePathname } from "next/navigation";
import { startTour } from "./Tour";

const TOUR_PATHS = ["/producer"];

export function TourButton() {
  const pathname = usePathname() ?? "";
  const hasTour = TOUR_PATHS.some(
    (p) => pathname === p || pathname.startsWith(`${p}/`),
  );
  if (!hasTour) return null;

  return (
    <button
      type="button"
      onClick={startTour}
      title="Запустити покроковий тур"
      aria-label="Запустити покроковий тур"
      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border bg-bg-card hover:border-accent transition-colors text-text-body text-sm font-medium"
    >
      <GraduationCap size={16} />
      <span className="hidden sm:inline">Навчання</span>
    </button>
  );
}
