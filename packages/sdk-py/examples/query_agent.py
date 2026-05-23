"""Ask 3 questions to 3 different persona agents."""
import os
from gecko_vpp_sdk import GeckoVPPClient

with GeckoVPPClient(
    base_url=os.environ.get("GECKO_API", "http://localhost:8000"),
    tenant_id=os.environ.get("GECKO_TENANT", "11111111-1111-1111-1111-111111111111"),
) as client:
    questions = [
        ("dispatcher_analyst", "що сьогодні з виробництвом?"),
        ("market_analyst", "який очікуваний дохід на ВДР завтра?"),
        ("battery_coach", "чи варто заряджати батарею зараз?"),
    ]
    for persona, q in questions:
        print(f"\n[{persona}] ❓ {q}")
        res = client.agents_query(persona, q)
        print(f"  → {res['answer']}")
        print(f"  intent: {res['intent']}, confidence: {res['confidence']}")
        for e in res.get("evidence", []):
            print(f"  · {e['label']}: {e['value']}")
