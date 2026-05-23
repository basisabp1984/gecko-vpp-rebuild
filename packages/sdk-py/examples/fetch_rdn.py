"""Fetch one day of РДН prices and summarise."""
import os
from gecko_vpp_sdk import GeckoVPPClient

with GeckoVPPClient(
    base_url=os.environ.get("GECKO_API", "http://localhost:8000"),
    tenant_id=os.environ.get("GECKO_TENANT", "11111111-1111-1111-1111-111111111111"),
) as client:
    rdn = client.market_rdn(date_start="2026-05-12", date_end="2026-05-12")
    prices = [float(r["price_uah_mwh"]) for r in rdn]
    capped = sum(1 for r in rdn if r["is_capped"])

    print(f"РДН на 2026-05-12: {len(rdn)} годин")
    print(f"  максимум:    {max(prices):.2f} грн/МВт·год")
    print(f"  мінімум:     {min(prices):.2f} грн/МВт·год")
    print(f"  капнуто:     {capped} годин")
    print()
    print("год | ціна грн/МВт·год | об'єм МВт·год | капнуто")
    for r in rdn:
        mark = " ⚠️" if r["is_capped"] else ""
        vol = r["volume_mwh"] or "—"
        print(f"{r['hour']:>3} | {r['price_uah_mwh']:>16} | {vol:>13} |{mark}")
