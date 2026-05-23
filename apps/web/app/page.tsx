import Link from "next/link";
import { Factory, Building2, Battery, Code2, ShieldCheck } from "lucide-react";
import { ArchitectureDiagram } from "@/components/diagram/ArchitectureDiagram";
import { ScenarioCard } from "@/components/ScenarioCard";

export default function HomePage() {
  return (
    <div className="flex flex-col gap-10">
      {/* Tagline */}
      <section className="relative text-center pt-6 pb-2">
        <div className="absolute inset-0 -z-10 bg-gradient-hero opacity-50 pointer-events-none" />
        <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-text-heading tracking-tight">
          Робимо складну енергетику{" "}
          <span className="text-accent-deep">керованою</span>.
        </h1>
        <p className="mt-3 text-base sm:text-lg text-text-muted max-w-2xl mx-auto">
          Для бізнесу. Для виробників. Для ринку.
        </p>
      </section>

      {/* Architecture diagram */}
      <section className="rounded-2xl border border-border bg-bg-card p-4 sm:p-6 shadow-card">
        <ArchitectureDiagram />
      </section>

      {/* Persona entry cards */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <ScenarioCard
          title="Я виробник"
          icon={<Factory size={20} />}
          description={
            <>
              Сонячна, вітрова, газо-поршнева чи гібридна станція. Прогноз, торгівля
              на ДД/РДН/ВДР, оптимізація проти кепа та небалансів.
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
