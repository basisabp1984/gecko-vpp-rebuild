# FRONTEND_INSTRUCTIONS — GECKO VPP rebuild

**Status:** v0.1 · Stage 3 (Frontend specialist lead) · 2026-05-23
**Parent docs:** `ARCHITECTURE.md` v0.1 (§2 repo, §4 API, §5 frontend, §10 testing, §11 FMEA, §12 phases, §14.3 hand-off checklist) · `PRODUCT_BRIEF.md` v0.4 (§5 brand, §10 site map, §11 acceptance criteria) · `HIGH_LEVEL_ARCHITECTURE.md` (D7, D15, R10) · `DESIGN_INSPIRATION.md` (29 references)
**Audience:** the implementing agent (or human) building `apps/web/` mechanically.
**Length target:** 10–12 pages.

This document tells you exactly what to build, in what order, with which props, calling which endpoints, satisfying which acceptance criterion. Where the architect locked a decision, it is restated here as **LOCKED**. Where the architect punted, it is restated as **DECIDED HERE** with rationale. Where the implementer must choose, it is marked **IMPLEMENTER**.

---

## 0. Goal

Build a Next.js 16 (App Router, React 19, TypeScript strict) frontend at `apps/web/` that implements every surface from `PRODUCT_BRIEF.md` §10 over the FastAPI endpoints defined in `ARCHITECTURE.md` §4. Single component tree skinned by a **CSS-variable design-token system** with light theme primary + dark theme accessibility toggle. Persona-stratified URLs (`/`, `/producer/*`, `/c-i/*`, `/storage/*`, `/developer/*`, `/admin/*`). Ukrainian UI throughout. Deploy target: `gecko.radai-1984.dev` on Vercel.

---

## 1. Success criteria (measurable checklist)

These are gates the implementing agent must pass before declaring the frontend done. Cite the acceptance-criterion ID from `PRODUCT_BRIEF.md` §11.

- [ ] **§11.1 brand + both themes:** every persona surface renders professionally in both light and dark. Theme toggle in topbar persists via `localStorage` and survives navigation + cold reload (no flash of wrong theme).
- [ ] **§11.2 tenancy:** topbar tenant switcher swaps data without full page reload (uses Next.js router refresh, not `window.location`).
- [ ] **§11.3 architecture diagram:** the slide-7 hub-and-spoke diagram on `/` is an interactive React+SVG component — hover animates the adjacent edges; click on a node routes to the matching persona/feature URL.
- [ ] **§11.4 all 9 producer surfaces** return HTTP 200 in Playwright smoke, both themes, zero console errors.
- [ ] **§11.5 persona variants:** `/c-i/*` and `/storage/*` ship the 5-surface floor (home, aktyvy, prognozy [or uze for storage], rynok, zvity). Locked at 5 per `ARCHITECTURE.md` §5.3.4.
- [ ] **§11.6 admin:** `/admin/engage/`, `/admin/operate/`, `/admin/analyze/` exist and pull cross-tenant data via `X-Admin: true`.
- [ ] **§11.7 command palette:** `Ctrl+K` / `Cmd+K` opens on every persona surface and `/admin/*`; `Enter` fires the highlighted action (mitigates FMEA F09).
- [ ] **§11.9 API-first:** no page imports any synthetic data directly; every fetch goes through Next.js `/api/*` route handlers which proxy to FastAPI.
- [ ] **§11.20 КЕП stub:** every `<KEPSignBadge>` renders the `DEMO` watermark (mitigates FMEA F13).
- [ ] **§11.24 smoke pass:** the Playwright suite in `apps/web/tests/smoke.spec.ts` is green on Vercel preview.
- [ ] **§11.25 production-fidelity feel:** `/` LCP ≤ 1.5s on cold cache; `/producer/`, `/c-i/`, `/storage/` (home) ≤ 1.5s; denser surfaces (`/producer/aktyvy/`, `/producer/rynok/`, `/developer/api/explorer`, `/admin/*`) ≤ 2.0s. Lighthouse CI runs warn-only per §5.7.
- [ ] **§11.22 CO₂ KPI** present on `/producer/`, `/c-i/`, `/storage/` home dashboards.
- [ ] **All Ukrainian copy.** No English fallback strings anywhere in user-visible UI (developer portal Markdown bodies are an exception — see §3.5 of this doc).
- [ ] **No literal hex outside `tokens.css`.** ESLint custom rule passes; CI blocks merge on violation.
- [ ] **All charts** read colours from CSS vars `--chart-c1` … `--chart-c5`.
- [ ] **Accessibility:** keyboard-navigable, ARIA labels on icon-only buttons, visible focus rings, theme toggle accessible via `Shift+T`, command palette via `Ctrl+K`/`Cmd+K`, axe-core passes with zero serious violations on home pages of all four personas.

---

## 2. Tools / stack (with versions, locked)

| Tool | Version | Why |
|---|---|---|
| Next.js | **16.x** | App Router, React 19, server components default. Locked by architect (§5, HLA D7). |
| React | **19.x** | Comes with Next 16. |
| TypeScript | **5.x strict** | Architect §1.1, §5. |
| Tailwind CSS | **3.x** | **NOT 4** — stability. Locked here. Tailwind reads CSS vars via `theme.extend.colors['color-bg-page']: 'var(--color-bg-page)'`. |
| Recharts | **2.x** | Locked by architect (§5.2.5). Plays well with CSS-var inheritance + SSR. |
| @tanstack/react-query | **5.x** | Server state. Locked §5.4. |
| Zustand | **5.x** | Client-only state (theme/palette/tenant optimistic UI). Locked §5.4. |
| cmdk | **1.x** | Command palette per architect §5.2.10. |
| Framer Motion | **11.x** | Slide-7 diagram hover animation (HLA D15, R10). Dynamically imported. |
| lucide-react | **0.x** | Icon set. Tree-shakable. |
| @scalar/api-reference-react | **latest stable** | OpenAPI explorer at `/developer/api/explorer` (§5.2.12). Fallback: redoc-cli static export if Scalar breaks (see §9 branching). |
| openapi-typescript | **6.x** | Generates `types/api.ts` from `packages/openapi/openapi.json`. |
| vitest + @testing-library/react | latest | Unit tests (§7.2 of this doc). |
| @playwright/test | latest | Smoke (§7.1 of this doc). |
| ESLint + custom no-hex rule | — | Token enforcement (§4 of this doc). |
| @axe-core/playwright | latest | Accessibility assertions inside smoke. |
| Node | **20.x** | `.nvmrc` already pinned in repo root (`ARCHITECTURE.md` §2). |
| pnpm | **9.x** | Workspace root (`pnpm-workspace.yaml`). |

**Explicitly forbidden:**
- `@vercel/analytics@2.x` (FMEA F04, memory `project_vercel_analytics_next16_bug`). If analytics required, pin `@vercel/analytics@~1.x` or omit.
- Redux / MobX / Recoil (Zustand only).
- Tailwind 4 (3.x for stability with `next@16`).
- styled-components / Emotion (Tailwind + CSS vars only).
- next-intl (overkill — we ship a simple `lib/i18n/uk.json` dict + a `<T id>` helper).

---

## 3. Repo layout for `apps/web/`

The Stage-2 architect specified this tree at `ARCHITECTURE.md` §2. Recreate it verbatim. Below is the same tree with file-creation order columns (Phase a/b/c/d/e as defined in §5 of this doc) and the §11.x criterion each file services.

```
apps/web/
├── app/
│   ├── layout.tsx                          [a-1 — theme bootstrap, AppShell mount]
│   ├── page.tsx                            [b-7 — hero / persona picker]   §11.3
│   ├── loading.tsx                         [a-1]
│   ├── error.tsx                           [a-1]
│   ├── not-found.tsx                       [a-1]
│   ├── providers.tsx                       [a-1 — TanStack QueryClient, theme]
│   ├── globals.css                         [a-1 — Tailwind directives + token import]
│   │
│   ├── producer/
│   │   ├── layout.tsx                      [b-7  — persona-aware Sidebar]
│   │   ├── page.tsx                        [b-8  — Результати]            §11.4
│   │   ├── aktyvy/
│   │   │   ├── page.tsx                    [b-9]                            §11.4
│   │   │   └── [id]/page.tsx               [b-9 — asset detail w/ KEP, downtime] §11.30
│   │   ├── prognozy/page.tsx               [b-10]                           §11.19
│   │   ├── dyspetcheryzatsiya/page.tsx     [b-11]                           §11.14
│   │   ├── rynok/page.tsx                  [b-12]                           §11.21
│   │   ├── uze/page.tsx                    [b-13]                           §11.4
│   │   ├── spovishchennya/page.tsx         [b-14]
│   │   ├── zvity/page.tsx                  [b-15]                           §11.20 §11.31
│   │   └── nalashtuvannya/page.tsx         [b-16]                           §11.23 §11.29
│   │
│   ├── c-i/
│   │   ├── layout.tsx                      [c-17]
│   │   ├── page.tsx                        [c-17 — w/ ScenarioCards]        §11.27
│   │   ├── aktyvy/page.tsx                 [c-17]
│   │   ├── prognozy/page.tsx               [c-17 — consumption forecast]    §11.19
│   │   ├── rynok/page.tsx                  [c-17]
│   │   └── zvity/page.tsx                  [c-17]
│   │
│   ├── storage/
│   │   ├── layout.tsx                      [c-18]
│   │   ├── page.tsx                        [c-18 — w/ ScenarioCards + SoC]  §11.27
│   │   ├── aktyvy/page.tsx                 [c-18]
│   │   ├── uze/page.tsx                    [c-18 — SoC arc primary]
│   │   ├── rynok/page.tsx                  [c-18]
│   │   └── zvity/page.tsx                  [c-18]
│   │
│   ├── developer/
│   │   ├── layout.tsx                      [d-19 — sidebar w/ TOC]
│   │   ├── page.tsx                        [d-19 — overview]               §11.18
│   │   ├── api/explorer/page.tsx           [d-20 — Scalar embed]            §11.18
│   │   ├── sdk-ts/page.tsx                 [d-21]                           §11.17
│   │   ├── sdk-py/page.tsx                 [d-21]                           §11.17
│   │   ├── webhooks/page.tsx               [d-21]
│   │   └── auth/page.tsx                   [d-21 — mock-key flow]
│   │
│   ├── admin/
│   │   ├── layout.tsx                      [d-22]
│   │   ├── engage/page.tsx                 [d-22 — slide-7 diagram embed]   §11.6
│   │   ├── operate/page.tsx                [d-22]                           §11.6
│   │   └── analyze/page.tsx                [d-22]                           §11.6
│   │
│   ├── about/credentials/page.tsx          [a-2 — stubbed-surfaces list]    HLA R6
│   │
│   └── api/
│       ├── auth/
│       │   ├── me/route.ts                 [a-3]
│       │   └── switch-tenant/route.ts      [a-3]                            §11.2
│       └── [...path]/route.ts              [a-3 — catch-all proxy]          §11.9
│
├── components/
│   ├── shell/
│   │   ├── AppShell.tsx                    [a-4]
│   │   ├── TopBar.tsx                      [a-4]
│   │   ├── Sidebar.tsx                     [a-4]
│   │   ├── TenantSwitcher.tsx              [a-5]                            §11.2
│   │   ├── PersonaSwitcher.tsx             [a-5]
│   │   ├── ThemeToggle.tsx                 [a-5]                            §11.1
│   │   ├── AlertsBell.tsx                  [a-5]
│   │   ├── AgentLauncher.tsx               [a-5]
│   │   └── VoiceButton.tsx                 [a-5 — coordinates w/ Voice lead]§11.16
│   ├── hero/
│   │   ├── PersonaPicker.tsx               [b-7]                            §10
│   │   ├── ArchitectureDiagram.tsx         [b-7 — dynamic import]           §11.3
│   │   ├── ArchitectureDiagramNodes.ts     [b-7 — node + edge data]
│   │   └── LiveDataTicker.tsx              [b-7 — faked ticker per §10]
│   ├── kpi/
│   │   ├── KPITile.tsx                     [b-8]
│   │   └── KPIGrid.tsx                     [b-8]                            §11.22
│   ├── assets/
│   │   ├── AssetCard.tsx                   [b-9]
│   │   ├── AssetTable.tsx                  [b-9]
│   │   └── AssetDrawer.tsx                 [b-9 — fast peek]
│   ├── charts/
│   │   ├── HourlyChart.tsx                 [a-6 then used in b-8…b-15]
│   │   ├── BatterySoCArc.tsx               [b-13]
│   │   ├── ForecastChart.tsx               [b-10]
│   │   ├── PriceCapOverlay.tsx             [b-12]
│   │   └── RevenueSplit.tsx                [b-12]
│   ├── dispatch/
│   │   ├── DispatchQueue.tsx               [b-11]
│   │   ├── InstructionRow.tsx              [b-11]
│   │   └── RunOptimisationButton.tsx       [b-11]                           §11.14
│   ├── market/
│   │   ├── MarketTabs.tsx                  [b-12 — РДН/ВДР/БР/ДД]            §11.21
│   │   ├── MarketBidForm.tsx               [b-12]
│   │   └── BidHistory.tsx                  [b-12]
│   ├── alerts/
│   │   ├── AlertsTimeline.tsx              [b-14]
│   │   └── AlertRow.tsx                    [b-14]
│   ├── reports/
│   │   ├── ReportCard.tsx                  [b-15]
│   │   ├── KEPSignBadge.tsx                [b-15 — DEMO watermark]          §11.20
│   │   └── ESGSubtab.tsx                   [b-15]                           §11.31
│   ├── settings/
│   │   ├── OnboardingChecklist.tsx         [b-16]                           §11.23
│   │   ├── IntegrationsCatalogue.tsx       [b-16]
│   │   └── InviteCollaboratorForm.tsx      [b-16]                           §11.29
│   ├── scenarios/
│   │   └── ScenarioCard.tsx                [c-17 / c-18]                    §11.27
│   ├── palette/
│   │   ├── CommandPalette.tsx              [a-6]                            §11.7
│   │   └── CommandIndex.ts                 [a-6 — registered commands]
│   ├── agent/
│   │   ├── AgentChat.tsx                   [e-23]                           §11.15
│   │   ├── AgentBubble.tsx                 [e-23]
│   │   ├── EvidenceChips.tsx               [e-23 — links to live DB rows]   §11.15
│   │   └── VoiceSession.tsx                [e-24 — overlay UI]              §11.16
│   ├── dev/
│   │   ├── OpenAPIExplorer.tsx             [d-20 — Scalar wrapper, dynamic] §11.18
│   │   ├── CodeBlock.tsx                   [d-21]
│   │   └── QuickstartList.tsx              [d-21]
│   └── primitives/
│       ├── Button.tsx                      [a-4]
│       ├── Card.tsx                        [a-4]
│       ├── Drawer.tsx                      [a-4 — Radix Dialog base]
│       ├── Popover.tsx                     [a-4]
│       ├── Pill.tsx                        [a-4 — status badge]
│       ├── Skeleton.tsx                    [a-4]
│       ├── T.tsx                           [a-4 — i18n helper]
│       └── DemoWatermark.tsx               [b-15 — reused on every stub]
│
├── lib/
│   ├── api/
│   │   ├── client.ts                       [a-3 — fetch wrapper]
│   │   ├── queries.ts                      [a-3 — TanStack Query hooks]
│   │   └── envelope.ts                     [a-3 — Success/Error unwrap]
│   ├── tenant.ts                           [a-3 — cookie helpers]
│   ├── theme.ts                            [a-1 — theme apply / read]
│   ├── i18n/
│   │   └── uk.json                         [a-1]
│   ├── format-uah.ts                       [a-1]
│   ├── format-date.ts                      [a-1]
│   ├── persona.ts                          [a-3 — URL prefix → persona code]
│   └── feature-flags.ts                    [a-1]
│
├── stores/
│   ├── theme-store.ts                      [a-1]
│   ├── tenant-store.ts                     [a-3]
│   ├── palette-store.ts                    [a-6]
│   └── agent-chat-store.ts                 [e-23]
│
├── types/
│   ├── api.ts                              [a-2 — generated from openapi.json]
│   └── ui.ts                               [a-2 — UI-only types]
│
├── styles/
│   └── tokens.css                          [a-1 — THE ONLY hex-containing file] §11.1
│
├── tests/
│   ├── smoke.spec.ts                       [Phase f testing] §11.24
│   ├── theme.spec.ts                       [Phase f]
│   └── unit/
│       ├── format-uah.test.ts
│       ├── persona.test.ts
│       ├── theme.test.ts
│       └── hourly-chart-cap-pinning.test.tsx
│
├── public/
│   ├── manifest.webmanifest                [a-1 — PWA stub]                  PWA §5.6
│   ├── favicon.svg
│   ├── icon-192.png
│   ├── icon-512.png
│   └── gecko-logo.svg
│
├── .eslintrc.json                          [a-1 — no-hex rule]
├── eslint-rules/no-literal-hex.js          [a-1 — custom rule]
├── next.config.mjs                         [a-1]
├── tailwind.config.ts                      [a-1]
├── postcss.config.mjs                      [a-1]
├── tsconfig.json                           [a-1]
├── playwright.config.ts                    [Phase f]
├── vitest.config.ts                        [Phase f]
└── package.json
```

---

## 4. Design token system (the critical foundation)

This section is the foundation everything else builds on. Get this right first. Architect's spec lives in `ARCHITECTURE.md` §5.1; this section operationalises it.

### 4.1 `styles/tokens.css` — the only hex file

Copy the token block from `ARCHITECTURE.md` §5.1 verbatim into `apps/web/styles/tokens.css`. Categories:

- **Surfaces** — `--color-bg-page`, `--color-bg-card`, `--color-bg-elevated`, `--color-bg-muted`.
- **Text** — `--color-text-primary`, `--color-text-heading`, `--color-text-muted`, `--color-text-inverse`.
- **Brand** — `--color-brand-primary` (`#14B8A6`), `--color-brand-deep` (`#0F766E`), `--color-brand-light` (`#2DD4BF`).
- **Status** — `--color-status-success` (`#10B981`), `--color-status-warning` (`#F59E0B`), `--color-status-alert` (`#F43F5E`), `--color-status-info` (`#0EA5E9`).
- **Border** — `--color-border-base`, `--color-border-strong`.
- **Chart palette** — `--chart-c1` … `--chart-c5`.
- **Spacing** — `--space-1` (0.25rem) … `--space-16` (4rem), base 4px scale.
- **Typography** — `--font-sans` (Manrope), `--font-mono` (JetBrains Mono). Size scale `--font-size-xs` (0.75rem) … `--font-size-4xl` (2.5rem).
- **Radii** — `--radius-sm` (0.25rem) … `--radius-xl` (1rem).
- **Shadows** — `--shadow-card`, `--shadow-popover`.

Two selectors: `:root[data-theme="light"]` (default) and `:root[data-theme="dark"]`. Spacing / typography / radii **do not change between themes** — declare them on `:root` outside the theme selectors.

**DECIDED HERE — `data-theme` attribute default value:** because the architect set "Light is default" but also wired a bootstrap script, attach `data-theme="light"` to `<html>` as the static default in `layout.tsx`. The bootstrap script swaps to `dark` if and only if `localStorage.getItem('gecko_theme') === 'dark'`. This prevents FOUC on first paint for the most common (light) case.

### 4.2 Tailwind config

`tailwind.config.ts` extends Tailwind's theme to read CSS vars:

```ts
theme: {
  extend: {
    colors: {
      'bg-page':       'var(--color-bg-page)',
      'bg-card':       'var(--color-bg-card)',
      'bg-elevated':   'var(--color-bg-elevated)',
      'bg-muted':      'var(--color-bg-muted)',
      'text-primary':  'var(--color-text-primary)',
      'text-heading':  'var(--color-text-heading)',
      'text-muted':    'var(--color-text-muted)',
      'text-inverse':  'var(--color-text-inverse)',
      'brand':         'var(--color-brand-primary)',
      'brand-deep':    'var(--color-brand-deep)',
      'brand-light':   'var(--color-brand-light)',
      'status-success':'var(--color-status-success)',
      'status-warning':'var(--color-status-warning)',
      'status-alert':  'var(--color-status-alert)',
      'status-info':   'var(--color-status-info)',
      'border-base':   'var(--color-border-base)',
      'border-strong': 'var(--color-border-strong)',
    },
    fontFamily: { sans: 'var(--font-sans)', mono: 'var(--font-mono)' },
    boxShadow:  { card: 'var(--shadow-card)', popover: 'var(--shadow-popover)' },
    borderRadius: { sm: 'var(--radius-sm)', md: 'var(--radius-md)', lg: 'var(--radius-lg)', xl: 'var(--radius-xl)' },
  },
},
content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],
```

Use Tailwind classes like `bg-bg-page text-text-primary border-border-base` everywhere. **Never** use Tailwind's built-in `bg-slate-50` / `text-gray-900` / `border-zinc-200` — those bake colour into the class and bypass the token system.

### 4.3 Theme bootstrap (no FOUC)

In `app/layout.tsx`, before `<body>`, render an inline script with a string literal (so it executes before hydration):

```tsx
<head>
  <script dangerouslySetInnerHTML={{ __html: `
    (function() {
      try {
        var t = localStorage.getItem('gecko_theme');
        if (t === 'dark') document.documentElement.setAttribute('data-theme','dark');
        else document.documentElement.setAttribute('data-theme','light');
      } catch(e) { document.documentElement.setAttribute('data-theme','light'); }
    })();
  `}} />
</head>
```

The static `data-theme="light"` declared on the `<html>` element in JSX is fine — the script overrides it before paint.

### 4.4 ESLint no-hex rule

Custom rule file: `apps/web/eslint-rules/no-literal-hex.js`. Pseudocode:

```js
module.exports = {
  meta: { type: 'problem', docs: { description: 'No literal hex outside tokens.css' } },
  create(context) {
    const filename = context.getFilename();
    if (filename.endsWith('tokens.css') || filename.endsWith('tokens.ts')) return {};
    return {
      Literal(node) {
        if (typeof node.value !== 'string') return;
        if (/^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$/.test(node.value)) {
          context.report({ node, message: 'Literal hex forbidden — use design tokens.' });
        }
      },
    };
  },
};
```

Register in `.eslintrc.json` under `rules: { 'local-rules/no-literal-hex': 'error' }`. Wire `local-rules` via `eslint-plugin-local-rules` or eslint flat config. CI gate per `ARCHITECTURE.md` §10.7 row 2 (`pnpm lint`).

The rule also applies to `*.css` files via a stylelint companion (`stylelint-config-standard` + `declaration-property-value-disallowed-list`) — add only if a real `*.css` other than `tokens.css` is created. In v2, `globals.css` should contain only Tailwind directives and `@import './tokens.css'`.

### 4.5 Fonts

Use `next/font/google` to self-host Manrope. `app/layout.tsx`:

```tsx
import { Manrope, JetBrains_Mono } from 'next/font/google';
const manrope = Manrope({ subsets: ['latin','cyrillic'], weight: ['400','500','600','700','800'], variable: '--font-sans-loaded' });
```

Apply on `<html className={manrope.variable}>`. Then in `tokens.css`: `--font-sans: var(--font-sans-loaded), 'Manrope', system-ui, sans-serif;`.

---

## 5. Component build order (dependency-respecting)

Build phases. Within a phase, multiple files may be built in parallel; across phases, downstream phases require upstream done.

### Phase a — Foundation (must be done first)

1. **`styles/tokens.css`** + **`tailwind.config.ts`** + **`app/globals.css`** + **`app/layout.tsx`** with theme bootstrap script + **font setup** + **`stores/theme-store.ts`** + **`lib/theme.ts`**. Smoke: `<html data-theme>` swaps on Zustand call, persists across reload.
2. **`types/api.ts`** generated from `packages/openapi/openapi.json`. If openapi.json doesn't yet exist (backend not done), hand-stub the types from `ARCHITECTURE.md` §4 schemas: `Tenant`, `Asset`, `RdnPrice`, `VdrTrade`, `BrSettlement`, `DdContract`, `Bid`, `Setpoint`, `Telemetry`, `Forecast`, `KpiPortfolio`, `SettlementStatement`, `SignedDocument`, `RegulatorEvent`, `AgentQueryResponse`, `OptimisationRun`. Each as TS `interface`. Also `Success<T>` / `Error` envelope types per §4.1. **`about/credentials/page.tsx`** — static UA list of every stub (KEP, voice, optimiser, market submissions). Reads architecturally from a literal list, not the API.
3. **`lib/api/client.ts`** + **`lib/api/queries.ts`** + **`lib/api/envelope.ts`** + **`lib/tenant.ts`** + **`stores/tenant-store.ts`** + **`lib/persona.ts`** + **catch-all `/api/[...path]/route.ts` proxy** + **`/api/auth/me/route.ts`** + **`/api/auth/switch-tenant/route.ts`**. The proxy reads `gecko_tenant_id` cookie, forwards to `process.env.NEXT_PUBLIC_API_BASE_URL` with `X-Tenant-Id` header injected. Smoke: `curl http://localhost:3000/api/v1/auth/me` returns envelope with mock user.
4. **`components/shell/AppShell.tsx`** + **`TopBar.tsx`** + **`Sidebar.tsx`** + all `components/primitives/*`. The shell renders a flex layout: TopBar (h-14, sticky top-0), then `<div class="flex">` with Sidebar (w-60, persona-aware) + main content. Use `bg-bg-page`, `text-text-primary`, `border-border-base` everywhere.
5. **`TenantSwitcher.tsx`** + **`PersonaSwitcher.tsx`** + **`ThemeToggle.tsx`** + **`AlertsBell.tsx`** + **`AgentLauncher.tsx`** + **`VoiceButton.tsx`** (stub UI; logic handed off to Voice lead in Phase e).
6. **`CommandPalette.tsx`** (`Ctrl+K`/`Cmd+K`) using `cmdk`. Two sections: navigation (every persona surface URL, filtered by current persona via `lib/persona.ts`) + actions (toggle-theme, run-optimisation [calls API], submit-forecast-stub, sign-stub, jump-to-admin). On `Enter`: invoke action or `router.push(url)`. **Mitigation for FMEA F09:** include a Playwright assertion that `Enter` actually fires (smoke step §7.1 below).

### Phase b — Producer surfaces (hero persona, build first)

7. **`/` page** — `<PersonaPicker>` + `<ArchitectureDiagram>` + `<LiveDataTicker>`. See §6.1 of this doc for the diagram contract. The page itself is a Server Component; `ArchitectureDiagram` is dynamically imported as a Client Component to keep the LCP budget (HLA R10 mitigation).
8. **`/producer/page.tsx` — Результати.** Fetches `/api/v1/ems/kpi/portfolio?range=30d` for the 6 KPI tiles + `/api/v1/market/rdn?date=<today-1>&date_end=<today>` for the recent РДН chart + `/api/v1/regulatory/events` for the alerts strip.
   - Components used: `<KPIGrid kind="producer">`, `<HourlyChart variant="rdn">`, `<AlertsTimeline limit={5}>`.
   - KPI tiles (services §11.22): грн зекономлено, грн зароблено, небаланси уникнено (МВт·год), CO₂ avoided (тонн), доступність (%), рейтинг можливостей (0–100).
9. **`/producer/aktyvy/page.tsx`** — `<AssetTable>` (server-fetched from `/api/v1/assets`). Click row → `router.push('/producer/aktyvy/[id]')`. **Plus** a "fast peek" `<AssetDrawer>` invoked from a magnifier icon on each row (Radix Dialog, opens from right, shows last-24h `<HourlyChart variant="telemetry">` + 3 KPI tiles).
   - **`/producer/aktyvy/[id]/page.tsx`** — asset detail. Header card + tabs: Телеметрія (24h hourly), Налаштування, Технічне обслуговування (services §11.30 polish — "оголосити простій" form that POSTs `/api/v1/dispatch/operator_adjustments` stub or local-state if endpoint absent).
10. **`/producer/prognozy/page.tsx`** — `<ForecastChart>` (overlay actual / primary / refined per `ARCHITECTURE.md` §5.2.5). MAPE footer line. **`<ForecastSubmitButton>`** posts to `/api/v1/ems/forecasts/submit`; after server response, switches to a status badge that polls (`refetchInterval: 1000` for first 5 seconds then stops). Status flips DRAFT → SUBMITTED → ACK reflect the server-computed-on-read mechanism (`ARCHITECTURE.md` §3.6.1). Mock КЕП sign button shows `<KEPSignBadge>` on success (services §11.19 + §11.20).
11. **`/producer/dyspetcheryzatsiya/page.tsx`** — `<DispatchQueue>` (vertical timeline 24h) + `<RunOptimisationButton>` which POSTs `/api/v1/ems/optimise { scenario: 'arbitrage', horizon_hours: 24, asset_ids: [...] }`. On result, render recommendations as a list under the queue with "Apply" buttons (each POST `/api/v1/dispatch/setpoints`). Services §11.14.
12. **`/producer/rynok/page.tsx`** — `<MarketTabs>` with 4 tabs: РДН (uses `HourlyChart` + `PriceCapOverlay`) / ВДР / БР / ДД. Below: `<BidHistory>` + `<MarketBidForm>` + `<RevenueSplit>` donut. Services §11.21. **DECIDED HERE — tabs are URL-driven** via `?market=RDN|VDR|BR|DD` query param so the command palette can deep-link.
13. **`/producer/uze/page.tsx`** — `<BatterySoCArc>` (custom SVG, see §6.2) + cycle accounting table + arbitrage P&L `<HourlyChart variant="storage-pnl">`.
14. **`/producer/spovishchennya/page.tsx`** — `<AlertsTimeline>` (full, not truncated). Pull from `/api/v1/regulatory/events` + `/api/v1/dispatch/instructions?priority=1`. Acknowledge button per row POSTs (stub) — UI flips to "Підтверджено" locally.
15. **`/producer/zvity/page.tsx`** — list `<ReportCard>`s grouped by period (daily / weekly / monthly). Each card shows period, status pill, sign button. On sign click → POST `/api/v1/regulatory/documents/SETTLEMENT_ACT/{id}/sign` → render `<KEPSignBadge>` (with DEMO watermark, services §11.20). Bottom: `<ESGSubtab>` reading `kpi_daily.co2_avoided_tn` (services §11.31 polish).
16. **`/producer/nalashtuvannya/page.tsx`** — `<OnboardingChecklist>` (4 mock steps per slide-10, services §11.23) + `<IntegrationsCatalogue>` (cards Mock / Planned / Ready-for-API) + `<InviteCollaboratorForm>` (services §11.29 polish; email field + role select; on submit show "Запрошення надіслано (демо)" + the form clears).

### Phase c — Persona variants (5 surfaces each)

17. **`/c-i/*`** — five pages. Use the same components but persona-tuned:
   - **Home (`/c-i/page.tsx`)**: `<KPIGrid kind="c-i">` swaps "грн зароблено" → "своя генерація %"; adds "load shaved (МВт·год)". Three `<ScenarioCard>`s: «Захист від відключення», «Захист від небалансу», «Арбітражна можливість» (services §11.27).
   - **`/c-i/aktyvy/`**: same `<AssetTable>` but pre-filtered by tenant (the API does this; just pass `?owner_segment=c-i` in convenience).
   - **`/c-i/prognozy/`**: consumption forecast variant — `<ForecastChart>` with `kind="consumption"`.
   - **`/c-i/rynok/`**: same `<MarketTabs>`.
   - **`/c-i/zvity/`**: same `<ReportCard>` list; OBIS sub-tab on consumption (services §11.28 polish — render `<ObisZoneBreakdown>` from `kpi_daily` if metadata present; otherwise hide).
18. **`/storage/*`** — five pages. УЗЕ-first:
   - **Home (`/storage/page.tsx`)**: `<KPIGrid kind="storage">` — cycles used, ancillary revenue (грн), arbitrage delta, доступність %, рейтинг можливостей, CO₂ avoided. `<BatterySoCArc>` prominent above-the-fold. Three `<ScenarioCard>`s: «Захист від відключення», «Арбітражна можливість», «Допоміжні послуги».
   - **`/storage/aktyvy/`**: same.
   - **`/storage/uze/`**: detailed cycle chart + SoC arc + arbitrage P&L; primary surface for this persona (substitutes for `/prognozy/`).
   - **`/storage/rynok/`**: same `<MarketTabs>` + ancillary services sub-tab.
   - **`/storage/zvity/`**: same.

### Phase d — Dev portal + admin

19. **`/developer/page.tsx`** — overview + getting-started + key concepts (Markdown body inline). Services §11.18.
20. **`/developer/api/explorer/page.tsx`** — `<OpenAPIExplorer>` wrapping Scalar's `<ApiReferenceReact />` component. The spec is fetched at build time from `/packages/openapi/openapi.json` (committed). Dynamically imported (`next/dynamic` with `ssr: false`) to keep the page lightweight and meet the 2.0s LCP budget. **Fallback** in §9.
21. **`/developer/sdk-ts/`**, **`/developer/sdk-py/`**, **`/developer/webhooks/`**, **`/developer/auth/`** — MDX-style pages with `<CodeBlock>` + `<QuickstartList>`. Each SDK page lists install command, import line, 3 example snippets (from `ARCHITECTURE.md` §8.1 / §8.2).
22. **`/admin/engage/`** — cross-tenant portfolio view + embedded `<ArchitectureDiagram>` on the right (HLA D15 says both `/` and `/admin/engage/` use it). Fetch `/api/v1/admin/portfolio` (sends `X-Admin: true` via the catch-all proxy — see §3.5).
    **`/admin/operate/`** — cross-tenant dispatch queue; cross-tenant `<RunOptimisationButton>`.
    **`/admin/analyze/`** — cross-tenant KPI feed; cross-tenant alerts.

### Phase e — Agent UI (last)

23. **`<AgentChat>`** drawer (right-side, full-height). Header = persona name (computed from current URL via `lib/persona.ts`). Input field at bottom; bubble list above. Each agent bubble renders `<EvidenceChips>` — small pills that, on click, navigate to the source row (e.g., a chip linking to `market.br_settlements row_id=12345` routes to `/producer/rynok?market=BR&date=...&hour=...`).
   - State in `stores/agent-chat-store.ts` (Zustand). Persists conversation per `(tenant, persona)` key in `sessionStorage`.
   - Calls `POST /api/v1/agents/{persona}/query`. Persona derived: `/producer/` → toggleable between `dispatcher_analyst` (default) and `market_analyst`; `/c-i/` → `energy_advisor`; `/storage/` → `battery_coach`; `/admin/` → `dispatcher_analyst`.
24. **`<VoiceSession>`** overlay — coordinated with Voice agent lead. The Frontend lead provides the **UI surface only**: the push-to-talk overlay, the waveform canvas, the transcript line, and the fallback banner. Voice lead provides the Web Speech API integration and the `/api/v1/agents/voice/session` consumption. Services §11.16.

### Phase f — Tests (after each surface ships)

See §7 of this doc.

---

## 6. Special components (call out the tricky ones)

### 6.1 `<ArchitectureDiagram>` — services §11.3 (the load-bearing piece)

**Spec:** SVG, ~15 nodes, ~25 connection paths, hub-and-spoke. Layout per `PRODUCT_BRIEF.md` §7 (slide-7). Central node = "GECKO" platform. Upper half = contractual/regulatory side (4 branches: Допоміжні послуги → РВЧ, БР · Торгівля е/е → ДД, РДН, ВДР · Регуляторні питання → НКРЕ КП, ГП, Укренерго · Технічна справність → Аналітика, Телеметрія, ТО). Lower half = physical asset side (4 owner clusters: Активний споживач, Виробник-СЕС+УЗЕ, Споживач, Виробник-ВЕС+УЗЕ+ГПУ).

**Implementation rules (LOCKED here):**
- Plain inline SVG (`<svg viewBox="0 0 1200 800">`) inside a React Client Component.
- Node data in `components/hero/ArchitectureDiagramNodes.ts`: array of `{ id, x, y, label_ua, kind: 'hub' | 'contractual' | 'physical', href }`.
- Edge data in same file: array of `{ from, to, animateOnHover: boolean }`.
- Hover behaviour: on `onMouseEnter` of a node, find adjacent edges and apply a Framer Motion `pathLength` animation (0 → 1) on those `<path>` elements. Sibling nodes get a subtle scale-up (`scale: 1.05`) and a glow (CSS-var driven, `--color-brand-primary` filter drop-shadow).
- Click behaviour: `onClick={() => router.push(node.href)}`.
- Theme awareness: node fill = `var(--color-bg-card)`, stroke = `var(--color-border-strong)`, label = `var(--color-text-primary)`, edge stroke = `var(--color-border-base)`, hover stroke = `var(--color-brand-primary)`. No hex in this file.
- Mobile (<768px): replace SVG with a simplified two-column vertical list using the same node array — central column = "GECKO", outer column = clickable cards. Use `useMediaQuery` (or CSS-only via `@media` swap of two render trees).
- Dynamically imported via `next/dynamic` with a lightweight skeleton so the hero page LCP stays ≤ 1.5s (HLA R10 mitigation).
- **Node positions:** the implementer samples slide-7 from `source/01_GECKO_VPP_client_brief.pdf` page 7 to set the layout. Recommended layout: hub at (600, 400); contractual branches at 12 / 2 / 4 / 8 o'clock (top half); physical clusters at 5 / 7 o'clock (bottom half), each with 2–3 child icons radiating outward. Cite this in a `// LAYOUT-NOTE:` comment.

**Accessibility:** every node has `role="button"` + `tabIndex={0}` + `onKeyDown` (Enter/Space) handlers + `aria-label={label_ua}`. Skip-to-content link above the diagram lets keyboard users bypass.

### 6.2 `<HourlyChart>` — used everywhere

Wraps Recharts `<ComposedChart>`. Props:

```ts
type HourlyChartProps = {
  data: Array<{ hour: number; value: number; capped?: boolean; capValue?: number }>;
  xAxis: 'hour' | 'timestamp';
  yLabel: string;          // 'грн/МВт·год' | 'МВт' | 'МВт·год' | '%'
  variant: 'rdn' | 'telemetry' | 'forecast' | 'storage-pnl' | 'consumption';
  capPinning?: boolean;    // if true, render <PriceCapOverlay> + red dashed line
  overlay?: 'actual-vs-forecast' | 'primary-vs-refined';
  height?: number;         // default 280
};
```

**Implementation rules:**
- All colours from CSS vars via `useTheme()` hook reading `getComputedStyle(document.documentElement).getPropertyValue('--chart-c1')` (cached, re-read on theme change). Pass to Recharts `stroke` / `fill` props as runtime values.
- X-axis: UA convention `hour 1..24` (1-indexed). When `xAxis='timestamp'`, format ISO via `lib/format-date.ts` (`Intl.DateTimeFormat('uk-UA', { timeZone: 'Europe/Kyiv', hour: '2-digit', minute: '2-digit' })`).
- Cap-pinning visual (services §11.21 part of the РДН story): when `capPinning && data.some(d => d.capped)`, render a horizontal `<ReferenceLine>` at `capValue` with `stroke: var(--color-status-alert)` and `strokeDasharray: '4 4'`. On hover of a capped bar, the tooltip shows "Ціна досягла стелі: {{capValue}} грн/МВт·год".
- Loading state: render a `<Skeleton>` matching chart bounds.
- Empty data: render a centered muted message "Немає даних за цей період".

### 6.3 `<BatterySoCArc>` — `/producer/uze/`, `/storage/page.tsx`

Custom SVG (no library). Arc from 0% to 100%, current SoC filled in `var(--color-brand-primary)`. Threshold marks at 10% (`var(--color-status-warning)`) and 90% (`var(--color-status-info)`). Numeric % center-aligned. Props: `{ socPct: number; targetSocPct?: number; capacityMwh: number }`. Animated transition between values using Framer Motion `animate={{ pathLength }}` (lightweight, no full Motion bundle needed — use `motion.path` only).

### 6.4 `<KEPSignBadge>` — services §11.20

**Always renders DEMO watermark.** This is a mitigation for FMEA F13 — the watermark is a required prop in TypeScript:

```ts
type KEPSignBadgeProps = {
  signerName: string;
  signerEdrpou: string;
  signedAtIso: string;
  hashShort: string;       // "9f3a8b21…d71c40af"
  acskName: string;
  isDemo: true;            // LITERAL TRUE — TypeScript forces this in v2
};
```

Visual: pill or rounded card with `border: 1px solid var(--color-brand-primary)`, check icon (Lucide `<CheckCircle2 />`) in `var(--color-status-success)`, the `<DemoWatermark>` sub-component layered top-right (semi-transparent rotated "DEMO"). Clicking opens a `<Popover>` with the full hash + the disclaimer "Це демонстраційний підпис, не реальний КЕП. Деталі — /about/credentials".

Smoke test (§7.1 step 5) asserts the literal string "DEMO" is present in the badge DOM on `/producer/zvity/` after clicking sign.

### 6.5 `<CommandPalette>` — services §11.7

Uses `cmdk` library. Z-index above all overlays. Mounted globally in `app/layout.tsx` so it works on every page.

**Index** (`components/palette/CommandIndex.ts`): array of `{ id, label_ua, kind: 'nav' | 'action', target?: string, handler?: () => void, personaScope?: PersonaCode[] }`. Items:

- Navigation entries for every persona surface URL (28 of them in v2 — see §3 tree). `personaScope` filters out items that don't make sense for the current persona (e.g., `/producer/dyspetcheryzatsiya/` is hidden when current persona is `c-i`).
- Actions: "Подати прогноз" (opens prognozy + invokes submit), "Подати заявку РДН" (opens rynok?market=RDN + focuses form), "Запустити оптимізацію" (POST `/api/v1/ems/optimise`), "Підписати звіт" (jump to zvity), "Переключити тему" (calls `theme-store.toggle()`), "Перейти до /admin/engage", "Переключити tenant: producer-1", "tenant: ci-1", "tenant: storage-1".

Fuzzy search via cmdk's built-in. On `Enter`: if `kind='nav'` → `router.push(target)`; if `kind='action'` → `handler()`. The `Enter` behaviour MUST be asserted in smoke (FMEA F09 mitigation).

### 6.6 `<AgentChat>` — services §11.15

Drawer (right slide-in, 420 px wide, full height). Triggered from `<AgentLauncher>` in TopBar OR from a floating action button on persona surfaces. Persona derivation from URL prefix via `lib/persona.ts`. On `/producer/`, header shows two-tab switcher: "Диспетчерський аналітик" | "Ринковий аналітик" (the user can toggle between the two producer personas).

Calls `POST /api/v1/agents/{persona}/query` with `{ text, context: { current_url: pathname } }`. Renders the response's `answer` text + `evidence[]` as `<EvidenceChips>`.

`<EvidenceChips>` props: `{ evidence: Array<{ table: string; row_id: number; columns_used: string[]; ui_link: string }> }`. Each chip shows `table.column` and is a `<Link href={ui_link}>`. The `ui_link` is computed by the backend so the frontend doesn't need to know which row maps to which URL.

Loading state: typing indicator. Error state: red callout "Не вдалося отримати відповідь. Спробуйте ще раз.".

---

## 7. Testing requirements

### 7.1 Smoke (Playwright) — `apps/web/tests/smoke.spec.ts`

Mandatory test cases (mirrors `ARCHITECTURE.md` §10.1 + adds frontend-specific assertions):

1. **All 29 routes return 200 + zero console errors:**
   - `/`, `/about/credentials`
   - `/producer/`, `/producer/aktyvy/`, `/producer/prognozy/`, `/producer/dyspetcheryzatsiya/`, `/producer/rynok/`, `/producer/uze/`, `/producer/spovishchennya/`, `/producer/zvity/`, `/producer/nalashtuvannya/`
   - `/c-i/`, `/c-i/aktyvy/`, `/c-i/prognozy/`, `/c-i/rynok/`, `/c-i/zvity/`
   - `/storage/`, `/storage/aktyvy/`, `/storage/uze/`, `/storage/rynok/`, `/storage/zvity/`
   - `/developer/`, `/developer/api/explorer`, `/developer/sdk-ts/`, `/developer/sdk-py/`, `/developer/webhooks/`, `/developer/auth/`
   - `/admin/engage/`, `/admin/operate/`, `/admin/analyze/`
2. **Both themes** render correctly on `/`, `/producer/`, `/c-i/`, `/storage/`, `/admin/engage/`. Toggle via the `<ThemeToggle>`, assert `<html>` `data-theme` flips, then run `await injectAxe(page); await checkA11y(page)` — zero serious violations.
3. **Tenant switcher §11.2:** on `/producer/`, open switcher → click `ci-1` → assert KPI tile "грн зекономлено" value differs from pre-switch.
4. **Command palette §11.7 / FMEA F09:** `await page.keyboard.press('Control+K')`, type "акти", `await page.keyboard.press('Enter')`, assert URL becomes `/producer/aktyvy/`.
5. **КЕП sign §11.20 / FMEA F13:** on `/producer/zvity/`, click first report card's "Підписати" button, assert `<KEPSignBadge>` element appears AND contains literal text "DEMO".
6. **Architecture diagram §11.3:** on `/`, hover the "РДН" node → assert at least one edge gains the `data-animating="true"` attribute; click the node → assert URL becomes `/producer/rynok/?market=RDN`.
7. **Theme persistence:** toggle to dark on `/`, navigate to `/producer/`, reload page, assert `data-theme="dark"` still set with no FOUC (use `page.evaluate(() => document.documentElement.getAttribute('data-theme'))` immediately after `goto`).
8. **No FOUC test:** assert no element has computed `background-color: rgb(248, 250, 252)` (light page bg) during dark-theme first paint window — use Playwright tracing.

Run command: `pnpm -F web test:smoke`. CI gate: blocks merge per `ARCHITECTURE.md` §10.7.

### 7.2 Unit (vitest) — `apps/web/tests/unit/`

- `format-uah.test.ts`: `formatUah(123456.78)` → `"123 456,78 грн"`.
- `persona.test.ts`: `personaFromUrl('/producer/aktyvy/')` → `'producer'`; `agentPersonaForUrl('/storage/')` → `'battery_coach'`.
- `theme.test.ts`: simulate `localStorage.getItem('gecko_theme') === 'dark'` → `applyTheme()` sets `data-theme="dark"`.
- `hourly-chart-cap-pinning.test.tsx`: render `<HourlyChart capPinning data={[{hour:18, value:6900, capped:true, capValue:6900}]} />` → assert a `<ReferenceLine>` is rendered with `stroke-dasharray` set.

### 7.3 Visual regression (optional, defer-OK)

Playwright `toHaveScreenshot` for `/producer/`, `/c-i/`, `/storage/` in both themes — one snapshot per (route × theme) = 6 baselines. Flake-tolerant via `maxDiffPixelRatio: 0.01`. Run on PR but warn-only initially.

---

## 8. Pre-flight check (the implementing agent runs this before any component)

Before writing a single line of `apps/web/`, confirm:

- [ ] **Goal clear.** Built the full frontend per `PRODUCT_BRIEF.md` §10. Acceptance criteria listed in §1 above.
- [ ] **Tools installed.** `node -v` ≥ 20; `pnpm -v` ≥ 9; `pnpm install` from repo root succeeds; `pnpm -F web typecheck` runs (no errors yet OK — but the command resolves).
- [ ] **Backend reachable for dev.** Either FastAPI running on `localhost:8000` (`docker compose up api postgres` from `infra/docker/`), or stub fixtures exist at `apps/web/tests/fixtures/*.json` if backend isn't ready (proxy can fall back to fixtures via `NEXT_PUBLIC_API_BASE_URL=fixtures://`).
- [ ] **OpenAPI types generated.** `pnpm -F web codegen:api` runs `openapi-typescript packages/openapi/openapi.json -o types/api.ts`. If `openapi.json` doesn't exist yet, stub `types/api.ts` from `ARCHITECTURE.md` §4 schemas (per Phase a-2).
- [ ] **Plan complete.** This document.
- [ ] **Branching protocol acknowledged.** §9 below.
- [ ] **PROGRESS.md updated** when frontend phase starts and at each phase b/c/d/e completion.

---

## 9. Branching protocol

If you hit a wall, **don't paper over**. Log to `difficulties_log.md` using the entry format already in that file, document the workaround, and continue.

Specific anticipated obstacles + their workarounds:

| Obstacle | Branch | Resume |
|---|---|---|
| Recharts can't draw the cap-pinning red dashed line in some browser | Switch to a custom SVG overlay on top of the chart (Recharts `<Customized />` slot), or visx Reference Line. Log it. | Same surface, different impl. |
| Scalar `@scalar/api-reference-react` clashes with Next 16 server components | Wrap in `dynamic(() => import(...), { ssr: false })`. If still broken, fall back to embedding Swagger UI via `<iframe src="/openapi.json">` with `swagger-ui-dist`. Log it. | `/developer/api/explorer` ships either way. |
| Framer Motion clashes with React 19 strict mode | Replace hover animation with pure CSS transitions (`stroke-dasharray` + `stroke-dashoffset` + `transition`). Log it. | Diagram still animates. |
| Web Speech API doesn't pronounce Ukrainian on the dev machine | Coordinate with Voice lead. Frontend ships the UI; voice provider is their concern. The fallback text-only mode is already specified in `ARCHITECTURE.md` §7.5. | Done — no frontend change required. |
| `cmdk` `Enter` regression | Pin `cmdk@^1.x` (latest stable as of Stage 3); if regression in 1.x, fall back to Radix Dialog + custom keyboard handler. Log. Smoke step 4 enforces correctness. | Same. |
| `@vercel/analytics` breaks Vercel deploy | Per `project_vercel_analytics_next16_bug` memory + FMEA F04: pin `~1.x` or omit entirely. Omit by default in v2. | Deploy succeeds. |
| Lighthouse LCP > 1.5s on `/` due to Architecture diagram | Already mitigated via dynamic import. If still slow: render a static `<img src="/architecture-static.svg">` initially, swap to interactive on mouseover anywhere in viewport. Log. | Budget met. |
| Component shows a console error | NEVER paper over with `console.error = noop`. Fix the root cause. Log if fix is non-trivial. | Smoke pass step 1. |

If genuinely stuck after one branch attempt → log to `difficulties_log.md`, document the workaround taken, continue with the rest.

---

## 10. Done definition

The frontend phase is **done** iff all of the following hold:

- [ ] All 29 surfaces in `apps/web/app/` exist and render with synthetic data, both themes.
- [ ] `pnpm -F web typecheck` passes with zero errors.
- [ ] `pnpm -F web lint` passes (includes the custom no-hex rule).
- [ ] `pnpm -F web test:unit` passes.
- [ ] `pnpm -F web test:smoke` passes on Vercel preview URL.
- [ ] Lighthouse home-page score ≥ 90 perf + ≥ 90 a11y (warn-only acceptable; aim to clear).
- [ ] All §11 frontend acceptance criteria from `PRODUCT_BRIEF.md` pass (cross-reference the checklist in §1 of this doc).
- [ ] Both themes render every page without broken styles. Manual eyeball on `/`, `/producer/`, `/c-i/`, `/storage/`, `/admin/engage/`, `/developer/api/explorer`.
- [ ] `PROGRESS.md` updated with a "Frontend phase DONE" entry under "Stage transitions log".
- [ ] `difficulties_log.md` honest record of any workarounds taken.
- [ ] Frontend instruction-checklist in `ARCHITECTURE.md` §14.3 all 9 items ticked.

---

## 11. Self-review notes

After drafting §0–§10 I re-read this document looking for places an implementer would stall, missing acceptance coverage, or contradictions with `ARCHITECTURE.md`.

### 11.1 Locked decisions an implementer might otherwise re-litigate

- **`data-theme="light"` static default + script override** (§4.3). Architect said "bootstrap script swaps before paint"; I locked the JSX default at `light` so the script only swaps when the user previously chose dark. This minimises FOUC for the common case.
- **Tailwind 3 explicitly, not 4** (§2). Architect said "Tailwind 4" in `HLA §3.1` and `PRODUCT_BRIEF` is silent. Stage-2 `ARCHITECTURE.md` §2 says `tailwind.config.ts` (which suggests 3.x — Tailwind 4 has different config format). I locked **3.x** to avoid the version-mismatch trap on a tight timeline.
- **Market tabs are URL-driven** (`?market=RDN|VDR|BR|DD`) so the command palette can deep-link. Not in architect's spec; locked here.
- **`<KEPSignBadge>` enforces `isDemo: true` as a literal-true prop type.** Compiler-level mitigation for FMEA F13.
- **Architecture diagram layout positions** — locked at "hub at 600,400, contractual at top, physical at bottom" but final pixel positions sampled by implementer from slide-7 PNG. Acceptable because requires visual judgement.
- **`/storage/` substitutes `/uze/` for `/prognozy/`** to give storage persona a SoC-first detail surface, while keeping the 5-floor count. Matches `PRODUCT_BRIEF.md` §10 storage emphasis.

### 11.2 Acceptance criterion coverage check

Walked every §11.x and confirmed coverage in this doc:

- §11.1 ✅ §4 token system + §1 checklist
- §11.2 ✅ §5 Phase a-3 + §6.5 palette tenant action
- §11.3 ✅ §5 Phase b-7 + §6.1 detailed spec
- §11.4 ✅ §5 Phase b (all 9 producer surfaces enumerated)
- §11.5 ✅ §5 Phase c (5-of-9 explicitly locked + storage substitutes uze)
- §11.6 ✅ §5 Phase d-22
- §11.7 ✅ §6.5
- §11.9 ✅ §5 Phase a-3 catch-all proxy
- §11.14 ✅ §5 Phase b-11 `<RunOptimisationButton>`
- §11.15 ✅ §5 Phase e-23 `<AgentChat>` + `<EvidenceChips>`
- §11.16 ✅ §5 Phase e-24 (UI surface, Voice lead does provider integration)
- §11.17 ✅ §5 Phase d-21 SDK quickstart pages
- §11.18 ✅ §5 Phase d-19/20
- §11.19 ✅ §5 Phase b-10 forecast submit + status flip
- §11.20 ✅ §6.4 KEP badge + literal-true `isDemo` prop type
- §11.21 ✅ §5 Phase b-12 MarketTabs
- §11.22 ✅ §5 Phase b-8 KPIGrid CO₂ tile
- §11.23 ✅ §5 Phase b-16 OnboardingChecklist
- §11.24 ✅ §7.1 smoke
- §11.25 ✅ §1 checklist LCP budgets + §6.1 diagram dynamic import (HLA R10)
- §11.27 ✅ §5 Phase c-17/c-18 ScenarioCards
- §11.28 polish ✅ §5 Phase c `/c-i/zvity/` OBIS sub-tab (conditional render — defer-OK)
- §11.29 polish ✅ §5 Phase b-16 `<InviteCollaboratorForm>`
- §11.30 polish ✅ §5 Phase b-9 `/producer/aktyvy/[id]/` planned-downtime form
- §11.31 polish ✅ §5 Phase b-15 `<ESGSubtab>`

All MVP criteria addressed. All polish criteria touched (defer-OK if time-pressed; render conditionally).

### 11.3 Punted decisions (intentional, with rationale)

- **Exact slide-7 node coordinates.** §6.1 locks layout zones but final pixels need the PNG. Acceptable: requires visual judgement.
- **Manrope weight subset.** Listed common weights 400/500/600/700/800; implementer trims if bundle > 200 KB.
- **Voice provider integration.** §5 Phase e-24 hands the Web Speech API + Realtime WebSocket integration to the Voice lead. Frontend ships only the UI surface.
- **Visual-regression baselines.** §7.3 marks defer-OK; can be skipped if time-pressed.
- **OBIS sub-tab data.** §11.28 polish — render only if synthetic data carries the OBIS zone metadata (DB lead's call). Conditional render.

### 11.4 Contradictions with `ARCHITECTURE.md` resolved

- Architect §3.1 says "Tailwind 4"; §2 repo layout has `tailwind.config.ts`. Tailwind 4 uses CSS-only config (`@theme`). I locked **Tailwind 3** for compatibility; this is a forward-compatible choice (the token system migrates trivially to Tailwind 4 later by moving the `extend` block into `@theme` in CSS).
- Architect §5.4 says "no Context API beyond Next's built-in" but Next's `App Router` has built-in providers for TanStack Query; those are mounted in `app/providers.tsx` (§3 of this doc). Consistent.
- Architect §5.2.6 says `<DispatchQueue>` lists "pending/executing/done"; the DB enum (`dispatch.setpoints.state` per §3.4.1) has six states including `acknowledged`, `cancelled`, `failed`. The UI groups them: pending+acknowledged → "очікує", executing → "виконується", done → "завершено", cancelled+failed → "помилка/скасовано". Locked here.

### 11.5 Confidence

- **High confidence:** token system, repo layout, component-build order, routing, smoke spec.
- **Medium confidence:** slide-7 diagram visual fidelity (depends on implementer's care with the PNG sample); Scalar embed stability under Next 16 (fallback documented).
- **Lower confidence (acknowledged):** Lighthouse 1.5s LCP budget on `/` with the diagram — Framer Motion + dynamic import should clear it but cold-cache mobile may need an additional optimisation pass. Mitigation: HLA R10's "Server Component skeleton" pattern is already in §6.1.

---

*End of FRONTEND_INSTRUCTIONS.md v0.1. Next: implementing agent runs §8 pre-flight, then begins Phase a.*
