"""List all assets in the demo portfolio."""
import os
from gecko_vpp_sdk import GeckoVPPClient

with GeckoVPPClient(
    base_url=os.environ.get("GECKO_API", "http://localhost:8000"),
    tenant_id=os.environ.get("GECKO_TENANT", "11111111-1111-1111-1111-111111111111"),
) as client:
    assets = client.assets()
    print(f"Found {len(assets)} assets:")
    for a in assets:
        print(f"  {a['code']:<20} {a['display_name']:<30} {a['asset_class']:<8} {a['capacity_mw']:>7} МВт  {a.get('region') or ''}")
