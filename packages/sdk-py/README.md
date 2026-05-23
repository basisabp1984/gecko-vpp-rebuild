# gecko-vpp-sdk (Python)

Python SDK for the GECKO VPP REST API. Sync (httpx.Client) and async (httpx.AsyncClient) variants.

## Install

```bash
pip install gecko-vpp-sdk
```

## Quickstart

```python
from gecko_vpp_sdk import GeckoVPPClient

with GeckoVPPClient(
    base_url="https://api.gecko.radai-1984.dev",
    tenant_id="11111111-1111-1111-1111-111111111111",  # demo: producer
) as client:
    assets = client.assets()
    print(f"Active assets: {len(assets)}")

    rdn = client.market_rdn(date_start="2026-05-12", date_end="2026-05-12")
    print(f"РДН hours: {len(rdn)}, capped: {sum(1 for r in rdn if r['is_capped'])}")

    ans = client.agents_query("disp", "що сьогодні з виробництвом?")
    print(ans["answer"])
```

## Async

```python
import asyncio
from gecko_vpp_sdk import AsyncGeckoVPPClient

async def main():
    async with AsyncGeckoVPPClient(tenant_id="11111111-1111-1111-1111-111111111111") as client:
        rdn = await client.market_rdn(date_start="2026-05-12", date_end="2026-05-12")
        print(len(rdn))

asyncio.run(main())
```

## Demo tenants

| Tenant ID                              | Segment | Persona       |
| -------------------------------------- | ------- | ------------- |
| `11111111-1111-1111-1111-111111111111` | producer | Виробник      |
| `22222222-2222-2222-2222-222222222222` | c-i      | C&I prosumer  |
| `33333333-3333-3333-3333-333333333333` | storage  | УЗЕ-власник   |

## Examples

```bash
pip install -e .
python examples/list_assets.py
python examples/fetch_rdn.py
python examples/query_agent.py
```

## License

MIT.
