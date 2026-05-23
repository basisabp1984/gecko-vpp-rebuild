"use client";

import Link from "next/link";
import { useState } from "react";
import {
  ArrowLeft,
  PlugZap,
  CircleDot,
  Bell,
} from "lucide-react";
import { useToast } from "@/components/Toast";

interface EventSpec {
  id: string;
  type: string;
  description: string;
  payload: object;
}

const EVENTS: EventSpec[] = [
  {
    id: "forecast.submitted",
    type: "forecast.submitted",
    description: "Прогноз генерації / навантаження подано до УкрЕнерго.",
    payload: {
      event: "forecast.submitted",
      tenant_id: "11111111-1111-1111-1111-111111111111",
      occurred_at: "2026-05-23T08:15:23+03:00",
      data: {
        submission_id: 4218,
        date: "2026-05-24",
        kind: "solar",
        status: "submitted",
        deadline_at: "2026-05-23T09:00:00+03:00",
      },
    },
  },
  {
    id: "document.signed",
    type: "document.signed",
    description: "Регуляторний документ підписано КЕП (демо-стуб у v2).",
    payload: {
      event: "document.signed",
      tenant_id: "11111111-1111-1111-1111-111111111111",
      occurred_at: "2026-05-23T11:42:01+03:00",
      data: {
        signed_doc_id: 91,
        document_type: "REPORT",
        signed_by: "operator@polyana.energy",
        is_demo_stub: true,
      },
    },
  },
  {
    id: "instruction.ack",
    type: "instruction.ack",
    description: "Диспетчерська інструкція підтверджена або відхилена оператором.",
    payload: {
      event: "instruction.ack",
      tenant_id: "11111111-1111-1111-1111-111111111111",
      occurred_at: "2026-05-23T13:01:55+03:00",
      data: {
        instruction_id: 7733,
        state: "acknowledged",
        operator_user_id: "u-12",
        reason: "aFRR-up",
      },
    },
  },
  {
    id: "optimisation.completed",
    type: "optimisation.completed",
    description: "Оптимізатор завершив прогін — є нові рекомендації setpoint-ів.",
    payload: {
      event: "optimisation.completed",
      tenant_id: "11111111-1111-1111-1111-111111111111",
      occurred_at: "2026-05-23T05:55:12+03:00",
      data: {
        optimisation_id: 552,
        scenario: "day_ahead",
        uplift_uah: "184320.50",
        confidence: 0.78,
        recommendations_count: 24,
      },
    },
  },
  {
    id: "setpoint.issued",
    type: "setpoint.issued",
    description: "Виписано новий setpoint на актив (УЗЕ заряд/розряд, СЕС обмеження).",
    payload: {
      event: "setpoint.issued",
      tenant_id: "33333333-3333-3333-3333-333333333333",
      occurred_at: "2026-05-23T14:00:00+03:00",
      data: {
        setpoint_id: 30911,
        asset_id: 12,
        effective_from: "2026-05-23T14:00:00+03:00",
        effective_to: "2026-05-23T15:00:00+03:00",
        target_power_mw: "-2.5",
        target_soc_pct: "65.0",
        reason: "arbitrage",
        state: "issued",
      },
    },
  },
  {
    id: "regulatory.event",
    type: "regulatory.event",
    description:
      "З'явилася нова постанова НКРЕКП / повідомлення УкрЕнерго / ринкова подія.",
    payload: {
      event: "regulatory.event",
      tenant_id: null,
      occurred_at: "2026-05-23T09:00:00+03:00",
      data: {
        id: 12,
        issuer: "НКРЕКП",
        act_type: "Постанова",
        act_number: "№ 871",
        severity: "WARN",
        category: "tariff",
        title: "Зміна годинних кепів РДН для категорії «виробник»",
        effective_at: "2026-06-01T00:00:00+03:00",
      },
    },
  },
];

const ALL_EVENT_IDS = EVENTS.map((e) => e.id);

export default function WebhooksPage() {
  const toast = useToast();
  const [email, setEmail] = useState("");
  const [url, setUrl] = useState("");
  const [selected, setSelected] = useState<string[]>(ALL_EVENT_IDS);

  function toggle(id: string) {
    setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));
  }

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!email || !url) {
      toast.push({ tone: "warning", title: "Заповніть email і URL" });
      return;
    }
    if (!url.startsWith("http")) {
      toast.push({
        tone: "alert",
        title: "URL має починатись з http:// або https://",
      });
      return;
    }
    if (selected.length === 0) {
      toast.push({ tone: "warning", title: "Оберіть хоча б одну подію" });
      return;
    }
    toast.push({
      tone: "success",
      title: "Підписка прийнята",
      description: `Ми повідомимо ${email} коли webhooks вийдуть з бети.`,
    });
    setEmail("");
    setUrl("");
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
          <span>Webhooks</span>
        </div>
        <h1 className="text-2xl sm:text-3xl font-bold text-text-heading flex items-center gap-2">
          <PlugZap size={22} className="text-accent-deep" /> Webhooks
        </h1>
        <p className="text-sm text-text-muted max-w-3xl">
          Push-сповіщення про події у вашому VPP-портфелі — без поллінгу. HMAC-SHA256 підпис у
          заголовку <code className="text-xs font-mono px-1 py-0.5 rounded bg-bg-subtle">X-Gecko-Signature</code>,
          ретраї з експоненційним відступом, доставка at-least-once.
        </p>
      </header>

      {/* Status banner */}
      <div className="rounded-xl border border-warning/40 bg-warning/10 p-4 flex items-start gap-3">
        <Bell size={18} className="text-warning shrink-0 mt-0.5" />
        <div>
          <div className="text-sm font-semibold text-text-heading">Поки що webhooks у стадії розробки</div>
          <p className="text-sm text-text-muted mt-1">
            Полінг через REST API уже працює — підпишіться нижче, щоб отримати раннє оповіщення про
            запуск push-доставки.
          </p>
        </div>
      </div>

      {/* Event types */}
      <section className="flex flex-col gap-4">
        <h2 className="text-lg font-semibold text-text-heading">Типи подій</h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {EVENTS.map((e) => (
            <article
              key={e.id}
              className="rounded-xl border border-border bg-bg-card p-4 shadow-card"
            >
              <div className="flex items-center gap-2 mb-1">
                <CircleDot size={14} className="text-accent-deep" />
                <code className="text-sm font-mono font-semibold text-text-heading">
                  {e.type}
                </code>
              </div>
              <p className="text-xs text-text-muted mb-3">{e.description}</p>
              <pre className="rounded-lg bg-bg-subtle border border-border p-3 overflow-x-auto text-[11px] font-mono text-text-body leading-relaxed">
                <code>{JSON.stringify(e.payload, null, 2)}</code>
              </pre>
            </article>
          ))}
        </div>
      </section>

      {/* Signup form */}
      <section className="rounded-xl border border-border bg-bg-card p-5 shadow-card">
        <h2 className="text-base font-semibold text-text-heading mb-1">
          Зареєструйтеся щоб отримати раннє оповіщення
        </h2>
        <p className="text-sm text-text-muted mb-4">
          Заповніть email + URL та оберіть події. Коли webhooks вийдуть з бети — ми відправимо
          тестовий пейлоад на вашу адресу.
        </p>
        <form onSubmit={submit} className="flex flex-col gap-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <label className="flex flex-col gap-1">
              <span className="text-xs font-medium text-text-muted">Email</span>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="dev@company.com"
                className="px-3 py-2 rounded-lg border border-border bg-bg-page text-sm focus:outline-none focus:border-accent transition-colors"
              />
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-xs font-medium text-text-muted">Webhook URL</span>
              <input
                type="url"
                required
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://hooks.company.com/gecko"
                className="px-3 py-2 rounded-lg border border-border bg-bg-page text-sm focus:outline-none focus:border-accent transition-colors"
              />
            </label>
          </div>

          <fieldset className="flex flex-col gap-2">
            <legend className="text-xs font-medium text-text-muted mb-1">
              Типи подій
            </legend>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {EVENTS.map((e) => (
                <label
                  key={e.id}
                  className="flex items-center gap-2 px-3 py-2 rounded-lg border border-border bg-bg-subtle hover:border-accent transition-colors cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={selected.includes(e.id)}
                    onChange={() => toggle(e.id)}
                    className="accent-accent"
                  />
                  <code className="text-xs font-mono text-text-body">{e.type}</code>
                </label>
              ))}
            </div>
          </fieldset>

          <button
            type="submit"
            className="self-start inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-accent text-text-inverse text-sm font-semibold hover:bg-accent-deep transition-colors"
          >
            Підписатись
          </button>
        </form>
      </section>
    </div>
  );
}
