# PRODUCT_BRIEF — GECKO VPP

**Status:** v0.4 · fully frozen 2026-05-23 (Phase 2 research closed; all amendments incorporated; all open questions closed or dismissed; awaits user before Phase 3 Architecture starts)
**Source of truth:** this document. All downstream artefacts (Phase 3 architecture, Phase 4 code, Phase 5 verification) reference it.
**Inputs used:** `source/01_GECKO_VPP_client_brief.pdf` (11 slides), digested through `phase-1-understanding/_raw_extraction.md` + `_analysis.md`, then audited against `phase-2-solution/RESEARCH_FINDINGS.md` v0.1, `DESIGN_INSPIRATION.md`, `BRIEF_AMENDMENTS.md`.

This brief is **Phase 1 — Understanding** (frozen) in the bible's 6-phase task lifecycle. Phase 4 (code) does not begin until Phase 3 (Architecture) is approved.

---

## 1. What we are building

GECKO VPP — інфраструктурна платформа для портфельного управління енергетичними активами на українському ринку електроенергії. Aggregates physical energy assets of multiple owners into one disciplined trading-and-dispatch entity, and gives each owner a single screen for their generation, storage, consumption and revenue.

**Frame for this rebuild:** "production-fidelity demo" — a working skeleton with synthetic data flesh. End-to-end logic, real backend, real DB, real architectural separation. Only the data layer is synthetic. Swap synthetic for client data and the product runs.

**Category framing (per RF §1 conclusion 1):** No public UA VPP product exists yet. GECKO is the **category-creator** for Ukraine. The visual story (slide-7 architecture diagram + role-split workflow + KPI-first home) IS the differentiator — equal weight to functional depth.

**The slogan that anchors the product:**
> Робимо складну енергетику керованою. Для бізнесу. Для виробників. Для ринку.

---

## 2. Who it is for

Three direct paying segments + one indirect beneficiary.

### Segment A — Бізнес (C&I prosumer)
Industrial / commercial site with own generation (солар), storage and grid connection.
- **Pain:** electricity cost spiked; on-site solar + battery + grid mix is not optimised as one wallet; no in-house team for hourly forecasting and bid optimisation.
- **What GECKO promises:** lower electricity cost. One screen with all generation + load + storage in one грн/h view.

### Segment B — Виробники (independent power producers)
Owner of a 1–20 МВт solar / wind / gas plant (or 2–3 of them).
- **Pain:** зелений тариф is being phased down; missing dispatching analytics; no strategy across РДН + ВДР + БР.
- **What GECKO promises:** higher net income. Accurate own-generation forecast → confident РДН bids → fewer balancing penalties → intraday rebalancing on top.

### Segment C — Власники УЗЕ та гібридних систем (storage / hybrid owners)
Standalone batteries or batteries paired with renewables/gas. 1–20 МВт / 2–40 МВт·год.
- **Pain:** static control settings don't match volatile prices; no access to Допоміжні послуги / БР without dispatching capability; operational income untapped.
- **What GECKO promises:** controllable risk + revenue stacking (arbitrage + capacity + ancillary in one P&L).

### Indirect — Ринок (system operator's view)
The aggregated GECKO portfolio looks to СОП / Укренерго / НКРЕ КП like one large disciplined market participant. The market does not get a UI, but the architecture must support producing predictable, audited submissions on its behalf.

---

## 3. Primary persona for v2

**Single hero persona for v2: Segment B — виробник (independent producer).**

Rationale:
- The deck dedicates the densest pain set to producers.
- The product story (forecast → bid → dispatch → settle) is most legible on a producer's day.
- C&I and УЗЕ owners get **their own dedicated surfaces** (per §10 site map, NQ1-closed), not just dataset variations — research showed this is the universal pattern in mature platforms.

**Tenancy:** mock multi-tenancy via a "customer switcher" in the topbar. Three demo customers (one per segment). No real auth — just a session-level "current customer" with realistic data. Tenant isolation enforced in DB via `tenant_id` even though access control is trivial.

---

## 4. Market context (constraints, non-negotiable)

The product is **Ukrainian-market-native**. Every visible thing must read as Ukrainian.

| Concern | Choice |
|---|---|
| Language | Ukrainian, full UI |
| Currency | грн (UAH) |
| Energy unit | МВт, МВт·год, кВт·год |
| Price unit | грн/МВт·год |
| Time zone | Europe/Kyiv (EET/EEST), 24h format |
| Day-ahead market gate | РДН of СОП "Оператор ринку"; gate ~12:30 D-1 |
| Intraday | ВДР, continuous trading |
| Balancing | БР, settled via Укренерго |
| Bilateral | ДД (Двосторонні договори) |
| Ancillary | Допоміжні послуги (РВЧ, РВЧ-2, резерв) |
| Regulator | НКРЕ КП |
| Counterparty for green-tariff settlement | ДП "Гарантований Покупець" |
| TSO | НЕК "Укренерго" |
| Geography | Ukrainian oblasts (Закарпатська, Київська, Львівська, Дніпропетровська, Одеська, Запорізька) |

Demo dataset uses Ukrainian asset names: "Поляна СЕС", "Кагарлицька ВЕС", "Запорізька ГПУ-1", "Дніпровська УЗЕ", etc. Demo portfolio total ≈ 50 МВт across 8–12 assets in the 1–20 МВт range.

**Data-model invariant:** internal entities speak **ENTSO-E codes** (BZN, MTU, A01–A99 business types) even though synthetic. This makes the schema "real" and post-demo data swaps safer.

---

## 5. Brand identity (visual contract)

**Theme system: LIGHT primary + DARK as accessibility toggle (NQ2-closed). Both first-class, switcher in topbar, persistent per user.**

Rationale (per RF §1 conclusion 5 + user decision): UA professional users have muscle memory for light (OREE, regulator portals, every UA SaaS). EU VPPs default light. The PDF brand colour (dark teal) survives as **accent** on a light ground — green/teal elements pop more on white than they do on dark.

### Light theme (primary)
| Property | Spec |
|---|---|
| Background | `#F8FAFC` (page), `#FFFFFF` (cards) |
| Brand primary (teal) | `#14B8A6` (button), `#0F766E` (heading accent), `#2DD4BF` (highlight) |
| Text | `#0F172A` (body), `#020617` (heading), `#475569` (muted) |
| Border / divider | `#E2E8F0` |
| Status colours | success `#10B981`, warning `#F59E0B`, alert `#F43F5E`, info `#0EA5E9` |
| Chart accent palette | teal `#14B8A6`, deep teal `#0F766E`, sand `#FBBF24`, slate `#64748B`, magenta `#D946EF` for high-contrast highlights |

### Dark theme (accessibility / late-night)
| Property | Spec |
|---|---|
| Background | Gradient `#0E2B2E → #0A1C1F` |
| Card / surface raised | `#114248` |
| Brand primary (teal) | `#2DD4BF` (lighter accent), `#14B8A6` (button), `#0F766E` (deep) |
| Text | `#F1F5F9` (body), `#FFFFFF` (heading) |
| Status colours | same as light |

### Cross-theme
| Property | Spec |
|---|---|
| Logo | Stylised gecko-head silhouette + wordmark "GECKO VPP" |
| Typography | Geometric sans-serif, **Manrope** primary, Montserrat fallback; body regular, headings bold, taglines all-caps spaced |
| Icon style | Filled minimalist, brand teal accent |

**Hex codes are intentions** — final values will be confirmed in Phase 3 by sampling the PNG slides.

---

## 6. The three sub-systems (product decomposition)

Per slide 6 of the client deck, GECKO has three sub-systems. The rebuild's code architecture must reflect this:

| Sub-system | Function | Owns |
|---|---|---|
| **Ринкова інтеграція** | Bids and confirmations to РДН / ВДР / БР; ancillary-service offers; bilateral-contract bookkeeping | All market connectors, settlement, revenue ledger |
| **Комерційна диспетчеризація** | Issues setpoints to physical assets in real time; closes the loop between market commitment and physical execution | Dispatch queue, telemetry ingest, instruction acknowledgement |
| **EMS (Програмна платформа)** | Forecast, optimise, analyse, report | Forecast models, optimiser, KPI engine, report generator, AI analyst |

Internal data flow: **EMS → Диспетчеризація → Ринкова інтеграція**. Reverse signals (market price, regulator notices) flow back into EMS.

---

## 7. Architecture map (from slide 7)

GECKO VPP is a **hub-and-spoke aggregator**. The hub is the platform; the spokes are everyone else. No spoke talks to another spoke directly — every interaction is routed through GECKO.

**Upper half — what GECKO talks to on the contractual / regulatory side:**

| GECKO branch | Counterparty / function | Children |
|---|---|---|
| Допоміжні послуги | Bids & activations for system services | РВЧ, БР |
| Торгівля е/е | Energy trading channels | ДД, РДН, ВДР |
| Регуляторні питання | Compliance, permits, settlement | НКРЕ КП, ДП "Гарантований Покупець", НЕК "Укренерго" |
| Технічна справність | Engineering oversight, ops analytics | Аналітика, телеметрія, ТО |

**Lower half — what GECKO talks to on the physical-energy side:**

| Owner type | Asset cluster inside it |
|---|---|
| Активний споживач (C&I prosumer) | СЕС + УЗЕ + flexible load |
| Виробник (RES producer) | СЕС + УЗЕ |
| Споживач (demand-only) | Flexible load |
| Виробник (mixed producer) | ВЕС + УЗЕ + ГПУ |

This map is the **single most important diagram** in the brief. It must be rendered as an interactive React component on the hero `/` page (NQ6-closed); on hover the connection lines animate, click on a node navigates to the matching surface.

---

## 8. Asset taxonomy

| Code | Full | Class | Cap. range |
|---|---|---|---|
| СЕС | Сонячна електростанція | Variable RES | 1–20 МВт |
| ВЕС | Вітрова електростанція | Variable RES | 1–20 МВт |
| ГПУ | Газопоршнева установка | Dispatchable thermal | 1–20 МВт |
| УЗЕ | Установка зберігання електроенергії | Storage | 1–20 МВт, 2–40 МВт·год |
| Активний споживач | C&I prosumer site | Mixed (gen + load + storage) | 1–10 МВт peak load |
| Споживач | Pure demand site | Flexible load | 1–10 МВт peak load |

---

## 9. Engagement workflow → UI surface map

| Slide-10 stage | UI surface |
|---|---|
| 1. Аналіз активів та цілей | **Out of scope** (pre-sales discovery, manual) |
| 2. Технічна інтеграція та налаштування EMS | **"Налаштування / Onboarding"** — stub with checklist (asset registration, SCADA pairing, forecast model selection, bid strategy template). No real wizard, but the surface exists. |
| 3. Operations: forecast + dispatch + market + analytics | **Daily-use surfaces** (the bulk of the UI — see §10) |
| 4. Клієнт отримує результат у цифрах | **"Результати" / persona-home dashboard** with KPI-first layout — money saved, money earned, imbalances avoided, CO₂ avoided |

---

## 10. Site map (v2 — persona-stratified URLs)

Per NQ1-closed: separate URL surfaces per persona, not a single tree with a toggle. Hero `/` is always the persona picker (NQ6-closed); tenant switcher in chrome lets the user swap tenant without leaving the persona surface.

### `/` — Hero / persona picker
- Slide-7 architecture diagram as the centrepiece interactive component
- Three persona entry cards: "Я виробник" → `/producer/`, "Я бізнес (C&I)" → `/c-i/`, "Я УЗЕ-власник" → `/storage/`
- Smaller links to `/developer/` and `/admin/`
- Tagline + brand block
- Live demo data ticker (faked)

### `/producer/*` — Hero persona surface (виробник, full 9 surfaces)

| # | Path | Ukrainian title | Purpose |
|---|---|---|---|
| 1 | `/producer/` | **Результати** | KPI-first home: грн зекономлено, грн зароблено, небаланси уникнено, CO₂, доступність, рейтинг можливостей |
| 2 | `/producer/aktyvy/` | **Активи** | Owner-grouped asset list (per slide-7 lower half), click → drawer |
| 3 | `/producer/prognozy/` | **Прогнози** | Solar/wind/load/price forecasts, hourly, with MAPE accuracy + **подача прогнозу** stub (NQ4: КЕП fake) |
| 4 | `/producer/dyspetcheryzatsiya/` | **Диспетчеризація** | Setpoint queue + timeline + run-optimisation button |
| 5 | `/producer/rynok/` | **Ринок** | РДН / ВДР / БР prices, spreads, bid history, revenue split |
| 6 | `/producer/uze/` | **УЗЕ** | Storage SOC, charge/discharge windows, cycle accounting, arbitrage P&L |
| 7 | `/producer/spovishchennya/` | **Сповіщення та події** | SCADA + market + regulator events, ack workflow |
| 8 | `/producer/zvity/` | **Звіти** | Daily / weekly / monthly reports — financial, technical, regulatory + **ESG sub-tab** (CO₂ avoided per asset) |
| 9 | `/producer/nalashtuvannya/` | **Налаштування** | Onboarding checklist + integrations catalogue (Mock / Planned / Ready for API) + customer profile + trusted-person invite stub + tenant switcher hint |

### `/c-i/*` — Segment A surface (C&I prosumer)
- Same 9-surface skeleton, C&I-tuned data and labels
- KPI focus shifts: грн зекономлено / навантаження керовано / своя генерація % замість «грн зароблено»
- Scenario cards on home: «Захист від відключення», «Захист від небалансу», «Арбітражна можливість» (Segment-A flavour)
- OBIS-coded tariff zone overlay on consumption charts where dataset has multi-tariff customer
- AI agent: **Енергетичний радник**

### `/storage/*` — Segment C surface (УЗЕ-власник)
- Same 9-surface skeleton, УЗЕ-first variant
- KPI focus: cycles used, capacity-payment revenue, ancillary-service revenue, arbitrage delta
- Battery SoC visualisation primitive (large arc + numeric %) per sonnen pattern
- Scenario cards on home: «Захист від відключення», «Арбітражна можливість», «Допоміжні послуги»
- AI agent: **Тренер по батареях**

### `/developer/*` — Public developer portal (NQ5-closed: visible to everyone, no login)

| Path | Content |
|---|---|
| `/developer/` | Overview + getting-started + key concepts |
| `/developer/api/explorer` | OpenAPI 3.1 spec auto-generated from FastAPI; Swagger/Scalar UI |
| `/developer/sdk-ts/` | TypeScript SDK quickstart, reference, install via npm |
| `/developer/sdk-py/` | Python SDK quickstart, reference, install via PyPI |
| `/developer/webhooks/` | Webhook subscription docs (event types, payload schemas) |
| `/developer/auth/` | Mock API-key flow (synthetic — show the shape, no real provisioning) |

### `/admin/*` — Cross-tenant operator (mock; visible to demo visitors)

| Path | Content |
|---|---|
| `/admin/engage/` | Concerto-style Engage view: aggregated portfolio across all tenants, slide-7 diagram as operator's mental model |
| `/admin/operate/` | Optimize: cross-tenant dispatch queue + system-wide setpoints |
| `/admin/analyze/` | Cross-tenant analytics, market-wide KPI, alerts feed |

### Chrome (top-of-screen on every surface)
- Tenant switcher (3 mock customers)
- Persona switcher (collapsed: shows current persona, click → picker)
- Command palette `Ctrl+K` / `Cmd+K` (Linear-style, navigation + action search) — first-class on `/producer/`, `/c-i/`, `/storage/`, `/admin/`
- Alerts bell
- AI agent launcher (persona-aware: pulls in the agent matching current surface)
- Voice agent push-to-talk button
- Theme toggle (light ↔ dark)
- Current user

---

## 11. Acceptance criteria

A v2 implementation is "done enough to show" iff **every line below is true**. Each criterion is tagged **[MVP]** (must ship) or **[POLISH]** (ship if time allows, defer to v2.5 if not).

### Brand & shell
1. **[MVP] Brand:** Manrope-class font, gecko-head logo, Ukrainian copy throughout. **Both themes fully designed** (light primary + dark accessibility): all surfaces look professional in both, switcher in topbar, theme persists per user (localStorage).
2. **[MVP] Tenancy:** topbar tenant switcher with at least 3 demo customers (one per segment A/B/C), data swaps on selection, no auth.
3. **[MVP] Architecture map:** slide-7 diagram is rendered as a real interactive React component on `/` (welcome / hero) AND optionally embedded on `/admin/engage/`. On hover, connection lines animate; clicking a node navigates to the matching surface.
4. **[MVP] Surfaces:** all 9 surfaces from §10 exist under `/producer/*` and render with synthetic data without errors.
5. **[MVP] Persona surfaces:** `/c-i/*` and `/storage/*` exist as thin variants of the 9 surfaces with persona-tuned data and labels — at minimum: home (Результати), активи, прогнози, ринок, звіти.
6. **[MVP] Cross-tenant operator:** `/admin/engage/`, `/admin/operate/`, `/admin/analyze/` exist as functional pages (even if some sections are summary-tile-only).
7. **[MVP] Command palette:** `Ctrl+K` / `Cmd+K` opens a Linear-style palette on `/producer/*`, `/c-i/*`, `/storage/*`, `/admin/*` — supports navigation + action search.

### Code structure & data
8. **[MVP] Sub-system separation in code:** the codebase has clearly identifiable modules for Ринкова інтеграція, Диспетчеризація, EMS (whether as folders, services, or both — Phase 3 decides).
9. **[MVP] API-first invariant:** no page imports data directly from the synthetic store; everything goes through HTTP endpoints.
10. **[MVP] Storage:** Postgres holds the synthetic dataset. Restarting the app does not regenerate data; seeded once and persists.
11. **[MVP] ENTSO-E codes in data model:** internal entities (bidding zones, market time units, business types) use ENTSO-E codes (BZN, MTU, A01–A99) even though synthetic.
12. **[MVP] Synthetic dataset:** Ukrainian asset names, грн prices, EET timestamps, capacities in the 1–20 МВт range, total portfolio ≈ 50 МВт.
13. **[MVP] Sub-1 hour to swap data:** the synthetic dataset is replaceable by a real customer dataset via SQL inserts / a documented loader, no code changes required.

### Optimiser, agents, dev portal
14. **[MVP] Optimiser:** at least one optimisation scenario returns a real result (recommended actions + revenue uplift + risk flags + confidence) from a service that is not the Next.js process — separate FastAPI endpoint (Hetzner VPS) or clearly isolated function. Math is faked (deterministic perturbation) but service boundary is real.
15. **[MVP] AI text agents — 4 total, persona-aware:** Диспетчерський аналітик + Ринковий аналітик on `/producer/`, Енергетичний радник on `/c-i/`, Тренер по батареях on `/storage/`. Shared underlying engine (one classifier + per-persona system prompts). Each answers ≥3 question families with evidence drawn from the live DB, not hard-coded strings.
16. **[MVP] Voice agent:** ≥1 voice agent accessible from topbar (push-to-talk). OpenAI Realtime / Whisper+TTS / Eleven Labs — Phase 3 chooses. Covers 3–5 базових сценаріїв українською («що сьогодні з виробництвом?», «коли заряджати батарею?», «коли наступний небаланс?», etc.).
17. **[MVP] SDK для розробників:** TypeScript SDK + Python SDK для читання даних через публічний API. Мінімум: client class + 3 приклади. Опубліковано як npm + PyPI (можна scoped namespace; submodule в repo прийнятно).
18. **[MVP] Public dev portal:** `/developer/` exists, is publicly browsable without login, contains OpenAPI explorer + both SDK quickstarts + webhooks docs.

### UA-specific workflows
19. **[MVP] Подача прогнозу:** forecast-submission workflow stub on `/producer/prognozy/` (for production) and `/c-i/prognozy/` (for consumption). Posts a synthetic forecast; UI shows acknowledgement + status. No real submission anywhere.
20. **[MVP] КЕП / Дія.Підпис:** every emitted document (settlement statement, report, contract stub) has a "Підписати через КЕП" button. **Fake / stub** (NQ4-closed) — clicking shows a "підписано ✓" badge with timestamp; no real crypto.
21. **[MVP] Single pane over fragmented UA market:** `/producer/rynok/` and `/admin/analyze/` show РДН + ВДР + БР + ДД settlements in one view — explicit reference to fragmentation in competing UA tools (UEEX).
22. **[MVP] CO₂ avoided KPI:** present on `/producer/`, `/c-i/`, `/storage/` home dashboards. Computed per asset, summed across portfolio.

### Onboarding & quality
23. **[MVP] Onboarding stub:** `/producer/nalashtuvannya/` (and per persona) has a 4-step checklist matching slide-10 stages 1–4 with mock progress.
24. **[MVP] Smoke pass:** every persona surface returns HTTP 200 on live URL; every API endpoint returns well-formed JSON; both themes render correctly on every surface.
25. **[MVP] Production-fidelity feel:** loading under 1.5s on a fresh tab; no obvious "this is a fake" moments (mismatched units, English fallback strings, broken loading spinners, broken theme switches).
26. **[MVP] Research-summary** existed and was agreed (`phase-2-solution/RESEARCH_FINDINGS.md` + `DESIGN_INSPIRATION.md` + `BRIEF_AMENDMENTS.md`) — **closed in v0.4 of this brief**. No further action.

### Polish (defer-OK)
27. **[POLISH] Scenario cards:** on `/c-i/` and `/storage/` home — at least 3 cards each (Захист від відключення, Захист від небалансу, Арбітражна можливість).
28. **[POLISH] OBIS-coded tariff zones:** consumption charts on `/c-i/` and `/producer/` (where dataset has multi-tariff customer) display zonal split (1.8.1 / 1.8.2 / 1.8.3).
29. **[POLISH] Trusted-person invite:** on `/*/nalashtuvannya/` — operator can grant read or read-write to another email within the same tenant. UI only, no real email sent.
30. **[POLISH] Maintenance/deregistration declaration:** producer can declare planned downtime on `/producer/aktyvy/[id]/`; affects forecast and revenue projections.
31. **[POLISH] ESG / carbon-credit sub-tab:** on `/producer/zvity/` — CO₂ avoided per asset, scope-2 totals, carbon-credit potential.

---

## 12. Out of scope (v2 will NOT do these)

- Real SCADA / OPC-UA / Modbus / MQTT bridge.
- Real market connector to СОП / Укренерго.
- Real auth, SSO, RBAC.
- Real LLM (analyst stays a keyword classifier over the DB; LLM-shaped UX, deterministic backing).
- Real MILP / convex solver (optimiser perturbs deterministic baselines; phrasing is realistic, math is faked).
- Real КЕП / Дія.Підпис crypto (fake badge only — NQ4-closed).
- Multi-language UI (Ukrainian only; no English / Russian toggle).
- **Mobile-native build** (PWA-only — NQ3-closed; native iOS/Android moved to **v3 roadmap mention**).
- Blockchain settlement / token incentives (**never** for this product line).
- Billing / settlement automation (`/zvity` shows reports; no invoices generated).
- Background workers / cron / queue (data is static at runtime; "live telemetry" is faked client-side).
- Production-grade observability (Sentry / tracing / RUM stays out of v2).

---

## 13. Risks and assumptions

| Risk | Why it matters | Mitigation in this brief |
|---|---|---|
| Synthetic data fails the Ukrainian-energy-expert sniff test | A real reviewer dismisses the demo as fake | §4 + §11.12 anchor every visible number to a real Ukrainian-market shape; portfolio scale matches deck's 1–20 МВт range |
| Persona-split ambition explodes scope (3 full dashboards) | Building three full surfaces is 3× the work | §10 makes `/producer/*` the full implementation; `/c-i/*` and `/storage/*` are **thin variants** of the same 9-surface skeleton — same components, persona-tuned data |
| Slide-7 architecture diagram is not just text — clients ask "show me where it lives in the product" | If we don't render this diagram, the brief's most-important visual goes missing | §11.3 makes interactive rendering an acceptance criterion |
| Sub-system separation might be cosmetic ("three folders, same monolith") | Defeats the "real backend" framing | Phase 3 decides whether sub-systems are folders, services, or both; §11.8 + §11.14 require visible separation + optimiser outside Next.js process |
| Both themes designed = 2× design work | Light + dark fully designed is a real cost | Use a single design token system (CSS variables) so each component is written once; theme toggles tokens, not components — Phase 3 specifies the token contract |
| Vercel + Next 16 hidden bugs (`@vercel/analytics` modifyConfig already bit us) | Could derail deployment a second time | Memory [[vercel-analytics-next16-bug]] captures the fix; Phase 3 deployment topology must account for this |
| Tenant data isolation in the demo is a security fiction | A demo with three "customers" and no auth still must not leak data between switcher selections (credibility) | Mock tenancy via separate datasets in Postgres with `tenant_id` partitioning, even though access control is trivial |
| Public dev portal exposing OpenAPI invites prompt-injection attacks against the AI agents | A visible API may attract probing | Agents use deterministic classifier, not LLM, so no prompt-injection surface; rate-limit per IP at the Hetzner side; this risk is small but logged |
| 4 AI agents instead of 2 increases prompt-engineering surface | Quality could degrade across agents | One shared engine + per-persona system prompts (per A.4 RF). Agents share the same retrieval, only the persona "voice" varies. |
| Light theme as primary contradicts brand-PDF dark | Brand recognition risk | Light theme uses the same teal accents; dark theme remains shipped, switcher visible. Both themes look on-brand. (User decision, NQ2-closed.) |

**Assumptions baked in (worth flagging explicitly):**

- The product targets the Ukrainian market in 2025–2026 conditions (post-РДН-launch, active green-tariff regime under wind-down, martial-law-era reliability events present in the dataset where appropriate).
- The customer (the person Andrii is selling to / showing the demo to) is comfortable in Ukrainian and energy-domain literate.
- "Production-fidelity" means: a Ukrainian energy person could be shown this demo for 5 minutes and not be sure on first glance whether the data is real or synthetic. They must be told.
- The rebuild reuses no code from gecko-vpp v1 except where reuse is faster than rewrite (charts, portal pattern, type structure). v1 deploy (`vpp.radai-1984.dev`) stays live during rebuild as the "before" reference; the rebuild gets a new URL or replaces it after acceptance.

---

## 14. Open questions log

Per Constitution P16: each question remains open until answered or explicitly dismissed.

**Closed in v0.2 / v0.3 (2026-05-23):** Q1, Q2, Q3, Q5, Q8, Q9, Q10. Dismissed: Q7. (See version history.)

**Closed in v0.4 (2026-05-23):**

- **NQ1 ✅** Site map architecture — **separate URL surfaces per persona** (`/producer/`, `/c-i/`, `/storage/`, `/developer/`, `/admin/`). `/c-i/` and `/storage/` are thin variants of the 9-surface skeleton.
- **NQ2 ✅** Theme — **LIGHT primary + DARK as accessibility toggle**, both first-class, switcher in topbar, persists per user. (User decision: light is UA-pro muscle memory; teal/green accents from client PDF survive on white as accents.)
- **NQ3 ✅** Mobile — **PWA-only**; native iOS/Android moved to v3 roadmap mention.
- **NQ4 ✅** КЕП / Дія.Підпис — **stub / fake badge**, no real crypto in v2.
- **NQ5 ✅** Public dev portal — **visible to everyone, no login**; this IS one of the differentiators, must be browsable by anyone landing on the demo.
- **NQ6 ✅** Hero `/` page — **always show persona picker** with slide-7 diagram as the centrepiece; tenant switcher available in chrome on persona surfaces.

**No open questions remain.**

---

## 15. Next phases

- **Phase 2 — Solution: CLOSED.** Research synthesised in `phase-2-solution/RESEARCH_FINDINGS.md` v0.1, design references in `DESIGN_INSPIRATION.md`, all amendments accepted in `BRIEF_AMENDMENTS.md`, brief updated to v0.4.

- **Phase 3 — Architecture** (`phase-3-architecture/ARCHITECTURE.md`):
  - Components + contracts at the seams (API ↔ frontend ↔ SDK ↔ AI agents)
  - Data model (Postgres schema with `tenant_id` partitioning, ENTSO-E codes, time-series partitioning if relevant)
  - Design-token system specification (so light + dark are one component, two skins)
  - FMEA (what fails, how, how detected, how recovered)
  - Phased implementation plan with input / output / acceptance per phase
  - Synthetic-dataset shape specification (how many assets per segment, what hours of data, what events injected)
  - Security boundaries (even with mock auth — what is the credible isolation story)
  - Tests strategy (what is smoke, what is real, what is faked)
  - Deployment topology (Vercel + Hetzner FastAPI + Postgres + DNS)

  **Phase 3 cannot start autonomously.** It requires synchronous review with the user — Phase 3 is where end-product vision is locked, and that decision is not delegated.

- **Phase 4 — Implementation:** only after Phase 3 is approved.

- **Phase 5 — Verification:** smoke tests, acceptance walk-through, demo-mode validation.

- **Phase 6 — Operation:** deploy to `gecko-vpp.radai-1984.dev` (or chosen subdomain in Phase 3); v1 stays at `vpp.radai-1984.dev` until v2 is accepted.

---

## Version history

- **v0.4 — 2026-05-23** — Phase 2 research closed. All 6 mandatory amendments (A.1–A.6) and all 6 optional amendments (B.1–B.6) from `BRIEF_AMENDMENTS.md` incorporated. NQ1–NQ6 closed by user. Major changes: persona-stratified URL site map (NQ1, A.1); light theme as primary + dark as accessibility toggle (NQ2, A.2 reversed from initial recommendation per user); public `/developer/` portal as first-class surface (NQ5, A.3); 4 AI agents instead of 2 (A.4); UA-specific workflows added as acceptance criteria 19–22 (A.5); 6 polish criteria 27–31 (B.1–B.6); mobile moved to PWA-only with v3-roadmap-mention (NQ3); КЕП as stub (NQ4); hero `/` as persona picker with slide-7 diagram (NQ6, A.6). Brief frozen. Awaits user before Phase 3 (Architecture) is opened.
- **v0.3 — 2026-05-23** — Q7 dismissed by user (slide-4 content irrelevant). No open questions remained. Brief frozen for Phase 2 research authorisation.
- **v0.2 — 2026-05-23** — user closed Q1, Q2, Q3, Q5, Q8, Q9, Q10. Added acceptance criteria 15–18: SDK (TS + Python), 2 text AI agents, 1 voice agent, research-summary as Phase 3 gate.
- **v0.1 — 2026-05-23** — initial draft generated from `_raw_extraction.md` + `_analysis.md`. Awaiting user confirmation. Open questions Q1, Q2, Q3, Q5, Q7, Q8, Q9, Q10.
