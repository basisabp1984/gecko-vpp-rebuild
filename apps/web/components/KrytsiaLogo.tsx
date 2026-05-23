"use client";

import Link from "next/link";

/**
 * Krytsia wordmark with a minimal geometric energy-bar accent.
 * Industrial / AI-energy aesthetic — clean text mark + 4 vertical bars
 * suggesting forecast / spectrum / signal layer.
 */
export function KrytsiaLogo({ size = 28 }: { size?: number }) {
  return (
    <Link
      href="/"
      className="flex items-center gap-2.5 group"
      aria-label="Krytsia — головна"
    >
      <svg
        width={size}
        height={size}
        viewBox="0 0 32 32"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="text-accent group-hover:text-accent-deep transition-colors"
      >
        {/* Four vertical bars of increasing height — AI/forecast/signal mark */}
        <rect x="4"  y="22" width="3" height="6"  rx="0.5" fill="currentColor" opacity="0.55" />
        <rect x="11" y="17" width="3" height="11" rx="0.5" fill="currentColor" opacity="0.75" />
        <rect x="18" y="11" width="3" height="17" rx="0.5" fill="currentColor" opacity="0.9" />
        <rect x="25" y="4"  width="3" height="24" rx="0.5" fill="currentColor" />
      </svg>
      <span className="font-bold text-text-heading tracking-[0.04em] text-lg uppercase">
        Krytsia
      </span>
    </Link>
  );
}
