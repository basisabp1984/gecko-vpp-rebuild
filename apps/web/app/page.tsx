import Link from "next/link";
import { Factory, Building2, Battery, Code2, ShieldCheck } from "lucide-react";
import { ArchitectureDiagram } from "@/components/diagram/ArchitectureDiagram";
import { ScenarioCard } from "@/components/ScenarioCard";
import { AgentShowcase } from "@/components/AgentShowcase";
import { HeroVideo } from "@/components/HeroVideo";

export default function HomePage() {
  return (
    <div className="flex flex-col gap-14">
      {/* Cinematic hero with drone-aerial video + AI-first headline */}
      <HeroVideo
        videoSrc="/hero/renewables-aerial-720.mp4"
        posterSrc="/hero/renewables-aerial-poster.jpg"
        eyebrow="AI-перша платформа · VPP + EMS"
        headline={
          <>
            Робимо складну енергетику{" "}
            <span className="text-accent-light">керованою</span>.
          </>
        }
        subline={
          <>
            Krytsia — Virtual Power Plant + Energy Management Platform для України.
            Чотири фахівці-агенти на основі AI у вашому кабінеті: прогноз, ринок,
            диспетчеризація, оптимізація батарей.
          </>
        }
        primaryCta={{ href: "/producer", label: "Спробувати кабінет" }}
        secondaryCta={{ href: "/developer", label: "Developer-портал" }}
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
            Оберіть свій сценарій
          </h2>
          <p className="mt-1 text-sm sm:text-base text-text-muted max-w-2xl">
            Один продукт — три кабінети під різні ролі на ринку. Дані живі,
            мульти-тенант через <code className="text-xs font-mono px-1 py-0.5 rounded bg-bg-subtle">X-Tenant-Id</code>.
          </p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <ScenarioCard
            title="Я виробник"
            icon={<Factory size={20} />}
            description={
              <>
                Сонячна, вітрова, газо-поршнева чи гібридна станція. Прогноз,
                торгівля на ДД/РДН/ВДР, оптимізація проти кепа та небалансів.
              </>
            }
            href="/producer"
            cta="Кабінет виробника"
            tone="accent"
          />
          <ScenarioCard
            title="Я бізнес (C&I)"
            icon={<Building2 size={20} />}
            description={
              <>
                Завод, агрохолдинг, ритейл. Мінімізуйте рахунок: тарифні плани,
                перенесення навантажень, групова закупівля, DR-послуги.
              </>
            }
            href="/c-i"
            cta="Кабінет активного споживача"
          />
          <ScenarioCard
            title="Я УЗЕ-власник"
            icon={<Battery size={20} />}
            description={
              <>
                Електрохімічне сховище як актив. Арбітраж, БР, послуги системі.
                Знайдемо щотижневу стратегію з найкращим IRR.
              </>
            }
            href="/storage"
            cta="Кабінет УЗЕ"
          />
        </div>
      </section>

      {/* Secondary links */}
      <section className="flex flex-wrap items-center justify-center gap-4 text-sm">
        <Link
          href="/developer"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-border bg-bg-card hover:border-accent transition-colors text-text-body"
        >
          <Code2 size={14} /> Developer-портал
        </Link>
        <Link
          href="/admin"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-border bg-bg-card hover:border-accent transition-colors text-text-body"
        >
          <ShieldCheck size={14} /> Адмін-консоль
        </Link>
      </section>
    </div>
  );
}
