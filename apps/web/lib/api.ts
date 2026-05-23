"use client";

import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { useTenantStore } from "./store";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

/* -------------------------------------------------------------------------- */
/* Envelope types                                                              */
/* -------------------------------------------------------------------------- */

export interface ResponseMeta {
  request_id?: string;
  tenant_id?: string;
  generated_at?: string;
  [key: string]: unknown;
}

export interface ApiResponse<T> {
  data: T;
  meta: ResponseMeta;
}

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
}

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly details: Record<string, unknown>;

  constructor(
    message: string,
    code: string,
    status: number,
    details: Record<string, unknown> = {},
  ) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

/* -------------------------------------------------------------------------- */
/* Low-level fetch                                                             */
/* -------------------------------------------------------------------------- */

export interface FetchOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  tenantId?: string;
  query?: Record<string, string | number | boolean | undefined | null>;
}

export async function fetchAPI<T>(
  path: string,
  opts: FetchOptions = {},
): Promise<ApiResponse<T>> {
  const { body, tenantId, query, headers, ...rest } = opts;

  // Build URL with query string
  let url = path.startsWith("http")
    ? path
    : `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;
  if (query) {
    const sp = new URLSearchParams();
    for (const [k, v] of Object.entries(query)) {
      if (v !== undefined && v !== null && v !== "") sp.append(k, String(v));
    }
    const qs = sp.toString();
    if (qs) url += (url.includes("?") ? "&" : "?") + qs;
  }

  const finalHeaders: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
    ...(headers as Record<string, string> | undefined),
  };

  // Resolve tenant id (override → store → none)
  const resolvedTenant =
    tenantId ??
    (typeof window !== "undefined"
      ? useTenantStore.getState().currentTenantId
      : undefined);
  if (resolvedTenant) finalHeaders["X-Tenant-Id"] = resolvedTenant;

  const res = await fetch(url, {
    ...rest,
    headers: finalHeaders,
    body: body !== undefined ? JSON.stringify(body) : undefined,
    cache: "no-store",
  });

  const text = await res.text();
  let json: unknown = null;
  if (text) {
    try {
      json = JSON.parse(text);
    } catch {
      throw new ApiError(
        `Невалідна відповідь сервера (${res.status})`,
        "PARSE_ERROR",
        res.status,
      );
    }
  }

  if (!res.ok || (json && typeof json === "object" && "error" in json)) {
    const errBody = json as ApiErrorBody | null;
    const err = errBody?.error;
    throw new ApiError(
      err?.message ?? `Помилка ${res.status}`,
      err?.code ?? "HTTP_ERROR",
      res.status,
      err?.details ?? {},
    );
  }

  return json as ApiResponse<T>;
}

/* -------------------------------------------------------------------------- */
/* React Query wrapper                                                         */
/* -------------------------------------------------------------------------- */

export function useAPI<T>(
  path: string | null,
  params?: FetchOptions["query"],
  options?: Omit<
    UseQueryOptions<ApiResponse<T>, ApiError>,
    "queryKey" | "queryFn"
  >,
) {
  const tenantId = useTenantStore((s) => s.currentTenantId);
  return useQuery<ApiResponse<T>, ApiError>({
    queryKey: ["api", path, params, tenantId],
    queryFn: () => fetchAPI<T>(path as string, { query: params }),
    enabled: path !== null,
    staleTime: 60_000,
    ...options,
  });
}
