# SDK_INSTRUCTIONS — GECKO VPP v2

**Owner:** SDK sub-lead (Stage-3 specialist; executes Phase 4.10 of `ARCHITECTURE.md §12`).
**Parent contracts:** `ARCHITECTURE.md` §8 (SDK contracts — TS + Py), §6.7 (OpenAPI generation pipeline), §13.4 (GitHub repo), §14.6 (this lead's checklist).
**Prerequisite:** Backend API phase has produced `packages/openapi/openapi.json` and the local FastAPI is reachable at `http://localhost:8000` (run via `uvicorn` for SDK example testing). Spectral lint already green (`spectral lint packages/openapi/openapi.json` passes).
**Length:** ~4 pages.

---

## 1. Goal

Ship two SDKs that wrap GECKO VPP's REST API:

1. **`@gecko-vpp/sdk`** on npm (TypeScript, ESM + CJS dual output).
2. **`gecko-vpp`** on PyPI (Python, async-first via `httpx`).

Both are **generated from the single source of truth** `packages/openapi/openapi.json` so they cannot drift from the API. Each ships with:
- a thin hand-written `GeckoVPPClient` class wrapping the generated types,
- three quickstart example scripts,
- a README with install/import/example/license,
- a buildable package artifact (tarball / sdist+wheel) ready to publish — **but no auto-publish** without explicit human approval (manual gate, per architect §8.1/§8.2).

The dev-portal pages `/developer/sdk-ts/` and `/developer/sdk-py/` (Frontend lead's deliverable) embed these example scripts as code samples.

---

## 2. Success criteria (binary checklist)

- [ ] `make sdk` (or `pnpm sdk:build` + `uv run sdk:build`) regenerates BOTH SDKs from `packages/openapi/openapi.json` and builds them.
- [ ] `pnpm -F @gecko-vpp/sdk build` produces ESM + CJS bundles + `.d.ts` types under `packages/sdk-ts/dist/`.
- [ ] `pnpm -F @gecko-vpp/sdk pack` produces a tarball; manual inspection shows: README, LICENSE, dist/, no source maps with secrets, no dev deps in `dependencies`.
- [ ] `uv build` inside `packages/sdk-py/` produces sdist + wheel under `packages/sdk-py/dist/`.
- [ ] Both SDKs expose `GeckoVPPClient` constructor accepting `{ baseUrl, tenantId, apiKey? }` (TS) / `(base_url, tenant_id, api_key=None)` (Py).
- [ ] Both SDKs expose typed methods grouped by domain: `client.market.rdn(...)`, `client.assets.list(...)`, `client.agents.query(persona, ...)`, etc.
- [ ] **3 example scripts each:** `list_assets.{ts,py}`, `fetch_rdn.{ts,py}`, `query_agent.{ts,py}`. They run against local FastAPI in CI (`pytest --sdk-examples` per `ARCHITECTURE.md §8.3` and `§10.4`).
- [ ] CI gate `sdk_examples` blocks merge on any example failure (R9 mitigation).
- [ ] Each SDK's README has: install command, 5-line quickstart, link to dev portal, license (MIT).
- [ ] No paid API keys committed; example scripts use `process.env.GECKO_TENANT_ID` / `os.environ["GECKO_TENANT_ID"]`.
- [ ] Publish steps documented but gated: `pnpm publish --access public` on tag `sdk-ts-v*` requires manual `OPENAUTH`/`NPM_TOKEN` approval; `uv publish` on tag `sdk-py-v*` requires `PYPI_API_TOKEN` approval.
- [ ] Pre-flight (§7) all YES before starting.

---

## 3. Tools (verify available)

| Tool | Purpose | Pin / version |
|---|---|---|
| Node.js | runtime | 20.x (matches `.nvmrc` per `ARCHITECTURE.md §2`) |
| `pnpm` | JS workspace manager | 9.x; declared in `pnpm-workspace.yaml` |
| `openapi-typescript` | OpenAPI → TS types | latest (>=7) |
| `tsup` | bundler (ESM + CJS + dts) | latest |
| `typescript` | strict mode | >=5.4 |
| `vitest` | TS unit tests | latest |
| Python 3.12 | runtime | matches DB+API phase |
| `uv` | Python build | latest |
| `openapi-python-client` | OpenAPI → async Python client | latest |
| `httpx` | runtime dep of generated client | >=0.27 |
| `pytest` + `pytest-asyncio` | example-script test runner | latest |

**Verify before starting:**
```bash
node --version && pnpm --version && tsc --version
python --version && uv --version
npx openapi-typescript --version
uv tool run openapi-python-client --version
```

---

## 4. Step-by-step plan

### Phase A — Build pipeline plumbing

**Step 1. `make sdk` target.** Root `Makefile` (or `package.json` script) does:

```make
sdk: sdk-openapi sdk-ts-gen sdk-py-gen sdk-ts-build sdk-py-build

sdk-openapi:
	@curl -sf http://localhost:8000/openapi.json > packages/openapi/openapi.json
	@spectral lint packages/openapi/openapi.json

sdk-ts-gen:
	@npx openapi-typescript packages/openapi/openapi.json \
		--output packages/sdk-ts/src/generated/api.ts

sdk-py-gen:
	@rm -rf packages/sdk-py/gecko_vpp/generated
	@uv tool run openapi-python-client generate \
		--path packages/openapi/openapi.json \
		--output-path packages/sdk-py/gecko_vpp/generated \
		--meta=none

sdk-ts-build:
	@pnpm -F @gecko-vpp/sdk build

sdk-py-build:
	@cd packages/sdk-py && uv build
```

Two ingestion paths:
- **CI:** API container starts, `curl` dumps spec, generators run.
- **Local dev:** developer runs `make sdk` after editing API code; uvicorn must be already running.

Add a CI step `make sdk` after Backend API tests pass; commits the regenerated openapi.json if changed (PR-bot path, DevOps owns wiring).

### Phase B — TypeScript SDK (`packages/sdk-ts/`)

**Step 2. Package skeleton.**

```
packages/sdk-ts/
├── src/
│   ├── client.ts          # hand-written GeckoVPPClient
│   ├── index.ts           # public exports: GeckoVPPClient + types
│   ├── generated/         # openapi-typescript output (gitignored? NO — commit for reproducibility)
│   │   └── api.ts
│   └── examples/
│       ├── list_assets.ts
│       ├── fetch_rdn.ts
│       └── query_agent.ts
├── tests/
│   └── client.test.ts     # vitest unit tests
├── tsup.config.ts         # dual ESM + CJS + dts output
├── tsconfig.json
├── package.json
├── README.md
└── LICENSE
```

`package.json` essentials:
```json
{
  "name": "@gecko-vpp/sdk",
  "version": "0.1.0",
  "description": "Official TypeScript SDK for GECKO VPP REST API",
  "type": "module",
  "exports": {
    ".": {
      "import": "./dist/index.mjs",
      "require": "./dist/index.cjs",
      "types": "./dist/index.d.ts"
    }
  },
  "files": ["dist", "README.md", "LICENSE"],
  "scripts": {
    "build": "tsup",
    "test": "vitest run",
    "typecheck": "tsc --noEmit"
  },
  "license": "MIT",
  "publishConfig": { "access": "public" },
  "engines": { "node": ">=20" }
}
```

**Step 3. `GeckoVPPClient` class (hand-written wrapper).**

`src/client.ts` — small, deliberate surface. Pseudocode (DO NOT copy literally; implementer writes the real version):

```typescript
import type { paths, components } from './generated/api';
import createClient from 'openapi-fetch';

export interface GeckoVPPClientOptions {
  baseUrl: string;
  tenantId: string;
  apiKey?: string;       // reserved for future; ignored in v2 mock auth
  fetch?: typeof fetch;  // injectable for tests
}

export class GeckoVPPClient {
  private client: ReturnType<typeof createClient<paths>>;
  constructor(opts: GeckoVPPClientOptions) {
    this.client = createClient<paths>({
      baseUrl: opts.baseUrl,
      fetch: opts.fetch ?? fetch,
      headers: { 'X-Tenant-Id': opts.tenantId },
    });
  }

  readonly market = {
    rdn: (params: paths['/api/v1/market/rdn']['get']['parameters']['query']) =>
      this.client.GET('/api/v1/market/rdn', { params: { query: params } }),
    vdr: (params: any) => this.client.GET('/api/v1/market/vdr', { params: { query: params } }),
    br:  (params: any) => this.client.GET('/api/v1/market/br',  { params: { query: params } }),
    dd:  (params: any) => this.client.GET('/api/v1/market/dd',  { params: { query: params } }),
    bids: { list: (...), submit: (...) },
    revenue: (range = '30d') => this.client.GET('/api/v1/market/revenue', { params: { query: { range } } }),
  };

  readonly assets = {
    list: (params?) => this.client.GET('/api/v1/assets', { params: { query: params } }),
    get:  (id: string) => this.client.GET('/api/v1/assets/{id}', { params: { path: { id } } }),
  };

  readonly dispatch = { ... };
  readonly ems = { ... };
  readonly regulatory = { ... };
  readonly agents = {
    query: (persona: string, body: { text: string; context?: any }) =>
      this.client.POST('/api/v1/agents/{persona}/query', { params: { path: { persona } }, body }),
    voiceSession: () => this.client.GET('/api/v1/agents/voice/session'),
  };
}
```

**Implementation notes:**
- Use `openapi-fetch` (preferred over hand-rolled `fetch` calls) — typed param/body inference comes free from `openapi-typescript` output.
- Errors: do NOT throw on 4xx by default; return `{ data, error }` per `openapi-fetch` convention. Document in README.
- All methods return Promises; no callback API.

**Step 4. Three example scripts.**

`src/examples/list_assets.ts`:
```typescript
import { GeckoVPPClient } from '@gecko-vpp/sdk';
const client = new GeckoVPPClient({
  baseUrl: process.env.GECKO_BASE_URL ?? 'http://localhost:8000',
  tenantId: process.env.GECKO_TENANT_ID!,
});
const { data, error } = await client.assets.list({ asset_class: 'СЕС' });
if (error) { console.error(error); process.exit(1); }
console.log(`Found ${data.data.length} solar assets`);
for (const a of data.data) console.log(`  - ${a.display_name} (${a.capacity_mw} МВт)`);
```

`src/examples/fetch_rdn.ts`:
```typescript
// Fetch last 7 days of РДН prices and report capped evening hours
import { GeckoVPPClient } from '@gecko-vpp/sdk';
const client = new GeckoVPPClient({ baseUrl: ..., tenantId: ... });
const today = new Date(); const weekAgo = new Date(today.getTime() - 7*86400000);
const { data } = await client.market.rdn({
  date: weekAgo.toISOString().slice(0,10),
  date_end: today.toISOString().slice(0,10),
});
const cappedHours = data.data.filter(r => r.is_capped);
console.log(`${cappedHours.length} capped hours in last 7 days`);
```

`src/examples/query_agent.ts`:
```typescript
// Ask the dispatcher analyst about the next imbalance window
import { GeckoVPPClient } from '@gecko-vpp/sdk';
const client = new GeckoVPPClient({ baseUrl: ..., tenantId: ... });
const { data } = await client.agents.query('dispatcher_analyst', {
  text: 'коли наступний небаланс?',
  context: { current_url: '/producer/rynok' },
});
console.log(`Intent: ${data.data.intent} (confidence ${data.data.confidence})`);
console.log(`Answer: ${data.data.answer}`);
console.log(`Evidence: ${data.data.evidence.length} rows linked`);
```

### Phase C — Python SDK (`packages/sdk-py/`)

**Step 5. Package skeleton.**

```
packages/sdk-py/
├── gecko_vpp/
│   ├── __init__.py        # public exports
│   ├── client.py          # hand-written async GeckoVPPClient
│   ├── generated/         # openapi-python-client output (regen-only)
│   │   └── ...
│   └── examples/
│       ├── list_assets.py
│       ├── fetch_rdn.py
│       └── query_agent.py
├── tests/
│   └── test_client.py
├── pyproject.toml
├── README.md
└── LICENSE
```

`pyproject.toml`:
```toml
[project]
name = "gecko-vpp"
version = "0.1.0"
description = "Official Python SDK for GECKO VPP REST API"
requires-python = ">=3.10"
dependencies = ["httpx>=0.27", "pydantic>=2.7"]
license = { text = "MIT" }
readme = "README.md"

[project.urls]
Homepage = "https://gecko.radai-1984.dev/developer/"
Repository = "https://github.com/basisabp1984/gecko-vpp-rebuild"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["gecko_vpp"]
```

Public surface (`gecko_vpp/__init__.py`):
```python
from gecko_vpp.client import GeckoVPPClient
__all__ = ["GeckoVPPClient"]
```

**Step 6. `GeckoVPPClient` (Python).** Wrap the generated client (which `openapi-python-client` emits as a `Client` class plus per-tag function modules). Sketch:

```python
import httpx
from typing import Optional

class GeckoVPPClient:
    def __init__(self, *, base_url: str, tenant_id: str, api_key: Optional[str] = None):
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"X-Tenant-Id": tenant_id},
            timeout=30.0,
        )
        self.market = _MarketResource(self._client)
        self.assets = _AssetsResource(self._client)
        self.dispatch = _DispatchResource(self._client)
        self.ems = _EMSResource(self._client)
        self.regulatory = _RegulatoryResource(self._client)
        self.agents = _AgentsResource(self._client)

    async def __aenter__(self): return self
    async def __aexit__(self, *_): await self._client.aclose()
    async def close(self): await self._client.aclose()
```

Each `_<Domain>Resource` wraps the generated `get_/post_` functions. Methods accept primitive args, return parsed Pydantic models from the generated `models/` package. Mirror the TS surface 1:1 so the README examples translate by line.

**Step 7. Three example scripts** (mirror TS). Each runs standalone via `python -m gecko_vpp.examples.list_assets`.

`gecko_vpp/examples/list_assets.py`:
```python
import asyncio, os
from gecko_vpp import GeckoVPPClient

async def main():
    async with GeckoVPPClient(
        base_url=os.environ.get("GECKO_BASE_URL", "http://localhost:8000"),
        tenant_id=os.environ["GECKO_TENANT_ID"],
    ) as c:
        resp = await c.assets.list(asset_class="СЕС")
        for a in resp.data:
            print(f"  - {a.display_name} ({a.capacity_mw} МВт)")

if __name__ == "__main__":
    asyncio.run(main())
```

`fetch_rdn.py` and `query_agent.py` similarly mirror the TS versions.

### Phase D — Tests, READMEs, publish gates

**Step 8. CI example tests** (`ARCHITECTURE.md §8.3` + §10.4).

In `apps/api/tests/integration/test_sdk_examples.py` (or under each SDK's `tests/`):
- Start FastAPI on a free port (testcontainers + uvicorn or a `pytest` fixture that spawns the app).
- Set `GECKO_BASE_URL` to that port and `GECKO_TENANT_ID` to one of the 3 demo UUIDs.
- Run each example script as a subprocess (`subprocess.run([..., "list_assets.ts"], ...)` via `tsx` for TS; `python -m gecko_vpp.examples.list_assets` for Py).
- Assert exit code 0 and stdout non-empty.
- Mark with `pytest.mark.sdk_examples`; CI invokes `pytest -m sdk_examples`.

**Step 9. READMEs.**

Each SDK README (≤2 pages) must include:
- One-line tagline.
- Install: `npm install @gecko-vpp/sdk` / `pip install gecko-vpp`.
- 5-line quickstart (use the `list_assets` example, condensed).
- Link to https://gecko.radai-1984.dev/developer/.
- Demo-mode disclaimer ("This SDK targets the GECKO VPP demo environment; tenant UUIDs are listed at /about/credentials.").
- License: MIT, link to LICENSE file.

**Step 10. Publish gates (documented, NOT auto-run).**

`.github/workflows/release-sdk-ts.yml` (skeleton, manual trigger):
```yaml
on:
  push:
    tags: [ 'sdk-ts-v*' ]
jobs:
  publish:
    if: github.actor == 'basisabp1984'   # manual gate via tag-pusher identity
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v3
      - run: pnpm install --frozen-lockfile
      - run: make sdk-ts-build
      - run: pnpm -F @gecko-vpp/sdk publish --access public
        env:
          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}
```

Mirror for Py (`pypi.org`, `uv publish`, `PYPI_API_TOKEN`). **Do not** trigger on every merge — tag-driven manual only (architect §8.1/§8.2 lock).

If publish credentials are not present at audit time, the workflow exits 0 with a NO-OP message. Build artifacts are still produced (tarball + wheel) under `dist/` so they can be inspected / sideloaded.

---

## 5. Conventions

- **Single source of truth:** `packages/openapi/openapi.json`. Both SDKs regenerate from it. No hand-edits to `generated/` folders.
- **Hand-written class is thin:** the `GeckoVPPClient` exists only to (a) bundle resources by domain, (b) inject `X-Tenant-Id`, (c) provide a stable public import name. Business logic stays in the generated code.
- **Errors:** non-2xx responses surface as `{ data, error }` (TS, openapi-fetch convention) / via `httpx.HTTPStatusError` raised on `response.raise_for_status()` (Py, opt-in). README documents both.
- **Versioning:** `0.1.0` initial. Bump minor on any new endpoint; bump patch on internal refactors. Semver strict.
- **No paid API keys** in examples (architect §11.16 + user hard constraint). All example scripts read `GECKO_TENANT_ID` from env; if absent, print the 3 demo UUIDs from `/about/credentials` and exit 1 with a helpful message.

---

## 6. §11 acceptance criteria this file's domain services

- **§11.17** — TS + Py SDKs with `GeckoVPPClient` class + 3 examples each, built for npm + PyPI.
- **§11.18** — SDKs power the `/developer/sdk-ts/` and `/developer/sdk-py/` pages.
- **§11.24** — SDK example tests run in CI smoke gate.
- **§11.25** — both SDKs ship with TypeScript types (TS) and Pydantic-model returns (Py) so consumers get IDE help out of the box.

---

## 7. Pre-flight check

- [ ] **(a) Goal clear?** "Two SDKs generated from one OpenAPI; both buildable and example-tested; not auto-published."
- [ ] **(b) Success criteria measurable?** "Every line in §2 is binary checkable."
- [ ] **(c) Tools available?** "Node 20 + pnpm + openapi-typescript + tsup; Python 3.12 + uv + openapi-python-client + httpx; all resolvable."
- [ ] **(d) Plan complete?** "I can produce both SDKs by following Phase A→D mechanically; no architectural decisions left."
- [ ] **(e) Upstream green?** "Backend API done; `packages/openapi/openapi.json` exists and Spectral-clean; local FastAPI reachable for example tests."

If any NO → STOP. Write `SDK_CHECKLIST.md` addendum, ping orchestrator.

---

## 8. Branching protocol

| Branch point | Fallback |
|---|---|
| `openapi-typescript` choke on a specific schema construct | Pin to a known-good version; or simplify the FastAPI Pydantic model causing it (escalate to Backend API lead). Log the cause. |
| `openapi-python-client` emits broken syntax | Same — pin version; or hand-patch the generated client and document the patch in `packages/sdk-py/PATCHES.md`. |
| Example script test exceeds 30 s | Set `timeout=10.0` on httpx; ensure synth data is seeded before tests run (depends on DB phase ordering). |
| `tsup` ESM/CJS dual fails | Drop CJS, ship ESM-only (`"type": "module"` already set). Node 20+ supports ESM. Document in README. |
| npm scope `@gecko-vpp` not registered | `npm org create gecko-vpp` requires the maintainer's npm login — escalate to user. Build still produces the tarball; publish step skipped. |
| PyPI name `gecko-vpp` taken | Fall back to `gecko-vpp-sdk`. Update README + package.json. |
| Spectral lint regresses after a backend endpoint change | Stop and re-sync: pull latest `packages/openapi/openapi.json`, re-run `make sdk-openapi`. Don't paper over. |
| `make sdk-openapi` can't reach localhost:8000 | Add a precondition step: `curl -f http://localhost:8000/health` retry up to 30 s. If still failing, fail loudly. |

Log each branch in `difficulties_log.md`.

---

## 9. Done definition

SDK phase DONE iff:

1. All boxes in §2 checked.
2. CI gates green: `pnpm typecheck`, `pnpm test` (SDK unit tests), `pytest -m sdk_examples` (example scripts against local API), `make sdk` end-to-end.
3. Tarball (`@gecko-vpp/sdk-0.1.0.tgz`) and wheel (`gecko_vpp-0.1.0-py3-none-any.whl`) both produced under `packages/sdk-{ts,py}/dist/` and committed as build artifacts (CI uploads).
4. Both READMEs reviewed; examples copy-pasted into the dev-portal pages by the Frontend lead (Phase 4.11).
5. Append to `PROGRESS.md`:
   ```
   - YYYY-MM-DD — Phase 4.10 (SDK lead) DONE. @gecko-vpp/sdk (npm) + gecko-vpp (PyPI) buildable; 6 example scripts CI-green; publish gates documented (manual). [one-line gotcha]
   ```
6. Any branch logged in `difficulties_log.md`.

When done, hand off to Frontend lead (Phase 4.11) — they embed the example scripts into `/developer/sdk-ts/` and `/developer/sdk-py/` pages.

---

*End of SDK_INSTRUCTIONS v0.1.*
