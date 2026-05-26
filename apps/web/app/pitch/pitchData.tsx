import type { ReactNode } from "react";
import Link from "next/link";
import {
  Activity,
  Battery,
  BookOpen,
  Building2,
  ExternalLink,
  Factory,
  Globe2,
  Layers,
  Lightbulb,
  Mail,
  Send,
  Sparkles,
  TrendingUp,
  Workflow,
  Zap,
} from "lucide-react";

export interface PitchSlide {
  /** Used for aria-labels on dot navigation. */
  title: string;
  /** Tailwind classes applied to the slide background layer. */
  bgClass: string;
  /** Renders the slide body. Each slide is responsible for its own layout. */
  render: () => ReactNode;
}

const Eyebrow = ({ children }: { children: ReactNode }) => (
  <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-accent-subtle text-accent-deep text-xs sm:text-sm font-semibold uppercase tracking-wider">
    {children}
  </div>
);

const Bullet = ({
  icon: Icon,
  title,
  body,
}: {
  icon: React.ComponentType<{ size?: number; className?: string }>;
  title: string;
  body: ReactNode;
}) => (
  <div className="flex gap-4 items-start">
    <span className="inline-flex items-center justify-center w-11 h-11 rounded-2xl bg-accent-subtle text-accent-deep flex-shrink-0">
      <Icon size={20} />
    </span>
    <div>
      <div className="text-base sm:text-lg font-semibold text-text-heading">
        {title}
      </div>
      <p className="text-sm sm:text-base text-text-body leading-relaxed mt-1">
        {body}
      </p>
    </div>
  </div>
);

const StatCard = ({
  value,
  label,
}: {
  value: string;
  label: string;
}) => (
  <div className="px-5 py-4 rounded-2xl border border-border bg-bg-card">
    <div className="text-2xl sm:text-3xl font-extrabold text-accent-deep tracking-tight">
      {value}
    </div>
    <div className="text-xs sm:text-sm text-text-muted mt-1">{label}</div>
  </div>
);

export const PITCH_SLIDES: PitchSlide[] = [
  // 0 — Title
  {
    title: "Krytsia · титульний",
    bgClass:
      "bg-gradient-to-br from-bg-page via-bg-page to-accent-subtle/40",
    render: () => (
      <div className="text-center">
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-bg-card border border-border text-xs sm:text-sm font-semibold uppercase tracking-widest text-accent-deep">
          <Sparkles size={14} />
          RadAI · Презентація для партнерів
        </div>
        <h1 className="mt-8 text-6xl sm:text-7xl lg:text-8xl font-extrabold text-text-heading tracking-tight">
          Krytsia
        </h1>
        <p className="mt-5 text-lg sm:text-xl lg:text-2xl text-text-muted max-w-2xl mx-auto leading-snug">
          AI-first VPP + EMS платформа для українського ринку.
          <br className="hidden sm:block" />
          Що це таке, навіщо це вам — і що ми вже вміємо.
        </p>
        <div className="mt-14 inline-flex items-center gap-3 text-sm text-text-muted">
          <kbd className="px-2.5 py-1.5 rounded-lg border border-border bg-bg-card font-mono text-xs shadow-card">
            →
          </kbd>
          <span>Натисніть стрілку, щоб почати</span>
        </div>
      </div>
    ),
  },

  // 1 — European context: what is a VPP aggregator
  {
    title: "Європейський контекст",
    bgClass:
      "bg-gradient-to-br from-bg-page to-bg-subtle",
    render: () => (
      <div>
        <Eyebrow>
          <Globe2 size={14} /> Контекст
        </Eyebrow>
        <h2 className="mt-5 text-4xl sm:text-5xl lg:text-6xl font-extrabold text-text-heading tracking-tight leading-[1.05]">
          Європа вже зробила <span className="text-accent-deep">цей крок</span>
        </h2>
        <p className="mt-5 text-lg sm:text-xl text-text-muted max-w-3xl leading-relaxed">
          Сотні дрібних виробників, споживачів і батарей об&apos;єднуються у{" "}
          <strong className="text-text-heading">віртуальну електростанцію</strong>{" "}
          (VPP) — і торгуються на ринку як одна велика, передбачувана генерація.
        </p>

        <div className="mt-10 grid sm:grid-cols-3 gap-3 sm:gap-4">
          <StatCard value="~10 ГВт" label="портфель Next Kraftwerke (DE)" />
          <StatCard value="200+" label="VPP-операторів у Європі" />
          <StatCard value="2030" label="ціль ЄС: 60% VRES у мережі" />
        </div>

        <div className="mt-10 grid sm:grid-cols-2 gap-5 max-w-4xl">
          <Bullet
            icon={Workflow}
            title="Як це працює"
            body="Агрегатор підписує контракти з власниками малих станцій. Він прогнозує генерацію портфеля, виставляє ціни на РДН/ВДР, балансує дисбаланси через БР, торгує допоміжними послугами — і ділить дохід."
          />
          <Bullet
            icon={Layers}
            title="Хто це робить"
            body="Next Kraftwerke, Statkraft, Sonnen, Tiko, EnBW в Німеччині. Tauron, Enspirion у Польщі. Кожен — мільярдні обороти. В Україні незалежних операторів VPP практично немає."
          />
        </div>
      </div>
    ),
  },

  // 2 — What this means for grid operators
  {
    title: "Що це означає для вас",
    bgClass:
      "bg-gradient-to-br from-bg-page via-accent-subtle/20 to-bg-page",
    render: () => (
      <div>
        <Eyebrow>
          <TrendingUp size={14} /> Куди це йде в Україні
        </Eyebrow>
        <h2 className="mt-5 text-4xl sm:text-5xl lg:text-6xl font-extrabold text-text-heading tracking-tight leading-[1.05]">
          Ваші станції —{" "}
          <span className="text-accent-deep">сировина нового шару</span>
        </h2>
        <p className="mt-5 text-lg sm:text-xl text-text-muted max-w-3xl leading-relaxed">
          Сьогодні ваші об&apos;єкти — замкнуті системи. Завтра — будівельні
          блоки портфелів незалежних VPP-агрегаторів. Це нова виручка, до якої
          поодинці ви не доберетесь.
        </p>

        <div className="mt-10 grid sm:grid-cols-3 gap-4 max-w-5xl">
          <Bullet
            icon={Zap}
            title="Стабільний контрагент"
            body="Агрегатор гарантує викуп надлишку та бере на себе балансування — менше штрафів, передбачуваний грошовий потік."
          />
          <Bullet
            icon={Activity}
            title="Доступ до ринків"
            body="ВДР, БР, Допоміжні послуги — поодинці ви туди не зайдете. Через агрегатора — заходите автоматично."
          />
          <Bullet
            icon={Layers}
            title="Взаємне покриття"
            body="Вночі одна станція віддає, вдень інша забирає. У портфелі це нівелюється — а отже зменшує небаланси і збільшує ефективну ціну."
          />
        </div>

        <div className="mt-10 inline-flex items-start gap-3 px-5 py-4 rounded-2xl border border-accent/40 bg-accent-subtle/60 max-w-3xl">
          <Lightbulb
            size={20}
            className="text-accent-deep flex-shrink-0 mt-0.5"
          />
          <p className="text-sm sm:text-base text-text-body leading-relaxed">
            Не сьогодні. Не завтра. Але це напрям, куди рухається ринок.
            Хто адаптується першим — той перший і підключається до цих грошей.
          </p>
        </div>
      </div>
    ),
  },

  // 3 — What we (RadAI) built — Krytsia
  {
    title: "Krytsia — що ми побудували",
    bgClass:
      "bg-gradient-to-br from-bg-page via-bg-page to-accent-subtle/40",
    render: () => (
      <div>
        <Eyebrow>
          <Sparkles size={14} /> Що ми вже зробили
        </Eyebrow>
        <h2 className="mt-5 text-4xl sm:text-5xl lg:text-6xl font-extrabold text-text-heading tracking-tight leading-[1.05]">
          Krytsia — як це виглядає{" "}
          <span className="text-accent-deep">у коді</span>
        </h2>
        <p className="mt-5 text-lg sm:text-xl text-text-muted max-w-3xl leading-relaxed">
          Це працююча платформа VPP + EMS для українського ринку. Не статичні
          слайди — реальний backend, реальна база, реальні розрахунки. Тільки
          дані синтетичні; підставите свої — і продукт працює.
        </p>

        <div className="mt-10 grid sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 max-w-5xl">
          {[
            { icon: Activity, name: "Dispatch analyst", tag: "виробництво · небаланси · ТО" },
            { icon: TrendingUp, name: "Market analyst", tag: "біди · виручка · арбітраж" },
            { icon: Lightbulb, name: "Energy advisor", tag: "споживання · сценарії" },
            { icon: Battery, name: "Battery coach", tag: "SOC · цикли · заряд/розряд" },
          ].map(({ icon: Icon, name, tag }) => (
            <div
              key={name}
              className="p-4 rounded-2xl border border-border bg-bg-card"
            >
              <span className="inline-flex items-center justify-center w-10 h-10 rounded-xl bg-accent-subtle text-accent-deep mb-3">
                <Icon size={18} />
              </span>
              <div className="text-sm sm:text-base font-semibold text-text-heading">
                {name}
              </div>
              <div className="text-xs text-text-muted mt-1">{tag}</div>
            </div>
          ))}
        </div>

        <p className="mt-6 text-sm sm:text-base text-text-muted max-w-3xl leading-relaxed">
          Чотири AI-агенти, які знають живі дані з кабінету. Жодна інша VPP
          платформа в Україні такого не дає. Архітектура під ENTSO-E,
          мульти-тенант, ринкові терміни РДН/ВДР/БР/ДД/НКРЕКП — все на місці.
        </p>

        <div className="mt-8 flex flex-wrap gap-3">
          <Link
            href="/producer"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-5 py-3 rounded-xl bg-accent text-text-inverse hover:bg-accent-deep transition-colors text-sm sm:text-base font-semibold shadow-card"
          >
            <Factory size={16} /> Кабінет виробника
            <ExternalLink size={14} />
          </Link>
          <Link
            href="/c-i"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-5 py-3 rounded-xl border border-border bg-bg-card hover:border-accent transition-colors text-sm sm:text-base font-semibold text-text-body"
          >
            <Building2 size={16} /> Кабінет C&amp;I
            <ExternalLink size={14} />
          </Link>
          <Link
            href="/storage"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-5 py-3 rounded-xl border border-border bg-bg-card hover:border-accent transition-colors text-sm sm:text-base font-semibold text-text-body"
          >
            <Battery size={16} /> Кабінет накопичувача
            <ExternalLink size={14} />
          </Link>
          <Link
            href="/admin"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-5 py-3 rounded-xl border border-border bg-bg-card hover:border-accent transition-colors text-sm sm:text-base font-semibold text-text-body"
          >
            <BookOpen size={16} /> Адмін-консоль
            <ExternalLink size={14} />
          </Link>
        </div>
      </div>
    ),
  },

  // 4 — Готові поговорити
  {
    title: "Готові поговорити",
    bgClass:
      "bg-gradient-to-br from-accent-subtle/40 via-bg-page to-bg-page",
    render: () => (
      <div>
        <Eyebrow>
          <Send size={14} /> Контакти
        </Eyebrow>
        <h2 className="mt-5 text-4xl sm:text-5xl lg:text-6xl font-extrabold text-text-heading tracking-tight leading-[1.05]">
          Готові <span className="text-accent-deep">поговорити</span>
        </h2>

        <div className="mt-8 grid sm:grid-cols-3 gap-5 max-w-5xl">
          <Bullet
            icon={Workflow}
            title="Платформа для ваших станцій"
            body="Готовий скелет, який адаптується під ваш парк за тижні, не місяці."
          />
          <Bullet
            icon={Layers}
            title="Інтеграція з агрегатором"
            body="Архітектура вже сумісна з шаром VPP — мульти-тенант, ENTSO-E коди, ринкові протоколи."
          />
          <Bullet
            icon={Sparkles}
            title="Будь-яка ІТ-робота"
            body="Krytsia — це доказ, що ми вміємо робити складні енергетичні платформи швидко і якісно."
          />
        </div>

        <div className="mt-12 flex flex-wrap gap-3 items-center">
          <a
            href="mailto:basisabp1984@gmail.com?subject=Krytsia%20%2F%20VPP"
            className="inline-flex items-center gap-2 px-5 py-3 rounded-xl bg-accent text-text-inverse hover:bg-accent-deep transition-colors text-sm sm:text-base font-semibold shadow-card"
          >
            <Mail size={16} />
            basisabp1984@gmail.com
          </a>
          <a
            href="https://t.me/Radkovskyi_Andrii"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-5 py-3 rounded-xl border border-border bg-bg-card hover:border-accent transition-colors text-sm sm:text-base font-semibold text-text-body"
          >
            <Send size={16} />
            @Radkovskyi_Andrii
          </a>
          <a
            href="https://github.com/basisabp1984/gecko-vpp-rebuild"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-5 py-3 rounded-xl border border-border bg-bg-card hover:border-accent transition-colors text-sm sm:text-base font-semibold text-text-body"
          >
            <BookOpen size={16} />
            Код Krytsia на GitHub
            <ExternalLink size={14} />
          </a>
        </div>

        <p className="mt-12 text-sm sm:text-base text-text-muted max-w-2xl">
          Якщо тема резонує — напишіть. Розкажемо детальніше, покажемо живий
          кабінет, обговоримо, що з цього підходить саме вам.
        </p>
      </div>
    ),
  },
];
