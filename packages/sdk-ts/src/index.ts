import type {
  Envelope,
  ErrorEnvelope,
  Tenant,
  Asset,
  RDNPrice,
  AgentResponse,
  KPIPortfolio,
  Persona,
} from "./types.js";

export * from "./types.js";

export interface GeckoVPPClientOptions {
  baseURL?: string;
  tenantId: string;
  fetch?: typeof fetch;
}

/**
 * Thin client for the GECKO VPP REST API.
 *
 *   import { GeckoVPPClient } from "@gecko-vpp/sdk-ts";
 *
 *   const client = new GeckoVPPClient({
 *     baseURL: "https://api.gecko.radai-1984.dev",
 *     tenantId: "11111111-1111-1111-1111-111111111111",
 *   });
 *
 *   const rdn = await client.market.rdn({ dateStart: "2026-05-01", dateEnd: "2026-05-07" });
 */
export class GeckoVPPClient {
  readonly baseURL: string;
  readonly tenantId: string;
  private readonly _fetch: typeof fetch;

  constructor(opts: GeckoVPPClientOptions) {
    this.baseURL = (opts.baseURL ?? "https://api.gecko.radai-1984.dev").replace(/\/$/, "");
    this.tenantId = opts.tenantId;
    this._fetch = opts.fetch ?? globalThis.fetch.bind(globalThis);
  }

  private async _request<T>(method: string, path: string, body?: unknown): Promise<T> {
    const res = await this._fetch(`${this.baseURL}${path}`, {
      method,
      headers: {
        "X-Tenant-Id": this.tenantId,
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    if (!res.ok) {
      const err = (await res.json().catch(() => ({}))) as ErrorEnvelope;
      const msg = err?.error?.message ?? `HTTP ${res.status}`;
      throw new GeckoVPPError(msg, err?.error?.code ?? "HTTP_ERROR", res.status, err?.error?.details);
    }
    const env = (await res.json()) as Envelope<T>;
    return env.data;
  }

  private _qs(params: Record<string, string | number | boolean | undefined | null>): string {
    const parts: string[] = [];
    for (const [k, v] of Object.entries(params)) {
      if (v === undefined || v === null) continue;
      parts.push(`${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`);
    }
    return parts.length ? `?${parts.join("&")}` : "";
  }

  // Core
  healthz = () => this._request<{ status: string }>("GET", "/api/v1/healthz");
  me = () => this._request<{ tenant_id: string; tenant: Tenant; current_user: { name: string } }>("GET", "/api/v1/auth/me");
  tenants = () => this._request<Tenant[]>("GET", "/api/v1/tenants");

  // Assets
  assets = {
    list: (params: { asset_type?: string; segment?: string; active?: boolean } = {}) =>
      this._request<Asset[]>("GET", `/api/v1/assets${this._qs(params)}`),
    get: (id: string) => this._request<Asset>("GET", `/api/v1/assets/${id}`),
    telemetry: (id: string, params: { date_start?: string; date_end?: string } = {}) =>
      this._request<unknown[]>("GET", `/api/v1/assets/${id}/telemetry${this._qs(params)}`),
  };

  // Market
  market = {
    rdn: (params: { date_start?: string; date_end?: string } = {}) =>
      this._request<RDNPrice[]>("GET", `/api/v1/market/rdn${this._qs(params)}`),
    vdr: (params: { date_start?: string; date_end?: string } = {}) =>
      this._request<unknown[]>("GET", `/api/v1/market/vdr${this._qs(params)}`),
    br: (params: { date_start?: string; date_end?: string } = {}) =>
      this._request<unknown[]>("GET", `/api/v1/market/br${this._qs(params)}`),
    dd: () => this._request<unknown[]>("GET", "/api/v1/market/dd"),
    bids: {
      list: (params: { date_start?: string; date_end?: string } = {}) =>
        this._request<unknown[]>("GET", `/api/v1/market/bids${this._qs(params)}`),
      submit: (body: unknown) => this._request<unknown>("POST", "/api/v1/market/bids", body),
    },
    revenue: (params: { date_start?: string; date_end?: string } = {}) =>
      this._request<unknown>("GET", `/api/v1/market/revenue${this._qs(params)}`),
  };

  // Dispatch
  dispatch = {
    setpoints: (params: { asset_id?: string; date_start?: string; date_end?: string } = {}) =>
      this._request<unknown[]>("GET", `/api/v1/dispatch/setpoints${this._qs(params)}`),
    telemetry: (params: { asset_id?: string; date_start?: string; date_end?: string } = {}) =>
      this._request<unknown[]>("GET", `/api/v1/dispatch/telemetry${this._qs(params)}`),
    instructions: (params: { date_start?: string; date_end?: string } = {}) =>
      this._request<unknown[]>("GET", `/api/v1/dispatch/instructions${this._qs(params)}`),
  };

  // EMS
  ems = {
    forecasts: (params: { type?: string; asset_id?: string; date_start?: string; date_end?: string } = {}) =>
      this._request<unknown[]>("GET", `/api/v1/ems/forecasts${this._qs(params)}`),
    submitForecast: (body: unknown) =>
      this._request<unknown>("POST", "/api/v1/ems/forecasts/submit", body),
    optimise: (body: { scenario: "arbitrage" | "capacity" | "day_ahead"; date: string }) =>
      this._request<unknown>("POST", "/api/v1/ems/optimise", body),
    kpiDaily: (params: { date_start?: string; date_end?: string } = {}) =>
      this._request<unknown[]>("GET", `/api/v1/ems/kpi/daily${this._qs(params)}`),
    kpiPortfolio: (params: { range?: string } = {}) =>
      this._request<KPIPortfolio>("GET", `/api/v1/ems/kpi/portfolio${this._qs(params)}`),
  };

  // Regulatory
  regulatory = {
    settlements: (params: { period?: string } = {}) =>
      this._request<unknown[]>("GET", `/api/v1/regulatory/settlements${this._qs(params)}`),
    documents: () => this._request<unknown[]>("GET", "/api/v1/regulatory/documents"),
    signDocument: (id: string) =>
      this._request<unknown>("POST", `/api/v1/regulatory/documents/${id}/sign`),
    events: (params: { date_start?: string; date_end?: string } = {}) =>
      this._request<unknown[]>("GET", `/api/v1/regulatory/events${this._qs(params)}`),
    submissions: (params: { date_start?: string; date_end?: string } = {}) =>
      this._request<unknown[]>("GET", `/api/v1/regulatory/submissions${this._qs(params)}`),
  };

  // Agents
  agents = {
    query: (persona: Persona, question: string) =>
      this._request<AgentResponse>("POST", `/api/v1/agents/${persona}/query`, { question }),
    voiceSession: () =>
      this._request<{ provider: string; session_token: string | null; websocket_url: string | null }>(
        "GET",
        "/api/v1/agents/voice/session",
      ),
  };

  // Admin
  admin = {
    portfolio: () => this._request<unknown>("GET", "/api/v1/admin/portfolio"),
    operations: () => this._request<unknown>("GET", "/api/v1/admin/operations"),
    analytics: () => this._request<unknown>("GET", "/api/v1/admin/analytics"),
  };
}

export class GeckoVPPError extends Error {
  constructor(
    message: string,
    public readonly code: string,
    public readonly status: number,
    public readonly details?: unknown,
  ) {
    super(message);
    this.name = "GeckoVPPError";
  }
}
