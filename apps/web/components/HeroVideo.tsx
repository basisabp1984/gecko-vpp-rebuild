"use client";

import Link from "next/link";
import { ArrowRight, Sparkles } from "lucide-react";
import { useEffect, useRef, useState } from "react";

interface HeroVideoProps {
  videoSrc: string;
  posterSrc: string;
  eyebrow?: string;
  headline: React.ReactNode;
  subline: React.ReactNode;
  primaryCta: { href: string; label: string };
  secondaryCta?: { href: string; label: string };
}

export function HeroVideo({
  videoSrc,
  posterSrc,
  eyebrow,
  headline,
  subline,
  primaryCta,
  secondaryCta,
}: HeroVideoProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const reduced = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    if (reduced) return;

    const v = videoRef.current;
    if (!v) return;

    const onCanPlay = () => setLoaded(true);
    v.addEventListener("canplay", onCanPlay, { once: true });
    void v.play().catch(() => {
      // Autoplay blocked — poster stays visible, no error UX needed.
    });
    return () => v.removeEventListener("canplay", onCanPlay);
  }, []);

  return (
    <section
      aria-label="Krytsia hero"
      className="relative -mx-4 sm:-mx-6 lg:-mx-8 -mt-6 mb-2 overflow-hidden"
      style={{ minHeight: "min(78vh, 720px)" }}
    >
      {/* Video layer — covers entire hero */}
      <div className="absolute inset-0 z-0">
        <video
          ref={videoRef}
          className={`w-full h-full object-cover transition-opacity duration-700 ${
            loaded ? "opacity-100" : "opacity-0"
          }`}
          src={videoSrc}
          poster={posterSrc}
          autoPlay
          loop
          muted
          playsInline
          preload="metadata"
          aria-hidden
        />
        {/* Poster shown until video reports canplay */}
        <div
          aria-hidden
          className={`absolute inset-0 bg-cover bg-center transition-opacity duration-700 ${
            loaded ? "opacity-0" : "opacity-100"
          }`}
          style={{ backgroundImage: `url(${posterSrc})` }}
        />
      </div>

      {/* Gradient overlay — readability + brand tint */}
      <div
        aria-hidden
        className="absolute inset-0 z-10 pointer-events-none"
        style={{
          background:
            "linear-gradient(180deg, rgba(2,6,23,0.55) 0%, rgba(2,6,23,0.35) 35%, rgba(2,6,23,0.65) 100%), radial-gradient(ellipse at 15% 0%, rgba(20,184,166,0.35) 0%, transparent 55%)",
        }}
      />

      {/* Content */}
      <div className="relative z-20 mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 flex flex-col justify-center min-h-[inherit] py-16 sm:py-24">
        {eyebrow && (
          <span className="inline-flex items-center gap-1.5 self-start px-3 py-1 rounded-full bg-white/15 backdrop-blur text-white text-xs font-semibold ring-1 ring-white/25 mb-5">
            <Sparkles size={12} />
            {eyebrow}
          </span>
        )}
        <h1 className="text-white font-extrabold tracking-tight text-4xl sm:text-5xl lg:text-6xl xl:text-7xl leading-[1.05] max-w-4xl drop-shadow-[0_2px_24px_rgba(0,0,0,0.45)]">
          {headline}
        </h1>
        <p className="mt-5 sm:mt-6 text-white/90 text-base sm:text-lg lg:text-xl max-w-2xl drop-shadow-[0_1px_12px_rgba(0,0,0,0.55)]">
          {subline}
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link
            href={primaryCta.href}
            className="inline-flex items-center gap-2 px-5 py-3 rounded-xl bg-accent hover:bg-accent-deep text-text-inverse font-semibold shadow-elevated transition-colors"
          >
            {primaryCta.label} <ArrowRight size={16} />
          </Link>
          {secondaryCta && (
            <Link
              href={secondaryCta.href}
              className="inline-flex items-center gap-2 px-5 py-3 rounded-xl bg-white/15 hover:bg-white/25 backdrop-blur text-white font-semibold ring-1 ring-white/30 transition-colors"
            >
              {secondaryCta.label}
            </Link>
          )}
        </div>
      </div>

      {/* Bottom fade to page bg, softens transition to next section */}
      <div
        aria-hidden
        className="absolute inset-x-0 bottom-0 h-24 z-10 pointer-events-none"
        style={{
          background:
            "linear-gradient(180deg, transparent 0%, var(--color-bg-page) 100%)",
        }}
      />
    </section>
  );
}
