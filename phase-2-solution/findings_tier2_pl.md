# Tier 2 — Polish / CEE VPP & EMS frontend inventory

**Researcher:** Tier-2 subagent
**Date:** 2026-05-23
**Scope:** Structural inventory only. Sources cited per claim; "NOT FOUND" means I could not verify on a public source within budget.

General note: The Polish/CEE VPP segment splits between (a) aggregators/operators that mostly publish marketing sites and gate the product behind login (Enspirion, Next Kraftwerke PL, VPPlant, Reo.pl, Restart Energy), and (b) utility/DSO customer portals (TAURON eLicznik, PGE eBOK, Energa24, ČEZ DIP) that are widely documented in third-party how-to guides. Dispatcher/SCADA UIs of pure-aggregator products are essentially not in the public web index.

---

## Platform: Enspirion (PSE / Orlen Group aggregator)
- **Region:** Poland
- **Customer segment they target:** C&I (largest energy-intensive enterprises and smaller manufacturing/service facilities), municipalities (JST), renewable producers. Operates as Poland's longest-running power aggregator on the capacity market (DSR/IRP).
- **Public product URL(s):** https://enspirion.pl/ ; https://enspirion.pl/uslugi-elastycznosci/ ; https://enspirion.pl/uslugi-elastycznosci/rynek-mocy/dsr/
- **Pricing model:** Enterprise (contract-based). NOT FOUND publicly.
- **Screenshots / video / demo URLs:** NOT FOUND on enspirion.pl. Marketing/corporate site only.
- **Stated tech stack:** NOT FOUND on public site.

### Information architecture
- **Pages observed (Polish):** Rynek Mocy, DSR (Demand Side Response), TETRA, ENIRA (dispatcher console), kody sieciowe (NCER), drony, o firmie, aktualności, kontakt.
- **Multi-tenancy / org switcher:** NOT FOUND.

### Things this platform has that our v1 missed
- A separate product line ENIRA (dispatcher console) bundled alongside the aggregator — aggregator and dispatcher console sold as separate-but-adjacent products.

### Frontend-tech-lead's-eye verdict
Evidence of a serious B2B aggregator that hides its product behind login. The product taxonomy (DSR, IRP, capacity, dispatcher console as separate stream) is visible; the UI is not.

---

## Platform: Next Kraftwerke Polska — Moja Elektrownia + NEMOCS + NEXTRA
- **Region:** Poland (subsidiary of Cologne-based Next Kraftwerke)
- **Customer segment they target:** Renewable producers ≥100 kWp (solar, wind, hydro, biogas, CHP), storage, flexible consumers.
- **Public product URL(s):** https://www.next-kraftwerke.pl/ ; https://moja-elektrownia.next-kraftwerke.pl/login ; NEMOCS https://www.next-kraftwerke.com/products/vpp-solution
- **Pricing model:** Aggregator contract (revenue share)
- **Screenshots / video / demo URLs:** Two portal mockup images on the German "Mein Kraftwerk" page (https://www.next-kraftwerke.de/unternehmen/mein-kraftwerk); NEMOCS simulation at vpp.next-kraftwerke.com (cert expired at fetch time).

### Information architecture
- **Pages observed (Polish):** Wirtualna Elektrownia, Produkty (energia słoneczna, wiatrowa, wodna, biogaz, magazyny), Moja Elektrownia (login).
- **Home screen (Moja Elektrownia, after login):** Per product copy — current production from the installation, monthly revenue, status of the installation, fault/maintenance reporting.
- **Multi-tenancy:** Customer-portal scope = single producer org with one or many assets ("plants").

### Visualisation patterns
- **Chart types observed (from product copy, not pixel-verified):** time-series for power output (kW), monthly revenue bar/line, status indicator/badge per plant.
- **Time-window controls:** Monthly granularity explicitly mentioned; intra-day live status mentioned.

### Interaction patterns
- **Downtime/maintenance registration ("deregistration")** implies a form modal or drawer.
- **Push notifications:** YES — mobile push for outages.

### Things this platform has that our v1 missed
- Separation of consumer portal (Moja Elektrownia) from trading portal (NEXTRA) from SaaS dispatcher (NEMOCS) — three distinct UI surfaces for three distinct user roles in one company.
- Mandatory field gateway (Next Box) as integration anchor — protocol negotiation moved into controlled hardware.

### Frontend-tech-lead's-eye verdict
A mature product company with explicit role segmentation. The product-line split itself is a structural pattern worth copying.

---

## Platform: TAURON eLicznik (DSO consumption portal) + TAURON Biznes
- **Region:** Poland
- **Customer segment they target:** Residential and SME prosumers (eLicznik); B2B/commercial purchasing (TAURON Biznes).
- **Public product URL(s):** https://elicznik.tauron-dystrybucja.pl/ ; https://elicznik.tauron-dystrybucja.pl/page/pomoc.html ; https://biznes.tauron.pl/
- **Pricing model:** Free (utility customer self-service).
- **Screenshots:** App-store listing shows mobile screenshots — https://apps.apple.com/gh/app/elicznik-tauron/id577050364

### Information architecture
- **Pages observed (eLicznik, Polish):** Startowa (Home), Zużycie (Consumption), Cele (Goals), Odczyty (Readings), Pytania (FAQ), Ustawienia (Settings).
- **Home screen layout:** Aggregate data card: stan licznika (meter reading), zużycie (consumption total), wskaźnik realizacji celu (goal-progress indicator).
- **Multi-tenancy:** Multi-point support — one user, many consumption points (PPE), with default selection in Settings.

### Visualisation patterns
- **Chart types observed:** Time-series consumption chart (dominant element); supports "Porównania" (comparison with own averages + statistical benchmarks) and "Pokaż strefy" (multi-tariff zone breakdown using OBIS codes 1.8.1 / 1.8.2 / 1.8.3).
- **Time-window controls:** Daily, monthly, yearly, custom range.

### Interaction patterns
- Goal-setting flow (Cele tab) — implies a form modal.
- **Notifications:** Email and push for goal-threshold breaches.
- **Mobile landscape mode:** Explicitly mentioned — rotating the phone enlarges the chart.

### Theme & visual language
- **Theme:** Light (TAURON corporate orange-on-white).
- **Brand accent colour:** TAURON orange (~#F39200; not pixel-verified).

### Things this platform has that our v1 missed
- Explicit "consumption goal" feature with target-breach alerting.
- Multi-point selector built into Settings (one user, many PPE codes).
- App-store-distributed mobile native client.

### Frontend-tech-lead's-eye verdict
Competent but conservative utility self-service app — the canonical "DSO digital front door" pattern in CEE. The tab taxonomy (Home / Consumption / Goals / Readings / Help / Settings) is replicated almost identically across Polish DSO portals.

---

## Platform: PGE eBOK + Moje PGE (utility customer portal)
- **Region:** Poland
- **Customer segment they target:** Residential customers, prosumers, small business (PGE Obrót retail sales).
- **Public product URL(s):** https://www.gkpge.pl/dla-domu/strefa-klienta/pge-ebok
- **Pricing model:** Free for PGE customers.

### Information architecture
- **Pages observed:** Faktury i płatności (Invoices & payments), Zużycie energii (Energy consumption), Odczyty (Meter readings), Dokumenty, Oferty, Ustawienia, Zaproszenia (Invite trusted persons).
- **Multi-tenancy / org switcher:** YES — multi-account linking explicitly supported (link many billing accounts from different PGE billing systems under one login).

### Interaction patterns
- **Trusted-person invite flow:** YES — share account access with another person.

### Things this platform has that our v1 missed
- **Trusted-person invite** (share account access without sharing password) — B2C collaboration pattern.
- **Multi-billing-account aggregation** under one identity.

### Frontend-tech-lead's-eye verdict
Same DSO/retailer pattern as eLicznik, plus multi-account aggregation. Visually unremarkable; structurally instructive.

---

## Platform: ČEZ Distribuce — Distribuční portál (DIP)
- **Region:** Czech Republic
- **Customer segment they target:** End customers, retailers/suppliers (B2B), planners/contractors (B2B technical).
- **Public product URL(s):** https://www.cezdistribuce.cz/cs/pro-zakazniky/distribucni-portal ; https://dip.cezdistribuce.cz/
- **Pricing model:** Free for distribution-grid customers.
- **Stated tech stack:** SAP NetWeaver Enterprise Portal (URL contains `/irj/portal/`).

### Information architecture
- **Pages observed (Czech):** Připojení (Connection requests), Měření / Odečty (Metering / readings), Samoodečet (Self-readings), Plánované odstávky (Planned outages), Smluvní vztahy, Dokumenty, Plné moci (Powers of attorney).
- **Multi-tenancy / org switcher:** Role-based segregation, not tenant switcher — same URL, role-dependent UI.

### Visualisation patterns
- **Chart types observed:** Measured-data portal ("Portál naměřených dat") — quarter-hourly or daily consumption/generation time-series.

### Things this platform has that our v1 missed
- **ESB-style integration channel for retailers** — DSO publishes a system-to-system interface as a first-class product.

### Frontend-tech-lead's-eye verdict
SAP NetWeaver Portal application, mid-2010s enterprise-portal styling. Not modern but structurally robust. The *role-based portal* model (same login, different routes for customer / retailer / contractor) and the *ESB-as-product* posture are the lessons.

---

## Platform: Reo.pl (Polish renewable-energy P2P marketplace)
- **Region:** Poland
- **Customer segment they target:** Renewable energy consumers, prosumers, producers.
- **Public product URL(s):** https://reo.pl/ ; https://reo.pl/en/about-us/reopl-platform

### Information architecture
- **Pages observed (English):** Offer, Services, About Us, Information, ESG, For Producers, Contact. Four trading modalities: **Business Groups**, **PPAs**, **Table of Offers** (order book / marketplace), **Peer-to-Peer Platform**.

### Things this platform has that our v1 missed
- **Explicit four-modality trading taxonomy** (Business Groups / PPA / Table of Offers / P2P).
- ESG / sustainability reporting as a first-class menu item alongside trading.

### Frontend-tech-lead's-eye verdict
Marketing site only — no product UI visible. The valuable signal is Reo.pl's division of "renewable energy trading" into four distinct UX surfaces rather than collapsing them.

---

## Platform: VPPlant (Polish commercial-buildings DSR / VPP)
- **Region:** Poland
- **Customer segment they target:** Owners/operators of commercial buildings (HVAC-heavy real estate); ESG-focused B2B.
- **Public product URL(s):** https://vpplant.pl/ ; https://vpplant.pl/en/technologies/virtual-power-plant/

### Information architecture
- **Pages observed:** Technologies (Enabler DSR, oBEMS, OHT, driv2e, Virtual Power Plant), Solutions (ECO / PPA / Enerchain / VAS).

### AI / agent features
- **Stated:** "AI-supported service of active management of building comfort" — claimed in vision statement, not verified.

### Things this platform has that our v1 missed
- **Buildings as the unit of aggregation** (rather than individual inverters / batteries) — HVAC-driven negawatts.
- Enerchain (blockchain settlement) as a product line.

### Frontend-tech-lead's-eye verdict
Polish market segments customers by site type, not just by asset type.

---

## Platform: Restart Energy — RED Platform (Romania)
- **Region:** Romania (CEE adjacent).
- **Customer segment they target:** Renewable producers / prosumers, corporations needing ESG reporting & carbon credits, retail consumers.
- **Public product URL(s):** https://restartenergy.ro/ ; https://restartenergy.ro/en/red-platform/
- **Stated tech stack:** Blockchain (proprietary; tokens = RED MWAT). Inverter integrations: Huawei, SMA.

### Things this platform has that our v1 missed
- **ESG / carbon-credit module bundled with energy trading** — "monitor green energy" + "report ESG" + "trade carbon credits" in one platform.
- **Token-as-settlement (RED MWAT)** — structurally different settlement primitive.

### Frontend-tech-lead's-eye verdict
Romanian outlier — bet on blockchain + ESG-reporting rather than grid-level flexibility. Relevant signal: *bundling of ESG/carbon reporting* with energy supply.

---

## Tier 2 summary

- **Platforms found:** 8 covered with at least one verified public URL (Enspirion, Next Kraftwerke Polska / Moja Elektrownia / NEMOCS / NEXTRA, TAURON eLicznik + Biznes, PGE eBOK, ČEZ DIP, Reo.pl, VPPlant, Restart Energy / RED).
- **Confidence:** MEDIUM-LOW. HIGH on platform existence and IA; LOW on pixel-level UI details (most product surfaces are login-gated).

- **Common information-architecture patterns:**
  - **Role-split products inside one company** — Next Kraftwerke runs three separate UI surfaces; Enspirion separates aggregator from dispatcher console (ENIRA); ČEZ DIP uses role-based routing.
  - **Tab-based residential portal taxonomy** is near-identical across Polish DSO/retailer products: Home / Consumption / Goals or Targets / Readings / Documents / Settings.
  - **PPE / connection-point as the unit of multi-tenancy** for residential and SME.
  - **Marketing site light, product portal gated** — every aggregator hides the actual product behind login.

- **Common visualisation patterns:**
  - Time-series consumption / production charts as the dominant element.
  - Zonal breakdown using OBIS-coded tariff zones (1.8.1 / 1.8.2 / 1.8.3) — Polish/CEE-specific data model directly exposed in the UI.
  - Daily / monthly / yearly toggles + custom range.
  - Comparison overlays ("my consumption vs. my average vs. statistical average").
  - KPI strip on home + drill-into-tab pattern; data density on residential surfaces is *comfortable*, not dense.
  - Quarter-hourly granularity available where smart meters exist.

- **Common interaction patterns:**
  - **Mobile-native client distributed via App Store / Google Play** — push notifications for fault/threshold alerts.
  - **Goal-setting + threshold notification** as the closest thing to "proactive" interaction.
  - **Trusted-person / multi-account invite** (PGE eBOK).
  - **Power-of-attorney / authorisation flows** baked into the IA (ČEZ DIP).
  - **Command palettes, Cmd+K, keyboard shortcuts, in-app AI chat: NOT FOUND in any of the surveyed Polish/CEE platforms.**

- **Theme/visual language consensus:**
  - **Light theme dominates** across all visible surfaces. No mainstream Polish/CEE VPP/EMS platform was found that ships dark mode by default.
  - **Corporate utility palettes:** TAURON orange, ČEZ orange, PGE green, Enspirion navy/teal, VPPlant + Reo + Restart Energy green-on-white.
  - **Typography:** uniformly corporate sans-serif.
  - **Density:** comfortable for residential / B2C, compact/utility for utility back-office, spacious for marketing sites.

- **AI / agent features present in CEE platforms:**
  - **Forecasting** (wind/solar/prosumer) is value-prop messaging — but exposed as data-in-charts, not as a chatbot.
  - **AI-supported building comfort management** — claimed by VPPlant; not verified visually.
  - **"In-app consultant" for carbon-footprint** — claimed by RED Platform; could be human, not AI.
  - **Conversational AI assistants, voice assistants, recommendation cards as first-class UI: NOT OBSERVED in any verified Polish/CEE platform.**

- **SDK / public API maturity in CEE:**
  - **Generally low.** No public developer documentation URL found for any surveyed platform.
  - ČEZ Distribuce has an ESB channel for retailers — system-to-system, not a developer-facing REST/GraphQL API.
  - Third-party / hobbyist scrapes of eLicznik exist — evidence no official Polish DSO API is available.

- **Recommendations for GECKO VPP frontend based on Polish/CEE benchmarks:**
  1. **Adopt the role-split product-line pattern** — one login, three or more URL surfaces.
  2. **Expose OBIS-coded tariff zones in the consumption UI** if GECKO targets Polish/CEE-style markets.
  3. **PPE / connection-point selector + multi-billing-account aggregation** under one identity.
  4. **Ship a mobile native client (iOS + Android)** with push notifications.
  5. **Position the dispatcher / operator console as a distinct UI surface** rather than as a power-user mode of the customer portal.
  6. **Bundle ESG / carbon-reporting as a first-class menu item.**
  7. **Publish an actual developer API page** — no Polish/CEE competitor does, so this is both a low bar and a credible differentiator.
  8. **Default to a dark teal-gecko theme deliberately** — every verified CEE competitor ships light corporate-orange or corporate-green; a polished dark teal product surface is recognisable as a deliberate modernisation move.
  9. **Avoid replicating SAP NetWeaver Portal architecture.**
  10. **Add command-palette (Cmd+K) and keyboard-shortcut surfacing** as a "modern product" tell.
