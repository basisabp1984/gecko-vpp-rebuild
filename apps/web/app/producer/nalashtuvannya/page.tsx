"use client";

import { useState } from "react";
import clsx from "clsx";
import {
  CheckCircle2,
  Circle,
  ArrowRight,
  UserPlus,
  Send,
  ServerCog,
  Mail,
  Webhook,
  ShieldCheck,
  Activity,
  Network,
  Building2,
  FileSignature,
} from "lucide-react";
import { useAPI } from "@/lib/api";
import { useToast } from "@/components/Toast";

interface AuthMe {
  tenant_id: string;
  tenant: {
    id: string;
    code: string;
    display_name: string;
    segment: string;
    edrpou: string;
    participant_eic: string;
    bzn_eic: string;
    region: string;
  };
  current_user: {
    id: string;
    display_name: string;
    role: string;
  };
}

interface StepItem {
  done: boolean;
  inProgress?: boolean;
  active?: boolean;
  title: string;
  description: string;
}

const STEPS: StepItem[] = [
  {
    done: true,
    title: "Аналіз активів та цілей",
    description:
      "Інвентаризація активів, визначення бізнес-цілей та KPI, базова сегментація портфеля.",
  },
  {
    done: false,
    inProgress: true,
    title: "Технічна інтеграція та налаштування EMS",
    description:
      "Підключення SCADA, OPC-UA та MQTT, конфігурація прогнозних моделей і кеп-логіки.",
  },
  {
    done: false,
    active: true,
    title: "Operations — щоденна робота на ринках",
    description:
      "Подача прогнозів до ГП, торгівля на РДН/ВДР, балансування і диспетчеризація.",
  },
  {
    done: false,
    active: true,
    title: "Результати — звіти, ESG, КЕП",
    description:
      "Місячні розрахункові акти, ESG-показники, підписи КЕП, регуляторні звіти.",
  },
];

interface IntegrationCard {
  name: string;
  description: string;
  icon: React.ReactNode;
  status: "Ready for API" | "Mock" | "Planned";
}

const INTEGRATIONS: IntegrationCard[] = [
  {
    name: "SCADA Modbus TCP",
    description: "Опитування інверторів та лічильників через Modbus реєстри",
    icon: <ServerCog size={18} />,
    status: "Ready for API",
  },
  {
    name: "OPC-UA сервер",
    description: "Промисловий стандарт для ВЕС та ГПУ контролерів",
    icon: <Network size={18} />,
    status: "Ready for API",
  },
  {
    name: "MQTT broker",
    description: "Легкий transport для IoT-датчиків і мобільних диспетчерів",
    icon: <Activity size={18} />,
    status: "Mock",
  },
  {
    name: "Email звіти",
    description: "Щотижневі та щомісячні PDF-зведення на пошту команди",
    icon: <Mail size={18} />,
    status: "Mock",
  },
  {
    name: "КЕП провайдер (АЦСК)",
    description: "Дія, Приват, ІДД ДПС — для підпису розрахункових актів",
    icon: <FileSignature size={18} />,
    status: "Mock",
  },
  {
    name: "Outbound webhook",
    description: "Подія `setpoint.updated` → ваш HTTP endpoint",
    icon: <Webhook size={18} />,
    status: "Planned",
  },
  {
    name: "Single Sign-On (SAML/OIDC)",
    description: "Корпоративна автентифікація через Okta, Azure AD",
    icon: <ShieldCheck size={18} />,
    status: "Planned",
  },
];

export default function ProducerSettingsPage() {
  const me = useAPI<AuthMe>("/api/v1/auth/me");
  const tenant = me.data?.data?.tenant;
  const toast = useToast();

  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("operator");

  function sendInvite(e: React.FormEvent) {
    e.preventDefault();
    if (!inviteEmail.trim()) return;
    toast.push({
      tone: "success",
      title: "Запрошення надіслано (демо)",
      description: `${inviteEmail} · роль: ${inviteRole}`,
    });
    setInviteEmail("");
  }

  return (
    <div className="flex flex-col gap-6">
      <header>
        <h1 className="text-2xl sm:text-3xl font-bold text-text-heading">
          Налаштування
        </h1>
        <p className="text-sm text-text-muted">
          Етапи онбордингу, інтеграції, профіль та команда.
        </p>
      </header>

      {/* Onboarding checklist */}
      <section className="rounded-xl border border-border bg-bg-card shadow-card overflow-hidden">
        <header className="p-4 border-b border-border">
          <h2 className="text-base font-semibold text-text-heading">
            Етапи запуску
          </h2>
          <p className="text-xs text-text-muted">
            Стандартний шлях від першого підключення до повної автоматизації.
          </p>
        </header>
        <ol className="divide-y divide-border">
          {STEPS.map((s, i) => (
            <li
              key={i}
              className={clsx(
                "p-4 flex items-start gap-3",
                s.inProgress && "bg-info/5",
              )}
            >
              <div className="shrink-0 mt-0.5">
                {s.done ? (
                  <CheckCircle2 size={22} className="text-success" />
                ) : (
                  <Circle
                    size={22}
                    className={
                      s.inProgress ? "text-info" : "text-text-muted"
                    }
                  />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <h3 className="text-sm font-semibold text-text-heading">
                    {i + 1}. {s.title}
                  </h3>
                  {s.done && (
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-success/15 text-success">
                      Завершено
                    </span>
                  )}
                  {s.inProgress && (
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-info/15 text-info">
                      У процесі (автоматично)
                    </span>
                  )}
                  {s.active && !s.inProgress && !s.done && (
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-accent-subtle text-accent-deep">
                      Активно
                    </span>
                  )}
                </div>
                <p className="text-sm text-text-muted mt-1">{s.description}</p>
                <a
                  href="#"
                  className="mt-1.5 inline-flex items-center gap-1 text-xs text-accent hover:text-accent-deep"
                  onClick={(e) => e.preventDefault()}
                >
                  Детальніше
                  <ArrowRight size={11} />
                </a>
              </div>
            </li>
          ))}
        </ol>
      </section>

      {/* Tenant profile */}
      <section className="rounded-xl border border-border bg-bg-card shadow-card p-5">
        <header className="flex items-center justify-between mb-3">
          <h2 className="text-base font-semibold text-text-heading flex items-center gap-2">
            <Building2 size={16} className="text-accent" />
            Профіль клієнта
          </h2>
          <button
            type="button"
            onClick={() =>
              toast.push({
                tone: "info",
                title: "Редагування профілю",
                description: "Доступне в наступному релізі",
              })
            }
            className="text-xs px-3 py-1 rounded border border-border bg-bg-card hover:border-accent"
          >
            Редагувати
          </button>
        </header>
        {me.isLoading ? (
          <div className="text-sm text-text-muted">Завантаження…</div>
        ) : !tenant ? (
          <div className="text-sm text-alert">
            Не вдалося отримати дані клієнта.
          </div>
        ) : (
          <dl className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            <ProfileField label="Назва" value={tenant.display_name} />
            <ProfileField label="Код клієнта" value={tenant.code} />
            <ProfileField
              label="ЄДРПОУ"
              value={<span className="font-mono">{tenant.edrpou}</span>}
            />
            <ProfileField
              label="Participant EIC"
              value={
                <span className="font-mono text-xs">
                  {tenant.participant_eic.trim()}
                </span>
              }
            />
            <ProfileField
              label="Bidding Zone EIC"
              value={
                <span className="font-mono text-xs">{tenant.bzn_eic}</span>
              }
            />
            <ProfileField label="Регіон" value={tenant.region} />
            <ProfileField label="Сегмент" value={tenant.segment} />
          </dl>
        )}
      </section>

      {/* Integrations */}
      <section>
        <header className="mb-3">
          <h2 className="text-base font-semibold text-text-heading">
            Каталог інтеграцій
          </h2>
          <p className="text-xs text-text-muted">
            Поточний статус готовності з'єднань. Демонстраційні підключення —
            тег Mock.
          </p>
        </header>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {INTEGRATIONS.map((it) => (
            <article
              key={it.name}
              className="rounded-xl border border-border bg-bg-card p-4 shadow-card flex flex-col gap-2"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="inline-flex items-center justify-center w-9 h-9 rounded-lg bg-accent-subtle text-accent-deep">
                  {it.icon}
                </span>
                <IntegrationBadge status={it.status} />
              </div>
              <h3 className="text-sm font-semibold text-text-heading">
                {it.name}
              </h3>
              <p className="text-xs text-text-muted flex-1">{it.description}</p>
            </article>
          ))}
        </div>
      </section>

      {/* Invite teammate */}
      <section className="rounded-xl border border-border bg-bg-card shadow-card p-5">
        <header className="mb-3">
          <h2 className="text-base font-semibold text-text-heading flex items-center gap-2">
            <UserPlus size={16} className="text-accent" />
            Запросити колегу
          </h2>
          <p className="text-xs text-text-muted">
            Надішліть email-запрошення з заданою роллю.
          </p>
        </header>
        <form
          onSubmit={sendInvite}
          className="flex flex-col sm:flex-row gap-2 items-stretch sm:items-center"
        >
          <input
            type="email"
            placeholder="colleague@example.com"
            value={inviteEmail}
            onChange={(e) => setInviteEmail(e.target.value)}
            className="flex-1 rounded-md border border-border bg-bg-page px-3 py-2 text-sm"
            required
          />
          <select
            value={inviteRole}
            onChange={(e) => setInviteRole(e.target.value)}
            className="rounded-md border border-border bg-bg-page px-3 py-2 text-sm"
          >
            <option value="operator">Оператор</option>
            <option value="analyst">Аналітик</option>
            <option value="admin">Адмін</option>
            <option value="readonly">Тільки перегляд</option>
          </select>
          <button
            type="submit"
            className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-md bg-accent text-text-inverse font-medium hover:bg-accent-deep"
          >
            <Send size={14} />
            Надіслати запрошення
          </button>
        </form>
      </section>
    </div>
  );
}

function ProfileField({
  label,
  value,
}: {
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border border-border bg-bg-page p-3">
      <dt className="text-[10px] uppercase tracking-wide text-text-muted">
        {label}
      </dt>
      <dd className="text-sm text-text-heading font-medium mt-0.5 break-words">
        {value}
      </dd>
    </div>
  );
}

function IntegrationBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    "Ready for API": "bg-success/15 text-success",
    Mock: "bg-warning/15 text-warning",
    Planned: "bg-bg-subtle text-text-muted",
  };
  const tone = map[status] ?? "bg-bg-subtle text-text-muted";
  return (
    <span
      className={clsx(
        "inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium",
        tone,
      )}
    >
      {status}
    </span>
  );
}
