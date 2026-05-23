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
    <section className="relative rounded-3xl border border-border bg-bg-card p-6 sm:p-10 shadow-card overflow-hidden">
      <div
        aria-hidden
        className="absolute inset-0 -z-10 bg-gradient-hero opacity-60 pointer-events-none"
      />

      <header className="flex flex-col gap-4 mb-8 sm:mb-10">
        <div className="inline-flex items-center gap-1.5 self-start px-3 py-1.5 rounded-full bg-accent-subtle text-accent-deep text-xs sm:text-sm font-semibold">
          <Sparkles size={14} />
          AI агенти Krytsia · ексклюзивно у нас
        </div>
        <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-text-heading tracking-tight max-w-3xl">
          Чотири фахівці —{" "}
          <span className="text-accent-deep">одне вікно</span>
        </h2>
        <p className="text-base sm:text-lg text-text-muted max-w-3xl leading-relaxed">
          Жодна інша VPP-платформа в Україні не дає такого. Кожен агент бачить ті
          самі живі дані, що й ваш кабінет: запитайте українською або голосом —
          отримаєте відповідь з посиланнями на конкретні рядки в базі.
        </p>
      </header>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5">
        {PERSONA_ORDER.map((code) => {
          const p = PERSONA_META[code];
          const Icon = p.icon;
          const firstSample = p.samples[0];
          return (
            <article
              key={code}
              className="group relative flex flex-col gap-4 p-5 sm:p-6 rounded-2xl border border-border bg-bg-page hover:border-accent hover:shadow-card transition-all"
            >
              <div className="flex items-start gap-3">
                <span className="inline-flex items-center justify-center w-12 h-12 sm:w-14 sm:h-14 rounded-2xl bg-accent-subtle text-accent-deep group-hover:bg-accent group-hover:text-text-inverse transition-colors flex-shrink-0">
                  <Icon size={26} />
                </span>
                <div className="min-w-0 pt-0.5">
                  <div className="text-base sm:text-lg font-semibold text-text-heading leading-tight">
                    {p.display}
                  </div>
                  <div className="text-xs sm:text-sm text-text-muted mt-1">
                    {p.tagline}
                  </div>
                </div>
              </div>

              <div className="flex flex-col gap-2">
                {p.samples.slice(0, 2).map((q) => (
                  <button
                    key={q}
                    type="button"
                    onClick={() => handleAsk(code, q)}
                    className="text-left text-xs sm:text-sm text-text-body px-3 py-2 rounded-lg border border-border bg-bg-card hover:border-accent hover:text-accent-deep transition-colors line-clamp-2"
                    title={q}
                  >
                    &ldquo;{q}&rdquo;
                  </button>
                ))}
              </div>

              <button
                type="button"
                onClick={() => handleAsk(code, firstSample)}
                className="mt-auto inline-flex items-center justify-between gap-2 px-4 py-2.5 rounded-xl bg-accent text-text-inverse hover:bg-accent-deep transition-colors text-sm font-semibold"
              >
                <span>Запитати агента</span>
                <ArrowRight
                  size={16}
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
