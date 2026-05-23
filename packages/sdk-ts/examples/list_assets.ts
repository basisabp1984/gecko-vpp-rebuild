import { GeckoVPPClient } from "../src/index.js";

const client = new GeckoVPPClient({
  baseURL: process.env.GECKO_API ?? "http://localhost:8000",
  tenantId: process.env.GECKO_TENANT ?? "11111111-1111-1111-1111-111111111111",
});

const assets = await client.assets.list();
console.log(`Found ${assets.length} assets:`);
for (const a of assets) {
  console.log(`  ${a.code.padEnd(20)} ${a.display_name.padEnd(30)} ${a.asset_class.padEnd(8)} ${a.capacity_mw} МВт  ${a.region ?? ""}`);
}
