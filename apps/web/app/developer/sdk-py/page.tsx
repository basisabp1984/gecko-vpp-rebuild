"use client";

import Link from "next/link";
import { useState } from "react";
import { ArrowLeft, Code2, Copy, Check, Github, Terminal } from "lucide-react";
import { useToast } from "@/components/Toast";

const INSTALL_CMD = `pip install krytsia-sdk
# або
poetry add krytsia-sdk
# або
uv add krytsia-sdk`;

const CLIENT_INIT = `from krytsia_sdk import KrytsiaClient

with KrytsiaClient(
    base_url="http://localhost:8000",
    tenant_id="11111111-1111-1111-1111-111111111111",
) as client:
    ...`;

const EX_LIST_ASSETS = `"""List all assets in the demo portfolio."""
import os
from krytsia_sdk import KrytsiaClient

with KrytsiaClient(
    base_url=os.environ.get("KRYTSIA_API", "http://localhost:8000"),
    tenant_id=os.environ.get("KRYTSIA_TENANT", "11111111-1111-1111-1111-111111111111"),
) as client:
    assets = client.assets()
    print(f"Знайдено {len(assets)} активів:")
    for a in assets:
        print(f"  {a['code']:<20} {a['display_name']:<30} {a['asset_class']:<8} {a['capacity_mw']:>7} МВт")`;

const EX_FETCH_RDN = `"""Fetch one day of РДН prices and summarise."""
import os
from krytsia_sdk import KrytsiaClient

with KrytsiaClient(
    base_url=os.environ.get("KRYTSIA_API", "http://localhost:8000"),
    tenant_id=os.environ.get("KRYTSIA_TENANT", "11111111-1111-1111-1111-111111111111"),
) as client:
    rdn = client.market_rdn(date_start="2026-05-12", date_end="2026-05-12")
    prices = [float(r["price_uah_mwh"]) for r in rdn]
    capped = sum(1 for r in rdn if r["is_capped"])

    print(f"РДН на 2026-05-12: {len(rdn)} годин")
    print(f"  максимум:    {max(prices):.2f} грн/МВт·год")
    print(f"  мінімум:     {min(prices):.2f} грн/МВт·год")
    print(f"  капнуто:     {capped} годин")`;

const EX_QUERY_AGENT = `"""Ask the dispatcher analyst a question."""
import os
from krytsia_sdk import KrytsiaClient

with KrytsiaClient(
    base_url=os.environ.get("KRYTSIA_API", "http://localhost:8000"),
    tenant_id=os.environ.get("KRYTSIA_TENANT", "11111111-1111-1111-1111-111111111111"),
) as client:
    res = client.agents_query(
        "dispatcher_analyst",
        "що сьогодні з виробництвом?",
    )
    print(f"→ {res['answer']}")
    print(f"  intent: {res['intent']}, confidence: {res['confidence']}")
    for e in res.get("evidence", []):
        print(f"  · {e['label']}: {e['value']}")`;

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

export default function SdkPyPage() {
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
      <header className="flex flex-col gap-2">
        <div className="flex items-center gap-2 text-xs text-text-muted">
          <Link
            href="/developer"
            className="inline-flex items-center gap-1 hover:text-accent-deep transition-colors"
          >
            <ArrowLeft size={12} /> Developer
          </Link>
          <span>/</span>
          <span>Python SDK</span>
        </div>
        <h1 className="text-2xl sm:text-3xl font-bold text-text-heading flex items-center gap-2">
          <Code2 size={22} className="text-accent-deep" /> Python SDK
        </h1>
        <p className="text-sm text-text-muted max-w-3xl">
          Обгортка над <code className="text-xs font-mono px-1 py-0.5 rounded bg-bg-subtle">httpx</code>{" "}
          для CPython 3.11+. Працює у скриптах, Jupyter та FastAPI-сервісах.
        </p>
        <a
          href="https://github.com/basisabp1984/gecko-vpp-rebuild/tree/main/packages/sdk-py"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 text-sm text-accent-deep hover:underline self-start"
        >
          <Github size={14} /> packages/sdk-py на GitHub
        </a>
      </header>

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

      <section className="rounded-xl border border-border bg-bg-card p-5 shadow-card">
        <h2 className="text-base font-semibold text-text-heading mb-1">Ініціалізація клієнта</h2>
        <p className="text-sm text-text-muted mb-3">
          Використовуйте контекстний менеджер — він автоматично закриває HTTP-сесію.
        </p>
        <CodeBlock
          id="init"
          code={CLIENT_INIT}
          language="python"
          copied={copiedId === "init"}
          onCopy={() => copy("init", CLIENT_INIT)}
        />
      </section>

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
              language="python"
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
