"use client";

import Link from "next/link";

export function GeckoLogo({ size = 28 }: { size?: number }) {
  return (
    <Link
      href="/"
      className="flex items-center gap-2 group"
      aria-label="GECKO VPP — головна"
    >
      <svg
        width={size}
        height={size}
        viewBox="0 0 40 40"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="text-accent group-hover:text-accent-deep transition-colors"
      >
        {/* Stylised gecko head — silhouette */}
        <path
          d="M8 22c0-8 6-14 14-14 6 0 10 4 10 8 0 3-2 5-5 5h-3c-2 0-3 1-3 3v3c0 3-2 5-5 5-5 0-8-4-8-10z"
          fill="currentColor"
          opacity="0.9"
        />
        <circle cx="26" cy="16" r="1.5" fill="var(--color-bg-card)" />
      </svg>
      <span className="font-bold text-text-heading tracking-tight text-lg">
        GECKO<span className="text-accent">.</span>VPP
      </span>
    </Link>
  );
}
