# RESEARCH_PLAN — Phase 2.0 / Visual & UX research of VPP / EMS platforms

**Status:** draft v0.1 · awaits user confirmation to start subagent runs
**Parent:** `PRODUCT_BRIEF.md` (v0.2, frozen 2026-05-23)
**Phase:** 2 — Finding the solution (bible `1.1` §2)
**Output gate:** `RESEARCH_FINDINGS.md` + `DESIGN_INSPIRATION.md` must exist and be user-approved before Phase 3 (Architecture) begins. This is locked in PRODUCT_BRIEF acceptance criterion §11.18.

---

## 1. Goal of this research (precise, narrow)

> **Find out how the frontend of modern VPP / EMS / energy-trading SaaS platforms is actually constructed — through the eyes of an experienced frontend tech lead.**

NOT goals (avoid scope creep):

- ❌ "Compare which platform is best" — irrelevant; we are not picking a vendor.
- ❌ "Find good vs bad features" — too subjective and not actionable for our build.
- ❌ "Benchmark performance" — pointless on synthetic data.
- ❌ "Decide our pricing / business model" — separate work, not research-driven.

DO goals (will land in our build):

- ✅ Inventory the **information architecture** patterns: which pages exist, in what order, what's the home screen.
- ✅ Inventory the **visualisation patterns**: what charts, how they are composed, how the data density per screen is managed.
- ✅ Inventory the **interaction patterns**: drawers, modals, command palettes, sticky sidebars, multi-asset selectors, time-window scrubbers.
- ✅ Inventory the **theme / brand conventions** in this product category: dark vs light? saturated vs muted? typography defaults?
- ✅ Inventory **gaps**: features other platforms don't have which we will add — React Portals overlays, AI text agents, voice agent, public SDK.
- ✅ Save **direct visual references** (screenshots / annotated screenshots / Loom-style URLs) into `DESIGN_INSPIRATION.md` so the Phase-3 designer has concrete material to reference.

---

## 2. Subjects of research (prioritised)

### Tier 1 — Ukrainian market (priority 1, lowest information density expected)

Ukraine has РДН/ВДР/БР since 2019, but VPP-class platforms aimed at SME aggregation barely exist publicly. Realistic find:

- Possibly **DTEK Energy / DTEK Trading** has internal tools but no public UI.
- Possibly **YASNO** / Centrenergo have trading dashboards.
- Possibly **ECOMETRICA** or other Ukrainian energy-software startups.
- Marketplaces / brokers — СОП "Оператор ринку" has a public market data area; check its UX (it's the regulator's portal, not a VPP, but it sets terminology baseline).

**Expectation:** Tier 1 will produce **terminology and visual language only**, not full reference UIs. That's still useful — Ukrainian-energy idiom comes from here.

### Tier 2 — Polish + nearby CEE (priority 2)

Polish market is similar maturity, more developed VPP segment. Targets:

- **Enspirion** (PSE-owned, balancing services aggregator) — public site, possibly portal screenshots in their press releases.
- **TAURON Polska Energia** — large utility with VPP-like products.
- **PGE / Polenergia / ZE PAK** — vertical integrated, may have customer portals.
- **Innogy Polska** (now part of E.ON) — VPP for prosumers.
- **Reo.pl / Re-Source** — Polish renewable aggregators.

**Expectation:** Tier 2 will give a few real customer-portal screenshots and a sense of how a Polish energy product onboards an SME owner.

### Tier 3 — EU benchmarks (priority 3, highest information density expected)

These are the global UX references for VPP/EMS. We want depth here.

- **Next Kraftwerke** (DE) — the canonical VPP aggregator; their NEMOCS customer portal is widely-screenshot-online.
- **sonnen** (DE) — residential battery + community VPP; consumer-grade UX as an upper bound.
- **Tesla Autobidder** (global) — institutional battery trading platform; rare public screenshots but case studies and press images exist.
- **Centrica / British Gas Business** (UK) — DSR + VPP for C&I; public product pages.
- **Octopus Energy KrakenFlex** (UK) — fastest-moving UX team in the segment; Twitter/LinkedIn often has product screenshots.
- **ZEN / Re-leased / Energy21 / Stoam** (NL) — Dutch energy-tech with strong UX.
- **GridX** (DE, B2B EMS infra) — explicit B2B platform with public docs.
- **Enbala / Generac Grid Services** (US/CA) — DERMS platforms.
- **AutoGrid (Schneider)** (US) — enterprise DERMS, sometimes shown at conferences.

**Expectation:** Tier 3 produces the bulk of reference patterns. Cherry-pick 5-7 of these for deep inspection.

### Tier 4 — Adjacent SaaS for inspiration (priority 4, optional)

If the energy-specific platforms aren't visually inspiring, look adjacent:

- **Linear** (project mgmt) — exemplar of dark-theme command palette + keyboard-driven UX.
- **Stripe Dashboard** — exemplar of financial reporting UX (P&L, balance, KPI tiles).
- **Datadog / Grafana** — exemplar of time-series-heavy dashboards.
- **Vercel Dashboard** — exemplar of multi-tenant scoped workspace.
- **OpenAI / Anthropic Console** — exemplar of API + SDK product layout.

These contribute **only** to the visual / interaction language, not to product-specific patterns.

---

## 3. What each subagent must extract

A strict report template — subagent must fill all fields, leaving "NOT FOUND" where applicable, never inventing content:

```
## Platform: <name>
- **Region:** <country>
- **Customer segment they target:** <C&I / producers / storage / utility-scale / residential / B2B SaaS>
- **Public product URL(s):** <list>
- **Pricing model:** <free / freemium / enterprise / NOT FOUND>
- **Screenshots / video / demo URLs:** <list with one-line description each>
- **Stated tech stack (from job ads or docs):** <list / NOT FOUND>

### Information architecture
- **Pages observed:** <list of menu items / routes — exact labels in source language>
- **Home screen layout:** <what's the first thing shown after login — describe in 1-3 sentences>
- **Multi-tenancy / org switcher:** <yes/no/NOT FOUND, location in UI>

### Visualisation patterns
- **Chart types observed:** <line / area / stacked bar / donut / candlestick / SOC curve / heat map / etc.>
- **Time-window controls:** <day picker / range slider / sticky 24h / NOT FOUND>
- **Data density per screen:** <how many KPI tiles, charts, tables on the main view>

### Interaction patterns
- **Overlays / drawers / modals:** <list with purpose>
- **Command palette:** <yes/no, Cmd+K or other>
- **Floating helpers / chat:** <yes/no, what for>
- **Keyboard shortcuts surfaced:** <yes/no/list>

### Theme & visual language
- **Theme:** <dark/light/both>
- **Brand accent colour:** <name + hex if visible>
- **Typography:** <serif/sans/mono, weight discipline>
- **Density:** <compact/comfortable/spacious>

### AI / agent features
- **Text AI assistant:** <yes/no, what it does>
- **Voice assistant:** <yes/no — expected NO across the board>
- **Recommendations / insight cards:** <yes/no, examples>

### SDK / public API
- **Public API documented:** <yes/no, URL>
- **SDK in any language:** <yes/no, languages>
- **Webhooks / event streams:** <yes/no>

### Things this platform does NOT have (vs our brief)
- <list — these are differentiators we keep>

### Things this platform has that our v1 missed
- <list — these are gaps we should consider adding>

### Frontend-tech-lead's-eye verdict (1 paragraph)
<would a senior FE tech lead recognise this as a serious modern product? what tells them so? what tells them otherwise?>
```

This template is the contract every subagent operates under.

---

## 4. Method

### Subagent topology (parallel where independent — Constitution P14)

Three subagents in parallel, one tier each:

- **Subagent UA** — Tier 1 (Ukraine). Tool budget: WebSearch + WebFetch. Time budget: ~10 min. Expected report: 2-4 platforms or "no public Ukrainian VPP-class portal found, here's what exists adjacent" with terminology references.
- **Subagent PL** — Tier 2 (Poland + nearby CEE). Same tools. ~12 min. Expected: 3-5 platforms with at least 2 screenshot URLs each.
- **Subagent EU** — Tier 3 (EU benchmarks). Same tools. ~15-20 min. Expected: 5-7 platforms with depth, screenshots, identified UX patterns we will adopt.

After all three return:

- **Subagent Synthesis** — sequential after the three above. Reads their outputs, deduplicates patterns, produces:
  - `RESEARCH_FINDINGS.md` — the consolidated answer to "how is the frontend of modern VPP platforms actually constructed".
  - `DESIGN_INSPIRATION.md` — annotated list of screenshot URLs with what we are borrowing from each.
  - `BRIEF_AMENDMENTS.md` — proposed additions to `PRODUCT_BRIEF.md` based on what we found (only if material).

### Quality checks per subagent

- No invented platforms — every claim is sourced (URL).
- No invented features — every UX pattern is observed in a screenshot or product doc, not inferred.
- "NOT FOUND" is a valid value — Constitution P8 (verify, don't trust).
- Each subagent reports its own confidence level on the platforms it covered.

### What subagents are NOT allowed to do

- ❌ Make product recommendations for GECKO VPP — only Synthesis does that.
- ❌ Decide our architecture — that's Phase 3.
- ❌ Edit `PRODUCT_BRIEF.md` directly — they propose via `BRIEF_AMENDMENTS.md`.
- ❌ Write code — research-only.

---

## 5. Success criteria (gate for Phase 3 to start)

This research is **done** if and only if:

1. **`RESEARCH_FINDINGS.md` exists** and lists ≥ 8 platforms across Tier 1+2+3 with the §3 template filled.
2. **Information-architecture patterns** are summarised as a "common shape" (what every serious VPP platform has) + "variations" (where they diverge).
3. **Visualisation patterns** are summarised — for each chart kind GECKO needs (forecast, SOC, market, dispatch, KPI tiles) at least one reference platform is cited that does it well.
4. **Interaction patterns** are summarised — which patterns are common, which are differentiators, where React Portals would or would not show up.
5. **`DESIGN_INSPIRATION.md` exists** and has ≥ 15 screenshot URLs grouped by pattern, with one-line annotations explaining what we borrow.
6. **Gap list** is explicit — what other platforms DON'T have that we add (SDK, voice agent, AI text agents, our portal overlays).
7. **`BRIEF_AMENDMENTS.md` exists** (even if empty — "no amendments needed" is a valid conclusion).
8. **User approval** — Andrii reads `RESEARCH_FINDINGS.md` and either confirms or asks for re-runs of specific tiers.

If any of these is missing, Phase 3 does NOT start.

---

## 6. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Subagents hallucinate platforms / features that don't exist | Strict "URL or NOT FOUND" rule in §3 template; Synthesis cross-checks |
| Tier 1 (Ukraine) returns near-zero — research feels thin | Acceptable; the goal of Tier 1 is **terminology**, not UX patterns; the gap is the finding |
| Subagent reports get long and pollute Synthesis context | Each subagent emits a structured report ≤ 3000 words; Synthesis reads them as files, not in-context |
| We over-borrow — Phase 3 becomes "copy of Next Kraftwerke" | `DESIGN_INSPIRATION.md` is **references**, not blueprints; Phase 3 architect picks consciously |
| Screenshots URLs rot before we use them | Save key screenshots to `phase-2-solution/screenshots/` as local files where copyright permits (low-res, attribution included) |
| Research delays the project | Hard time cap: total research budget = 45 min wallclock across subagents in parallel; if not done, ship with what we have and amend later |

---

## 7. Estimated effort

- Subagent UA: ~10 min wallclock
- Subagent PL: ~12 min wallclock
- Subagent EU: ~15-20 min wallclock
- Subagent Synthesis: ~10 min wallclock (sequential, reads all three)
- **Total wallclock with parallelism:** ~25-30 min
- **Tokens estimated:** ~200-400k across all subagents (research-heavy, mostly read)

This is acceptable; matches Constitution P9 — heavy process scaled to a task of this importance.

---

## 8. What I will NOT do without user confirmation

- Will not start the subagent runs until user gives explicit go-ahead on this RESEARCH_PLAN.
- Will not modify `PRODUCT_BRIEF.md` based on research findings without showing `BRIEF_AMENDMENTS.md` first.
- Will not begin Phase 3 (Architecture) until §5 gate passes AND user approves.

---

## 9. What I have already done in preparation

- `gecko-vpp-rebuild/phase-2-solution/` folder created.
- This plan written and saved.
- Subagent contracts (the §3 report template) written and ready to be passed to each subagent.
- No external calls made yet — awaiting user confirmation per §8.

---

## Version history

- **v0.1 — 2026-05-23** — initial draft. Awaits user "go" before subagent runs start.
