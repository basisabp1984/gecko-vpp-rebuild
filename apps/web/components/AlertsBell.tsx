"use client";

import { Bell } from "lucide-react";
import { useAPI } from "@/lib/api";

interface RegulatoryEvent {
  id: number;
  severity: string;
}

export function AlertsBell() {
  const { data } = useAPI<RegulatoryEvent[]>("/api/v1/regulatory/events");
  const count = data?.data?.length ?? 0;
  return (
    <button
      type="button"
      aria-label="Сповіщення"
      title="Сповіщення"
      className="relative p-2 rounded-lg border border-border bg-bg-card hover:border-accent transition-colors text-text-body"
    >
      <Bell size={16} />
      {count > 0 && (
        <span className="absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1 rounded-full bg-alert text-text-inverse text-[10px] font-bold flex items-center justify-center">
          {count > 9 ? "9+" : count}
        </span>
      )}
    </button>
  );
}
