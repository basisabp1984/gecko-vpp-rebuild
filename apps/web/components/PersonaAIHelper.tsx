"use client";

import { ArrowRight, Sparkles, Mic } from "lucide-react";
import {
  PERSONA_META,
  getAgentChatBridge,
  type PersonaCode,
} from "./AgentChat";

interface PersonaAIHelperProps {
  persona: PersonaCode;
}

export function PersonaAIHelper({ persona }: PersonaAIHelperProps) {
  const p = PERSONA_META[persona];
  const Icon = p.icon;

  function handleAsk(prefill?: string) {
    const bridge = getAgentChatBridge();
    if (bridge) bridge.openWithPersona(persona, prefill);
  }

  return (
    <section
      aria-label={`AI помічник — ${p.display}`}
      className="relative rounded-2xl border border-accent/30 bg-bg-card p-5 sm:p-6 shadow-card overflow-hidden"
    >
      <div
        aria-hidden
        className="absolute inset-0 -z-10 bg-gradient-hero opacity-50 pointer-events-none"
      />

      <div className="flex flex-col md:flex-row items-start md:items-center gap-4 md:gap-6">
        <span className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-accent text-text-inverse flex-shrink-0 shadow-elevated">
          <Icon size={28} />
        </span>

        <div className="flex-1 min-w-0">
          <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-accent-subtle text-accent-deep text-xs font-semibold mb-1.5">
            <Sparkles size={11} /> AI помічник
          </div>
          <h2 className="text-lg sm:text-xl font-bold text-text-heading leading-tight">
            {p.display}{" "}
            <span className="text-text-muted font-normal">— {p.tagline}</span>
          </h2>
          <p className="mt-1 text-sm text-text-muted">
            Запитайте українською або голосом. Відповіді з посиланнями на ваші
            живі дані.
          </p>
        </div>

        <button
          type="button"
          onClick={() => handleAsk(p.samples[0])}
          className="hidden md:inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-accent hover:bg-accent-deep text-text-inverse font-semibold transition-colors shadow-elevated"
        >
          Запитати <ArrowRight size={16} />
        </button>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {p.samples.map((q) => (
          <button
            key={q}
            type="button"
            onClick={() => handleAsk(q)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-border bg-bg-page hover:border-accent hover:text-accent-deep text-xs sm:text-sm text-text-body transition-colors"
            title={q}
          >
            <Mic size={12} className="text-accent" aria-hidden /> &ldquo;{q}&rdquo;
          </button>
        ))}

        <button
          type="button"
          onClick={() => handleAsk(p.samples[0])}
          className="md:hidden inline-flex items-center gap-1.5 px-4 py-1.5 rounded-full bg-accent hover:bg-accent-deep text-text-inverse text-sm font-semibold transition-colors ml-auto"
        >
          Запитати <ArrowRight size={14} />
        </button>
      </div>
    </section>
  );
}
