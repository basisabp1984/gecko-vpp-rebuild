"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowLeft, ArrowRight, X } from "lucide-react";
import { PITCH_SLIDES } from "./pitchData";

export default function PitchPage() {
  const total = PITCH_SLIDES.length;
  const [index, setIndex] = useState(0);

  const goTo = useCallback(
    (n: number) => setIndex(Math.max(0, Math.min(n, total - 1))),
    [total],
  );
  const goNext = useCallback(
    () => setIndex((i) => Math.min(i + 1, total - 1)),
    [total],
  );
  const goPrev = useCallback(
    () => setIndex((i) => Math.max(i - 1, 0)),
    [],
  );

  // Sync from URL hash so direct deep-links work (e.g. /pitch#3) and back/forward navigates slides.
  useEffect(() => {
    const fromHash = () => {
      const raw = window.location.hash.replace(/^#/, "");
      const n = parseInt(raw, 10);
      if (!Number.isNaN(n)) goTo(n);
    };
    fromHash();
    window.addEventListener("hashchange", fromHash);
    return () => window.removeEventListener("hashchange", fromHash);
  }, [goTo]);

  // Push hash without scrolling — so reload/bookmark restores current slide.
  useEffect(() => {
    const targetHash = `#${index}`;
    if (window.location.hash !== targetHash) {
      history.replaceState(null, "", targetHash);
    }
  }, [index]);

  // Keyboard navigation. Skips when focus is in an editable field so the
  // pitch never hijacks form input on embedded surfaces.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      const tag = target?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || target?.isContentEditable) {
        return;
      }
      if (
        e.key === "ArrowRight" ||
        e.key === " " ||
        e.key === "PageDown" ||
        e.key === "Enter"
      ) {
        e.preventDefault();
        goNext();
      } else if (e.key === "ArrowLeft" || e.key === "PageUp") {
        e.preventDefault();
        goPrev();
      } else if (e.key === "Home") {
        e.preventDefault();
        goTo(0);
      } else if (e.key === "End") {
        e.preventDefault();
        goTo(total - 1);
      } else if (/^[1-9]$/.test(e.key)) {
        const n = parseInt(e.key, 10) - 1;
        if (n < total) {
          e.preventDefault();
          goTo(n);
        }
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [goNext, goPrev, goTo, total]);

  const current = PITCH_SLIDES[index];

  return (
    <div className="fixed inset-0 overflow-hidden text-text-body">
      {/* Animated background — re-mounts per slide so gradient can crossfade. */}
      <AnimatePresence mode="sync">
        <motion.div
          key={`bg-${index}`}
          className={`absolute inset-0 ${current.bgClass}`}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.55, ease: "easeInOut" }}
        />
      </AnimatePresence>

      {/* Top frame */}
      <header className="absolute top-0 left-0 right-0 z-20 px-5 sm:px-10 py-5 flex items-center justify-between">
        <div className="flex items-center gap-2 text-[10px] sm:text-xs uppercase tracking-[0.18em] font-semibold text-text-muted">
          <span className="text-accent-deep">●</span>
          Krytsia · for partners
        </div>
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border bg-bg-card/70 hover:border-accent text-xs sm:text-sm text-text-muted hover:text-text-heading transition-colors"
        >
          <X size={14} /> закрити
        </Link>
      </header>

      {/* Slide content — vertically centered, scrollable if it overflows. */}
      <main className="absolute inset-0 z-10 overflow-y-auto pt-20 pb-24 px-5 sm:px-10">
        <div className="min-h-full flex items-center justify-center">
          <AnimatePresence mode="wait">
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -16 }}
              transition={{ duration: 0.4, ease: "easeOut" }}
              className="w-full max-w-5xl"
            >
              {current.render({ goNext, goPrev, goTo, index, total })}
            </motion.div>
          </AnimatePresence>
        </div>
      </main>

      {/* Bottom frame: progress + nav */}
      <footer className="absolute bottom-0 left-0 right-0 z-20 px-5 sm:px-10 py-5 flex items-center justify-between gap-4">
        {/* Dots */}
        <div className="flex items-center gap-2">
          {PITCH_SLIDES.map((s, i) => (
            <button
              key={i}
              type="button"
              onClick={() => goTo(i)}
              className={`h-1.5 rounded-full transition-all ${
                i === index
                  ? "w-9 bg-accent"
                  : "w-1.5 bg-border-strong hover:bg-accent-light"
              }`}
              aria-label={`Слайд ${i + 1}: ${s.title}`}
              aria-current={i === index ? "step" : undefined}
            />
          ))}
        </div>

        <div className="flex items-center gap-3">
          <span className="hidden sm:flex items-center gap-1.5 text-xs text-text-muted font-mono">
            <kbd className="px-1.5 py-0.5 rounded border border-border bg-bg-card">
              ←
            </kbd>
            <kbd className="px-1.5 py-0.5 rounded border border-border bg-bg-card">
              →
            </kbd>
            <span className="ml-1">
              {index + 1} / {total}
            </span>
          </span>
          <button
            type="button"
            onClick={goPrev}
            disabled={index === 0}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl border border-border bg-bg-card disabled:opacity-30 disabled:cursor-not-allowed hover:border-accent hover:text-accent-deep transition-colors text-sm font-medium"
            aria-label="Попередній слайд"
          >
            <ArrowLeft size={16} />
            <span className="hidden sm:inline">Назад</span>
          </button>
          <button
            type="button"
            onClick={goNext}
            disabled={index === total - 1}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-accent text-text-inverse disabled:opacity-30 disabled:cursor-not-allowed hover:bg-accent-deep transition-colors text-sm font-semibold shadow-card"
            aria-label="Наступний слайд"
          >
            <span>Далі</span>
            <ArrowRight size={16} />
          </button>
        </div>
      </footer>
    </div>
  );
}
