# @gecko-vpp/sdk-ts

TypeScript SDK for the GECKO VPP REST API.

## Install

```bash
npm install @gecko-vpp/sdk-ts
```

## Quickstart

```ts
import { GeckoVPPClient } from "@gecko-vpp/sdk-ts";

const client = new GeckoVPPClient({
  baseURL: "https://api.gecko.radai-1984.dev",
  tenantId: "11111111-1111-1111-1111-111111111111",   // demo: producer
});

const assets = await client.assets.list();
console.log(`You have ${assets.length} assets.`);

const rdn = await client.market.rdn({ date_start: "2026-05-12", date_end: "2026-05-12" });
console.log(`РДН: ${rdn.length} hours; ${rdn.filter(r => r.is_capped).length} capped.`);

const ans = await client.agents.query("disp", "що сьогодні з виробництвом?");
console.log(ans.answer);
```

## Demo tenants (no real auth — mock only)

| Tenant ID                              | Segment   | Persona |
| -------------------------------------- | --------- | ------- |
| `11111111-1111-1111-1111-111111111111` | producer  | Виробник |
| `22222222-2222-2222-2222-222222222222` | c-i       | C&I prosumer |
| `33333333-3333-3333-3333-333333333333` | storage   | УЗЕ-власник |

## Examples

```bash
npm install
npm run example:assets
npm run example:rdn
npm run example:agent
```

(All examples target `http://localhost:8000` by default; override with `GECKO_API` env var.)

## API surface

- `client.healthz()`
- `client.me()` / `client.tenants()`
- `client.assets.{ list, get, telemetry }`
- `client.market.{ rdn, vdr, br, dd, bids.list, bids.submit, revenue }`
- `client.dispatch.{ setpoints, telemetry, instructions }`
- `client.ems.{ forecasts, submitForecast, optimise, kpiDaily, kpiPortfolio }`
- `client.regulatory.{ settlements, documents, signDocument, events, submissions }`
- `client.agents.{ query, voiceSession }`
- `client.admin.{ portfolio, operations, analytics }`

## License

MIT.
