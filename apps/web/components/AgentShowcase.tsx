"use client";

import { ArrowRight, Sparkles } from "lucide-react";
import {
  PERSONA_META,
  PERSONA_ORDER,
  getAgentChatBridge,
  type PersonaCode,
} from "./AgentChat";

export function AgentShowcase() {
  function handleAsk(persona: PersonaCode, prefill?: string) {
    const bridge = getAgentChatBridge();
    if (bridge) bridge.openWithPersona(persona, prefill);
  }

  return (
    <section className="relative rounded-3xl border border-border bg-bg-card p-5 sm:p-7 shadow-card overflow-hidden">
      <div
        aria-hidden
        className="absolute inset-0 -z-10 bg-gradient-hero opacity-50 pointer-events-none"
      />

      <header className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3 mb-6">
        <div>
          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-accent-subtle text-accent-deep text-xs font-semibold mb-2">
            <Sparkles size={12} />
            AI агенти Krytsia
          </div>
          <h2 className="text-2xl sm:text-3xl font-bold text-text-heading tracking-tight">
            Чотири фахівці — одне вікно
          </h2>
          <p className="mt-1.5 text-sm sm:text-base text-text-muted max-w-2xl">
            Кожен агент бачить ті самі живі дані, що й ваш кабінет. Запитайте
            українською або голосом — отримаєте відповідь з посиланнями на джерела.
          </p>
        </div>
      </header>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        {PERSONA_ORDER.map((code) => {
          const p = PERSONA_META[code];
          const Icon = p.icon;
          const firstSample = p.samples[0];
          return (
            <article
              key={code}
              className="group relative flex flex-col gap-3 p-4 rounded-2xl border border-border bg-bg-page hover:border-accent transition-colors"
            >
              <div className="flex items-center gap-2.5">
                <span className="inline-flex items-center justify-center w-10 h-10 rounded-xl bg-accent-subtle text-accent-deep group-hover:bg-accent group-hover:text-text-inverse transition-colors">
                  <Icon size={20} />
                </span>
                <div className="min-w-0">
                  <div className="text-sm font-semibold text-text-heading truncate">
                    {p.display}
                  </div>
                  <div className="text-xs text-text-muted truncate">
                    {p.tagline}
                  </div>
                </div>
              </div>

              <div className="flex flex-col gap-1.5">
                {p.samples.slice(0, 2).map((q) => (
                  <button
                    key={q}
                    type="button"
                    onClick={() => handleAsk(code, q)}
                    className="text-left text-xs text-text-body px-2.5 py-1.5 rounded-lg border border-border bg-bg-card hover:border-accent hover:text-accent-deep transition-colors truncate"
                    title={q}
                  >
                    &ldquo;{q}&rdquo;
                  </button>
                ))}
              </div>

              <button
                type="button"
                onClick={() => handleAsk(code, firstSample)}
                className="mt-auto inline-flex items-center justify-between gap-2 px-3 py-2 rounded-lg bg-accent text-text-inverse hover:bg-accent-deep transition-colors text-sm font-medium"
              >
                <span>Запитати</span>
                <ArrowRight
                  size={14}
                  className="group-hover:translate-x-0.5 transition-transform"
                />
              </button>
            </article>
          );
        })}
      </div>
    </section>
  );
}
