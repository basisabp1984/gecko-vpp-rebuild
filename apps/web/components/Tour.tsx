"use client";

import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  useSyncExternalStore,
} from "react";
import { createPortal } from "react-dom";

// Stable subscribe + hydration-aware snapshots (same pattern as ThemeToggle)
const noopSubscribe = () => () => {};
const getClientMounted = () => true;
const getServerMounted = () => false;

export interface TourStep {
  selector: string | null;
  title: string;
  text: string;
  soft?: boolean;
}

interface TourProps {
  steps: TourStep[];
  storageKey: string;
  startDelayMs?: number;
}

type BubbleArrow = "up" | "down" | "left" | "right" | "none";

interface BubblePos {
  top: number;
  left: number;
  arrow: BubbleArrow;
}

const START_EVENT = "kr-tour-start";

export function Tour({ steps, storageKey, startDelayMs = 700 }: TourProps) {
  const mounted = useSyncExternalStore(
    noopSubscribe,
    getClientMounted,
    getServerMounted,
  );
  const [currentStep, setCurrentStep] = useState(-1);
  const [pos, setPos] = useState<BubblePos | null>(null);

  const bubbleRef = useRef<HTMLDivElement | null>(null);
  const highlightedRef = useRef<HTMLElement | null>(null);
  const highlightedClsRef = useRef<string | null>(null);

  const clearHighlight = useCallback(() => {
    if (highlightedRef.current && highlightedClsRef.current) {
      highlightedRef.current.classList.remove(highlightedClsRef.current);
    }
    highlightedRef.current = null;
    highlightedClsRef.current = null;
  }, []);

  const endTour = useCallback(() => {
    clearHighlight();
    setCurrentStep(-1);
    setPos(null);
    try {
      localStorage.setItem(storageKey, "1");
    } catch {
      /* private mode — ignore */
    }
  }, [clearHighlight, storageKey]);

  const nextStep = useCallback(() => {
    if (currentStep >= steps.length - 1) {
      endTour();
      return;
    }
    setCurrentStep((s) => s + 1);
  }, [currentStep, steps.length, endTour]);

  const prevStep = useCallback(() => {
    setCurrentStep((s) => (s <= 0 ? s : s - 1));
  }, []);

  // Auto-start: ?tour=1 OR first visit (storageKey not set)
  useEffect(() => {
    if (!mounted) return;
    let forceTour = false;
    try {
      const params = new URLSearchParams(window.location.search);
      forceTour = params.get("tour") === "1";
    } catch {
      /* ignore */
    }
    let seen = false;
    try {
      seen = !!localStorage.getItem(storageKey);
    } catch {
      /* private mode */
    }
    if (forceTour || !seen) {
      const t = setTimeout(() => setCurrentStep(0), startDelayMs);
      return () => clearTimeout(t);
    }
  }, [mounted, storageKey, startDelayMs]);

  // Listen for global "kr-tour-start" event (from TourButton)
  useEffect(() => {
    if (!mounted) return;
    const onStart = () => setCurrentStep(0);
    window.addEventListener(START_EVENT, onStart);
    return () => window.removeEventListener(START_EVENT, onStart);
  }, [mounted]);

  // Whenever step changes — apply highlight + scroll into view
  useEffect(() => {
    clearHighlight();
    if (currentStep < 0) return;
    const step = steps[currentStep];
    if (!step) return;

    let target: HTMLElement | null = null;
    if (step.selector) {
      try {
        target = document.querySelector<HTMLElement>(step.selector);
      } catch {
        target = null;
      }
    }
    const visible =
      !!target &&
      (target.offsetParent !== null ||
        getComputedStyle(target).position === "fixed");

    if (visible && target) {
      target.scrollIntoView({ block: "center", behavior: "smooth" });
      const t = setTimeout(() => {
        const cls = step.soft ? "kr-tour-highlight-soft" : "kr-tour-highlight";
        target.classList.add(cls);
        highlightedRef.current = target;
        highlightedClsRef.current = cls;
      }, 250);
      return () => clearTimeout(t);
    }
  }, [currentStep, steps, clearHighlight]);

  // Position bubble after each step render and on resize
  const positionBubble = useCallback(() => {
    const bubble = bubbleRef.current;
    if (!bubble || currentStep < 0) return;
    const step = steps[currentStep];
    let target: HTMLElement | null = null;
    if (step.selector) {
      try {
        target = document.querySelector<HTMLElement>(step.selector);
      } catch {
        target = null;
      }
    }
    const visible =
      !!target &&
      (target.offsetParent !== null ||
        getComputedStyle(target).position === "fixed");

    const margin = 16;
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const bw = bubble.offsetWidth;
    const bh = bubble.offsetHeight;

    if (!visible || !target) {
      setPos({
        top: Math.max(20, (vh - bh) / 2),
        left: Math.max(20, (vw - bw) / 2),
        arrow: "none",
      });
      return;
    }

    const r = target.getBoundingClientRect();
    let arrow: BubbleArrow;
    let top: number;
    let left: number;

    if (r.bottom + bh + margin <= vh) {
      arrow = "up";
      top = r.bottom + margin;
      left = Math.max(12, Math.min(r.left, vw - bw - 12));
    } else if (r.top - bh - margin >= 0) {
      arrow = "down";
      top = r.top - bh - margin;
      left = Math.max(12, Math.min(r.left, vw - bw - 12));
    } else if (r.right + bw + margin <= vw) {
      arrow = "left";
      top = Math.max(12, Math.min(r.top, vh - bh - 12));
      left = r.right + margin;
    } else if (r.left - bw - margin >= 0) {
      arrow = "right";
      top = Math.max(12, Math.min(r.top, vh - bh - 12));
      left = r.left - bw - margin;
    } else {
      arrow = "none";
      top = Math.max(20, (vh - bh) / 2);
      left = Math.max(20, (vw - bw) / 2);
    }
    setPos({ top, left, arrow });
  }, [currentStep, steps]);

  // Position right after layout, and re-position after the highlight settles.
  useLayoutEffect(() => {
    if (currentStep < 0) return;
    positionBubble();
    const t = setTimeout(positionBubble, 320); // after smooth scroll + 250ms highlight
    return () => clearTimeout(t);
  }, [currentStep, positionBubble]);

  // Keyboard nav + resize
  useEffect(() => {
    if (currentStep < 0) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") endTour();
      else if (e.key === "ArrowRight" || e.key === "Enter") nextStep();
      else if (e.key === "ArrowLeft") prevStep();
    };
    const onResize = () => positionBubble();
    document.addEventListener("keydown", onKey);
    window.addEventListener("resize", onResize);
    window.addEventListener("scroll", onResize, { passive: true });
    return () => {
      document.removeEventListener("keydown", onKey);
      window.removeEventListener("resize", onResize);
      window.removeEventListener("scroll", onResize);
    };
  }, [currentStep, endTour, nextStep, prevStep, positionBubble]);

  // Cleanup on unmount
  useEffect(() => clearHighlight, [clearHighlight]);

  if (!mounted || currentStep < 0) return null;
  const step = steps[currentStep];
  if (!step) return null;

  const total = steps.length;
  const isFirst = currentStep === 0;
  const isLast = currentStep === total - 1;

  // Derive "target missing" inline (no state needed)
  let targetMissing = false;
  if (step.selector && typeof document !== "undefined") {
    try {
      const el = document.querySelector<HTMLElement>(step.selector);
      const visible =
        !!el &&
        (el.offsetParent !== null ||
          getComputedStyle(el).position === "fixed");
      targetMissing = !visible;
    } catch {
      targetMissing = true;
    }
  }

  return createPortal(
    <>
      <div className="kr-tour-backdrop" onClick={endTour} />
      <div
        ref={bubbleRef}
        className={`kr-tour-bubble kr-arrow-${pos?.arrow ?? "none"}`}
        style={{
          top: pos?.top ?? -9999,
          left: pos?.left ?? -9999,
          visibility: pos ? "visible" : "hidden",
        }}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="kr-tour-title"
      >
        <div className="kr-tour-bubble-progress">
          Крок {currentStep + 1} з {total}
        </div>
        <h3 id="kr-tour-title" className="kr-tour-bubble-title">
          {step.title}
        </h3>
        {targetMissing && (
          <div
            className="kr-tour-bubble-progress"
            style={{ color: "var(--color-warning, #f59e0b)" }}
          >
            ⚠ Цей блок ще не доступний на цій сторінці.
          </div>
        )}
        <p
          className="kr-tour-bubble-text"
          dangerouslySetInnerHTML={{ __html: step.text }}
        />
        <div className="kr-tour-bubble-actions">
          <button
            type="button"
            className="kr-tour-bubble-skip"
            onClick={endTour}
          >
            {isLast ? "" : "Пропустити"}
          </button>
          <div className="kr-tour-bubble-nav">
            <button type="button" onClick={prevStep} disabled={isFirst}>
              ← Назад
            </button>
            <button
              type="button"
              className="kr-tour-next"
              onClick={nextStep}
            >
              {isLast ? "Завершити" : "Далі →"}
            </button>
          </div>
        </div>
      </div>
    </>,
    document.body,
  );
}

export function startTour() {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent(START_EVENT));
}
