import { NextResponse } from "next/server";

/**
 * Proxy /api/openapi → ${NEXT_PUBLIC_API_BASE}/openapi.json
 * Same-origin OpenAPI feed for the Scalar explorer, avoids CORS.
 */
export async function GET() {
  const base = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000";
  try {
    const upstream = await fetch(`${base}/openapi.json`, {
      // never cache — backend OpenAPI may change frequently in dev
      cache: "no-store",
    });
    if (!upstream.ok) {
      return NextResponse.json(
        { error: { code: "UPSTREAM_FAIL", message: `OpenAPI upstream ${upstream.status}` } },
        { status: 502 },
      );
    }
    const spec = await upstream.json();
    return NextResponse.json(spec, {
      headers: {
        "Cache-Control": "no-store",
      },
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return NextResponse.json(
      { error: { code: "UPSTREAM_UNREACHABLE", message } },
      { status: 502 },
    );
  }
}
