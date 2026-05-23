# Brief v0.5 — амендмент до PRODUCT_BRIEF.md v0.4

**Status:** draft / awaiting customer confirmation
**Date:** 2026-05-23
**Trigger:** user message 2026-05-23 («подняти першу сторінку до wow-tier якості Elementum/Stripe/Linear, винести AI-агентів як головний диференціатор, додати 4 мови EN/PL/UK/RU»)
**Parent doc:** [PRODUCT_BRIEF.md](PRODUCT_BRIEF.md) v0.4 (frozen 2026-05-23 ранок)
**Methodology:** bible/level-0/0a (constitution) + bible/level-1/1.1 §2 (lifecycle phases) + 1.2 §9 (load-bearing facts)

> Цей амендмент **не переписує** v0.4 — він додає три нових напрямки роботи поверх існуючого Krytsia: візуальний апгрейд лендінгу, AI-перше позиціонування, мультимовність. Всі 31 acceptance-критерій v0.4 залишаються в силі без змін.

---

## 1. Проблема (Phase 1 — Understanding)

**Як прийшов запит від клієнта** (дослівно, для верифікації фреймінгу):

> «Мне больше всего понравились слайды Elementum — давай прямо у них спиздим грубо говоря... важно высочайшее качество и огромный размер... ни у кого нету в платформах такого класса AI-помощника, а ты в принципе их уже сделал... сделать упор на это... может даже стоит... платформа и AI как-то позиционироваться... и ещё нам сделать на четырёх языках — английский первый, потом польский, украинский и русский».

**Як я це розумію (переказ власними словами):**

Поточна головна Krytsia виглядає **функціонально**, але не передає враження «серйозного software-продукту» при першому відкритті на зустрічі з клієнтом. Треба:

1. **Підняти візуальний рівень першої сторінки** до tier-1 SaaS-сайтів (Elementum-style — кінематографічне відео згори; Stripe/Linear — анімовані елементи, висока поліровка). Не копіювати сюжет — копіювати **рівень якості і масштаб**.
2. **Зробити AI-агентів головним диференціатором** — не «приховану фічу у FAB», а **публічне позиціонування**: «Перша VPP+EMS платформа з AI-агентами в Україні». Бо ні в Enspirion, ні в Elementum, ні в інших польських/українських референсах ми такого не бачили.
3. **Підтримати 4 мови UI:** EN (default + perceived primary), PL, UK, RU. EN перший бо проєкт продаватиметься міжнародним інвесторам.

**Worst-case frame** (Principle 2):
- ❌ Якщо ми зробимо «red carpet» головну але без даних — клієнт побачить що це лише обгортка
- ❌ Якщо ми перехвалимо AI у копірайтингу але самі агенти десь у кутку — невідповідність
- ❌ Якщо i18n зламає роутинг або SEO — втрата вже задеплоєних посилань
- ❌ Якщо переклад буде машинний-калька — гірше ніж монолінгвальна сторінка
- ❌ Якщо `next-intl` несумісний з Next 16 webpack-mode → блокер для всього напрямку C

## 2. Інвентаризація артефактів (Phase 1, обов'язково)

| Артефакт | Стан перевірено | Висновок |
|---|---|---|
| https://krytsia.radai-1984.dev/ (live) | ✅ 2026-05-23 (сьогодні) | Дані тягнуться через API, FAB і AgentShowcase v1 вже на проді |
| `apps/web/app/page.tsx` | ✅ прочитано | 84 рядки: tagline + diagram + 3 persona cards + secondary links |
| `apps/web/components/AppShell.tsx` | ✅ прочитано | header + main + footer; FAB через `<AgentChat />` global mount |
| `apps/web/components/AgentChat.tsx` | ✅ прочитано | вже має FAB, bridge, 4 персони з іконками+samples |
| `apps/web/components/AgentShowcase.tsx` | ✅ створено сьогодні | 4-cards grid на головній, працює |
| `package.json` | ✅ Next 16.2.6 + React 19.2.4 + Tailwind 3.4 + Framer Motion 11.11 + webpack-mode | OK для i18n |
| Інші 28 роутів (`/producer/*`, `/c-i/*`, `/storage/*`, `/developer/*`, `/admin/*`) | ⚠️ структурно знаю, рядки на переклад НЕ інвентаризовано порядково | **дія:** Phase 3 додає крок «string extraction» перед перекладом |

## 3. Confirmed facts vs assumptions (1.2 §9)

**Confirmed facts** (підтверджено користувачем у поточній сесії):
- ✅ Стиль Elementum «дуже сподобався», особливо відео
- ✅ Дрон-погляд (солнечні станції згори) — бажаний сюжет
- ✅ «Не важливо ЩО показуємо — важлива якість і розмір»
- ✅ AI-агентів треба вивести як головний пункт
- ✅ Мови: EN (перший), PL, UK, RU
- ✅ Робота автономна, з субагентами де доцільно

**Assumptions** (мої дефолти — будуть діяти якщо клієнт не заперечить **до старту Phase B**):
- ❓ Назва продукту = **Krytsia** залишається (бо це його реальна компанія krytsia.com). НЕ перейменовуємо у «Krytsia AI» / «Krytsia Platform». Лише **тегляйн** додає AI-акцент.
- ❓ EN — це **дефолтний** locale (browser без preferences → `/en/...`); user-saved locale у localStorage перекриває
- ❓ Доменно-специфічні терміни УКР ринку (**РДН/ВДР/БР/ДД, ENTSO-E коди, КЕП, назви областей**) **не перекладаються** — це власні назви ринку, як «NASDAQ» не перекладають. Поряд буде tooltip-розшифровка англійською в EN-локалі.
- ❓ Стокове відео береться з **Pexels Videos** (CC0, безоплатно, комерційне) — 1-2 дрон-кліпи сонця/вітру 5-10 сек, lazy-loaded
- ❓ i18n-бібліотека = **next-intl 4.x** (App Router native, server-component friendly, mature). Розглянуто paraglide-js — менша спільнота для Next 16, ризик вищий
- ❓ Локалізація **не торкається API даних** — БД залишається з українськими регіонами/назвами активів, переклад тільки UI-шар

## 4. Out-of-scope (явно НЕ робимо у v0.5)

- ❌ Перейменування Python-модуля `gecko_vpp` → `krytsia` (це інша задача, обговорено раніше)
- ❌ Перейменування GitHub-репо
- ❌ Зміна архітектури БД, RLS, multi-tenant механіки
- ❌ Заміна VPP/EMS бізнес-логіки чи додавання DSR-модуля (це окреме рішення; обговорено по Enspirion але рішення відкладене)
- ❌ Переклад API-відповідей чи доменних кодів РДН/ВДР/БР
- ❌ Реальний live-голосовий AI (залишається Web Speech API stub, як у v0.4)
- ❌ 3D-сцени через three.js (overkill для першої ітерації)
- ❌ Власні відео-зйомки (стокові з Pexels, з атрибуцією у footer)

## 5. Success criteria (acceptance, перевіряються Phase 5)

### A — Cinematic hero rebuild
- A1. На `/` головній видно повноекранне hero з відео-фоном (drone aerial солнечні/вітрові поля), gradient overlay, новим теглайном
- A2. Hero має «огромный размер» — мінімум 70vh висоти на desktop, 60vh на mobile
- A3. Текст hero **двомовний за замовчуванням** через i18n (на EN-локалі — англ., на UK — укр., тощо)
- A4. Score на PageSpeed/Lighthouse ≥ 70 для Performance (відео LCP не критичний бо poster image)
- A5. Працює і у dark і у light темах

### B — AI-перше позиціонування
- B1. Теглайн hero містить **AI-першу формулу** (приклад: «AI-перша платформа для VPP та EMS. Чотири фахівці-агенти у вашому кабінеті.»)
- B2. AgentShowcase секція **збільшена і перенесена вгору** — після hero, **перед** architecture diagram
- B3. На кожному persona-dashboard (`/producer`, `/c-i`, `/storage`) додано prominent «AI-помічник» картку з 2-3 sample queries
- B4. У footer додано слоган «Перша VPP+EMS платформа з AI-агентами в Україні»
- B5. Title `<head>` оновлений: «Krytsia — AI-перша платформа для VPP та EMS»

### C — i18n
- C1. Локалі: EN, PL, UK, RU. Routing: `/en/...`, `/pl/...`, `/uk/...`, `/ru/...`
- C2. Default redirect: `/` → `/en` (можна змінити через user локаль у localStorage)
- C3. Селектор локалі видно у header (поряд з TenantSwitcher)
- C4. Усі 29 існуючих UI-маршрутів працюють на всіх 4 локалях
- C5. **Жодного UA-тексту на EN-локалі** окрім: brand name «Krytsia», market codes (РДН/ВДР/БР), назви активів і регіонів (бо це власні назви)
- C6. Перемикання локалі НЕ перевантажує дані з API (тільки UI-ререндер)
- C7. SEO — `<html lang="...">` встановлюється по локалі, `hreflang` теги між версіями

### D — Не зламано існуюче
- D1. Усі дані з API продовжують відображатись (regression check)
- D2. Усі 29 маршрутів повертають 200 на проді
- D3. AI-агенти продовжують відповідати з evidence-chips
- D4. RLS multi-tenant продовжує працювати

## 6. Capability boundary (1.2 §2)

| Дія | Що я можу | Boundary |
|---|---|---|
| Знайти і вбудувати стокове відео | ✅ Так (CC0 з Pexels via WebFetch + download) | Не генерую відео самостійно |
| Написати i18n структуру і код | ✅ Так | — |
| Перекласти UI-тексти EN/PL/UK/RU | ✅ Так (через 3 паралельних субагенти) | Якість на рівні «native speaker grammatically correct», без літературної редактури |
| Згенерувати фотореалістичні зображення | ❌ Ні | Інструменти не вміють |
| 3D motion graphics як у Apple | ❌ Не у v0.5 | Outside scope |
| Запустити Lighthouse на Vercel preview | ✅ Так | — |
| Зробити cinematic motion-design як топ-агентство | ⚠️ Частково | Досягну «serious SaaS tier», не «top agency tier» |

## 7. Архітектура виконання (Phase 3)

### Фаза A — Hero + AI emphasis (sequential, ~4 год)
**Залежності:** жодних. Працює окремо.

- **A1.** Створити `components/HeroVideo.tsx`: full-bleed `<video autoplay loop muted playsInline>` з poster, gradient overlay, slot для headline/CTA. Стокове відео завантажене у `public/hero/` (1-2 файли по 1-2 MB MP4, перекодовані під веб).
- **A2.** Переробити `app/page.tsx`: новий порядок — HeroVideo → AgentShowcase (enlarged) → ArchitectureDiagram → ScenarioCards → secondary links.
- **A3.** Збільшити AgentShowcase — більші картки, помітніший фон, окремий заголовок-якір.
- **A4.** Додати «AI-помічник» картку на `/producer`, `/c-i`, `/storage` (новий компонент `PersonaAIHelper.tsx`).
- **A5.** Оновити `<head>` title + footer slogan.
- **A6.** Commit + deploy + smoke-test.

### Фаза B — i18n infrastructure (sequential, ~3-4 год)
**Залежності:** A завершено (інакше переробляти і нові, і старі компоненти двічі).

- **B1.** Встановити `next-intl@4`, перевірити Next 16 webpack-mode на dev-server.
- **B2.** Налаштувати `i18n.ts`, `middleware.ts` (locale routing), `[locale]` segment у `app/`.
- **B3.** Витягнути усі UI-strings у `messages/en.json` (master). Цей крок робить субагент Explore/general-purpose — він пробігається по всіх .tsx файлах і витягує всі рядки.
- **B4.** Міграція компонентів на `useTranslations()` — це найбільший обʼєм роботи.
- **B5.** Реалізувати `LocaleSwitcher.tsx` (dropdown EN/PL/UK/RU з прапорами).
- **B6.** Commit + deploy + smoke-test на EN.

### Фаза C — Translations (parallel, ~2-3 год)
**Залежності:** B завершено (інакше нема що перекладати).

Працюють **три субагенти паралельно** (Principle 14 — independent lines of work):
- **C1.** Subagent PL: бере `messages/en.json` → видає `messages/pl.json`
- **C2.** Subagent UK: бере `messages/en.json` → видає `messages/uk.json`
- **C3.** Subagent RU: бере `messages/en.json` → видає `messages/ru.json`

Усі три — окремі контексти, не діляться working copy.

Після кожного — я перевіряю на смислові помилки (швидкий діагональний read).

### Фаза D — Verify & deploy (sequential, ~1 год)
- D1. Build локально (webpack mode).
- D2. Smoke-test всі 29 роутів × 4 локалі = 116 запитів автоматично (curl loop).
- D3. Vercel prod deploy.
- D4. Verify на krytsia.radai-1984.dev — кожна локаль, кожен головний дашборд.
- D5. Lighthouse score на головній.

**Загальна оцінка:** ~10-12 годин агентної роботи. З паралелізмом фази C → ~8-9.

## 8. FMEA (топ-ризики)

| Ризик | Severity | Probability | Detection | Response |
|---|---|---|---|---|
| `next-intl@4` несумісний з Next 16 webpack-mode | High | Medium | dev-server fail на B1 | Fallback: `react-i18next` ручне налаштування |
| Стокове відео > 3 MB → повільний LCP | Med | High | Lighthouse < 60 | Перекодувати в WebM + AV1, або poster-only без autoplay |
| Машинний переклад дає кальку | High | Med | мій diagonal-read post-translation | Запит у субагентів: «використовуй идиоматичные конструкции», + я виправляю самі грубі помилки |
| RLS-роутинг ламається через `/[locale]/...` префікс | High | Low | smoke-test 116 запитів | Налаштувати `middleware.ts` так щоб `X-Tenant-Id` проходив незалежно від локалі |
| Брендова палітра teal губиться на відео-фоні | Med | Med | дизайн-рев'ю на A1 | Сильніший gradient overlay + контрастний CTA |
| Тег `<html lang>` залишається `uk` → SEO confusion | Low | Med | inspect HTML on prod | RootLayout приймає `locale` параметр |

## 9. Decisions taken (Principle 16 — рішення, не меню)

Я обираю наступне і пропоную користувачу підтвердити **загальний курс**, а не питати по кожному пункту:

1. **Назва продукту → Krytsia (без змін).** Емфаза AI — лише через теглайн та копірайт.
2. **Стокове відео з Pexels.** 1-2 кліпи дронових кадрів СЕС/ВЕС, з атрибуцією у footer.
3. **i18n = next-intl@4.** Якщо не зайде з Next 16 webpack — переключаємось на `react-i18next` (план Б у FMEA).
4. **EN — дефолтний routing locale.** `/` редиректить на `/en`.
5. **Market codes і регіони не перекладаються.** РДН/ВДР/БР/ДД, ENTSO-E коди, oblasti — залишаються українською.
6. **Black-box доменна логіка не торкається.** Лише UI, копірайт, контентні рядки.

## 10. Що відкриває цей амендмент

Після підтвердження клієнтом — починаю **Phase 4 (Implementation)** негайно, без додаткових питань, з checkpoint-ами:
- після фази A — show & tell (live preview), 5-хв пауза
- після фази B — show & tell (EN-only локаль працює)
- після фази C — show & tell (всі 4 локалі)
- після фази D — фінальний звіт

Якщо щось зламається — повертаюсь у відповідну фазу (Principle 5, 1.1 §3 «не waterfall»). Інциденти логую у `difficulties_log.md`. Пам'ять `feedback_*` оновлюю на кожному значущому уроці.
