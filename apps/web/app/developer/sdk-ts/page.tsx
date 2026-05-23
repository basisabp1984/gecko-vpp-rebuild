"use client";

import Link from "next/link";
import { useState } from "react";
import { ArrowLeft, Boxes, Copy, Check, Github, Terminal } from "lucide-react";
import { useToast } from "@/components/Toast";

const INSTALL_CMD = `npm install @krytsia/sdk-ts
# або
pnpm add @krytsia/sdk-ts
# або
bun add @krytsia/sdk-ts`;

const CLIENT_INIT = `import { KrytsiaClient } from "@krytsia/sdk-ts";

const client = new KrytsiaClient({
  baseURL: "http://localhost:8000",
  tenantId: "11111111-1111-1111-1111-111111111111",
});`;

const EX_LIST_ASSETS = `import { KrytsiaClient } from "@krytsia/sdk-ts";

const client = new KrytsiaClient({
  baseURL: process.env.KRYTSIA_API ?? "http://localhost:8000",
  tenantId: process.env.KRYTSIA_TENANT ?? "11111111-1111-1111-1111-111111111111",
});

const assets = await client.assets.list();
console.log(\`Знайдено \${assets.length} активів:\`);
for (const a of assets) {
  console.log(\`  \${a.code.padEnd(20)} \${a.display_name.padEnd(30)} \${a.asset_class.padEnd(8)} \${a.capacity_mw} МВт\`);
}`;

const EX_FETCH_RDN = `import { KrytsiaClient } from "@krytsia/sdk-ts";

const client = new KrytsiaClient({
  baseURL: process.env.KRYTSIA_API ?? "http://localhost:8000",
  tenantId: process.env.KRYTSIA_TENANT ?? "11111111-1111-1111-1111-111111111111",
});

const rdn = await client.market.rdn({
  date_start: "2026-05-12",
  date_end: "2026-05-12",
});

const capped = rdn.filter((r) => r.is_capped).length;
const max = rdn.reduce((m, r) => Math.max(m, Number(r.price_uah_mwh)), 0);
const min = rdn.reduce((m, r) => Math.min(m, Number(r.price_uah_mwh)), Infinity);

console.log(\`РДН на 2026-05-12: \${rdn.length} годин\`);
console.log(\`  максимум:    \${max.toFixed(2)} грн/МВт·год\`);
console.log(\`  мінімум:     \${min.toFixed(2)} грн/МВт·год\`);
console.log(\`  капнуто:     \${capped} годин\`);`;

const EX_QUERY_AGENT = `import { KrytsiaClient } from "@krytsia/sdk-ts";

const client = new KrytsiaClient({
  baseURL: process.env.KRYTSIA_API ?? "http://localhost:8000",
  tenantId: process.env.KRYTSIA_TENANT ?? "11111111-1111-1111-1111-111111111111",
});

const res = await client.agents.query(
  "dispatcher_analyst",
  "що сьогодні з виробництвом?",
);
console.log(\`→ \${res.answer}\`);
console.log(\`  intent: \${res.intent}, confidence: \${res.confidence}\`);
for (const e of res.evidence ?? []) {
  console.log(\`  · \${e.label}: \${e.value}\`);
}`;

const EXAMPLES = [
  {
    id: "list-assets",
    title: "Перерахувати активи",
    description: "Отримати всі активи у портфелі тенанта.",
    code: EX_LIST_ASSETS,
  },
  {
    id: "fetch-rdn",
    title: "Завантажити ціну РДН",
    description: "Отримати погодинні ціни Ринку «на добу наперед».",
    code: EX_FETCH_RDN,
  },
  {
    id: "query-agent",
    title: "Запитати AI-агента",
    description: "Класифікувати намір, повернути відповідь з evidence.",
    code: EX_QUERY_AGENT,
  },
];

export default function SdkTsPage() {
  const toast = useToast();
  const [copiedId, setCopiedId] = useState<string | null>(null);

  async function copy(id: string, code: string) {
    try {
      await navigator.clipboard.writeText(code);
      setCopiedId(id);
      toast.push({ tone: "success", title: "Скопійовано" });
      setTimeout(() => setCopiedId(null), 1500);
    } catch {
      toast.push({ tone: "alert", title: "Не вдалося скопіювати" });
    }
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Breadcrumb + header */}
      <header className="flex flex-col gap-2">
        <div className="flex items-center gap-2 text-xs text-text-muted">
          <Link
            href="/developer"
            className="inline-flex items-center gap-1 hover:text-accent-deep transition-colors"
          >
            <ArrowLeft size={12} /> Developer
          </Link>
          <span>/</span>
          <span>TypeScript SDK</span>
        </div>
        <h1 className="text-2xl sm:text-3xl font-bold text-text-heading flex items-center gap-2">
          <Boxes size={22} className="text-accent-deep" /> TypeScript SDK
        </h1>
        <p className="text-sm text-text-muted max-w-3xl">
          Thin-wrapper над <code className="text-xs font-mono px-1 py-0.5 rounded bg-bg-subtle">fetch</code>{" "}
          з типами, згенерованими з OpenAPI. Працює у Node 20+, Deno, Bun та у браузері.
        </p>
        <a
          href="https://github.com/basisabp1984/gecko-vpp-rebuild/tree/main/packages/sdk-ts"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 text-sm text-accent-deep hover:underline self-start"
        >
          <Github size={14} /> packages/sdk-ts на GitHub
        </a>
      </header>

      {/* Install */}
      <section className="rounded-xl border border-border bg-bg-card p-5 shadow-card">
        <h2 className="text-base font-semibold text-text-heading mb-3 flex items-center gap-2">
          <Terminal size={16} className="text-accent-deep" /> Встановлення
        </h2>
        <CodeBlock
          id="install"
          code={INSTALL_CMD}
          language="bash"
          copied={copiedId === "install"}
          onCopy={() => copy("install", INSTALL_CMD)}
        />
      </section>

      {/* Init */}
      <section className="rounded-xl border border-border bg-bg-card p-5 shadow-card">
        <h2 className="text-base font-semibold text-text-heading mb-1">Ініціалізація клієнта</h2>
        <p className="text-sm text-text-muted mb-3">
          Створіть один екземпляр на тенант. UUID тенанта летить у заголовку{" "}
          <code className="text-xs font-mono px-1 py-0.5 rounded bg-bg-subtle">X-Tenant-Id</code>{" "}
          автоматично.
        </p>
        <CodeBlock
          id="init"
          code={CLIENT_INIT}
          language="typescript"
          copied={copiedId === "init"}
          onCopy={() => copy("init", CLIENT_INIT)}
        />
      </section>

      {/* Examples */}
      <section className="flex flex-col gap-4">
        <h2 className="text-lg font-semibold text-text-heading">Приклади</h2>
        {EXAMPLES.map((ex) => (
          <article
            key={ex.id}
            className="rounded-xl border border-border bg-bg-card p-5 shadow-card"
          >
            <h3 className="text-base font-semibold text-text-heading mb-1">{ex.title}</h3>
            <p className="text-sm text-text-muted mb-3">{ex.description}</p>
            <CodeBlock
              id={ex.id}
              code={ex.code}
              language="typescript"
              copied={copiedId === ex.id}
              onCopy={() => copy(ex.id, ex.code)}
            />
          </article>
        ))}
      </section>
    </div>
  );
}

function CodeBlock({
  id,
  code,
  language,
  copied,
  onCopy,
}: {
  id: string;
  code: string;
  language: string;
  copied: boolean;
  onCopy: () => void;
}) {
  return (
    <div className="relative group">
      <button
        type="button"
        onClick={onCopy}
        aria-label="Скопіювати код"
        className="absolute top-2 right-2 inline-flex items-center gap-1 px-2 py-1 rounded border border-border bg-bg-card text-xs text-text-muted hover:text-text-heading hover:border-accent transition-colors opacity-90"
      >
        {copied ? <Check size={12} /> : <Copy size={12} />}
        {copied ? "Готово" : "Копіювати"}
      </button>
      <pre className="rounded-lg bg-bg-subtle border border-border p-4 overflow-x-auto text-xs font-mono text-text-body leading-relaxed">
        <code data-language={language}>{code}</code>
      </pre>
      <span aria-hidden className="hidden">
        {id}
      </span>
    </div>
  );
}
