# DESIGN_INSPIRATION — annotated screenshot references

**Parent:** `RESEARCH_FINDINGS.md` v0.1
**Purpose:** concrete visual references for Phase 3 design and build. Each entry lists the URL, the source platform, what we borrow, and which Acceptance / Adopt-pattern row in RESEARCH_FINDINGS it supports.

**Note on URL longevity:** marketing assets often rot. If a URL stops resolving by Phase 3 start, the local PNG copies in `source/slides/` (for client PDF) and any saved fallbacks here remain canonical. We do NOT redistribute these images in our repo — links only, attribution preserved.

---

## Tier 3 — EU benchmarks (highest information density)

### Next Kraftwerke (DE)

**inspiration_001 — NEMOCS control reserve view**
URL: https://image-proxy.nextkraftwerke.cloud.fcse.io/tZo2TJpM7SGRxcNsTVqaQhFsQKg=/fit-in/1920x1080/https%3A%2F%2Fstrapistoragegkuxf.blob.core.windows.net%2Fprod-gkuxf%2Fassets%2FVPP_As_A_Service_Nemocs_control_reserve_119ff1a6c4.jpg
Borrow: control-reserve dashboard layout (status per asset + cumulative reserve curve). Supports A2 (fleet table), A10 (alerts surface), §2.1.
What we change: dark theme; Ukrainian РВЧ/БР labels instead of German.

**inspiration_002 — NEXTRA trading portal preview**
URL: https://strapistoragegkuxf.blob.core.windows.net/prod-gkuxf/assets/Trading_Platform_Nextra_809317ec3c.jpg
Borrow: trader-facing layout — portfolio, transactions, forecast upload, market info in one screen. Supports the `/producer/rynok/` page concept.
What we change: РДН/ВДР/БР split, грн currency.

**inspiration_003 — NEMOCS brochure PDF**
URL: https://cdn.asp.events/CLIENT_CL_EE_E92EC48A_9F42_8E1E_7106D5CAFEEF513B/sites/Enlit365/media/libraries/exhibitor-brochures/21511-nemocs-brochure-next-kraftwerke.pdf
Borrow: product-positioning vocabulary, "VPP-as-a-Service" framing.
Use: marketing copy reference for GECKO's "Hero" landing page (`/`).

### gridX (DE) — STRONGEST tier-3 reference

**inspiration_004 — Admin/EMS dashboard (English)**
URL: https://cdn.prod.website-files.com/65b3e159d25a6097b6ca5815/691463ac2dd6fe80c3615739_EMS%20dashboard_EN.png
Borrow: operator home layout — top KPI tiles, fleet table beneath, status badges. **Most important single reference.**
Supports A2, A10, §2.1, §6 site map.

**inspiration_005 — Animated energy-flow / Energy management dashboard (EN)**
URL: https://cdn.prod.website-files.com/65b3e159d25a6097b6ca5815/6914638b884ae8d5c10e6d6c_Energy%20management%20dashboard_EN.png
Borrow: live energy-flow visualisation, central layout.
Supports A4 (animated energy-flow).

**inspiration_006 — EMS dashboard for installers (EN)**
URL: https://cdn.prod.website-files.com/65b3e159d25a6097b6ca5815/691465278319e46d2e7180b4_EMS%20dashboard%20for%20installers_EN.png
Borrow: installer persona's distinct UI (different from operator/admin).
Supports A1 (three-persona split — installer surface).

**inspiration_007 — Energy management dashboard for installers (EN)**
URL: https://cdn.prod.website-files.com/65b3e159d25a6097b6ca5815/69146404d57eadc8b3fe6647_Energy%20management%20dashboard%20for%20installers_EN.png
Borrow: installer drill-into-single-system pattern.

**inspiration_008 — Fleet-wide asset view (EN)**
URL: https://cdn.prod.website-files.com/65b3e159d25a6097b6ca5815/6849695bd53157b6b6ec554f_Home%20energy%20monitoring_asset%20view_EN.png
Borrow: paginated table with status indicators per system; serial numbers, registration dates, last-connection timestamps.
Supports A2 (fleet table).

**inspiration_009 — System Details (EN)**
URL: https://cdn.prod.website-files.com/65b3e159d25a6097b6ca5815/6849698cace08fb71899b736_Energy%20management%20software_System%20details_EN.png
Borrow: asset detail page layout — header card, telemetry chart, sub-sections.
Supports A3 (page-nav drill-down).

**inspiration_010 — Regulatory Compliance Configuration (EN)**
URL: https://cdn.prod.website-files.com/65b3e159d25a6097b6ca5815/68496c6cadf6939df96b79db_Energy%20monitoring_Regulatory%20compliance_EN.png
Borrow: regulatory-mode toggle as first-class UI primitive (gridX shows §14a EnWG / §9 EEG toggles).
Supports A9 — adapt to UA: НКРЕКП-friendly toggles, Гарантований Покупець mode, зелений тариф mode.

**inspiration_011 — gridBox IP Address (DE)**
URL: https://cdn.prod.website-files.com/65b3e159d25a6097b6ca5815/68496d88a523f364cc8747cb_Energy%20monitoring%20IP%20address_DE.png
Borrow: gateway-config UI layout.

**inspiration_012 — Installation Wizard (EN)**
URL: https://cdn.prod.website-files.com/65b3e159d25a6097b6ca5815/68496d086689c8ecb8098218_Energy%20monitoring_wizard_EN.png
Borrow: 4-step onboarding wizard layout.
Supports A24 (commissioning wizard) → maps to `/nalashtuvannya/onboarding` per client PDF slide-10 stage 2.

### sonnen (DE / Shell)

**inspiration_013 — App main screen (EN)**
URL: https://cdn.prod.website-files.com/6880e94a10d268be27eed8af/689db2f4f9cfd4d1bb771391_App-screen-EN%20%281%29.avif
Borrow: consumer-grade dashboard density, real-time tile + solar/battery/use indicators, mint-green accent for renewable.
Supports A4 + §2.5 (theme).

**inspiration_014 — Energy insights card**
URL: https://cdn.prod.website-files.com/6880e94a10d268be27eed8af/689237f84214727b6393f2dd_Card-App-Screen-EN-2025-Version.avif
Borrow: card-based information design for the prosumer dashboard.

**inspiration_015 — Storm Protection scenario card**
URL: https://cdn.prod.website-files.com/6880e94a10d268be27eed8af/6880e94a10d268be27eeda4c_57d4167f6acef7e0d1de6631d92486f5_CARD_SP_storm.avif
Borrow: scenario-card pattern (storm-protection mode that auto-charges battery on weather forecast).
Supports A7 (scenario cards) — UA adaptation: "Blackout mode" (UA-specific given war-era outages), "Curtailment defence", "Imbalance hedge".

**inspiration_016 — Battery status card**
URL: https://cdn.prod.website-files.com/6880e94a10d268be27eed8af/6892371dd452b18789c18227_Card-sonnenHome-Battery-11.avif
Borrow: battery SoC visualisation primitive — large circle / arc + numeric percentage.
Use in `/storage/uze/` for УЗЕ owners.

### Next Kraftwerke Mein Kraftwerk mockups

**inspiration_017 — Mein Kraftwerk mobile mockup 1**
Filename: `Meik_Mock_Up_3_1_dad68d7c06.png` (host: next-kraftwerke.de)
Borrow: producer-facing mobile layout — live status + monthly revenue.

**inspiration_018 — Mein Kraftwerk mobile mockup 2**
Filename: `Meik_Mock_Up_2_2_82e77b4897.png` (host: next-kraftwerke.de)
Borrow: producer asset-status detail.

### Generac Concerto (US/CA)

**inspiration_019 — Concerto Engage / Optimize / Analyze marquee**
URL: https://www.generacgs.com/wp-content/uploads/2022/11/concerto_marquee_logo_overview.png
URL: https://www.generacgs.com/wp-content/uploads/2022/11/concerto_over_engage.png
URL: https://www.generacgs.com/wp-content/uploads/2022/11/concerto_over_optimize.png
URL: https://www.generacgs.com/wp-content/uploads/2022/11/concerto_over_analyze.png
Borrow: three-module taxonomy (Engage / Optimize / Analyze).
Supports A8.
Note: these are stylised marketing graphics, not real UI. Use for **conceptual structure only**.

### Adjacent SaaS — Linear

**inspiration_020 — Linear dark theme + command palette**
URL: https://linear.app/docs/account-preferences
URL: https://linear.style/
Borrow: dark-theme productivity SaaS visual language; Cmd+K command palette UX.
Supports D6 (command palette), §7 (dark theme).

### Tesla Powerhub (US)

**inspiration_021 — Powerhub support page**
URL: https://www.tesla.com/support/energy/tesla-software/powerhub
Borrow: balance-of-plant alerts as first-class operator surface; framing of "active alerts dashboard" at top of operator UI.
Supports A10. No actual UI screenshots publicly available; use the product description as reference.

### Octopus KrakenFlex (UK)

**inspiration_022 — KrakenFlex marketing hero**
URL: https://octopusenergy.group/kraken-flex
Borrow: ML-driven autonomy framing for operator copilot; "match supply and demand" home framing.
No actual UI screenshots publicly available.

---

## Tier 2 — Polish / CEE benchmarks

### TAURON eLicznik (PL)

**inspiration_023 — TAURON eLicznik mobile app**
URL: https://apps.apple.com/gh/app/elicznik-tauron/id577050364
Borrow: residential portal tab taxonomy (Startowa / Zużycie / Cele / Odczyty / Pytania / Ustawienia); OBIS-coded tariff zone display.
Supports A15 (OBIS zones), A6 (comparison overlays).

### PGE eBOK (PL)

**inspiration_024 — PGE eBOK marketing**
URL: https://www.gkpge.pl/dla-domu/strefa-klienta/pge-ebok
Borrow: multi-billing-account aggregation + trusted-person invite pattern.
Supports A19.

---

## Tier 1 — UA references (terminology + accessibility patterns)

### OREE / AT Оператор ринку

**inspiration_025 — OREE market data**
URL: https://www.oree.com.ua/index.php/indexes
URL: https://www.oree.com.ua/index.php/IDM_graphs
Borrow: UA market terminology, regulator-grade accessibility (dark-mode toggle, font sizing, zoom).
Supports A13 (light-theme accessibility toggle).

### NKREKP dashboard

**inspiration_026 — NKREKP dashboard launch**
URL: https://www.nerc.gov.ua/news/novij-dashbord-yak-instrument-analizu-cin-na-vdr-ta-rdn
Borrow: regulator-style ВДР/РДН analysis tile layout.

### Energy Map (DiXi / USAID)

**inspiration_027 — Energy Map**
URL: https://energy-map.info/uk/
Borrow: dataset-page IA, hourly-granularity-as-default, bilingual UA/EN parity, public API existence.
Supports A14 (hourly default), A20 (UA/EN parity).

### YASNO Business

**inspiration_028 — YASNO Energy Management**
URL: https://yasno.com.ua/business/energymanagement
Borrow: UA-specific workflows — "Подача прогнозу", KEP/Дія.Підпис document signing.
Supports A16 (forecast submission), A21 (KEP integration).

### Aggregator.Energy

**inspiration_029 — Aggregator.Energy four-segment marketing**
URL: https://aggregator.energy/
Borrow: four-segment customer taxonomy (Бізнес / Генерація / Оператор мережі / Домогосподарство).
Use: A1 (persona split) — confirms our three-segment choice has UA-market resonance.

---

## Summary

- **Total inspiration entries:** 29
- **Strongest single reference:** gridX (9 screenshots) — adopt structurally
- **Strongest IA reference:** Next Kraftwerke persona-split + Concerto Engage/Optimize/Analyze module names
- **Strongest visual-language reference:** sonnen consumer cards (mint, mobile-first) + Linear (dark productivity)
- **Strongest UA-grounding reference:** OREE (terminology, accessibility), Energy Map (bilingual + hourly default), Aggregator.Energy (four-segment taxonomy)

These 29 references collectively answer "what does a serious modern frontend in this category look like" with enough specificity that Phase 3 can begin building without further visual research.
