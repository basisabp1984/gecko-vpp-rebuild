# BRIEF_AMENDMENTS — proposed updates to PRODUCT_BRIEF v0.3 → v0.4

**Parent:** `RESEARCH_FINDINGS.md` v0.1
**Target:** `../PRODUCT_BRIEF.md` (currently v0.3, frozen 2026-05-23)
**Authority:** these are **proposed** changes. PRODUCT_BRIEF.md is the source of truth and only the user can approve its un-freezing.

This file lists every change research recommends to v0.3 of the brief. Each amendment cites its evidence in RESEARCH_FINDINGS.md (RF) and the source platform.

---

## A. Mandatory amendments (research surfaces a real gap in v0.3)

### A.1 — Site map: persona-split into separate URL surfaces

**v0.3 §10 says:** flat list of 9 surfaces under one root.

**Proposed v0.4:** add §10.bis describing the role-stratified hierarchy:
- `/` — welcome / persona picker
- `/producer/` — hero persona = виробник; contains the 9 surfaces
- `/c-i/` — Segment A surface, reuses the 9-surface skeleton with C&I-tuned data and labels
- `/storage/` — Segment C surface, УЗЕ-first variant of the 9 surfaces
- `/developer/` — public dev portal (SDK + API docs + webhooks)
- `/admin/` — cross-tenant operator view (Engage / Operate / Analyze sub-modules)

**Evidence:** RF §2.2 (every mature platform has ≥2 persona surfaces); RF §3 row A1 (gridX, Next Kraftwerke, sonnen).

**Impact:** acceptance criterion §11.4 ("all 9 surfaces exist") is now scoped to `/producer/*`. Total page count rises but each non-producer surface is a thin variant.

---

### A.2 — Theme: dark default + light toggle as first-class

**v0.3 §5 says:** Theme = Dark (single value).

**Proposed v0.4:** Theme system = dark primary (per client PDF) + light secondary (accessibility + UA-professional muscle memory). Both shipped, switcher in topbar, persistent per user.

**Evidence:** RF §1 conclusion 5; RF §7 design system table; RF §3 row A13.
- Client PDF brand is dark teal (source of truth for primary).
- OREE and most UA regulator portals ship light + dark accessibility toggle as a regulatory expectation for state portals — UA pro users have muscle memory for both.
- EU VPPs default light → light option is professionally credible.

**Impact:** acceptance criterion §11.1 expands from "dark theme" to "dark default + working light toggle, both fully designed, no half-baked light-mode quirks".

---

### A.3 — Public developer portal as a first-class surface

**v0.3 §11.15** mentions SDK but does NOT specify a dev portal surface in the IA.

**Proposed v0.4:** add to §10 / §10.bis a `/developer/` surface with:
- Auto-generated OpenAPI 3.1 spec from FastAPI backend
- Swagger / Scalar UI at `/developer/api/explorer`
- TypeScript SDK quickstart + reference at `/developer/sdk-ts/`
- Python SDK quickstart + reference at `/developer/sdk-py/`
- Webhook subscription docs at `/developer/webhooks/`

**Evidence:** RF §5 D5 — only gridX has any kind of API and it's gated. A public dev portal is category-defining.

**Impact:** acceptance §11.15 SDK becomes more specific. Add new criterion §11.19: dev portal `/developer/` exists and is publicly browsable.

---

### A.4 — AI agent per persona (4 total instead of 2 generic)

**v0.3 §11.16** says "minimum 2 text agents (e.g. Market Analyst for producer, Storage Coach for УЗЕ-власник)".

**Proposed v0.4:** 4 agents total — Диспетчерський аналітик + Ринковий аналітик for producer; Енергетичний радник for C&I; Тренер по батареях for УЗЕ. Each lives in the matching persona surface; one shared underlying API + classifier with per-persona system prompts.

**Evidence:** RF §8 — research confirms zero competitors have visible AI agents; expanding from 2 to 4 with persona-aware system prompts is cheap because the underlying engine is one classifier with prompt variants.

**Impact:** acceptance §11.16 wording updated; implementation cost negligible (same engine, more prompt templates).

---

### A.5 — UA-specific workflows missing from v0.3

Research surfaced four UA-specific workflows that v0.3 implies but does NOT lock in as acceptance criteria:

1. **Forecast-submission workflow** ("Подача прогнозу") for consumption (C&I) and for production (RES producers). UA regulatory obligation per ГП and per energy supply contracts.
2. **KEP / Дія.Підпис document signing stub** on any document the product emits (settlement statements, reports, contracts).
3. **ENTSO-E code semantics in the data model** (BZN, MTU, A01-A99). Even with synthetic data, the internal data model must speak ENTSO-E.
4. **Single pane over fragmented UA market apps** (visual reference to РДН + ВДР + БР + ДП settlements in one view) — UEEX fragments these, GECKO unifies.

**Proposed v0.4:** add to §11 new criteria §11.20 — §11.23 covering these four.

**Evidence:** RF §3 rows A16, A17, A21; RF §5 D9; tier 1 findings.

**Impact:** more work in `/producer/prognozy/` and `/zvity/`; data model rev needed.

---

### A.6 — Acceptance §11.3 (architecture diagram render) needs sharper wording

**v0.3 §11.3 says:** "slide-7 diagram is rendered as a real interactive component somewhere".

**Proposed v0.4 wording:** "slide-7 architecture diagram from the client PDF is rendered as an interactive React component on `/` (welcome / hero) AND optionally embedded on `/admin/engage/` for the cross-tenant operator's mental model of the platform topology. Component animates the connections (lines between nodes) on hover; clicking a node navigates to the matching surface."

**Evidence:** RF §1 conclusion 1 (UA market lacks a category-creator narrative — slide 7 IS that narrative) + sonnen/gridX precedent for animated diagrams.

**Impact:** clearer build scope; one shared component used in 1-2 places.

---

## B. Optional / soft amendments (research suggests, but v0.3 does not strictly contradict)

### B.1 — Add command palette `Cmd+K` to acceptance criteria

**v0.3:** mentions React Portals overlays but does not specify command palette.

**Proposed v0.4 addition to §11:** "Command palette via `Cmd+K` (Linear-style) on all operator-tier surfaces (`/producer/`, `/c-i/`, `/storage/`, `/admin/`). Supports navigation + action search."

**Evidence:** RF §5 D6 — zero hits in energy segment.

**Decision required:** confirm or defer to v3.

---

### B.2 — Scenario cards inspired by sonnen Storm Protection

**v0.3:** does not mention scenario cards.

**Proposed v0.4 addition:** scenario cards on `/c-i/` and `/storage/` home — at least 3 scenarios:
- "Захист від відключення" (Blackout protection — UA-specific given war-era reliability)
- "Захист від небалансу" (Imbalance defence)
- "Арбітражна можливість" (Arbitrage opportunity)

**Evidence:** RF §3 row A7 — sonnen scenario cards are an effective behavioural-design pattern.

**Decision required:** include in v2 or defer.

---

### B.3 — OBIS-coded tariff zones in consumption charts

**v0.3:** does not mention.

**Proposed v0.4:** consumption charts on `/c-i/` and `/producer/` (for self-consumption) display OBIS-coded zonal split (1.8.1 / 1.8.2 / 1.8.3) where the dataset has multi-tariff customers.

**Evidence:** RF §3 row A15 — Polish DSO standard.

**Decision required:** include if synthetic dataset supports multi-tariff modelling.

---

### B.4 — Trusted-person invite ("Запросити колегу")

**v0.3:** mock tenancy implicit; no explicit invite flow.

**Proposed v0.4 addition to `/nalashtuvannya/`:** trusted-person invite — operator can grant read or read-write to another email within the same tenant. UI only (no real email sent in v2).

**Evidence:** RF §3 row A19 — PGE eBOK pattern.

**Decision required:** include or defer.

---

### B.5 — Maintenance/deregistration declaration

**v0.3:** does not mention.

**Proposed v0.4:** producer can declare planned downtime windows on `/producer/aktyvy/[id]/`; affects forecast and revenue projections (synthetic numbers update accordingly).

**Evidence:** RF §3 row A22 — Next Kraftwerke "Abmeldefunktion".

**Decision required:** include in v2 or defer.

---

### B.6 — ESG / carbon-credit sub-tab in /zvity/

**v0.3 §11.21 acceptance criterion is the rebuild's CO₂ avoided KPI** but does not specify an ESG/carbon tab.

**Proposed v0.4 addition to `/producer/zvity/`:** ESG sub-tab showing CO₂ avoided per asset, scope-2 totals, carbon-credit potential (Restart Energy / Reo.pl pattern).

**Evidence:** RF §3 row A23.

**Decision required:** include or defer.

---

## C. No-changes (v0.3 acceptance criteria validated by research, no edits needed)

- v0.3 §1 product framing — confirmed by RF §1 (category-creator framing).
- v0.3 §2 three segments — confirmed by every tier's segmentation analysis.
- v0.3 §3 hero persona = виробник — research adds nuance (gridX-style separate surfaces) but does NOT change which is the hero.
- v0.3 §4 market context (Ukrainian-market-native) — confirmed by RF §2.5 theme analysis + RF §3 rows A14, A16, A17, A20, A21.
- v0.3 §5 brand palette — confirmed (with amendment A.2 about light toggle).
- v0.3 §6 sub-system decomposition — confirmed.
- v0.3 §7 architecture map — confirmed; amendment A.6 makes the rendering more concrete.
- v0.3 §8 asset taxonomy — confirmed.
- v0.3 §9 engagement workflow → surfaces — confirmed.
- v0.3 §11.17 voice agent — confirmed by RF §8.
- v0.3 §12 out-of-scope — research adds two more items (mobile-native to v3; blockchain settlement to "never for v2"); no removal.
- v0.3 §13 risks — research validates all existing risks; adds none.

---

## D. New open questions surfaced by research

Listed in `RESEARCH_FINDINGS.md` §11 as NQ1–NQ6. Reproduced here as the "to be answered" gate before PRODUCT_BRIEF is unfrozen for v0.4:

- **NQ1** — Confirm separate URL surfaces per persona vs persona-mode toggle. (Recommended: separate URL surfaces.)
- **NQ2** — Confirm dark default + light toggle, both first-class. (Recommended: yes.)
- **NQ3** — PWA-only mobile or PWA + roadmap mention of native? (Recommended: PWA-only + roadmap mention.)
- **NQ4** — KEP integration: real or stub? (Recommended: stub.)
- **NQ5** — Public dev portal at `/developer/` visible to demo visitors? (Recommended: yes — it IS the differentiator.)
- **NQ6** — Hero `/` page: tenant-aware redirect or always-show persona picker? (Recommended: always show picker + tenant-switcher in chrome.)

---

## E. Recommended next steps

1. **User reviews this file + RESEARCH_FINDINGS.md.**
2. **User answers NQ1–NQ6** (above) and approves/rejects amendments §A.1–A.6 (mandatory) and §B.1–B.6 (optional).
3. **Brief is unfrozen, v0.4 is written**, incorporating accepted amendments.
4. **Brief is re-frozen** at v0.4.
5. **Phase 3 (Architecture) starts.**

No code changes until step 5.

---

## Version history

- **v0.2 — 2026-05-23 (closed)** — user approved ALL 6 mandatory (A.1–A.6) and ALL 6 optional (B.1–B.6) amendments. User decision overrode initial recommendation on A.2: theme = **LIGHT primary + DARK as accessibility toggle** (not dark primary). NQ1–NQ6 answered: NQ1 = separate URL surfaces; NQ2 = light primary + dark accessibility toggle (user override); NQ3 = PWA-only + v3 roadmap mention; NQ4 = КЕП stub; NQ5 = dev portal public to everyone; NQ6 = always show persona picker on hero `/`. PRODUCT_BRIEF rewritten to v0.4 incorporating all of the above. **This file is now closed** — no further changes expected; future amendments go to a new file referencing v0.4 of PRODUCT_BRIEF.
- **v0.1 — 2026-05-23** — initial draft. 6 mandatory + 6 optional amendments proposed. 6 new open questions. Awaits user review.
