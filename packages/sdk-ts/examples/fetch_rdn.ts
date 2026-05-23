import { GeckoVPPClient } from "../src/index.js";

const client = new GeckoVPPClient({
  baseURL: process.env.GECKO_API ?? "http://localhost:8000",
  tenantId: process.env.GECKO_TENANT ?? "11111111-1111-1111-1111-111111111111",
});

const rdn = await client.market.rdn({ date_start: "2026-05-12", date_end: "2026-05-12" });

const capped = rdn.filter((r) => r.is_capped).length;
const max = rdn.reduce((m, r) => Math.max(m, Number(r.price_uah_mwh)), 0);
const min = rdn.reduce((m, r) => Math.min(m, Number(r.price_uah_mwh)), Infinity);

console.log(`РДН на 2026-05-12: ${rdn.length} годин`);
console.log(`  максимум:    ${max.toFixed(2)} грн/МВт·год`);
console.log(`  мінімум:     ${min.toFixed(2)} грн/МВт·год`);
console.log(`  капнуто:     ${capped} годин з обмеженням ціни`);
console.log();
console.log("год | ціна грн/МВт·год | об'єм МВт·год | капнуто");
for (const r of rdn) {
  const mark = r.is_capped ? " ⚠️" : "";
  console.log(`${String(r.hour).padStart(3)} | ${r.price_uah_mwh.padStart(16)} | ${(r.volume_mwh ?? "—").padStart(13)} | ${mark}`);
}
