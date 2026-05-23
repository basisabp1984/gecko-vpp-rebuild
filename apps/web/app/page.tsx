"use client";

import Link from "next/link";
import { Factory, Building2, Battery, ShieldCheck } from "lucide-react";
import { useTranslations } from "next-intl";
import { ArchitectureDiagram } from "@/components/diagram/ArchitectureDiagram";
import { ScenarioCard } from "@/components/ScenarioCard";
import { AgentShowcase } from "@/components/AgentShowcase";
import { HeroVideo } from "@/components/HeroVideo";

export default function HomePage() {
  const tHero = useTranslations("hero");
  const tScenario = useTranslations("scenarios");
  const tSecondary = useTranslations("secondaryLinks");

  return (
    <div className="flex flex-col gap-14">
      {/* Cinematic hero with drone-aerial video + AI-first headline */}
      <HeroVideo
        videoSrc="/hero/renewables-aerial-720.mp4"
        posterSrc="/hero/renewables-aerial-poster.jpg"
        eyebrow={tHero("eyebrow")}
        headline={
          <>
            {tHero("headlinePrefix")}{" "}
            <span className="text-accent-light">
              {tHero("headlineHighlight")}
            </span>
            .
          </>
        }
        subline={tHero("subline")}
        primaryCta={{ href: "/producer", label: tHero("primaryCta") }}
        secondaryCta={{ href: "#agents", label: tHero("secondaryCta") }}
      />

      {/* AI agents — the headline differentiator, raised to second screen */}
      <AgentShowcase />

      {/* Architecture diagram */}
      <section className="rounded-2xl border border-border bg-bg-card p-4 sm:p-6 shadow-card">
        <ArchitectureDiagram />
      </section>

      {/* Persona entry cards */}
      <section>
        <div className="mb-4">
          <h2 className="text-2xl sm:text-3xl font-bold text-text-heading tracking-tight">
            {tScenario("heading")}
          </h2>
          <p className="mt-1 text-sm sm:text-base text-text-muted max-w-2xl">
            {tScenario("subline")}
          </p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <ScenarioCard
            title={tScenario("producer.title")}
            icon={<Factory size={20} />}
            description={<>{tScenario("producer.description")}</>}
            href="/producer"
            cta={tScenario("producer.cta")}
            tone="accent"
          />
          <ScenarioCard
            title={tScenario("ci.title")}
            icon={<Building2 size={20} />}
            description={<>{tScenario("ci.description")}</>}
            href="/c-i"
            cta={tScenario("ci.cta")}
          />
          <ScenarioCard
            title={tScenario("storage.title")}
            icon={<Battery size={20} />}
            description={<>{tScenario("storage.description")}</>}
            href="/storage"
            cta={tScenario("storage.cta")}
          />
        </div>
      </section>

      {/* Secondary links */}
      <section className="flex flex-wrap items-center justify-center gap-4 text-sm">
        <Link
          href="/admin"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-border bg-bg-card hover:border-accent transition-colors text-text-body"
        >
          <ShieldCheck size={14} /> {tSecondary("admin")}
        </Link>
      </section>
    </div>
  );
}
