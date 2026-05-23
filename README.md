# Krytsia — VPP + Energy Management Platform

> Інтелектуальний шар для критичної енергетичної інфраструктури. Україна · ЄС.

**Virtual Power Plant + Energy Management Platform для українського енергоринку. AI-агенти, прогнозування, диспетчеризація, ринкова інтеграція.**

---

## What this is

Krytsia — production-fidelity demo of a Virtual Power Plant + EMS platform for Ukraine. Aggregates solar (СЕС), wind (ВЕС), gas (ГПУ), and battery storage (УЗЕ) assets of multiple owners into one disciplined trading-and-dispatch entity.

- **Frontend:** Next.js 16 (App Router, React 19, TypeScript). Deployed on Vercel at `krytsia.radai-1984.dev`.
- **Backend:** FastAPI (Python 3.11+, async SQLAlchemy 2.0). Deployed on Hetzner VPS at `api.gecko.radai-1984.dev` (internal API URL, retained from build infra).
- **Database:** Postgres 16 with multi-tenant Row-Level Security.
- **Data:** Synthetic, modelled to Ukrainian market shapes (РДН/ВДР/БР/ДД, ENTSO-E EIC codes, КЕП stub). 30 days window (`2026-04-23 → 2026-05-23`).

## Architecture at a glance

```
Browser
  ↓
Vercel Edge (Next.js 16 — frontend + thin API proxies)
  ↓ (HTTPS, X-Tenant-Id header)
api.gecko.radai-1984.dev (Caddy on Hetzner)
  ↓
FastAPI (gecko-api container)
  ↓
Postgres 16 (gecko-postgres container, RLS-enforced)
```

Three sub-systems inside FastAPI (per client deck slide 6):
- **Ринкова інтеграція** — bids and confirmations to РДН / ВДР / БР; ancillary; bilateral
- **Комерційна диспетчеризація** — setpoints, telemetry, instruction acks
- **EMS (Програмна платформа)** — forecast, optimise, KPI, AI agents

## Repository layout

```
gecko-vpp-rebuild/
├── apps/
│   ├── web/                  # Next.js 16 frontend
│   └── api/                  # FastAPI backend
├── packages/
│   ├── sdk-ts/               # @gecko-vpp/sdk-ts
│   └── sdk-py/               # gecko-vpp-sdk (PyPI)
├── data-generator/           # synthetic data seeder
├── infra/
│   ├── docker/
│   ├── caddy/
│   └── postgres/
├── tests/
└── phase-{1,2,3}-*/          # design artefacts (frozen)
```

## Personas / URL surfaces

- `/` — hero with interactive architecture diagram + persona picker
- `/producer/` — hero persona (виробник): 9 surfaces
- `/c-i/` — Segment A (Бізнес): 5 surfaces
- `/storage/` — Segment C (УЗЕ-власник): 5 surfaces
- `/developer/` — public dev portal: OpenAPI explorer + SDK quickstarts + webhooks
- `/admin/` — cross-tenant operator view: Engage / Operate / Analyze

## Key differentiators (vs UA market)

1. Only public VPP UI for Ukraine (per Phase 2 research — no competing product exists)
2. Public developer portal with SDK
3. 4 persona-aware AI agents
4. Voice agent with push-to-talk
5. Dark + light theme parity
6. UA-native data model (ENTSO-E EIC codes, `(date, hour 1..24)` convention, КЕП-signed documents)

## Demo data

Synthetic. 30 days `2026-04-23 → 2026-05-23`. Portfolio: 8–12 assets totalling ~50 МВт across Закарпатська, Київська, Львівська, Дніпропетровська, Одеська oblasts. Three mock tenants (one per segment).

**Synthetic data is told to be synthetic.** The KЕП-stub badge always shows a "DEMO" watermark.

## Status

This is **v2 rebuild** (Krytsia rebrand of the v1 GECKO VPP demo). v1 lives at `vpp.radai-1984.dev`. See `phase-2-solution/`, `phase-3-architecture/` for the design trail.

## License

MIT.
