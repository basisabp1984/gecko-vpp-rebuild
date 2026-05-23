"use client";

import Link from "next/link";
import { useState } from "react";
import {
  Code2,
  BookOpen,
  Boxes,
  PlugZap,
  Sparkles,
  Copy,
  Check,
  Workflow,
  ArrowRight,
  Github,
} from "lucide-react";
import { useToast } from "@/components/Toast";
import { TENANT_LIST } from "@/lib/tenants";

const QUICK_START_TS = `import { KrytsiaClient } from "@krytsia/sdk-ts";

const client = new KrytsiaClient({
  baseURL: "http://localhost:8000",
  tenantId: "11111111-1111-1111-1111-111111111111",
});

const assets = await client.assets.list();
console.log(\`Знайдено \${assets.length} активів\`);`;

const QUICK_START_PY = `from krytsia_sdk import KrytsiaClient

with KrytsiaClient(
    base_url="http://localhost:8000",
    tenant_id="11111111-1111-1111-1111-111111111111",
) as client:
    assets = client.assets()
    print(f"Знайдено {len(assets)} активів")`;

const ENTRY_CARDS = [
  {
    href: "/developer/api/explorer",
    icon: BookOpen,
    title: "API Explorer",
    description: "Інтерактивна документація OpenAPI 3.1 з пробою всіх 35+ ендпоінтів.",
    cta: "Відкрити Scalar",
  },
  {
    href: "/developer/sdk-ts",
    icon: Boxes,
    title: "TypeScript SDK",
    description: "Thin-wrapper над fetch, типи з OpenAPI, працює у Node 20+ та Bun.",
    cta: "npm install",
  },
  {
    href: "/developer/sdk-py",
    icon: Code2,
    title: "Python SDK",
    description: "httpx-обгортка для CPython 3.11+, працює в скриптах та Jupyter.",
    cta: "pip install",
  },
  {
    href: "/developer/webhooks",
    icon: PlugZap,
    title: "Webhooks",
    description: "Push-події про підпис документів, оптимізації, інструкції. Beta.",
    cta: "Дивитися події",
  },
];

export default function DeveloperPage() {
  const [lang, setLang] = useState<"ts" | "py">("ts");
  const toast = useToast();
  const [copied, setCopied] = useState(false);

  async function copySnippet() {
    const code = lang === "ts" ? QUICK_START_TS : QUICK_START_PY;
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      toast.push({ tone: "success", title: "Скопійовано" });
      setTimeout(() => setCopied(false), 1500);
    } catch {
      toast.push({ tone: "alert", title: "Не вдалося скопіювати" });
    }
  }

  return (
    <div className="flex flex-col gap-10">
      {/* Hero */}
      <section className="relative pt-4">
        <div className="absolute inset-0 -z-10 bg-gradient-hero opacity-40 pointer-events-none rounded-3xl" />
        <div className="flex flex-col gap-3 max-w-3xl">
          <div className="inline-flex items-center gap-2 self-start px-2.5 py-1 rounded-full bg-accent-subtle text-accent-deep text-xs font-semibold">
            <Sparkles size={12} />
            Live demo
            <Link
              href="/producer"
              className="ml-1 inline-flex items-center gap-1 underline-offset-2 hover:underline"
            >
              /producer <ArrowRight size={11} />
            </Link>
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-text-heading tracking-tight">
            Розробникам Krytsia — <span className="text-accent-deep">API + SDK + Webhooks</span>
          </h1>
          <p className="text-base text-text-muted">
            Програмний доступ до тих самих даних, що бачать виробники, бізнес та власники
            УЗЕ у своїх кабінетах. RESTful, multi-tenant через заголовок <code className="text-xs font-mono px-1 py-0.5 rounded bg-bg-subtle">X-Tenant-Id</code>,
            OpenAPI 3.1, типобезпечні SDK.
          </p>
        </div>
      </section>

      {/* Entry cards */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {ENTRY_CARDS.map((c) => {
          const Icon = c.icon;
          return (
            <Link
              key={c.href}
              href={c.href}
              className="group rounded-xl border border-border bg-bg-card p-4 shadow-card hover:border-accent transition-colors"
            >
              <span className="inline-flex items-center justify-center w-10 h-10 rounded-lg bg-accent-subtle text-accent-deep mb-3">
                <Icon size={18} />
              </span>
              <h3 className="text-base font-semibold text-text-heading mb-1">{c.title}</h3>
              <p className="text-sm text-text-muted leading-snug">{c.description}</p>
              <span className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-accent-deep group-hover:gap-2 transition-all">
                {c.cta} <ArrowRight size={14} />
              </span>
            </Link>
          );
        })}
      </section>

      {/* Quick start */}
      <section className="rounded-xl border border-border bg-bg-card p-5 shadow-card">
        <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3 mb-4">
          <div>
            <h2 className="text-lg font-semibold text-text-heading">Швидкий старт</h2>
            <p className="text-sm text-text-muted">
              Кілька рядків — і у вас список активів портфеля.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <div className="inline-flex rounded-lg border border-border bg-bg-subtle overflow-hidden">
              <button
                type="button"
                onClick={() => setLang("ts")}
                className={`px-3 py-1.5 text-sm font-medium transition-colors ${
                  lang === "ts"
                    ? "bg-accent text-text-inverse"
                    : "text-text-muted hover:text-text-heading"
                }`}
              >
                TypeScript
              </button>
              <button
                type="button"
                onClick={() => setLang("py")}
                className={`px-3 py-1.5 text-sm font-medium transition-colors ${
                  lang === "py"
                    ? "bg-accent text-text-inverse"
                    : "text-text-muted hover:text-text-heading"
                }`}
              >
                Python
              </button>
            </div>
            <button
              type="button"
              onClick={copySnippet}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border bg-bg-subtle hover:border-accent text-sm text-text-body transition-colors"
            >
              {copied ? <Check size={14} /> : <Copy size={14} />}
              {copied ? "Скопійовано" : "Копіювати"}
            </button>
          </div>
        </div>
        <pre className="rounded-lg bg-bg-subtle border border-border p-4 overflow-x-auto text-xs font-mono text-text-body leading-relaxed">
          <code>{lang === "ts" ? QUICK_START_TS : QUICK_START_PY}</code>
        </pre>
      </section>

      {/* Get started + demo tenants */}
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="rounded-xl border border-border bg-bg-card p-5 shadow-card">
          <h3 className="text-base font-semibold text-text-heading mb-2 flex items-center gap-2">
            <Workflow size={16} className="text-accent-deep" />
            Як отримати tenant UUID?
          </h3>
          <ol className="list-decimal list-inside space-y-1.5 text-sm text-text-muted">
            <li>
              У продакшені — реєструєтесь, верифікуєте КЕП, отримуєте власний UUID.
            </li>
            <li>
              У цьому демо доступу не треба — використовуйте один з трьох публічних
              демо-tenant&apos;ів нижче.
            </li>
            <li>
              Передавайте UUID у заголовку{" "}
              <code className="text-xs font-mono px-1 py-0.5 rounded bg-bg-subtle">X-Tenant-Id</code>{" "}
              на кожний запит.
            </li>
          </ol>
        </div>

        <div className="rounded-xl border border-border bg-bg-card p-5 shadow-card">
          <h3 className="text-base font-semibold text-text-heading mb-3 flex items-center gap-2">
            <Boxes size={16} className="text-accent-deep" />
            Демо tenant UUID
          </h3>
          <ul className="space-y-2">
            {TENANT_LIST.map((t) => (
              <li
                key={t.id}
                className="flex items-start justify-between gap-3 rounded-lg border border-border bg-bg-subtle p-2.5"
              >
                <div className="min-w-0">
                  <div className="text-sm font-medium text-text-heading">
                    {t.name}{" "}
                    <span className="text-xs text-text-muted font-normal">
                      · {t.description}
                    </span>
                  </div>
                  <code className="text-[11px] font-mono text-text-muted block truncate">
                    {t.id}
                  </code>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    navigator.clipboard.writeText(t.id);
                    toast.push({ tone: "success", title: "UUID скопійовано" });
                  }}
                  className="shrink-0 p-1.5 rounded border border-border bg-bg-card hover:border-accent text-text-muted transition-colors"
                  aria-label="Скопіювати UUID"
                  title="Скопіювати"
                >
                  <Copy size={12} />
                </button>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* Architecture mini-diagram link */}
      <section className="rounded-xl border border-border bg-bg-card p-5 shadow-card flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold text-text-heading mb-1">Архітектура Krytsia</h3>
          <p className="text-sm text-text-muted">
            Хаб-і-спиці: 4 ринкові сервіси, 4 типи учасників. Усі шляхи дотепер ведуть до одного
            API.
          </p>
        </div>
        <Link
          href="/"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-border bg-bg-subtle hover:border-accent text-sm font-medium text-text-body transition-colors"
        >
          Відкрити діаграму <ArrowRight size={14} />
        </Link>
      </section>

      {/* GitHub */}
      <section className="text-center text-sm text-text-muted">
        <a
          href="https://github.com/basisabp1984/gecko-vpp-rebuild"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 hover:text-accent-deep transition-colors"
        >
          <Github size={14} /> github.com/basisabp1984/gecko-vpp-rebuild
        </a>
      </section>
    </div>
  );
}
