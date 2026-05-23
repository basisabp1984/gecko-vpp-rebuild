# Tier 1 — Ukrainian VPP / EMS / energy SaaS frontends

**Researcher:** Tier-1 subagent
**Date:** 2026-05-23
**Scope:** Public-facing VPP, EMS, energy-trading and regulator portals operating in Ukraine.
**Bias / confidence note:** Public VPP-class products in Ukraine are nearly absent — the regulatory regime for the "aggregator" institute is still in NKREKP consultation phase. Most findings are marketing sites, regulator dashboards, and utility customer cabinets. No live VPP operator dashboard was successfully viewed.

---

## Platform: Aggregator.Energy
- **Region:** Ukraine (IP held by Phage Technologies OÜ, Tallinn — but the product targets Ukrainian distributed energy resources)
- **Customer segment they target:** Businesses with own generation, generation facilities, grid operators (DSO/TSO), households — explicitly four segments in their "Для кого" block
- **Public product URL(s):** https://aggregator.energy/ , https://aggregator.energy/en/ , https://home.aggregator.energy/
- **Pricing model:** NOT FOUND (lead-form-driven; "Залишити заявку" / "Замовити консультацію")
- **Screenshots / video / demo URLs:** Marketing page contains hero imagery of BESS containers and animated GIFs demonstrating "how it works"; no product UI screenshots, no demo video, no app store links found on the public site
- **Stated tech stack:** NOT FOUND. Only protocol mention is MQTT for modern inverters and a "~$150 communication adapter" for legacy gear

### Information architecture
- **Pages observed:** Marketing-site only — "Приєднуйся", "Для кого", "Переваги", "Питання та відповіді", "Як це працює", "Партнери"
- **Home screen layout:** No authenticated product UI publicly exposed. Login portal not discoverable from the marketing site.
- **Multi-tenancy / org switcher:** NOT FOUND

### Visualisation patterns
- NOT FOUND in product (only marketing GIFs / static infographics)
- Marketing-page numbers shown as big-number tiles: "40+ specialists", "10+ connected participants", "86,950+ MWt generated"

### Interaction patterns
- **Overlays / drawers / modals:** Lead-capture form modal only
- **Command palette:** NOT FOUND
- **Floating helpers / chat:** NOT FOUND
- **Keyboard shortcuts surfaced:** NOT FOUND

### Theme & visual language
- **Theme:** Light
- **Brand accent colour:** Blue (specific hex not visible)
- **Typography:** Sans-serif
- **Density:** Spacious (marketing site)

### AI / agent features
- **Text AI assistant:** NOT FOUND in UI (claimed-but-not-verified: "AI-driven optimisation up to 30% lower consumption" — promotional claim)
- **Voice assistant:** NOT FOUND
- **Recommendations / insight cards:** NOT FOUND in UI; press copy claims "earn 30–50% annually by auto-selling surplus"

### SDK / public API
- **Public API documented:** NOT FOUND
- **SDK:** NOT FOUND
- **Webhooks:** NOT FOUND

### Things this platform does NOT have (vs our brief)
- No publicly visible product UI at all — pure marketing
- No documented API / SDK
- No demo or video walkthrough
- No pricing transparency
- No tenant model exposed

### Things this platform has that our v1 missed
- Clear Ukrainian-language segmentation into four customer types (Бізнес / Генерація / Оператор мережі / Домогосподарство) — a useful taxonomy our v1 collapsed
- Realistic emphasis on legacy-equipment adapters (acknowledges that Ukrainian DER fleet is not green-field)

### Frontend-tech-lead's-eye verdict
A senior FE lead would conclude there is no product to look at. The marketing site is credible (segmentation, FAQ depth, EN mirror) but the absence of even a screenshot or "request demo" page with a UI preview reads as "pre-product / pre-pilot". We can record only the brand language and the four-segment IA model.

---

## Platform: YASNO Business (DTEK retail brand)
- **Region:** Ukraine
- **Customer segment they target:** Legal entities, SMBs, condominiums (ОСББ), industrial consumers; separate "Для дому" residential portal
- **Public product URL(s):** https://mybiz.kyiv.yasno.com.ua/ (business cabinet login), https://yasno.com.ua/business/energymanagement (energy-management product page), https://yasno.com.ua/chatbot
- **Pricing model:** Tied to underlying electricity-supply contract; the cabinet is a free customer service
- **Screenshots / video / demo URLs:** Press article describes new business cabinet feature set (https://grids.dtek.com/media-center/press/dtek-kievskie-elektroseti-zapustil-novyy-lichnyy-kabinet-s-rasshirennym-funktsionalom-dlya-biznes-klientov/) — actual screenshots NOT verifiable behind login
- **Stated tech stack:** NOT FOUND

### Information architecture
- **Pages observed (from public marketing & press):** "Особистий кабінет", "Розрахунок вартості", "Подача прогнозу", "Документи з цифровим підписом YASNO", "Енергоменеджмент", "Чат-бот"
- **Home screen layout (claimed, not verified):** Consumption history, forecast submission for next year, document workflow with e-signature
- **Multi-tenancy / org switcher:** Implicitly per-EDRPOU per contract — NOT verified in UI

### Visualisation patterns
- **Chart types (claimed):** "flexible customisable dashboards for analysing consumption trends" — NOT verified visually
- **Time-window controls:** Forecast for "next year or tariff plan period" mentioned — NOT verified
- **Data density:** NOT FOUND

### Interaction patterns
- **Floating helpers / chat:** Yes — heavy reliance on Viber + Telegram chatbots (~860k clients use chatbot per company press); web "online chat with operator" launched
- **Command palette / keyboard shortcuts:** NOT FOUND

### Theme & visual language
- **Theme:** Light
- **Brand accent colour:** YASNO yellow / black wordmark
- **Typography:** Sans-serif
- **Density:** Comfortable (consumer-grade)

### AI / agent features
- **Text AI assistant:** Chatbot (rule-based, not LLM as far as visible); meter readings, payments, energy-alert notifications
- **Voice assistant:** NOT FOUND
- **Recommendations / insight cards:** "Energy alerts" chatbot pushes blackout notifications

### SDK / public API
- NOT FOUND

### Things this platform does NOT have (vs our brief)
- No market-side functionality (no DAM/IDM/balancing visibility) — it is a supplier-customer-relationship portal, not a trading product
- No multi-site portfolio view exposed in public copy
- No public API

### Things this platform has that our v1 missed
- **Chatbot-first interaction model** — for UA users Viber/Telegram bots are dominant channels
- **"Подача прогнозу"** (forecast submission) as a first-class workflow — UA consumers above a threshold must forecast monthly consumption
- **E-signed document workflow** ("цифровим підписом YASNO") — KEP/Дія.Підпис integration is baseline in UA enterprise software

### Frontend-tech-lead's-eye verdict
Competent but conservative retail-utility portal — comparable to E.ON or Vattenfall in EU. Chatbot-first channel mix and e-signature workflow are the Ukraine-specific tells.

---

## Platform: AT "Оператор ринку" (OREE)
- **Region:** Ukraine (state operator for DAM/IDM)
- **Customer segment they target:** Market participants on DAM (РДН) and IDM (ВДР), regulators, analysts
- **Public product URL(s):** https://www.oree.com.ua/ , https://www.oree.com.ua/index.php/IDM_graphs , https://www.oree.com.ua/index.php/indexes
- **Pricing model:** Regulator-funded; public dashboards free, trading access via accreditation
- **Screenshots / video / demo URLs:** Live public analytics pages double as screenshots. NKREKP regulator also publishes a dashboard at https://www.nerc.gov.ua/news/novij-dashbord-yak-instrument-analizu-cin-na-vdr-ta-rdn
- **Stated tech stack:** PHP query strings — legacy LAMP — no modern SPA detected

### Information architecture
- **Pages observed:** Top nav — "MARKET DATA", "FOR MARKET PARTICIPANTS", "ABOUT US"; Analytics cards — "Daily analysis", "Monthly analysis (common)", "DAM indexes", "IDM indexes"
- **Home screen layout:** Static page with cards + DAM/IDM toggle and toggles "IPS" / "BEI"
- **Multi-tenancy / org switcher:** N/A (public read-only)

### Visualisation patterns
- **Chart types observed:** Line charts for price indexes; supply/demand area-or-bar chart; HHI and concentration-coefficient metric tiles
- **Time-window controls:** "Daily" / "Monthly" toggle as top-level navigation
- **Data density per screen:** Low — 4 large cards on the analysis page

### Interaction patterns
- **Accessibility controls:** Dark-mode toggle, font-sizing, zoom controls in the header — driven by UA accessibility law for public-sector sites
- **Command palette / floating chat / keyboard shortcuts:** NOT FOUND

### Theme & visual language
- **Theme:** Light by default with explicit dark-mode accessibility toggle
- **Brand accent colour:** Corporate blue
- **Typography:** Government-style sans-serif
- **Density:** Spacious / low

### AI / SDK / API
- All NOT FOUND

### Things this platform has that our v1 missed
- Exact Ukrainian regulatory terminology: РДН, ВДР, БР, СОП, HHI / coefficient of concentration as standard KPIs
- IPS / BEI segmentation toggles
- Accessibility (dark-mode, font-size) is a regulator expectation in UA state portals

### Frontend-tech-lead's-eye verdict
A regulator portal, not a product. Its value to us is the terminology and the visual baseline UA energy professionals see daily.

---

## Platform: НЕК "Укренерго" — ua.energy and Datahub
- **Region:** Ukraine (TSO / ОСП)
- **Customer segment they target:** Market participants (PPКО), DSOs, journalists, analysts; ENTSO-E integration
- **Public product URL(s):** https://ua.energy/ , https://ua.energy/datahub/
- **Pricing model:** State; free public data
- **Screenshots / video / demo URLs:** Datahub pages returned HTTP 403 to WebFetch
- **Stated tech stack:** NOT FOUND

### Information architecture
- **Pages observed (from search):** "Диспетчерська інформація", "Datahub", "Балансуючий ринок", "Допоміжні послуги", "ENTSO-E Transparency Platform" cross-link
- **Multi-tenancy:** Datahub requires PPКО registration — implies tenant-per-market-participant

### Things this platform has that our v1 missed
- **PPКО** registration concept (commercial-metering data service provider)
- ENTSO-E integration: any serious UA platform must speak ENTSO-E codes (BZN, MTU, A01-A99 process types)

### Frontend-tech-lead's-eye verdict
Cannot evaluate the UI directly (403). The TSO's Datahub being ENTSO-E-aligned is itself the finding.

---

## Platform: ДП "Гарантований покупець" (gpee.com.ua)
- **Region:** Ukraine
- **Customer segment they target:** RES producers on green tariff and feed-in-premium; auction winners
- **Public product URL(s):** https://www.gpee.com.ua/
- **Pricing model:** State-mandated counterparty

### Information architecture
- **Pages observed:** "Про нас", "Новини", "Офіційна інформація", "Участь у зеленому аукціоні", "Графіки розподілу", "Реєстр виробників ВДЕ", "Звіти"
- **Personal cabinet:** Each green-tariff producer has a working cabinet for "submitting forecasts of electricity production volumes" and obtaining "data necessary to calculate the share of compensation for regulating the Guaranteed Buyer's electricity imbalance"
- **Multi-tenancy:** Implicitly per-contract (per producer EDRPOU)

### Things this platform has that our v1 missed
- **Forecast submission as a regulatory obligation, not a product feature** — green-tariff producers must submit production forecasts to ГП
- **Imbalance compensation share** ("частка компенсації витрат на врегулювання небалансу") — a specific KPI line item

### Frontend-tech-lead's-eye verdict
A 2000s-era corporate site over a private back-office. The interesting signal is the workflow (forecast → imbalance → settlement compensation), not the UI.

---

## Platform: D.TRADING (DTEK)
- **Region:** Ukraine + 24 European countries
- **Customer segment they target:** Energy producers, traders, consumers seeking market access / RES offtake / hedging
- **Public product URL(s):** https://d.trading/
- **Pricing model:** B2B trading desk — bespoke; not SaaS
- **Screenshots:** None — corporate marketing only

### Things this platform has that our v1 missed
- Terminology: "RES offtake financial hedging, market access, nomination, regulatory reporting"
- Multi-country / multi-jurisdiction stance treated as first-class identity

### Frontend-tech-lead's-eye verdict
Evidence that the biggest Ukrainian trader does not ship a customer-facing SaaS — relationships are managed by humans on the trading floor. The natural buyer currently expects a phone call, not a product login.

---

## Platform: Energy Map (DiXi Group / USAID, energy-map.info)
- **Region:** Ukraine
- **Customer segment they target:** Analysts, journalists, government, market participants needing open data
- **Public product URL(s):** https://energy-map.info/uk/
- **Pricing model:** Free, donor-funded

### Information architecture
- **Pages observed:** Top nav UA/EN + auth; six dashboards — "Ринкові показники", "Видобуток", "Домогосподарства", "Виробничі показники", "Інфраструктура", "Energy Map"; five chains — Electricity, Gas, "Розпорядники", Heat, Oil; six thematics — "Виробництво", "Запаси", "Торгівля", "Транспортування", "Постачання", "Споживання"

### Visualisation patterns
- **Chart types observed:** Hourly line/area for IPS balance; multi-series line for cross-border flows; categorical bar/donut for trade-volume splits
- **Time-window controls:** Time-range picker per dataset; "hourly" granularity is a first-class concept

### Theme & visual language
- **Theme:** Light, professional
- **Brand accent colour:** DiXi Group / USAID co-branded

### SDK / public API
- **Public API documented:** YES — API access mentioned in footer/about

### Things this platform has that our v1 missed
- **Hourly granularity as default** for IPS-balance and cross-border flows
- **Bilingual UA/EN parity** as a first-class feature
- Public API on an open-data portal

### Frontend-tech-lead's-eye verdict
The closest thing to a "modern UA energy data product" that exists publicly. Conservative but coherent.

---

## Platform: UEEX (Українська енергетична біржа)
- **Region:** Ukraine
- **Customer segment they target:** Accredited market participants (electricity, gas, LPG, oil products, coal, timber)
- **Public product URL(s):** https://www.ueex.com.ua/eng/
- **Pricing model:** Accreditation + transaction fees

### Information architecture
- **Pages observed:** "UEEX", "Services", "Trading Information", "Exchange Quotations", "Accreditation", "Documents", "Training Center", "Press Center", "Analytics & Stability"
- **Trading apps referenced:** BETS, EPBETS (bilateral electricity), ETP (gas), Prozorro.Sale
- **Multi-tenancy:** Per-accredited-participant inside trading apps

### Things this platform has that our v1 missed
- **Accreditation as a gate** before any market action — UA users expect formal onboarding, not self-service
- Multi-commodity coverage

### Frontend-tech-lead's-eye verdict
A regulator-adjacent exchange site fronting multiple separate trading apps. The fragmented multi-app login is a Ukrainian pain point GECKO VPP can leverage by offering a single pane.

---

## Tier 1 summary

- **Platforms found:** 8 (Aggregator.Energy, YASNO Business, OREE/Operator rynku, Ukrenergo ua.energy, Гарантований покупець, D.TRADING, Energy Map, UEEX). Of these, exactly zero expose a verifiable end-to-end VPP / aggregation product UI to non-authenticated visitors.
- **Confidence:** Medium-low. High confidence on the absence of mature UA VPP-class products; low confidence on actual UI details of private cabinets.
- **Key terminology harvested:**
  - **РДН** — Ринок на добу наперед (Day-Ahead Market)
  - **ВДР** — Внутрішньодобовий ринок (Intraday Market)
  - **БР** — Балансуючий ринок (Balancing Market)
  - **СОП** — Оператор ринку (OREE = AT "Оператор ринку")
  - **ОСП** — Оператор системи передачі (TSO; Ukrenergo)
  - **ОСР** — Оператор системи розподілу (DSO)
  - **PPКО** — Постачальник послуг комерційного обліку
  - **Гарантований покупець (ГП)** — counterparty for RES under green tariff
  - **Зелений тариф / зелений аукціон** — feed-in tariff / RES auction
  - **Балансуюча група** — balance-responsible group
  - **Агрегатор** — proposed legal role for VPP operator (still in NKREKP consultation)
  - **ВДЕ** — Відновлювані джерела енергії (RES)
  - **Небаланс / врегулювання небалансу** — imbalance / imbalance settlement
  - **Допоміжні послуги** — ancillary services
  - **Прогноз споживання / виробництва** — consumption / production forecast (mandatory workflow)
  - **УЗЕ / BESS** — Battery Energy Storage System ("установка зберігання енергії")
  - **НКРЕКП** — national energy and utilities regulator
- **Visual / UX patterns observed:**
  - **Light theme is the UA default.** All inspected products default to light; dark mode appears only as a public-sector accessibility toggle, not as identity.
  - **Bilingual UA/EN parity** is a baseline expectation
  - **Forecast-submission workflow** is a first-class UA-specific feature absent from typical EU VPP UIs
  - **Chatbot channel (Viber / Telegram)** is a real complement to web UI for SMB customers
  - **E-signature (Дія.Підпис / KEP)** expected wherever a document is generated
  - **PHP-era IA** dominates regulator surfaces — flat nav, card grids, no SPA
  - **Hourly granularity** is the canonical time-step for balance / flow data
  - **Accessibility controls (font-size, dark-mode, zoom)** legally expected on state portals
  - Big-number tiles + animated GIF dominate UA marketing pages
- **Gaps in the Ukrainian market:**
  - **No screenshot-able VPP product UI** in Ukrainian market
  - No publicly visible trader cockpit
  - No public Ukrainian SDK (Energy Map's API is the only public surface)
  - No command-palette / keyboard-first UI
  - No LLM-grade text AI assistant
  - No tenant-switcher patterns visible publicly
  - No mobile-first energy-management product
- **Recommendations for GECKO VPP brand:**
  1. **Default to light theme** — UA energy professionals work in light-themed government and exchange portals all day; dark-only reads as "crypto", not energy.
  2. **Ship UA-EN parity** from day one
  3. **Speak the regulator's vocabulary verbatim** (РДН, ВДР, БР, ГП, ОСП, ОСР, балансуюча група, прогноз, небаланс)
  4. **Hourly granularity as default time grain**
  5. **Bake in forecast-submission UX** for consumption and (for RES) production
  6. **Plan for chatbot / Viber / Telegram channel** as a roadmap line
  7. **Plan KEP / Дія.Підпис integration** for any document the product emits
  8. **Adopt accessibility controls** (font-size, theme toggle, zoom)
  9. **Use the four-segment customer taxonomy** Aggregator.Energy uses (Бізнес / Генерація / Оператор мережі / Домогосподарство)
  10. **Don't invent acronyms.** Reuse what's already in users' heads.

**Final note:** The brief's hypothesis ("Ukraine likely does not have many public VPP-class platforms") is confirmed. The information gap is itself the finding: GECKO VPP enters a market where terminology and regulatory expectations are set, but the product paradigm is not yet established by any incumbent.
