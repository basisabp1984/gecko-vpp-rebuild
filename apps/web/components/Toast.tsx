"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import clsx from "clsx";
import { CheckCircle2, AlertTriangle, Info, X } from "lucide-react";

export type ToastTone = "success" | "warning" | "alert" | "info";

interface ToastItem {
  id: number;
  tone: ToastTone;
  title: string;
  description?: string;
  ttl: number;
}

interface ToastContextValue {
  push: (t: Omit<ToastItem, "id" | "ttl"> & { ttl?: number }) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    // Safe fallback — log to console if provider missing
    return {
      push: (t) => {
        if (typeof window !== "undefined") {
          // eslint-disable-next-line no-console
          console.warn("[Toast no provider]", t);
        }
      },
    };
  }
  return ctx;
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);

  const push = useCallback<ToastContextValue["push"]>((t) => {
    const id = Date.now() + Math.random();
    const item: ToastItem = {
      id,
      tone: t.tone,
      title: t.title,
      description: t.description,
      ttl: t.ttl ?? 4500,
    };
    setItems((prev) => [...prev, item]);
    setTimeout(() => {
      setItems((prev) => prev.filter((x) => x.id !== id));
    }, item.ttl);
  }, []);

  return (
    <ToastContext.Provider value={{ push }}>
      {children}
      <div className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 max-w-sm w-full pointer-events-none">
        {items.map((it) => (
          <ToastCard
            key={it.id}
            item={it}
            onClose={() =>
              setItems((prev) => prev.filter((x) => x.id !== it.id))
            }
          />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

function ToastCard({
  item,
  onClose,
}: {
  item: ToastItem;
  onClose: () => void;
}) {
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setVisible(true), 10);
    return () => clearTimeout(t);
  }, []);

  const Icon =
    item.tone === "success"
      ? CheckCircle2
      : item.tone === "alert" || item.tone === "warning"
        ? AlertTriangle
        : Info;

  const toneClass =
    item.tone === "success"
      ? "border-success/40 bg-success/10 text-success"
      : item.tone === "warning"
        ? "border-warning/40 bg-warning/10 text-warning"
        : item.tone === "alert"
          ? "border-alert/40 bg-alert/10 text-alert"
          : "border-info/40 bg-info/10 text-info";

  return (
    <div
      className={clsx(
        "pointer-events-auto rounded-xl border bg-bg-card shadow-elevated p-3 flex items-start gap-3 transition-all duration-200",
        toneClass,
        visible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-2",
      )}
    >
      <Icon size={18} className="mt-0.5 shrink-0" />
      <div className="flex-1 min-w-0">
        <div className="text-sm font-semibold text-text-heading">
          {item.title}
        </div>
        {item.description && (
          <div className="text-xs text-text-muted mt-0.5 break-words">
            {item.description}
          </div>
        )}
      </div>
      <button
        type="button"
        onClick={onClose}
        className="text-text-muted hover:text-text-body p-0.5"
        aria-label="Закрити сповіщення"
      >
        <X size={14} />
      </button>
    </div>
  );
}
