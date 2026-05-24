import { NextRequest, NextResponse } from "next/server";

// POST /api/notify-visit
// Fired by <VisitNotifier /> on every page view (except admin-flagged devices).
// Sends a Telegram push to TELEGRAM_CHAT_ID via TELEGRAM_BOT_TOKEN bot.

export const runtime = "edge";

function parseDevice(ua: string): { device: string; os: string; browser: string } {
  let device = "desktop";
  if (/Tablet|iPad/i.test(ua)) device = "tablet";
  else if (/Mobile|Android|iPhone|iPod/i.test(ua)) device = "mobile";

  let os = "unknown";
  const macMatch = ua.match(/Mac OS X ([\d_]+)/);
  const winMatch = ua.match(/Windows NT ([\d.]+)/);
  const androidMatch = ua.match(/Android ([\d.]+)/);
  const iosMatch = ua.match(/(?:iPhone|iPad|iPod).*OS ([\d_]+)/);
  if (iosMatch) os = `iOS ${iosMatch[1].replace(/_/g, ".")}`;
  else if (androidMatch) os = `Android ${androidMatch[1]}`;
  else if (macMatch) os = `macOS ${macMatch[1].replace(/_/g, ".")}`;
  else if (winMatch) {
    const winMap: Record<string, string> = { "10.0": "10/11", "6.3": "8.1", "6.2": "8", "6.1": "7" };
    os = `Windows ${winMap[winMatch[1]] ?? winMatch[1]}`;
  } else if (/Linux/i.test(ua)) os = "Linux";

  let browser = "unknown";
  if (/Edg\//.test(ua)) browser = "Edge";
  else if (/Chrome\//.test(ua) && !/Chromium/.test(ua)) browser = "Chrome";
  else if (/Firefox\//.test(ua)) browser = "Firefox";
  else if (/Safari\//.test(ua)) browser = "Safari";

  return { device, os, browser };
}

export async function POST(req: NextRequest) {
  const token = process.env.TELEGRAM_BOT_TOKEN;
  const chatId = process.env.TELEGRAM_CHAT_ID;
  if (!token || !chatId) {
    return NextResponse.json({ ok: false, reason: "telegram-env-missing" }, { status: 200 });
  }

  const body = (await req.json().catch(() => ({}))) as { path?: string; referrer?: string };
  const path = body.path ?? "/";
  const referrer = body.referrer ?? "";

  const h = req.headers;
  const country = h.get("x-vercel-ip-country") ?? "??";
  const city = decodeURIComponent(h.get("x-vercel-ip-city") ?? "—");
  const region = h.get("x-vercel-ip-country-region") ?? "";
  const ua = h.get("user-agent") ?? "";
  const { device, os, browser } = parseDevice(ua);

  const text = [
    `🟢 <b>Krytsia visit</b>`,
    `📍 ${city}, ${country}${region ? ` (${region})` : ""}`,
    `📱 ${device} · ${os} · ${browser}`,
    `🔗 <code>${path}</code>`,
    referrer ? `↩️ from: ${referrer}` : null,
  ]
    .filter(Boolean)
    .join("\n");

  const tg = await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      chat_id: chatId,
      text,
      parse_mode: "HTML",
      disable_web_page_preview: true,
    }),
  });

  return NextResponse.json({ ok: tg.ok }, { status: 200 });
}
