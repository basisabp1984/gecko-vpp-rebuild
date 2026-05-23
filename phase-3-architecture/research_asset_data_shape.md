# Research: Asset Telemetry & Operational Data Shapes for GECKO VPP

**Purpose:** define the *shape* (fields, ranges, temporal patterns, value distributions) of synthetic operational data for a Ukrainian VPP demo. Exact numbers will be invented, but they must respect the underlying physics, market structure, and seasonality so a UA energy professional finds the dataset credible.

**Scope of "shape":** what fields exist per asset class, hourly granularity, expected ranges, daily/seasonal envelopes, and the *signature* of imbalances / curtailments / events that any real VPP would see.

---

## PART A — UA energy asset telemetry shapes

### 0. Common spine — `asset_telemetry_hourly`

Every generating / consuming / storage asset in the VPP shares a common hourly fact row. Specific fields differ; the spine is identical:

| Field | Type | Notes |
|---|---|---|
| `timestamp` | TIMESTAMPTZ | Hour-beginning in Europe/Kyiv (DST-aware). UA market uses **24-hour day** with DST anomalies — code must support the 23h spring-forward and 25h autumn day. |
| `asset_id` | UUID | FK to `asset` registry. |
| `active_power_mw` | NUMERIC(8,3) | Sign convention: **positive = injection to grid**, negative = consumption (for prosumers / charging batteries). |
| `reactive_power_mvar` | NUMERIC(8,3) | Optional; UA codified ancillary signal for transmission-connected assets. |
| `availability_pct` | NUMERIC(5,2) | 0..100. Drops below 100 during partial trips, derating, planned maintenance. |
| `status` | VARCHAR(16) | enum: `online`, `idle`, `maintenance`, `starting`, `stopping`, `tripped`, `curtailed_by_TSO`, `unavailable`. |
| `data_quality` | VARCHAR(8) | `measured`, `estimated`, `forecast`, `gap`. |
| `source` | VARCHAR(16) | `scada`, `manual`, `synthetic`. |

The Zhytomyr project uses the same `(date, hour 1..24)` decomposition rather than a timestamp — that pattern (separate `date` DATE + `hour` SMALLINT 1..24) is the **UA energy industry convention** (the 24 columns `Г1…Г24` in their daily Excel template, see `forecast_zhytomyr_2026-04-14.csv`). GECKO should use the same convention in any operator-facing screen so it reads like a Ukrainian dispatcher's spreadsheet.

---

### 1. СЕС — Solar PV stations

**Geography envelope.** UA solar resource sits at 1100–1400 kWh/kWp/year (south Odeska, Mykolaivska, occupied parts of Khersonska are best at ~1400; Volyn / Kyiv / Chernihiv at the low end ~1050–1150). Capacity factor (CF) range: 11–16% annual, **central estimate ~13%** for utility-scale single-axis tracker in central UA. Cite: [Global Solar Atlas — Ukraine](https://globalsolaratlas.info/map?c=49.0,32.0,7&r=UKR), IRENA UA renewable capacity statistics 2024, [NREL System Advisor Model](https://sam.nrel.gov/) defaults for 49° N.

**Diurnal shape (hourly CF as fraction of nameplate, central UA, clear day):**

| Hour (local) | Jun (summer solstice) | Mar/Sep (equinox) | Dec (winter solstice) |
|---|---|---|---|
| 00–05 | 0.00 | 0.00 | 0.00 |
| 06 | 0.10 | 0.00 | 0.00 |
| 07 | 0.30 | 0.10 | 0.00 |
| 08 | 0.50 | 0.30 | 0.05 |
| 09 | 0.70 | 0.55 | 0.20 |
| 10 | 0.85 | 0.75 | 0.40 |
| 11 | 0.92 | 0.85 | 0.55 |
| 12 | 0.95 | 0.90 | 0.60 |
| 13 | 0.95 | 0.90 | 0.58 |
| 14 | 0.92 | 0.80 | 0.45 |
| 15 | 0.82 | 0.65 | 0.25 |
| 16 | 0.65 | 0.45 | 0.05 |
| 17 | 0.45 | 0.25 | 0.00 |
| 18 | 0.28 | 0.10 | 0.00 |
| 19 | 0.10 | 0.00 | 0.00 |
| 20–23 | 0.00 | 0.00 | 0.00 |

Notes:
- **Zero-output hours:** Dec 16:00–08:00 (16 hours), Jun 20:00–05:00 (~9 hours).
- **Nameplate hit (>0.95 CF):** roughly Jun 11:00–14:00 on a clear day. Most inverters are sized 1.1–1.3× DC/AC ratio, so **clipping** appears as a flat top at 100% for 2–4 hours mid-day on the clearest summer days. Synthetic data should include this flat-top signature — it's a tell-tale sign of real PV data.
- **Module temp derating:** above ~25 °C module temp, power drops ~0.4 %/°C. A 35 °C cell temp day shaves ~4% from nameplate vs STC.

**Cloud variability (day-over-day at same hour, same season):** σ/μ ratio of 0.25–0.45 for partly-cloudy regimes. Heavy overcast days drop production to 10–25% of clear-day value. **Synthetic generator should layer:** clear-sky baseline × cloud index ∈ [0.15, 1.0] where the cloud index follows a persistent autoregressive process (AR(1) with high coefficient at hourly scale) — clouds cluster, they don't flicker independently each hour.

**Telemetry fields (extends spine):**
- `irradiance_w_m2` — 0..1100 W/m² (POA, plane-of-array). Synthetic should follow clear-sky × cloud factor; > 1000 only briefly at solar noon midsummer.
- `module_temp_c` — ambient + 25 °C × (irradiance/1000) roughly.
- `inverter_status_bitmap` — JSONB array `[{inverter_id, status, ac_power_kw}]` for utility-scale plants with 10–50 inverters.

---

### 2. ВЕС — Wind farms

**Geography envelope.** UA pre-war onshore wind CF was 28–35% in the south (Zaporizhzhia, Kherson, southern Odesa coast), 22–27% in central/west. Carpathian foothills (Lviv/Ivano-Frankivsk) have variable terrain effects: site-specific 18–28%. Cite: [IRENA Ukraine renewable energy roadmap REMAP 2030](https://www.irena.org/publications), [DTEK Tyligulska 114 MW Mykolaivska reported CF ~35% in 2024](https://dtek.com/), [Global Wind Atlas — Ukraine](https://globalwindatlas.info/en/area/Ukraine).

**Use a central estimate of 30% annual CF** for a "good UA onshore site" in the synthetic dataset.

**Hourly variability — fundamentally different from solar:**
- Wind has **no fixed diurnal pattern** — equally likely to be 0% or 90% CF at 3 AM as at 3 PM. Mild low-level jet effect at night in some regions can give slight nocturnal boost.
- **Seasonality:** UA winds are stronger Nov–Mar. Winter months can run 35–45% CF, summer (Jul–Aug) often drops to 18–25%. This matters because winter wind = winter heating load — strong correlation with system value.
- **Persistence:** hour-over-hour autocorrelation is ~0.85–0.95. A windy hour → next hour also windy. Use AR(2) or a Weibull-shape × persistence process.
- **Cut-out events:** at sustained > 25 m/s the entire farm trips → output drops from ~90% to 0% within 1 hour. Rare (a few times/year) but a *very* recognizable signature; include 1–3 such events per year in synthetic data.

**Telemetry fields (extends spine):**
- `wind_speed_m_s` — at hub height (typically 100–140 m for modern turbines). 0..30 m/s.
- `wind_direction_deg` — 0..360.
- `turbine_availability_pct` — distinct from grid availability; tracks how many turbines of N are online (e.g. 18/20 = 90%).
- `nacelle_temp_c` — optional secondary signal.

---

### 3. ГПУ — Gas reciprocating generators

**Role in the VPP.** Fast peaking + balancing. UA had a major build-out of distributed ГПУ (Jenbacher, MWM, Wärtsilä, Caterpillar) in 2023–2025 as decentralised backup to the war-damaged thermal grid. Typical units are 1–10 МВт each, often clustered into 10–50 МВт sites.

**Economics — dispatch logic.**
- Modern gas engine: **38–44% electrical efficiency (LHV)**, i.e. ~8–9 м³ natural gas per МВт·год.
- UA industrial gas price 2024–2025: roughly 25–35 UAH/м³ (post-subsidy, industrial; cite [Naftogaz business tariffs](https://www.naftogaz.com/), [ExPro Consulting reports](https://expro.com.ua/)).
- Marginal fuel cost: ~8.5 м³ × 30 UAH ≈ **255 UAH/МВт·год** plus O&M ~150–250 UAH/МВт·год → **break-even ~400–500 UAH/МВт·год**.
- РДН (day-ahead) prices vary 1500–8000 UAH/МВт·год across the day (price cap moved to 9000 UAH for evening peak in 2024 per ОРЕЕ rulings). So **ГПУ is profitable whenever РДН > ~600 UAH/МВт·год**, which is most peak hours.
- The dispatch logic the user wants reflected: **ночью дешевле (1500-2500), днём дороже (4000-7000), evening peak 17:00–22:00 highest**. ГПУ should be ON during 08:00–22:00 weekdays and OFF or idle 00:00–06:00 in the synthetic data — that pattern by itself reads as authentic.

**Operational parameters:**
- **Ramp rate:** 5–20% nameplate per minute (~3–8 minutes from cold to full). For a 5 МВт unit, ~1 МВт/min ramp.
- **Min stable load:** 30–50% of nameplate (engines won't run efficiently below). Below that → must shut down.
- **Start times:** hot start 1–5 minutes, cold start 10–20 minutes.
- **Heat rate variation:** efficiency drops 1–3 points at partial load (e.g. 42% at full → 39% at 50% load).

**Telemetry fields (extends spine):**
- `fuel_flow_nm3_h` — instantaneous gas flow.
- `cumulative_fuel_nm3` — meter reading, monotonically increasing.
- `engine_runtime_h` — total hours; matters for maintenance schedule (overhaul every 40 000–60 000 hours).
- `oil_pressure_bar`, `exhaust_temp_c`, `coolant_temp_c` — secondary telemetry, useful for "production fidelity" but not for VPP optimisation.
- `start_count` — increments each ignition; reliability metric.

---

### 4. УЗЕ — Battery storage (BESS)

**Market context.** UA market for grid-scale storage emerging post-2024. DTEK 200 МВт project at Zaporizhzhia announced. Tariff/market signals: arbitrage on РДН + ancillary services (РВЧ secondary frequency response, БР balancing reserve, FCR primary). New УЗЕ tariff structure under НКРЕКП resolutions 2024-2025.

**Operational shape:**
- **Round-trip efficiency:** 85–88% for modern LFP/NMC packaged systems (DC-DC ~94%, inverters ~96% each direction → ~86% AC-AC).
- **C-rate:** typical 0.5C (2-hour duration) for arbitrage; 1C (1-hour) for FCR/РВЧ. So a 20 МВт / 40 МВт·год system at 0.5C.
- **Cycles per day under arbitrage:** **1.0–1.5 typical**. One deep cycle = charge overnight 02:00–05:00 (cheap) + discharge evening 18:00–21:00 (expensive peak). A second shallow cycle possible midday (charge from solar surplus 11:00–14:00, discharge late afternoon 16:00–17:00).
- **DOD:** rarely 100%. Real arbitrage operates ~10–90% SOC window (80% DOD) to extend cycle life. Calendar + cycle degradation models target ~6000 full equivalent cycles over 10 years for LFP.
- **SOC swing pattern under arbitrage** (typical workday):
  - 00:00–05:00: charge, SOC 15% → 90%
  - 05:00–11:00: idle / hold (or shallow discharge during morning ramp 07:00–09:00)
  - 11:00–14:00: optional small charge from solar overproduction
  - 17:00–21:00: discharge, SOC 90% → 15%
  - 21:00–24:00: idle, await cheap overnight window

**Ancillary services activation:**
- **РВЧ (secondary frequency response):** activated several times per day, typical duration 30s–15 min per activation. The battery follows AGC signal — power swings around a setpoint with kW-level granularity. In synthetic data: 5–20 small activations per day, average dispatch ±5–15% of nameplate.
- **БР (balancing reserve):** activated by Укренерго ~1–5 times/day in stressed periods, can run 15 min – several hours. Larger swings (20–80% of nameplate). Activation log should include start_ts, end_ts, direction (up/down), avg_mw.

**Telemetry fields (extends spine):**
- `soc_pct` — 0..100, the *headline* state-of-charge.
- `active_power_mw` — signed: positive = discharge to grid, negative = charging from grid. Use the same sign convention consistently across all VPP assets to avoid the most common operator-confusion bug.
- `cumulative_cycles` — full-equivalent cycles since commissioning, NUMERIC(8,2). Increments by ~0.5 per typical day.
- `capacity_fade_pct` — degraded capacity vs nameplate; starts at 0 and slowly increases. Real systems lose ~2–3% in year 1, then ~1.5%/year. Worth showing on a "battery health" screen for credibility.
- `cell_temp_c_min`, `cell_temp_c_max` — thermal spread across the pack.
- `aux_load_kw` — HVAC + BMS overhead; ~1–3% of nameplate when idle.
- `activation_events` — separate event table: `(start_ts, end_ts, service_type ∈ {РВЧ, БР, FCR, arbitrage}, avg_mw, energy_mwh)`.

---

### 5. Активний споживач — C&I prosumer / flexible load

**Three archetypes the demo should support:**

**(a) Food processing (e.g. dairy, brewery, meat).** Daily cycle: ramp up 06:00, peak 09:00–17:00, ramp down 22:00. Weekend load 40–60% of weekday. Peak/base ratio ~3:1. Some on-site refrigeration → constant base ~30% nameplate even overnight. Flex potential: precool/preheat thermal mass → 1–2 hour shifts of 20–40% of load.

**(b) Metallurgy / steel mill arc furnace.** Sharply intermittent: 2–4 hour smelting batches drawing 50–100% nameplate, then idle 30 min between heats. Total daily on ratio 60–75%. Very poor flexibility (process-bound). Useful as a *base load that occasionally trips offline* during outages.

**(c) Water utility / municipal pumping (like Vodokanal in the user's other project).** Strong inverse correlation with electricity price — they pump at night when cheap and water tower buffers daytime demand. Peak/base ratio 2:1 within a day. **Big flex potential:** can shift 30–60% of total load by 4–6 hours. The user's Vodokanal SES project is the right reference for this archetype.

**(d) Retail / supermarket chain.** Smooth diurnal curve: low overnight ~30%, gradual ramp 07:00–10:00, plateau 10:00–21:00 at 100% (HVAC + refrigeration + lighting), wind down 22:00–23:00. Weekend HIGHER than weekday (opposite of B2B). Flex: HVAC setpoint ±2 °C → 10–20% reduction for 1–2 hours.

**Telemetry fields:**
- `active_power_consumed_mw` (always negative on the common spine, or positive on its own scale — pick one convention).
- `onsite_generation_mw` — non-zero if customer has rooftop solar / СЕС / ГПУ on-premise.
- `net_grid_exchange_mw` — consumed − generated.
- `flex_offered_mw` — how much of current load is curtailable (DR enrollment).
- `flex_activated_mw` — how much was actually called upon this hour.
- `building_temp_c`, `tank_level_pct` etc. — process-specific.

---

### 6. Imbalance & event patterns (cross-asset)

This is the **most important "feel" layer** — synthetic data without these patterns reads like a textbook, not a real VPP.

**Forecast-vs-actual mismatch (РДН imbalance).**
- For wind: hourly forecast error σ ~10–18% of nameplate (day-ahead horizon). Forecasts updated intraday narrow this to 6–10%.
- For solar: day-ahead σ ~8–12%; intraday ~4–7%. Cloud-passage events can produce 30–50% error spikes for 1–3 hours.
- For consumption (Zhytomyr-style city load): MAPE 2–5% on workdays, 4–8% on weekends, 8–15% on holidays / first hot/cold days of season. The Zhytomyr project's `lab_daily_metrics.mape_pct` and `wmape_pct` fields are exactly this. Cite the project's own metrics for credibility numbers.

**Imbalance settlement.** UA imbalance market under ОРЕЕ rules: two prices per imbalance period (system-positive and system-negative). Asset/BRP penalized for being on wrong side. Synthetic data should compute `imbalance_mwh = forecast - actual` per hour per BRP-aggregated unit and apply a price differential 1.1–1.4× РДН.

**RES curtailment (very UA-specific, very high credibility signal).**
- Укренерго imposed substantial RES curtailment 2024–2025 due to grid congestion + war-damaged transmission. Solar and wind curtailment exceeded historical norms. Quantification: see [Укренерго monthly operational reports](https://ua.energy/electric-power-industry/), [DiXi Group energy-map](https://www.energy-map.info/), [KSE Institute Ukraine electricity market reports](https://kse.ua/).
- Typical signature: **15–30 min to several hours of `status='curtailed_by_TSO'`** with `active_power_mw` clamped to a TSO-dispatched setpoint well below available. Most common around midday solar peak when system has surplus, or during forced thermal must-run conflicts.
- Frequency: **1–4 curtailment events per week per RES asset** during congested periods.
- Field on telemetry: `curtailment_cap_mw` — the TSO-imposed limit. `available_power_mw` (uncurtailed, derived from irradiance/wind) minus `active_power_mw` (delivered) = curtailment energy.

**Blackouts / графіки відключень.**
- 2022–2024 martial-law-era schedules ("графіки погодинних відключень") were the operational reality. By 2025 reduced in frequency but still present in winter peak periods.
- Data shape: a separate `outage_schedule` table — `(region, queue_number 1..6, date, hour, planned_outage BOOLEAN)`. Each consumer asset has `outage_queue` attribute. When `outage_schedule.planned_outage=TRUE` for that asset's queue × hour, the asset shows `status='unavailable'` and `active_power_consumed_mw=0`.
- Typical 2024 winter: 8–16 hours/day per queue, rotating. By 2025: 2–8 hours/day in worst weeks, none in good weeks.
- The demo can dramatically increase fidelity by including a `graphik` table and showing the operator a "next 24h outage map" widget.

---

## PART B — Zhytomyr Oblenergo project audit

### B.1 Folder found: **YES, locally**

**Path:** `d:\ВС коде вайбкодинг\Житомир погодинка\`

It's not literally named "zhytomyr" — it's `Житомир погодинка` ("Zhytomyr hourly"). The memory log referenced server path `/opt/zhytomyr` and prod URL `https://zhytomyr.radai-1984.dev`.

Three worktrees exist under `.claude\worktrees\`. Main code in repo root.

### B.2 Tech stack

- **Backend:** FastAPI (Python), psycopg3 raw SQL (no ORM).
- **DB:** PostgreSQL (Supabase-style — RLS policies present in `v11_snapshot_rls_policies.sql`, `v12_auth.sql`).
- **Frontend:** React + Vite + Tailwind (in `frontend/`).
- **ML:** custom ensemble (inv-MAPE weighting) + TimesFM wrapper (`backend/ml/models/timesfm_wrapper.py`).
- **Schema source of truth:** `db/schema.sql` (v0.4) plus migrations `v05..v17` in `db/migrations/`.

### B.3 What entities does Zhytomyr model?

Five table groups, all keyed on `(date DATE, hour SMALLINT 1..24)` — the UA dispatcher convention.

**Group A — input facts (immutable source of truth):**
- `hourly_consumption(date, hour, consumption_kwh, day_of_week, day_type)` — one row per hour. **This is the central time-series object.**
- `hourly_temperature(date, hour, temp_c, source, provider)` — weather (open-meteo).
- `daily_facts(date, day_of_week, day_type, consumption_mwh, temp_avg_c, temp_day_c, temp_night_c, anomaly_flag, anomaly_note)` — daily roll-up.

**Group B — held-out validation:**
- `hourly_validation(...)` — same shape as consumption but isolated for walk-forward.

**Group C — operator vitrine:**
- `daily_vitrine(date, forecast_type ∈ {primary, refined}, consumption_mwh, forecast_mwh, error_mw, error_pct, temp_*, anomaly_flag)` — what the operator sees daily.

**Group D — hourly results:**
- `hourly_errors(date, hour, fact_kwh, forecast_kwh, error_mw, error_pct, ensemble_id)` — heatmap source.
- `model_forecasts(date, hour, model_id, forecast_kwh, ensemble_weight, is_ensemble, forecast_type)` — per-model contribution.

**Group E — developer lab:**
- `model_registry`, `experiments`, `validation_results`, `production_tracking`, `lab_experiments`, `lab_predictions`, `lab_daily_metrics`, `lab_summary_metrics`, `lab_feature_snapshots`, `production_feature_snapshots` — full MLOps audit trail.

**Service:**
- `jobs` (queued/running/done/failed), `app_users` (RBAC: operator/manager/admin), `audit_log` (v14), `operator_adjustments(date, operator_mwh, reason)`.

### B.4 Data fixtures observed

CSV export format (one row per day, 24 hourly columns): see `forecast_zhytomyr_2026-04-14.csv`:
```
Дата;Т°д;Т°н;МВт·год;кВт·год;Г1;Г2;Г3;...;Г24
14.04.2026;14.9;0.2;7167,0;7167024;263604;248638;...;281942
```
Daily total ~7167 МВт·год, hourly range 240–345 МВт·год. **This is city-level load shape — exactly the kind of curve a regional active consumer asset would aggregate to in GECKO VPP.**

### B.5 Relevance to GECKO VPP

Direct re-use:
1. **`(date, hour 1..24)` convention** — adopt it everywhere operators look. This is what UA dispatchers expect.
2. **Day-type classification (`workday`, `weekend`, `holiday`)** — Zhytomyr's `calendar.day_type` should be reused in GECKO for any flex/consumption forecast.
3. **Forecast variants (`primary` vs `refined`)** — GECKO will need the same two-stage forecast: morning day-ahead vs intraday-refined.
4. **Ensemble of models + weights table** — directly applicable to multi-asset portfolio forecasting.
5. **`operator_adjustments` table** — manual override pattern. GECKO operators will absolutely need this for dispatchable assets.
6. **MAPE/WMAPE/bias metrics shape** in `lab_summary_metrics` — re-use field-for-field for VPP forecast accuracy reports.

Where Zhytomyr falls short for VPP needs:
- No asset registry — Zhytomyr models a single aggregated city load. GECKO needs `asset(id, type ∈ {СЕС, ВЕС, ГПУ, УЗЕ, AC}, capacity_mw, location, owner)`.
- No SOC / cycle accounting (no batteries).
- No market price / РДН integration — Zhytomyr is volume forecasting only, not revenue/dispatch optimisation.
- No event/activation log — needed for ancillary services in VPP.
- No imbalance settlement view — Zhytomyr models forecast error but doesn't price it.

### B.6 Files an architect should read first

Absolute paths, in priority order:
1. `d:\ВС коде вайбкодинг\Житомир погодинка\db\schema.sql`
2. `d:\ВС коде вайбкодинг\Житомир погодинка\db\migrations\v06_lab_tables.sql`
3. `d:\ВС коде вайбкодинг\Житомир погодинка\db\migrations\v09_control_loop.sql`
4. `d:\ВС коде вайбкодинг\Житомир погодинка\backend\api\routers\consumption.py`
5. `d:\ВС коде вайбкодинг\Житомир погодинка\backend\api\routers\forecasts.py`
6. `d:\ВС коде вайбкодинг\Житомир погодинка\backend\db\queries.py`
7. `d:\ВС коде вайбкодинг\Житомир погодинка\forecast_zhytomyr_2026-04-14.csv` (real export format)

---

## PART C — Sources & references

**For solar resource (СЕС):**
- [Global Solar Atlas — Ukraine country page](https://globalsolaratlas.info/map?c=49.0,32.0,7&r=UKR) — authoritative GHI / DNI / yield estimates.
- [NREL System Advisor Model documentation](https://sam.nrel.gov/) — for module temp / clipping model defaults.
- [IRENA Renewable Energy Statistics 2024 — Ukraine country chapter](https://www.irena.org/Publications/2024/Mar/Renewable-capacity-statistics-2024).

**For wind resource (ВЕС):**
- [Global Wind Atlas — Ukraine](https://globalwindatlas.info/en/area/Ukraine).
- [IRENA Ukraine REMAP — Renewable Energy Roadmap](https://www.irena.org/publications).
- DTEK public statements re: Tyligulska wind farm CF (search press releases at [dtek.com](https://dtek.com/)).

**For gas generation & market:**
- [Naftogaz commercial gas tariffs](https://www.naftogaz.com/) — industrial gas price.
- [ExPro Consulting UA energy reports](https://expro.com.ua/) — wholesale price commentary.
- Manufacturer datasheets (Jenbacher J920, MWM TCG 2032, Wärtsilä 34SG) for heat rate / ramp specs.

**For market structure (РДН, БР, РВЧ):**
- [Market Operator (ОРЕЕ / Market Operator LLC)](https://www.oree.com.ua/) — РДН price history.
- [Укренерго ancillary services pages](https://ua.energy/) — РВЧ, БР, FCR definitions and activation reports.
- [НКРЕКП resolutions database](https://www.nerc.gov.ua/) — tariff and ancillary service regulations.

**For UA system operations, curtailment, blackouts:**
- [Укренерго official operational reports](https://ua.energy/electric-power-industry/) — daily / monthly operational data, including outage schedules.
- [DiXi Group energy-map.info](https://www.energy-map.info/) — analytical dashboards.
- [KSE Institute Ukraine electricity market reports](https://kse.ua/).
- [Razumkov Centre energy briefs](https://razumkov.org.ua/).

**For storage / BESS market:**
- [DTEK press on Zaporizhzhia BESS project](https://dtek.com/).
- [IEA Battery Storage country snapshots](https://www.iea.org/reports).

**For Zhytomyr-specific load shape:**
- The user's own `d:\ВС коде вайбкодинг\Житомир погодинка\` CSVs are the *most credible* reference — real city-level hourly consumption Mar–May 2026.

---

## Caveats — explicit "I don't know" list

- **Curtailment frequency numbers for 2024-2025 are claims, not verified figures.** The 1–4 events/week range comes from general industry awareness; the architect must verify against Укренерго's actual monthly RES integration reports before locking in.
- **UA industrial gas price 25–35 UAH/м³** is a 2024-mid estimate; this fluctuates a lot quarter-to-quarter post-war. Verify before locking dispatch break-even.
- **Tyligulska wind CF ~35%** comes from public DTEK statements; not independently audited here.
- **РДН price cap moved to 9000 UAH** — this needs verification against current НКРЕКП resolutions (year-of-record matters; cap changed multiple times since 2022).
- **Зайнятий (occupied) regions:** Kherson and parts of Zaporizhzhia listed above as "best wind sites" — the demo should use *currently controlled* territory only (south Mykolayiv, southern Odesa, west Dnipropetrovsk for wind) to stay credible.

If GECKO is using *synthetic* data anyway, none of these need to be exact. They just need to be *internally consistent* and *not laughably wrong* to a UA energy professional.
