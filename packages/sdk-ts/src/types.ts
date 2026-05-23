/**
 * Hand-rolled types mirroring the FastAPI response envelopes.
 * For full schema coverage regenerate via `openapi-typescript packages/openapi/openapi.json`.
 */

export type Segment = "producer" | "c-i" | "storage";

export interface Envelope<T> {
  data: T;
  meta: {
    request_id: string;
    tenant_id: string | null;
    generated_at: string;
    pagination?: {
      page: number;
      per_page: number;
      total?: number | null;
    };
  };
}

export interface ErrorEnvelope {
  error: {
    code: string;
    message: string;
    details?: unknown;
  };
}

export interface Tenant {
  id: string;
  code: string;
  display_name: string;
  segment: Segment;
  edrpou: string;
  participant_eic: string;
  bzn_eic: string;
  region: string | null;
  created_at: string;
  is_demo: boolean;
}

export interface Asset {
  id: string;
  tenant_id: string;
  code: string;
  display_name: string;
  asset_class: "СЕС" | "ВЕС" | "ГПУ" | "УЗЕ" | "active_consumer" | "consumer";
  technology_type: string;
  resource_eic: string;
  metering_eic: string;
  capacity_mw: string;
  storage_capacity_mwh?: string | null;
  region: string;
  commissioned_on?: string | null;
  status: string;
  bzn_eic: string;
}

export interface RDNPrice {
  date: string;
  hour: number;
  interval_start: string;
  price_uah_mwh: string;
  volume_mwh: string | null;
  is_capped: boolean;
  cap_uah_mwh?: string | null;
  daily_index_base?: string | null;
  daily_index_peak?: string | null;
  daily_index_offpeak?: string | null;
  bidding_zone_eic: string;
}

export interface AgentResponse {
  answer: string;
  intent: string;
  confidence: number;
  evidence: Array<{
    label: string;
    value: string;
    source?: string;
  }>;
}

export interface KPIPortfolio {
  range: string;
  grn_saved_uah: string;
  grn_earned_uah: string;
  revenue_uah: string;
  imbalance_mwh: string;
  co2_avoided_tn: string;
  availability_pct: string;
  asset_count: number;
}

export type Persona = "dispatcher_analyst" | "market_analyst" | "energy_advisor" | "battery_coach";
