import { GeckoVPPClient } from "../src/index.js";

const client = new GeckoVPPClient({
  baseURL: process.env.GECKO_API ?? "http://localhost:8000",
  tenantId: process.env.GECKO_TENANT ?? "11111111-1111-1111-1111-111111111111",
});

const questions: Array<[string, "dispatcher_analyst" | "market_analyst" | "energy_advisor" | "battery_coach"]> = [
  ["що сьогодні з виробництвом?", "dispatcher_analyst"],
  ["який очікуваний дохід на ВДР завтра?", "market_analyst"],
  ["чи варто заряджати батарею зараз?", "battery_coach"],
];

for (const [q, persona] of questions) {
  console.log(`\n[${persona}] ❓ ${q}`);
  const res = await client.agents.query(persona, q);
  console.log(`  → ${res.answer}`);
  console.log(`  intent: ${res.intent}, confidence: ${res.confidence}`);
  if (res.evidence?.length) {
    for (const e of res.evidence) {
      console.log(`  · ${e.label}: ${e.value}`);
    }
  }
}
