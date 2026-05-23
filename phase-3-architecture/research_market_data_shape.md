# Research: Ukrainian Electricity Market Data — Shape & Structure

**Purpose:** internal architecture note for GECKO VPP demo. We use SYNTHETIC data, but it must look credible to a UA energy professional. This document captures the LOGIC and SHAPE of each market segment, not specific historical values. Numbers below are "typical ranges, not point values" — order-of-magnitude anchors for our synthetic generators.

**As-of date:** May 2026. War-era regime: damaged generation fleet (~1/3 of pre-invasion installed capacity), evening peak severely constrained, price caps changed twice in early 2026.

---

## 1. РДН — Ринок На Добу Наперед (Day-Ahead Market)

### Daily price shape
- **Double-peak profile is the rule** in the heating season. Sources confirm the **evening peak at 17:00 hit the price ceiling 100% of days** in Nov 2025; 16:00 hit it on 87% of days. Morning peak is softer (typically 08:00–10:00).
- **Trough** sits in the **deep night, ~03:00–05:00**. A secondary midday softening (~12:00–14:00) appears in summer when PV output is high.
- In a normal (non-war) market the shape would resemble Continental European patterns since synchronisation with ENTSO-E in March 2022 (UA-IPS + UA-BEI zones). Under current war conditions, the evening peak is structurally pinned to the cap because of generation deficit at peak demand.

### Typical price range (2024–2026, UAH/MWh — "typical ranges, not point values")
- **Baseload index:** roughly **3,500–6,500 UAH/MWh** depending on season and damage state. Nov 2025 base index = 6,387. May 2026 spot ~3,953.
- **Peakload index:** roughly **5,000–7,500 UAH/MWh**. Nov 2025 peak = 7,406.
- **Off-peak / night trough:** as low as **1,500–2,500 UAH/MWh** in shoulder seasons.
- **Price caps (regulatory):** changed Jan 2026 to 15,000 UAH/MWh (РДН/ВДР) and 16,000 UAH/MWh (БР); reverted March 31, 2026 to hourly caps of **5,600–6,900 UAH/MWh** (РДН/ВДР) and **6,600–8,250 UAH/MWh** (БР outside evening peak).
- **In summer trough hours under high renewables, occasional near-zero or low (<1,000 UAH/MWh) prices** are realistic.

### Seasonal pattern
- **Winter (Nov–Feb):** highest prices, sharpest evening peak, deepest night/peak ratio (peak/base ~1.2–1.4). Frequent cap-pinning.
- **Spring/Autumn (Mar–May, Sep–Oct):** moderate prices, broader peak, milder ratios.
- **Summer (Jun–Aug):** PV pushes midday prices down; peak shifts later (~19:00–20:00) when PV drops but cooling load persists. Lower overall level except heatwaves.

### Weekday vs weekend
- Weekend baseload **5–15% lower** than weekday. Industrial demand is the main differentiator. Holidays similar to weekend.

### Bidding zones
- **UA-IPS** (Integrated Power System — main grid) and **UA-BEI** (Burshtyn Energy Island). Both synchronously coupled with ENTSO-E CE since March 2022. UA-BEI is small (~2.5% of demand), pricing typically tracks Slovakia/Hungary border. Public OREE reports usually quote only UA-IPS — we should generate primarily UA-IPS data and only synthesise UA-BEI if a demo customer asks.

### Trading row structure (recommended schema)
```
дата (date)
година (1..24, integer hour-of-day, Kyiv time)
ціна_грн_мвт (price, UAH/MWh)
об'єм_мвт (cleared volume, MWh)
торгова_зона (bidding_zone: 'UA-IPS' | 'UA-BEI')
індекс_базовий | пік | позапік (daily index labels — derived)
```

### Gate timing
- **Gate closure: D-1, 11:00 Kyiv (CET/CEST 10:00)** historically per OREE rules; **temporarily extended to 13:00 Kyiv** on multiple delivery days during 2025 due to war-time emergency procedures. The "~12:30 D-1" assumption is in the right ballpark but **not exact** — confirm against OREE technical regulations before final demo. Results published by OREE typically 13:00–14:30 local.

### Authoritative sources
- https://www.oree.com.ua/index.php/indexes — РДН indices, weighted-average prices
- https://www.oree.com.ua/index.php/control/results_mo/DAM — trading results
- https://map.ua-energy.org/en/datasets/category/40 — Energy Map / DiXi datasets (PRIMARY for shape — open data, machine-readable)
- https://euenergy.live/electricity-prices/ukraine/ — hourly chart, ENTSO-E feed (good visual reference)
- **CAVEAT:** OREE stopped publishing trade-level info from **Dec 30, 2024** for security reasons. Aggregated indices continue. Recent hourly granularity is partial.

---

## 2. ВДР — Ринок Внутрішньодобовий (Intraday Market)

### Trading model
Continuous, discrete-event trades from gate-close through delivery hour. Each trade is its own row (not hourly bars). Hour-of-delivery is the key — trades for hour H can happen any time from D-1 evening through ~30–60 min before H.

### Price relationship to РДН
- Weighted-average IDM price typically **tracks РДН closely** — within ±10–20% under normal conditions. Aug 2025: IDM avg 4,913 vs РДН 5,420 UAH/MWh (IDM ~9% below). Nov 2025: IDM 6,658 vs РДН base 6,387 (~4% above).
- **Higher volatility per-trade** than РДН — individual trades can deviate ±30% from the РДН clearing price for the same hour, especially close to gate.

### Volume share
- IDM volume is roughly **15–25% of РДН volume** in normal conditions (Aug 2025: combined РДН+ВДР = 2.57 TWh; ВДР is the smaller share). Bigger share when forecasts swing (high wind days, blackout-schedule changes).

### Trade record schema (recommended)
```
timestamp (trade execution time)
година_постачання (delivery hour, 1..24)
дата_постачання
об'єм_мвт (trade size)
ціна_грн_мвт
сторона ('BUY' | 'SELL') — from our asset's perspective
контрагент_код (anonymised counterparty ID — string like CP-014)
торгова_зона
```

---

## 3. БР — Балансуючий Ринок (Balancing Market)

### Mechanism
Operated by **NEC Ukrenergo** (TSO). Daily auctions of bids/offers for activation; settlement of imbalances per settlement period.

### Settlement period
- **1 hour** historically. EU target model is 15 min; Ukraine roadmap toward 15-min not yet enforced. **Use 1-hour periods for demo.**

### Asymmetric pricing
- **YES, asymmetric.** Two prices per settlement period:
  - Price for system **short** (positive imbalance — TSO had to buy up energy): high, can be **2–5× РДН** in deficit hours.
  - Price for system **long** (negative imbalance — TSO sold excess): low, can fall well below РДН.
- A market participant whose imbalance was **against the system direction** is paid favourably; **with the system** is penalised. Standard EU dual-price model.
- 2025 price caps (post-March 2026): **6,600–8,250 UAH/MWh outside evening peak**, higher inside. Pre-March 2026 cap was 16,000 UAH/MWh.

### Magnitude vs РДН
- "Normal" hour: settlement price within 0.8×–1.5× РДН.
- "Stress" hour (cap-pinning, war-related shortfall): can be **2–5× РДН**, occasionally hitting the regulatory ceiling.

### Schema (recommended)
```
дата
період_розрахунку (settlement_period — integer 1..24)
ціна_дефіциту_грн_мвт (price_short, when system is short)
ціна_надлишку_грн_мвт (price_long, when system is long)
напрямок_небалансу_системи ('SHORT' | 'LONG' | 'BALANCED')
наш_небаланс_мвт (our_imbalance_mwh, signed)
розрахунок_грн (settlement_uah, signed)
```

---

## 4. ДД — Двосторонні Договори (Bilateral Contracts)

### Structure
- OTC. Counterparties agree volume + price + schedule directly; report cleared volumes to TSO (NEC Ukrenergo).
- Auctions are organised by **UEEX (Ukrainian Energy Exchange)** for state-sector volumes; private bilateral deals are pure OTC.
- **Producers ≤20 MW** can sell via bilateral agreements **without** mandatory auction (2024 enhancement).

### Profile types
- **Base load** — constant volume every hour of contract period (e.g., 5 MW × 24 h × N days).
- **Peak load** — volume only during peak hours (typically 08:00–22:00 weekdays).
- **Off-peak load** — night hours only.
- **Individual profile** — hourly schedule uploaded as a table (UEEX template). Most flexible; needed for VPP-style flexible assets.

### Pricing
- Most commonly **fixed UAH/MWh** for the contract period.
- Some indexed contracts reference РДН index ± premium/discount (e.g., "РДН base + 5%"). Common for industrial buyers hedging.

### Duration
- Spot bilateral: 1 day to 1 month.
- Forward bilateral: **1 month, quarter, half-year, full year** are standard tenors. Year-ahead common for industrial off-takers.

### Schema (recommended)
```
contract_id
counterparty (string)
profile_type ('BASE' | 'PEAK' | 'OFFPEAK' | 'INDIVIDUAL')
start_date, end_date
price_uah_mwh (or formula reference)
hourly_volumes_mwh (for INDIVIDUAL profile — array/JSON of 24 hourly values)
торгова_зона
total_contracted_energy_mwh (derived)
```

---

## 5. Зелений Тариф / ДП "Гарантований Покупець" Flow

### Current state (2025–2026)
- Green tariff regime is **being wound down but still active** for installations commissioned before policy changes. **2025 green tariff for new (small) installations: 576.91 коп/kWh** ≈ 5,769 UAH/MWh excl. VAT.
- Composition of Гарантований Покупець intake (2025): **solar 92.5%, wind 2.8%, bioenergy 2.7%, hydro 2.0%** — solar dominates absolutely.
- **2025 total payments: 54.3 bn UAH** to RES producers; settlement rate 86% (down from 99.8% in 2021).
- **Debt to RES producers: 23.3 bn UAH** as of 2025 — chronic settlement gap. Worth modelling as a "receivables aging" widget in the demo.

### New model (replacing green tariff)
- **Feed-in tariff auctions** (state-organised competitive auctions for new RES capacity) + standardised **PPAs**.
- **Market-based + premium** scheme moving forward — RES sells on РДН/ВДР, receives a contract-for-difference style premium from ГП.
- Roadmap not fully enforced; treat as "in transition" for demo realism.

### Settlement statement fields (monthly, per producer)
```
період (YYYY-MM)
виробник_id (producer_id, EIC code in formal docs)
тип_джерела (source_type: 'SOLAR' | 'WIND' | 'BIO' | 'HYDRO')
встановлена_потужність_мвт (installed_capacity_mw)
відпуск_мвт_год (delivered_mwh — monthly total, hourly metering also exists)
тариф_грн_мвт (tariff_uah_mwh — locked at commissioning date)
нарахування_грн (gross billing UAH)
сплачено_грн (paid UAH)
борг_грн (debt UAH — accumulated)
коефіцієнт_розрахунку (settlement_rate — 0..1, e.g., 0.86)
```

---

## 6. Допоміжні Послуги (Ancillary Services)

### Service catalogue (Ukrainian taxonomy aligned with ENTSO-E)
| UA term | EU equivalent | Activation | Volume in UA-IPS (2024 certified) |
|---------|---------------|------------|-----------------------------------|
| **ФКР / РПЧ** (Frequency Containment Reserve) | FCR | Automatic, ≤30 sec | ±177 MW |
| **аРВЧ** (auto Frequency Restoration Reserve) | aFRR | Automatic, ~30 sec–5 min | 1,649 MW (±914.5 MW) |
| **рРВЧ** (manual FRR) | mFRR | Manual, ≤15 min | 4,060 MW (one-sided -4,009) |
| **РР** (Replacement Reserves) | RR | Manual, ≥15 min | 4,808 MW |

### Payment structure
- **Two-component**: capacity payment (€/MW·h of availability) + energy payment (UAH/MWh of activated energy).
- **Capacity payment dominates** for FCR (always-on standby). Energy payment dominates for mFRR/RR (only activated when called).
- **Indexed to EUR** — mitigates FX risk for investors. NERC sets price caps in EUR-pegged form.
- **FCR price cap: 1,339.82 UAH per MW per hour** (approximate, as of 2025 NERC resolution).
- **Auctions**: daily, weekly, and special long-tenor (5-year) auctions exist. 5-year FCR auction was run by Ukrenergo to attract BESS investment.
- Indicative revenue: **a 1 MW BESS** providing FCR or aFRR earns **~€100k/year**. Useful anchor for our VPP business-case widget.

### Activation profile (for synthetic generation)
- FCR: continuously "armed", actual energy delivered is small (frequency wanders ±10–50 mHz constantly). Model as near-100% availability with low energy throughput.
- aFRR: activated **multiple times per hour**, durations typically 30 sec – 5 min.
- mFRR: activated **several times per day**, durations 15 min – 1 h.
- RR: activated **rarely**, during major events.

### Schema (recommended — one row per delivery hour per service per asset)
```
дата
година
послуга ('FCR' | 'aFRR_up' | 'aFRR_down' | 'mFRR_up' | 'mFRR_down' | 'RR')
заявлена_потужність_мвт (offered_capacity_mw)
прийнята_потужність_мвт (cleared_capacity_mw)
ціна_потужності_eur_мвт_год (capacity_price_eur)
активована_енергія_мвт_год (activated_energy_mwh)
ціна_енергії_грн_мвт (energy_price_uah)
дохід_потужність_грн, дохід_енергія_грн (revenue split)
```

---

## 7. Recommended Synthetic Dataset Shape for GECKO VPP Demo

### Portfolio assumption (from PRODUCT_BRIEF v0.4)
8–12 assets, ~50 MW total. Recommended mix for visual richness:
- 2–3 solar PV (5–10 MW each)
- 1–2 wind farms (~10 MW each)
- 1 small hydro or bioenergy (2–5 MW)
- 2–3 industrial consumer flexibility (demand response, 3–5 MW each)
- 1–2 BESS (1–3 MW / 2–4 MWh) — these unlock ancillary services demo

### Time span
**Recommendation: 13 months** (e.g., Apr 2025 – Apr 2026). Reasoning:
- 12 months captures full seasonality.
- 1 extra month allows "current month vs YoY same month" comparisons.
- Spans the **regulatory price-cap change of Jan 16, 2026 → revert Mar 31, 2026** — visual storytelling opportunity. Demo can point at the chart and say "look, our risk-engine flagged the cap-regime change".
- Spans **winter 2025–2026 blackout schedules** — visible pattern of curtailment hours.

### Granularity
- **РДН: hourly** (24 rows × 365 days × 2 zones ≈ 17,500 rows; UA-IPS only ≈ 8,760).
- **ВДР: trade-level events** (~30–80 trades per day for an active portfolio ≈ 15k–30k rows).
- **БР: hourly settlement** (~8,760 rows per zone).
- **Asset telemetry: 15-minute** (96 × 365 × ~10 assets ≈ 350k rows) — matches typical SCADA polling and what RTUs send to TSO.
- **Ancillary activations: event-level** (a few hundred per asset-month for aFRR-capable assets).

### Events to inject (for credibility)
1. **Scheduled blackouts (графіки відключень)** — recurring pattern Nov 2025–Mar 2026, hour-of-day buckets per oblast. Public ОблЕнерго schedules are the reference.
2. **Emergency curtailments** — random spikes following major Russian strikes (well-known dates: late Aug 2024, Nov 2024, Dec 2024, Jan 2025, Aug 2025, Nov 2025). Use real strike dates as anchors; magnitudes invented.
3. **Scheduled maintenance** — 1–2 of our assets out of service for 5–10 days at a time, ~2 events/year per asset.
4. **Regulatory price-cap regime change** Jan 16, 2026 (raised) and Mar 31, 2026 (lowered & hourly-granular) — visible step in РДН and БР price ceilings.
5. **Settlement rate degradation** — Гарантований Покупець pays only 86% of RES bills in 2025; model as growing receivable aging bucket.
6. **Negative price hours** — 5–15 events across summer 2025 in midday hours (PV surplus + low industrial load).
7. **PV high-summer dunkelflaute counterpoint** — calm wind + clouded summer day = price spike even in low-demand season.

### Approximate row counts (UA-IPS only, 13 months, 10 assets)
| Table | Rows |
|-------|------|
| рдн_prices | ~9,500 |
| вдр_trades | ~20,000 |
| бр_settlements | ~9,500 |
| дд_contracts (header) | ~30–60 |
| дд_contract_hourly_volume | ~50,000 |
| зт_settlements_monthly | ~50 (5 RES assets × 13 months) |
| ancillary_offers | ~20,000 |
| ancillary_activations | ~50,000–80,000 |
| asset_telemetry_15min | ~350,000 |
| graphic_outages (blackout schedule) | ~1,500 |
| **Total** | ~520k rows — fits comfortably in SQLite/Postgres |

---

## 8. Sources

**Tier 1 — primary data**
- ОРЕЕ market operator: https://www.oree.com.ua/index.php/indexes
- ОРЕЕ DAM results: https://www.oree.com.ua/index.php/control/results_mo/DAM
- НЕК Укренерго balancing market: https://ua.energy/for_market_participants/balancing-market/
- НЕК Укренерго imbalance settlement: https://ua.energy/for_market_participants/balancing-market-and-settlement-of-imbalances/
- ДП Гарантований Покупець: https://www.gpee.com.ua/
- Ukrainian Energy Exchange (bilateral auctions): https://www.ueex.com.ua/eng/auctions/electricenergy/
- НКРЕКП (regulator, price caps & methodology): https://nerc.gov.ua/

**Tier 2 — open datasets, machine-readable**
- Energy Map (DiXi / USAID): https://map.ua-energy.org/en/datasets/category/40 — **best single starting point for ML/synthesis work, has CSV exports**
- euenergy.live Ukraine hourly: https://euenergy.live/electricity-prices/ukraine/ (ENTSO-E pass-through)
- ENTSO-E Transparency Platform: https://transparency.entsoe.eu/ (filter on UA-IPS, UA-BEI)

**Tier 3 — analysis & quarterly reports**
- Energy Community Q4 2025 Observatory: https://www.energy-community.org/dam/jcr:ff7c985b-e87e-45c6-906b-c5300f98cdba/Observatory%20Report_Q42025_Final_13_02_2026.pdf
- IEA Ukraine energy profile / market design: https://www.iea.org/reports/ukraine-energy-profile/market-design
- EXPRO Consulting commentary: https://expro.com.ua/en/tidings/
- OECD Competition Market Study (2023): https://www.oecd.org/content/dam/oecd/en/publications/reports/2023/06/competition-market-study-of-ukraine-s-electricity-sector_045239a1/f28f98ed-en.pdf
- GMK Center industry data: https://gmk.center/
- ua-energy.org analytical posts: https://ua-energy.org/en/
- KSE Institute Ukraine energy briefs (search): https://kse.ua/about-the-school/news/

---

## Open questions / judgement calls flagged for the architect

1. **Exact РДН gate-closure time.** Sources reference both 11:00 standard and 13:00 wartime-extended. Architect should confirm against current OREE technical regulations (Регламент роботи РДН) before locking the demo's "trading day clock".
2. **UA-BEI bidding zone data.** Almost no public granular data — Burshtyn Island reports are aggregated. If the demo needs UA-BEI, we will invent it by anchoring to Slovakia/Hungary border prices.
3. **15-min settlement transition.** EU target model is 15-min for balancing. Ukraine has not yet enforced. For demo we use 1-hour БР; if customer asks "why not 15-min?" — answer "matches current UA regulation, would migrate when NEC Ukrenergo enforces 15-min".
4. **OREE data blackout from Dec 30, 2024.** Trade-level data is restricted. Aggregated indices continue. Our synthetic data fills the gap — but this also means real-world reference plots may have visible discontinuities; mention this in the demo if relevant.
5. **Asymmetric balancing-price exact formula.** We have the dual-price principle (system-short price vs system-long price) but not the exact NERC methodology in this doc. If demo customer drills into BR mechanics, pull the exact formula from НКРЕКП Resolution on balancing market rules before answering.
