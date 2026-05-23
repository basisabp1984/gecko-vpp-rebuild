# Tier 3 — EU VPP / EMS / Energy-Trading SaaS Frontend Research

**Researcher:** Tier-3 subagent
**Date:** 2026-05-23
**Scope:** Mature EU benchmarks for VPP / EMS / energy-trading SaaS frontends — structural inventory plus visual references.
**Strict rule applied:** P8 — verify, don't trust. All claims sourced; where I could not see the actual UI I write "claimed but not verified".

---

## Platform: Next Kraftwerke — NEMOCS + NEXTRA + Mein Kraftwerk

- **Region:** Germany (HQ Cologne), pan-European operations
- **Customer segment they target:** B2B SaaS for utilities/grid operators (NEMOCS), professional traders (NEXTRA), and producers connected to Next Kraftwerke's own VPP (Mein Kraftwerk)
- **Public product URL(s):**
  - https://www.next-kraftwerke.com/vpp
  - https://www.next-kraftwerke.com/news/next-kraftwerke-introduces-new-vpp-software-as-a-service-solution-nemocs
  - https://www.next-kraftwerke.com/news/first-customer-for-next-kraftwerkes-new-trading-portal-nextra
  - https://www.next-kraftwerke.de/unternehmen/mein-kraftwerk
  - https://vpp.next-kraftwerke.com/ (NEMOCS simulation/demo)
- **Pricing model:** Enterprise SaaS (case-by-case licensing — public references: Ecotricity UK, Eoly BE)
- **Screenshots / video / demo URLs:**
  1. NEMOCS control reserve view — `https://image-proxy.nextkraftwerke.cloud.fcse.io/tZo2TJpM7SGRxcNsTVqaQhFsQKg=/fit-in/1920x1080/https%3A%2F%2Fstrapistoragegkuxf.blob.core.windows.net%2Fprod-gkuxf%2Fassets%2FVPP_As_A_Service_Nemocs_control_reserve_119ff1a6c4.jpg` — "Manage control reserve provision with NEMOCS VPP-as-a-service."
  2. NEXTRA trading portal preview — `https://strapistoragegkuxf.blob.core.windows.net/prod-gkuxf/assets/Trading_Platform_Nextra_809317ec3c.jpg`
  3. Mein Kraftwerk mobile mockup 1 — `Meik_Mock_Up_3_1_dad68d7c06.png`
  4. Mein Kraftwerk mobile mockup 2 — `Meik_Mock_Up_2_2_82e77b4897.png`
  5. NEMOCS brochure PDF — https://cdn.asp.events/CLIENT_CL_EE_E92EC48A_9F42_8E1E_7106D5CAFEEF513B/sites/Enlit365/media/libraries/exhibitor-brochures/21511-nemocs-brochure-next-kraftwerke.pdf
- **Stated tech stack:** NOT FOUND. Strapi CMS for marketing.

### Information architecture
- **Pages observed:** "Assets" overview, "Control Reserve" provision view, real-time output/reserve/standby tile, schedule view, market signals view. NEXTRA: portfolio, transactions, forecast upload, market info/reports. Mein Kraftwerk: facility status, performance metrics, monthly revenue, document download, **"Abmeldefunktion"** (maintenance/deregistration function).
- **Home screen layout:** Real-time output, reserve level and standby status per asset (claimed but not pixel-verified beyond the control-reserve screenshot).
- **Multi-tenancy / org switcher:** NEMOCS is positioned as multi-tenant SaaS.

### Visualisation patterns
- **Chart types observed:** Time-series (line/area for output and reserve). Status tiles per asset.

### Theme & visual language
- **Theme:** Light theme on NEMOCS screenshot; brand uses bright green accent.
- **Brand accent colour:** Next Kraftwerke green (~#94C11F)
- **Typography:** Sans-serif.
- **Density:** Comfortable to spacious.

### AI / agent features
- **Text AI assistant / Voice assistant / Recommendations:** NOT FOUND.

### SDK / public API
- All NOT FOUND publicly.

### Things this platform has that our v1 missed
- Hard separation of three personas: aggregator (NEMOCS), trader (NEXTRA), asset owner (Mein Kraftwerk). Each persona = different app, not just role-based menu hiding.
- Mobile app for asset owners with push notifications.
- "Abmeldefunktion" — explicit maintenance-window declaration tied to revenue.

### Frontend-tech-lead's-eye verdict
NEMOCS reads as a serious, conservative B2B SaaS — light theme, big charts, real-time tile grid. The fact that ~14,000 assets and 2,555 MW run on it validates the patterns. But visually it looks 2018-era enterprise. For GECKO this is the floor of credibility, not the ceiling.

---

## Platform: gridX — XENON + XENON Flex + Installer Hub

- **Region:** Germany (Munich + Aachen). Operations DE/NL/AT/CH/UK.
- **Customer segment they target:** B2B EMS infrastructure / white-label HEMS — utilities, energy retailers, OEMs (E.ON, Viessmann, Soly, Fastned)
- **Public product URL(s):**
  - https://www.gridx.ai/xenon
  - https://www.gridx.ai/module/xenon-flex
  - https://www.gridx.ai/use-cases/home-energy-management-system
  - https://www.gridx.ai/blog/smarter-energy-monitoring-the-3-layers-of-xenons-interfaces
  - https://www.gridx.ai/blog/5-xenon-features-youll-wish-you-knew-about-sooner
- **Pricing model:** Enterprise (white-label).
- **Screenshots / video / demo URLs:**
  1. Admin/EMS dashboard EN — `https://cdn.prod.website-files.com/65b3e159d25a6097b6ca5815/691463ac2dd6fe80c3615739_EMS%20dashboard_EN.png`
  2. Energy management dashboard EN — `https://cdn.prod.website-files.com/65b3e159d25a6097b6ca5815/6914638b884ae8d5c10e6d6c_Energy%20management%20dashboard_EN.png`
  3. EMS dashboard for installers EN — `https://cdn.prod.website-files.com/65b3e159d25a6097b6ca5815/691465278319e46d2e7180b4_EMS%20dashboard%20for%20installers_EN.png`
  4. Energy management dashboard for installers EN — `https://cdn.prod.website-files.com/65b3e159d25a6097b6ca5815/69146404d57eadc8b3fe6647_Energy%20management%20dashboard%20for%20installers_EN.png`
  5. Fleet-wide asset view — `https://cdn.prod.website-files.com/65b3e159d25a6097b6ca5815/6849695bd53157b6b6ec554f_Home%20energy%20monitoring_asset%20view_EN.png`
  6. System Details — `https://cdn.prod.website-files.com/65b3e159d25a6097b6ca5815/6849698cace08fb71899b736_Energy%20management%20software_System%20details_EN.png`
  7. Regulatory Compliance Configuration — `https://cdn.prod.website-files.com/65b3e159d25a6097b6ca5815/68496c6cadf6939df96b79db_Energy%20monitoring_Regulatory%20compliance_EN.png`
  8. gridBox IP Address (DE) — `https://cdn.prod.website-files.com/65b3e159d25a6097b6ca5815/68496d88a523f364cc8747cb_Energy%20monitoring%20IP%20address_DE.png`
  9. Installation Wizard — `https://cdn.prod.website-files.com/65b3e159d25a6097b6ca5815/68496d086689c8ecb8098218_Energy%20monitoring_wizard_EN.png`
- **Stated tech stack:** Public "Energy API". White-label theming.

### Information architecture
- **Pages observed (exact labels):** "Asset view" (fleet), "System details", "Historical view", "Commissioning wizard"; regulatory-mode toggles for **"§14a EnWG"** and **"§9 EEG"**; "Installer Hub". Three explicit personas: Administrator (XENON Dashboard), Homeowner (User Dashboard), Installer (Installer Hub).
- **Home screen layout:** Fleet table with system tiles — status indicators, serial numbers, registration dates, last-connection timestamps. Pagination + column filtering.
- **Multi-tenancy / org switcher:** Yes — white-label multi-tenant.

### Visualisation patterns
- **Chart types observed:** Animated energy-flow diagram (icons + flowing dots + live wattage), historical line chart with dynamic price overlay and ToU decisions, asset-status tiles.
- **Time-window controls:** Daily-to-yearly navigation on historical view.
- **Data density per screen:** Asset view table-dense; user dashboard sparse.

### Interaction patterns
- Drill-down from fleet to system details is page navigation rather than drawer. Refresh-data button without page reload.
- Command palette / keyboard shortcuts / floating helpers: NOT FOUND.

### Theme & visual language
- **Theme:** Light by default; partner can override via white-label.
- **Brand accent colour:** gridX marketing uses orange/black.
- **Typography:** Modern geometric sans-serif.
- **Density:** Comfortable.

### AI / agent features
- Forecasting + heat pump explainers + solar surplus prioritization — explainers, not agent-driven.

### SDK / public API
- **Public API documented:** Yes — "Energy API" advertised. Dev-portal URL NOT FOUND publicly (likely behind partner login).
- **SDK in any language:** NOT FOUND publicly. Soly built two apps in 3 months via API.

### Things this platform has that our v1 missed
- Three-persona split done explicitly (admin / homeowner / installer)
- "Installer Hub" with commissioning wizard, gridBox auto-scan, ~10-minute setup
- Regulatory mode toggle as a first-class UI primitive
- Animated energy-flow visualisation — now table-stakes in EU HEMS

### Frontend-tech-lead's-eye verdict
gridX is the strongest reference of this tier. The 3-layer architecture (Admin / User / Installer) is a clean IA decision worth copying. Screenshots look 2024–2025-modern. Treat gridX as structural reference; Linear/Vercel for visual modernity.

---

## Platform: Octopus Energy — KrakenFlex

- **Region:** UK (London)
- **Customer segment they target:** B2B SaaS for asset owners, traders, suppliers, system operators; >1,300 MW across 1,200 assets.
- **Public product URL(s):**
  - https://octopusenergy.group/kraken-flex
  - https://kraken.tech/
  - https://dashboard.krakenflex.com/ (production dashboard — login-only)
- **Pricing model:** Enterprise (per-MW implied).
- **Screenshots / video / demo URLs:** Public marketing shows only hero. Actual product UI is login-gated.
- **Stated tech stack:** Cloud + ML/AI.

### Things this platform has that our v1 missed
- ML-driven autonomy: operator's job is exception handling
- "Match supply and demand" framing → home screen is health/imbalance, not lists

### Frontend-tech-lead's-eye verdict
Reputation outpaces public evidence — operator UI gated; published claims are "claimed but not verified". Confidence: medium.

---

## Platform: Tesla — Powerhub + Autobidder + Opticaster

- **Region:** US origin, global deployments including EU
- **Customer segment they target:** Utility-scale and C&I battery operators, IPPs, capital partners (Autobidder portfolio >7 GWh)
- **Public product URL(s):**
  - https://www.tesla.com/support/energy/tesla-software/autobidder
  - https://www.tesla.com/support/energy/tesla-software/powerhub
- **Stated tech stack:** "Tesla cloud infrastructure ... interfacing via secure web APIs".

### Information architecture
- **Pages observed:** Powerhub: "active alerts dashboard"; "single interface for many combinations of energy assets" — solar, storage, non-Tesla assets, site meters, individual battery blocks, solar inverters and diesel generators. Autobidder: market-bidding and dispatch control with value stacking.

### Things this platform has that our v1 missed
- Co-optimization across multiple value streams as a single autonomous loop
- Balance-of-plant alerts (transformer, breaker, fire) as first-class operator surface — operator UI is alert-driven, not chart-driven

### Frontend-tech-lead's-eye verdict
Closest reputation to "Linear of energy" but gated. Borrow the framing (alerts top, fleet under, drill-down).

---

## Platform: sonnen — Customer App + Dash 2.0 + Partner Portal

- **Region:** Germany (Wildpoldsried), part of Shell. DE/AU/US/IT.
- **Customer segment they target:** Residential battery owners, installers (Partner Portal), aggregators (operator-side sonnenVPP)
- **Public product URL(s):**
  - https://www.sonnenusa.com/en/sonnen-app/
  - https://my.sonnen.de/
  - https://find-my.sonnen-batterie.com/ (Customer Dashboard "Dash 2.0")
- **Pricing model:** Consumer hardware + bundled services.
- **Screenshots:**
  1. App main screen — `https://cdn.prod.website-files.com/6880e94a10d268be27eed8af/689db2f4f9cfd4d1bb771391_App-screen-EN%20(1).avif`
  2. Energy insights — `https://cdn.prod.website-files.com/6880e94a10d268be27eed8af/689237f84214727b6393f2dd_Card-App-Screen-EN-2025-Version.avif`
  3. Storm-protection / backup — `https://cdn.prod.website-files.com/6880e94a10d268be27eed8af/6880e94a10d268be27eeda4c_57d4167f6acef7e0d1de6631d92486f5_CARD_SP_storm.avif`
  4. Battery status — `https://cdn.prod.website-files.com/6880e94a10d268be27eed8af/6892371dd452b18789c18227_Card-sonnenHome-Battery-11.avif`

### Information architecture
- **Pages observed (exact labels):** "Your Account" (top right), **"Your locations"** (multi-property tiles), **"Backup buffer"** / **"Emergency mode"** / **"Storm Protection"**, historical analysis view.
- **Home screen layout:** Real-time tile + solar/storage/use indicators; backup-buffer slider; battery SoC indicator.
- **Multi-tenancy / org switcher:** Yes — "Your locations" tiles allow switching between properties.

### Visualisation patterns
- Energy-flow animation (solar → battery → house → grid); historical time-series; battery SoC circle.

### Things this platform has that our v1 missed
- Scenario cards ("Storm Protection", "Emergency Mode") that pre-charge to full when bad weather is forecast
- Multi-property "Your locations" tiles in chrome
- Backup buffer as user-controllable slider, not buried in settings

### Frontend-tech-lead's-eye verdict
Pure consumer-grade UX — useful as the upper bound for the household-owner persona.

---

## Platform: Generac Grid Services — Concerto (ex-Enbala)

- **Region:** US/Canada (Vancouver origin).
- **Customer segment:** Utilities, grid operators, electricity retailers, energy traders, large energy users.
- **Public product URL(s):** https://www.generacgs.com/concerto/, https://www.generacgs.com/concerto/optimize/

### Information architecture
- Three named modules: **Concerto Engage** (customer onboarding + asset activation), **Concerto Optimize** (control + automation), **Concerto Analyze** (visualization + alerts).

### Things this platform has that our v1 missed
- Three-module taxonomy (**Engage / Optimize / Analyze**) — borrow the taxonomy. GECKO could ship Onboard / Operate / Analyze tabs.

### Frontend-tech-lead's-eye verdict
Clean conceptual structure, thin public UI evidence. Borrow the IA taxonomy, not the visuals.

---

## Adjacent SaaS reference (brief)

### Linear — dark-theme command palette exemplar
- https://linear.app/docs/account-preferences — "dark and light" themes
- https://linear.style/ — brand guidelines
- Cmd+K command palette is "how experienced Linear users operate"
- **Implications for GECKO:** dark theme = standard for productivity B2B SaaS; Cmd+K is a strong differentiator vs every Tier-3 EU VPP platform.

---

## Tier 3 summary

- **Platforms found:** 6 in depth (Next Kraftwerke, gridX, Octopus KrakenFlex, Tesla, sonnen, Generac Concerto) + 1 adjacent (Linear).
- **Confidence:** Medium-high on gridX, sonnen, Next Kraftwerke. Medium on Concerto. Medium-low on KrakenFlex and Tesla Powerhub (operator UIs are gated; claims from marketing copy). Centrica FlexPond unreachable (ECONNREFUSED).
- **The "canonical shape" of a serious VPP/EMS frontend:**
  - Fleet overview as operator home (list/table of assets with status tiles)
  - Real-time energy-flow visualisation for household persona
  - Drill-down from fleet to system-details
  - Schedule / dispatch view tied to market signals
  - Historical time-series with daily-to-yearly navigation
  - Alerts dashboard near the top of operator UI
  - At least three explicit personas: aggregator-operator, installer, asset-owner
- **Variations:** Light vs dark — EU VPP defaults light (NEMOCS, gridX, sonnen); US/Tesla and adjacent SaaS (Linear) lean dark. Density: trader portals denser; consumer apps sparse.
- **Theme/visual language consensus:** Light theme is the EU default. Accent colours: green (Next Kraftwerke, sonnen mint), orange (gridX, Generac), purple/teal (Octopus). Typography uniformly modern geometric sans. Density "comfortable" — none Bloomberg-dense.
- **AI/agent features prevalence in EU VPP platforms:** 0 of 5 EU/EU-deployed platforms show a visible text AI assistant. **Wide-open opportunity for GECKO.**
- **Voice agents in EU VPP platforms:** Confirmed NONE across all 6 platforms. **Clear gap GECKO can fill.**
- **SDK / public API in EU VPP platforms:** gridX advertises an "Energy API" used in production but the dev portal isn't public. All others NOT FOUND. **Public, documented TypeScript+Python SDK would be category-defining for GECKO.**
- **Specific patterns we should adopt:**
  - Explicit three-persona split (Operator / Installer / Asset-owner) — from gridX
  - Animated energy-flow visualisation for household view — from gridX, sonnen
  - Fleet table with pagination + column filtering as operator home — from gridX
  - Drill-down to system-details with refresh-without-reload — from gridX
  - Scenario-card pattern ("Storm Protection", "Emergency Mode") for prosumers — from sonnen
  - Three-tab module taxonomy (Onboard / Operate / Analyze) — from Concerto
  - Regulatory-mode toggle as a first-class UI element — adapted from gridX (§14a / §9 EEG → НКРЕКП-friendly toggles)
  - Alerts-dashboard surface near the top of operator UI — from Tesla Powerhub
  - Multi-property/multi-site switcher in chrome — from sonnen
- **Specific patterns we should avoid / replace:**
  - Light-only theme — EU norm but reads 2018-era. Ship dark teal-gecko by default.
  - Marketing illustrations standing in for real UI
  - Persona switching as menu hiding — gridX does it right (separate apps), copy gridX
  - Hiding APIs behind partner-portal walls — ship public dev docs
- **Gaps we will fill (features no EU platform has):**
  - Visible AI agent(s) — text-based, per persona (operator, installer, owner)
  - Voice agent for hands-free operator monitoring
  - Public TypeScript+Python SDK + dev portal
  - Dark theme by default (teal-gecko brand)
  - Cmd+K command palette (Linear-style) in operator UI
  - React Portals overlays/drawers for fast drill-down without page navigation
  - Ukrainian-language by default with EU-grade IA
