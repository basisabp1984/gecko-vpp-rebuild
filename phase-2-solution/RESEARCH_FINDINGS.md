# RESEARCH_FINDINGS — Phase 2.0 / Visual & UX research consolidation

**Status:** Synthesis draft v0.1 · awaits user approval before Phase 3 starts
**Parent:** `RESEARCH_PLAN.md` v0.1 (executed 2026-05-23)
**Inputs:** `findings_tier1_ua.md`, `findings_tier2_pl.md`, `findings_tier3_eu.md`
**Total platforms analysed:** 22 (8 UA + 8 PL/CEE + 6 EU + 1 adjacent / 1 reachability failure)

This document answers the central research question from `RESEARCH_PLAN.md` §1:

> **How is the frontend of modern VPP / EMS / energy-trading SaaS platforms actually constructed?**

It does **not** decide GECKO VPP's architecture (Phase 3's job), but it constrains the architecture by enumerating the patterns that any serious platform in this space exhibits.

---

## 1. Headline conclusions (the 5 things that matter)

1. **Ukrainian market has no public reference UI of this product class.** Of 8 Ukrainian platforms inspected, zero expose a verifiable VPP / aggregator operator dashboard publicly. The "aggregator" institute itself is still in NKREKP consultation. **GECKO VPP enters as a category-creator in Ukraine**, with no incumbent to imitate and no incumbent to outperform on UI alone.

2. **The canonical mature shape is a three-persona split into separate apps.** gridX (Admin / Homeowner / Installer), Next Kraftwerke (NEMOCS / NEXTRA / Mein Kraftwerk), Enspirion (aggregator + ENIRA dispatcher). One company, one login, multiple URL surfaces. Menu-hiding is the weak version; separate apps is the strong version. **This is the strongest single structural lesson.**

3. **AI agents and voice are completely absent.** Zero of 22 platforms surveyed have a visible LLM-grade text assistant or any voice agent. Forecasting and optimisation run algorithmically under the hood, never surfaced as conversational UI. **This is GECKO's biggest open differentiation lane.**

4. **Public APIs and SDKs are also nearly absent.** Only gridX advertises an "Energy API" — the dev portal itself is behind partner login. No surveyed platform publishes a documented public TypeScript or Python SDK. **A second open differentiation lane.**

5. **Theme conflict resolved.** EU VPPs default light (NEMOCS, gridX, sonnen). UA energy professionals work in light-themed regulator and exchange portals all day. But the **client's own brand PDF is dark teal**, and productivity SaaS gold-standards (Linear, Vercel) are dark. **Resolution: dark teal-gecko as primary identity (matches client brand), light theme as an accessibility toggle (matches UA professional muscle memory and OREE's accessibility pattern).** Both shipped from day one.

---

## 2. The canonical shape of a serious VPP / EMS frontend

Every Tier-3 platform we surveyed has these structural elements. Any GECKO Phase-3 architecture that omits one of them is provably below the floor:

### 2.1 Information architecture

- **Operator home = fleet overview table.** Sortable, filterable list of assets with status tiles. gridX is the canonical reference. (See `inspiration_001` and `inspiration_002` in `DESIGN_INSPIRATION.md`.)
- **Drill-down to system details.** Click an asset row → full asset page with telemetry, charts, controls. Page navigation, not modal. (gridX `inspiration_004`.)
- **Schedule / dispatch view tied to market signals.** A separate page showing the next-N-hours plan against market prices. NEMOCS shows control-reserve provision; KrakenFlex shows dispatch-against-imbalance (claimed). (NEMOCS `inspiration_010`.)
- **Historical time-series with daily-to-yearly navigation.** Same chart, multiple time windows. Every consumer-facing platform has this; every operator platform has a denser version.
- **Alerts dashboard prominent.** Either as a dedicated page or as a top-of-home panel. Tesla Powerhub frames the operator UI as alert-first. Concerto Analyze module is alert-centric.
- **Settings + Integrations + Account chrome.** Universal.

### 2.2 Persona split

Every mature platform has **at least two** distinct UI surfaces:

| Platform | Persona surfaces |
|---|---|
| gridX | Admin (XENON) · Homeowner · Installer Hub |
| Next Kraftwerke | NEMOCS (utility/aggregator) · NEXTRA (trader) · Mein Kraftwerk (producer) |
| sonnen | Customer App · Dash 2.0 · Partner Portal |
| Enspirion | Aggregator portal · ENIRA dispatcher |
| Generac Concerto | Engage · Optimize · Analyze (modules, not separate apps) |

**For GECKO this means:** the three customer segments from the client PDF (C&I prosumer / RES producer / УЗЕ owner) are not just dataset variations of one screen — they are **three distinct app surfaces** under one login.

### 2.3 Visualisation

- **Animated energy-flow diagram** with icons + flowing dots + live wattage — table-stakes on the consumer/prosumer side. (gridX `inspiration_005`, sonnen `inspiration_013`.)
- **Time-series line / area charts** with comparison overlays (your-history vs. statistical average) — Polish DSO standard.
- **Asset status tiles** for the fleet view.
- **KPI strip on home** + drill-into-tab pattern.
- **OBIS-coded tariff zones** (1.8.1 / 1.8.2 / 1.8.3) directly exposed in consumption UI — Polish/CEE-specific data model that bleeds into Ukraine too.

### 2.4 Interaction

- **Page navigation for drill-down** (default in gridX, Next Kraftwerke).
- **Form modals for actions** (maintenance declaration, goal setting, downtime registration).
- **Push notifications** to mobile app for fault/threshold breaches.

### 2.5 Theme conventions

- **Light is the EU energy-sector default.** Visible across NEMOCS, gridX, sonnen, every Polish DSO portal, every UA regulator portal.
- **Dark is the productivity-SaaS / power-user default.** Linear, Vercel, Datadog. Tesla Powerhub is rumoured dark (not pixel-verified).
- **Brand accent colours observed:** green (Next Kraftwerke ~#94C11F, sonnen mint, PGE corporate green, several Polish renewables-orgs), orange (gridX, Generac ~#F37021, TAURON ~#F39200, ČEZ), navy/teal (Enspirion, our client's PDF), purple-pink-teal (Octopus consumer).

### 2.6 What is universally absent

The list of "what NO platform we surveyed has" is the GECKO opportunity surface:

- ❌ Visible AI text assistant
- ❌ Any voice agent
- ❌ Public documented developer SDK (TS / Python)
- ❌ Cmd+K command palette in operator UI
- ❌ React Portal drawers for fast drill-down without page nav
- ❌ Dark-default theme in EU VPP segment
- ❌ Ukrainian-language UI at EU-grade IA quality

GECKO ships these, and the product reads as **demonstrably ahead** of the surveyed field.

---

## 3. Patterns we will adopt (with sources)

For each, the source platform is cited so Phase 3 architects can pull the reference screenshot if they need to.

| # | Pattern | Source | Use in GECKO |
|---|---|---|---|
| A1 | Three separate persona apps under one login | gridX, Next Kraftwerke | C&I / Producer / Storage = three URL surfaces (`/c-i/...`, `/producer/...`, `/storage/...`) sharing one Postgres + auth |
| A2 | Operator home = fleet table with status tiles | gridX | `/aktyvy` (producer view) shows portfolio as table with status badges |
| A3 | Page-nav drill-down to system details | gridX | Click asset row → dedicated asset page (NOT a drawer); drawers reserved for fast peek |
| A4 | Animated energy-flow diagram | gridX, sonnen | Consumer / prosumer dashboards have a real-time animated SVG flow |
| A5 | Historical chart with day/week/month/year toggle | gridX, sonnen, every Polish DSO | Standard on every time-series page |
| A6 | Comparison overlays ("you vs. average") | TAURON eLicznik | Optional toggle on consumption / production charts |
| A7 | Scenario cards (Storm/Emergency Mode) | sonnen | Adapt for UA scenarios: "Blackout mode", "Curtailment defence", "Imbalance hedge" |
| A8 | Three-module IA: Onboard / Operate / Analyze | Generac Concerto | Top-level mental model used to organise our 9 surfaces into groups |
| A9 | Regulatory-mode toggle as first-class UI primitive | gridX §14a EnWG / §9 EEG | UA equivalent: НКРЕКП compliance toggles + "Гарантований Покупець" mode for green-tariff producers |
| A10 | Alerts surface near top of operator UI | Tesla Powerhub, Concerto | "Сповіщення" (alerts) page sits as a peer of the dashboard, not buried in a corner |
| A11 | Multi-site/multi-property switcher in chrome | sonnen "Your locations" | Tenant switcher in topbar (already in `PRODUCT_BRIEF` §3) |
| A12 | Push-notification mobile-native app | Polish DSOs uniformly | Roadmap line for v3; v2 ships PWA-grade mobile |
| A13 | Light-theme accessibility toggle | OREE, accessibility law | Dark default + Light toggle, both first-class — see §1.5 |
| A14 | Hourly granularity as canonical time-step | UA Energy Map | Default chart resolution = 1 hour |
| A15 | OBIS-coded tariff zones in consumption UI | TAURON eLicznik | Show 1.8.1 / 1.8.2 / 1.8.3 breakdowns where relevant |
| A16 | Forecast-submission workflow | UA YASNO Business, ДП Гарантований Покупець | Mandatory UA workflow — first-class page, not buried |
| A17 | ENTSO-E codes in data model | UA Ukrenergo Datahub | Internal data model speaks ENTSO-E (BZN, MTU, A01-A99) |
| A18 | PPE / connection-point selector | Polish DSOs | Drill into a single metering point within a customer org |
| A19 | Trusted-person invite | PGE eBOK | "Запросити колегу" feature in `/nalashtuvannya` |
| A20 | Bilingual UA/EN parity | Energy Map, OREE | Language toggle in header, both fully translated |
| A21 | KEP / Дія.Підпис document signing | YASNO Business, every UA enterprise tool | Documents emitted by `/zvity` carry e-sign action |
| A22 | Maintenance/deregistration declaration ("Abmeldefunktion") | Next Kraftwerke Mein Kraftwerk | Producer can declare planned downtime, ties to expected-revenue calc |
| A23 | ESG / carbon-credit reporting bundled | Reo.pl, Restart Energy | `/zvity` includes a CO₂ / ESG sub-tab |
| A24 | Commissioning wizard | gridX Installer Hub | `/nalashtuvannya/onboarding` has 4-step wizard per slide-10 of client PDF |

---

## 4. Patterns we explicitly REJECT (with reasons)

| # | Pattern | Where seen | Why we skip |
|---|---|---|---|
| R1 | Light-only theme | Most EU VPPs | Misses our client's dark-teal brand; the productivity-SaaS goldstandard is dark; we instead ship dark default + light toggle |
| R2 | Menu-hiding as persona switching | Next Kraftwerke NEMOCS suggests it | Weak form; we go full gridX-style separate apps |
| R3 | Marketing illustrations standing in for real UI | Generac Concerto | Always ship a real screenshot when marketing the product |
| R4 | Gated / partner-only API docs | gridX | Public dev portal from day one (free key, rate-limited) |
| R5 | SAP NetWeaver Portal-era architecture | ČEZ DIP | Reference for what to NOT look like |
| R6 | Inventing English-language acronyms for UA market | Risk in any imported design | Speak the regulator's vocabulary verbatim (РДН/ВДР/БР/ГП/ОСП/ОСР) |
| R7 | Single-screen "operator console" for all three segments | Our v1's mistake | Three separate URL surfaces per A1 |
| R8 | Blockchain settlement primitives | Restart Energy | Out of scope for v2; can be a future module |
| R9 | Hardware-mediated integration as the only path | Next Kraftwerke's Next Box | We support both gateway and pure API integrations |
| R10 | Aggregating buildings instead of assets as primary unit | VPPlant | Our taxonomy is asset-first (per client PDF slide 7) |

---

## 5. Differentiators (features no surveyed platform has, where GECKO leads)

These are listed in PRODUCT_BRIEF §11.15-18 already; research **confirms** these are genuine market gaps, not vanity features.

| # | Differentiator | Confidence in gap |
|---|---|---|
| D1 | Dark-default + light-toggle theme system | Very high — no EU VPP surveyed defaults dark |
| D2 | Ukrainian-language operator UI at EU-grade IA quality | Very high — no UA platform has both UI density and language quality |
| D3 | Visible AI text agents per persona (operator / installer / owner) | Very high — zero hits across 22 platforms |
| D4 | Voice agent for hands-free operator monitoring | Very high — zero hits |
| D5 | Public TypeScript + Python SDK with dev portal | Very high — only gridX claims an Energy API and it's gated |
| D6 | Cmd+K command palette in operator UI | Very high — zero hits in energy segment; Linear is the only adjacent reference |
| D7 | React Portal drawers / overlays for fast peek without nav | High — gridX uses page-nav-only drill-downs; sonnen uses scenario-card modals; no platform mixes both |
| D8 | Bilingual UA/EN parity from day one | Medium — Energy Map and OREE already do this in UA segment, so it's a UA-baseline differentiator |
| D9 | Single pane over multiple UA market apps (РДН + ВДР + БР + ДП settlements) | Very high — UEEX fragments these into separate logins; no UA platform unifies |

---

## 6. Information-architecture decisions for v2 (informed by §3, §4)

Based on research, the v2 site map should be:

```
gecko.radai-1984.dev (v2 root — replaces vpp.radai-1984.dev once accepted)
├── /                          [Welcome / persona picker — slide-11 hero]
├── /producer/                 [HERO persona — Segment B = виробник]
│   ├── (home)                 Results-first KPI dashboard (slide-10 stage 4)
│   ├── aktyvy/                Fleet table, click → detail page
│   ├── aktyvy/[id]/           Asset detail page (NOT drawer)
│   ├── prognozy/              Forecast submission + accuracy review
│   ├── prognozy/forecast/     Forecast-submission workflow (UA-specific)
│   ├── dyspetcheryzatsiya/    Setpoint queue + timeline + run optimization
│   ├── rynok/                 РДН / ВДР / БР aggregate view
│   ├── rynok/auctions/        Drill into single auction window
│   ├── uze/                   Battery-specific (relevant if hybrid producer)
│   ├── spovishchennya/        Alerts + acknowledgement workflow
│   ├── zvity/                 Daily / weekly / monthly + ESG sub-tab
│   └── nalashtuvannya/        4-step onboarding stub + integrations + KEP
├── /c-i/                      [Segment A surface — different chrome]
│   └── (similar structure tuned for prosumer with on-site gen + load)
├── /storage/                  [Segment C surface — storage-first]
│   └── (similar, with UZE / SOC / arbitrage as the hero)
├── /developer/                [Public dev portal — differentiator D5]
│   ├── api/                   OpenAPI / Swagger UI
│   ├── sdk-ts/                TypeScript SDK docs
│   ├── sdk-py/                Python SDK docs
│   └── webhooks/              Event stream subscription
└── /admin/                    [Internal operator — Generac-style Engage/Operate/Analyze]
    ├── engage/                Tenant management + onboarding admin
    ├── operate/               Cross-tenant ops view
    └── analyze/               Cross-tenant analytics
```

This expands the 9-surface flat list from `PRODUCT_BRIEF` §10 into a **role-stratified** hierarchy. The 9 surfaces still exist — they're nested under `/producer/` for the hero persona; `/c-i/` and `/storage/` reuse the same 9-surface skeleton with adjusted data and renamed labels.

---

## 7. Theme & design system decisions (informed by §3, §4)

Resolved here for Phase 3 to inherit:

| Property | Decision | Source |
|---|---|---|
| Primary theme | Dark teal-gecko (per client PDF) | Client brand |
| Secondary theme | Light teal-gecko (accessibility toggle) | OREE accessibility, UA professional muscle memory |
| Background dark | Gradient `#0E2B2E → #0A1C1F` | Client PDF |
| Background light | `#F8FAFC` neutral, `#FFFFFF` cards | UA regulator portals |
| Brand primary (teal) | `#2DD4BF` (lighter accent), `#14B8A6` (button), `#0F766E` (deep) | Client PDF (estimated; final pixel-pick TBD) |
| Status colours | success `#10B981`, warning `#F59E0B`, alert `#F43F5E`, info `#0EA5E9` | Standard |
| Typography primary | Manrope (geometric sans, matches client PDF) | Client PDF + EU VPP norm |
| Typography mono | JetBrains Mono | Standard |
| Density | Comfortable on consumer; compact on operator | gridX |
| Iconography | Filled minimalist (Lucide-style) | Standard, matches client PDF energy icons |

**Theme switcher placement:** topbar, right of search, before language toggle. Keyboard shortcut: `Shift+T`.

**Language switcher placement:** topbar, right of theme. Keyboard shortcut: `Shift+L`.

---

## 8. AI / voice agent strategy (informed by §5 differentiators)

Confirmed scope from `PRODUCT_BRIEF` §11.16-17 — research validates the gap.

**Text agents (minimum 2 per persona):**

| Persona | Agent name | Purpose |
|---|---|---|
| Producer | Диспетчерський аналітик | Already existed in v1; reuse and rewrite for UA + Producer dataset |
| Producer | Ринковий аналітик | New — answers "what's the best arbitrage window today?" |
| C&I | Енергетичний радник | New — answers "should I run the dryer at 14:00 or 21:00?" |
| УЗЕ | Тренер по батареях | New — answers "is today a good day for deep discharge?" |

**Voice agent (1, mandatory):**

- Push-to-talk button in operator chrome (next to AI launcher).
- 3-5 базових сценаріїв українською:
  - "Що сьогодні з виробництвом?"
  - "Коли заряджати батарею?"
  - "Коли наступний небаланс?"
  - "Покажи стан активів"
  - "Сформуй звіт за сьогодні"
- Implementation choice (Phase 3 decides): OpenAI Realtime API vs Whisper+TTS+chat vs ElevenLabs.

**Why this matters per research:** zero surveyed platforms have either, and the voice agent specifically maps to a real operator use-case (hands-free monitoring while doing physical tasks like checking SCADA hardware on site).

---

## 9. SDK strategy (informed by §5 differentiator D5)

Confirmed scope from `PRODUCT_BRIEF` §11.15.

**TypeScript SDK** (`@gecko-vpp/sdk` on npm):
- Client class with typed methods for all public endpoints.
- 3 usage examples (read portfolio, subscribe to alerts, submit forecast).
- Lives in `gecko-vpp/packages/sdk-ts/` of the monorepo (or separate repo — Phase 3 decides).

**Python SDK** (`gecko-vpp` on PyPI):
- Equivalent surface to TS SDK.
- Async-first (httpx).
- 3 usage examples.

**Public dev portal at `/developer/`:**
- OpenAPI 3.1 spec served from the FastAPI backend (auto-generated).
- Swagger UI at `/developer/api/explorer`.
- SDK quickstarts at `/developer/sdk-{ts,py}/`.
- Webhook subscriptions at `/developer/webhooks/`.

**Why this matters per research:** only gridX has an API and it's gated. A free + documented + multi-language SDK is a genuine category-defining move.

---

## 10. What we drop / defer vs PRODUCT_BRIEF v0.3

After research, nothing in v0.3 needs to be dropped. A handful of items move from "v2 ship" to "v3 / future":

- Mobile-native iOS/Android client (every Polish DSO has one; we ship PWA in v2, native in v3).
- Дія.Підпис KEP integration (UA enterprise expectation, but real integration needs a Diia API key and customer-org acquisition — v2 ships **stub** that shows where it would live).
- Blockchain settlement (Restart Energy pattern — out of scope).
- HVAC / building-level aggregation (VPPlant pattern — out of scope for v2; reconsider for v3 if C&I segment grows).

---

## 11. Open questions raised by research (need user confirmation before Phase 3 freezes)

These are NEW open questions surfaced by the research findings; the previous `PRODUCT_BRIEF` v0.3 open-questions log is fully closed.

- **NQ1.** Three persona apps as **separate URL surfaces** (`/c-i/`, `/producer/`, `/storage/`) vs. **persona-mode toggle** on one URL? Research strongly suggests separate surfaces (gridX pattern). Recommend: separate URL surfaces. Confirms?
- **NQ2.** Dark default + light toggle, both first-class — confirmed?
- **NQ3.** Mobile experience for v2: PWA-only or PWA + roadmap-mention-of-native? Recommend PWA-only + roadmap mention. Confirms?
- **NQ4.** Дія.Підпис KEP: real integration in v2 or stub-with-placeholder-button? Recommend stub. Confirms?
- **NQ5.** Public dev portal at `/developer/` — does the user want this visible to demo visitors, or hidden behind `gecko.radai-1984.dev/developer/` requiring a flag? Recommend visible — it IS the differentiator. Confirms?
- **NQ6.** Hero "welcome / persona-picker" page at `/` — does it pre-route based on a chosen tenant, or always show the picker? Recommend tenant-switcher in chrome + always-accessible picker at `/`. Confirms?

---

## 12. Acceptance against `RESEARCH_PLAN.md` §5 success criteria

| Criterion | Status |
|---|---|
| §5.1 ≥8 platforms with template filled | ✅ — 22 platforms covered across 3 tiers |
| §5.2 IA patterns summarised (common + variations) | ✅ — §2.1 + §2.5 |
| §5.3 Visualisation patterns summarised per chart kind | ✅ — §2.3 + §3 table |
| §5.4 Interaction patterns summarised, portal positioning identified | ✅ — §2.4 + §5 D7 |
| §5.5 ≥15 screenshot URLs in DESIGN_INSPIRATION | ✅ — see `DESIGN_INSPIRATION.md` |
| §5.6 Explicit gap list | ✅ — §2.6 + §5 |
| §5.7 BRIEF_AMENDMENTS.md exists | ✅ — see `BRIEF_AMENDMENTS.md` |
| §5.8 User approval | ⏳ — awaiting |

Phase 3 starts the moment §5.8 closes.

---

## Version history

- **v0.1 — 2026-05-23** — initial synthesis from three subagent reports. Awaits user approval. 6 new open questions in §11.
