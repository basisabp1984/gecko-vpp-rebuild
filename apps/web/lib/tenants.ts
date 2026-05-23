/**
 * Demo tenant constants — fixed UUIDs from backend seed data.
 * See PROGRESS.md / Stage 4 — these UUIDs are stable across reseeds.
 */

export type TenantKind = "producer" | "ci" | "storage";

export interface Tenant {
  id: string;
  kind: TenantKind;
  name: string;
  description: string;
}

export const TENANTS: Record<TenantKind, Tenant> = {
  producer: {
    id: "11111111-1111-1111-1111-111111111111",
    kind: "producer",
    name: "Поляна Енерго",
    description: "СЕС + УЗЕ — виробник ВДЕ",
  },
  ci: {
    id: "22222222-2222-2222-2222-222222222222",
    kind: "ci",
    name: "Карпатський завод",
    description: "Активний споживач (C&I)",
  },
  storage: {
    id: "33333333-3333-3333-3333-333333333333",
    kind: "storage",
    name: "БСЗ Захід-1",
    description: "Власник УЗЕ (storage)",
  },
};

export const TENANT_LIST: Tenant[] = Object.values(TENANTS);

export const DEFAULT_TENANT_ID = TENANTS.producer.id;

export function getTenantById(id: string): Tenant | undefined {
  return TENANT_LIST.find((t) => t.id === id);
}
