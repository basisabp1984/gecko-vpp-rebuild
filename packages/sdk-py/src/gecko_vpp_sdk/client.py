"""Thin Python wrapper for the GECKO VPP REST API."""
from __future__ import annotations

from typing import Any, Literal, Optional
from urllib.parse import urlencode

import httpx


Persona = Literal["dispatcher_analyst", "market_analyst", "energy_advisor", "battery_coach"]
Scenario = Literal["arbitrage", "capacity", "day_ahead"]


class GeckoVPPError(Exception):
    def __init__(self, message: str, code: str, status: int, details: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.status = status
        self.details = details


def _build_qs(params: dict[str, Any]) -> str:
    clean = {k: v for k, v in params.items() if v is not None}
    return f"?{urlencode(clean)}" if clean else ""


class _BaseClient:
    """Shared URL/headers logic for sync and async clients."""

    def __init__(
        self,
        tenant_id: str,
        base_url: str = "https://api.gecko.radai-1984.dev",
        timeout: float = 10.0,
    ) -> None:
        self.tenant_id = tenant_id
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {
            "X-Tenant-Id": self.tenant_id,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }


class GeckoVPPClient(_BaseClient):
    """Synchronous client.

        client = GeckoVPPClient(tenant_id="11111111-1111-1111-1111-111111111111")
        rdn = client.market_rdn(date_start="2026-05-12", date_end="2026-05-12")
        print(f"РДН: {len(rdn)} hours")
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._client = httpx.Client(timeout=self.timeout)

    def __enter__(self) -> "GeckoVPPClient":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def _request(self, method: str, path: str, json: Any | None = None) -> Any:
        resp = self._client.request(
            method,
            f"{self.base_url}{path}",
            headers=self._headers(),
            json=json,
        )
        if resp.is_success:
            return resp.json()["data"]
        try:
            err = resp.json()["error"]
            raise GeckoVPPError(err.get("message", f"HTTP {resp.status_code}"), err.get("code", "HTTP_ERROR"), resp.status_code, err.get("details"))
        except (ValueError, KeyError):
            raise GeckoVPPError(f"HTTP {resp.status_code}", "HTTP_ERROR", resp.status_code) from None

    # Core
    def healthz(self) -> dict[str, Any]:
        return self._request("GET", "/api/v1/healthz")

    def me(self) -> dict[str, Any]:
        return self._request("GET", "/api/v1/auth/me")

    def tenants(self) -> list[dict[str, Any]]:
        return self._request("GET", "/api/v1/tenants")

    # Assets
    def assets(self, asset_type: Optional[str] = None, segment: Optional[str] = None, active: Optional[bool] = None) -> list[dict[str, Any]]:
        return self._request("GET", "/api/v1/assets" + _build_qs({"asset_type": asset_type, "segment": segment, "active": active}))

    def asset(self, asset_id: str) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/assets/{asset_id}")

    def asset_telemetry(self, asset_id: str, date_start: Optional[str] = None, date_end: Optional[str] = None) -> list[dict[str, Any]]:
        return self._request("GET", f"/api/v1/assets/{asset_id}/telemetry" + _build_qs({"date_start": date_start, "date_end": date_end}))

    # Market
    def market_rdn(self, date_start: Optional[str] = None, date_end: Optional[str] = None) -> list[dict[str, Any]]:
        return self._request("GET", "/api/v1/market/rdn" + _build_qs({"date_start": date_start, "date_end": date_end}))

    def market_vdr(self, date_start: Optional[str] = None, date_end: Optional[str] = None) -> list[dict[str, Any]]:
        return self._request("GET", "/api/v1/market/vdr" + _build_qs({"date_start": date_start, "date_end": date_end}))

    def market_br(self, date_start: Optional[str] = None, date_end: Optional[str] = None) -> list[dict[str, Any]]:
        return self._request("GET", "/api/v1/market/br" + _build_qs({"date_start": date_start, "date_end": date_end}))

    def market_dd(self) -> list[dict[str, Any]]:
        return self._request("GET", "/api/v1/market/dd")

    def market_bids(self, date_start: Optional[str] = None, date_end: Optional[str] = None) -> list[dict[str, Any]]:
        return self._request("GET", "/api/v1/market/bids" + _build_qs({"date_start": date_start, "date_end": date_end}))

    def market_submit_bid(self, body: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/api/v1/market/bids", json=body)

    def market_revenue(self, date_start: Optional[str] = None, date_end: Optional[str] = None) -> dict[str, Any]:
        return self._request("GET", "/api/v1/market/revenue" + _build_qs({"date_start": date_start, "date_end": date_end}))

    # Dispatch
    def dispatch_setpoints(self, asset_id: Optional[str] = None, date_start: Optional[str] = None, date_end: Optional[str] = None) -> list[dict[str, Any]]:
        return self._request("GET", "/api/v1/dispatch/setpoints" + _build_qs({"asset_id": asset_id, "date_start": date_start, "date_end": date_end}))

    def dispatch_telemetry(self, asset_id: Optional[str] = None, date_start: Optional[str] = None, date_end: Optional[str] = None) -> list[dict[str, Any]]:
        return self._request("GET", "/api/v1/dispatch/telemetry" + _build_qs({"asset_id": asset_id, "date_start": date_start, "date_end": date_end}))

    def dispatch_instructions(self, date_start: Optional[str] = None, date_end: Optional[str] = None) -> list[dict[str, Any]]:
        return self._request("GET", "/api/v1/dispatch/instructions" + _build_qs({"date_start": date_start, "date_end": date_end}))

    # EMS
    def ems_forecasts(self, type: Optional[str] = None, asset_id: Optional[str] = None, date_start: Optional[str] = None, date_end: Optional[str] = None) -> list[dict[str, Any]]:
        return self._request("GET", "/api/v1/ems/forecasts" + _build_qs({"type": type, "asset_id": asset_id, "date_start": date_start, "date_end": date_end}))

    def ems_submit_forecast(self, body: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/api/v1/ems/forecasts/submit", json=body)

    def ems_optimise(self, scenario: Scenario, date: str) -> dict[str, Any]:
        return self._request("POST", "/api/v1/ems/optimise", json={"scenario": scenario, "date": date})

    def ems_kpi_daily(self, date_start: Optional[str] = None, date_end: Optional[str] = None) -> list[dict[str, Any]]:
        return self._request("GET", "/api/v1/ems/kpi/daily" + _build_qs({"date_start": date_start, "date_end": date_end}))

    def ems_kpi_portfolio(self, range: str = "week") -> dict[str, Any]:
        return self._request("GET", "/api/v1/ems/kpi/portfolio" + _build_qs({"range": range}))

    # Regulatory
    def regulatory_settlements(self, period: Optional[str] = None) -> list[dict[str, Any]]:
        return self._request("GET", "/api/v1/regulatory/settlements" + _build_qs({"period": period}))

    def regulatory_documents(self) -> list[dict[str, Any]]:
        return self._request("GET", "/api/v1/regulatory/documents")

    def regulatory_sign_document(self, document_id: str) -> dict[str, Any]:
        return self._request("POST", f"/api/v1/regulatory/documents/{document_id}/sign")

    def regulatory_events(self, date_start: Optional[str] = None, date_end: Optional[str] = None) -> list[dict[str, Any]]:
        return self._request("GET", "/api/v1/regulatory/events" + _build_qs({"date_start": date_start, "date_end": date_end}))

    def regulatory_submissions(self, date_start: Optional[str] = None, date_end: Optional[str] = None) -> list[dict[str, Any]]:
        return self._request("GET", "/api/v1/regulatory/submissions" + _build_qs({"date_start": date_start, "date_end": date_end}))

    # Agents
    def agents_query(self, persona: Persona, question: str) -> dict[str, Any]:
        return self._request("POST", f"/api/v1/agents/{persona}/query", json={"question": question})

    def agents_voice_session(self) -> dict[str, Any]:
        return self._request("GET", "/api/v1/agents/voice/session")

    # Admin
    def admin_portfolio(self) -> dict[str, Any]:
        return self._request("GET", "/api/v1/admin/portfolio")

    def admin_operations(self) -> dict[str, Any]:
        return self._request("GET", "/api/v1/admin/operations")

    def admin_analytics(self) -> dict[str, Any]:
        return self._request("GET", "/api/v1/admin/analytics")


class AsyncGeckoVPPClient(_BaseClient):
    """Async client (httpx.AsyncClient)."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._client = httpx.AsyncClient(timeout=self.timeout)

    async def __aenter__(self) -> "AsyncGeckoVPPClient":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _request(self, method: str, path: str, json: Any | None = None) -> Any:
        resp = await self._client.request(method, f"{self.base_url}{path}", headers=self._headers(), json=json)
        if resp.is_success:
            return resp.json()["data"]
        try:
            err = resp.json()["error"]
            raise GeckoVPPError(err.get("message", f"HTTP {resp.status_code}"), err.get("code", "HTTP_ERROR"), resp.status_code, err.get("details"))
        except (ValueError, KeyError):
            raise GeckoVPPError(f"HTTP {resp.status_code}", "HTTP_ERROR", resp.status_code) from None

    async def healthz(self) -> dict[str, Any]:
        return await self._request("GET", "/api/v1/healthz")

    async def market_rdn(self, date_start: Optional[str] = None, date_end: Optional[str] = None) -> list[dict[str, Any]]:
        return await self._request("GET", "/api/v1/market/rdn" + _build_qs({"date_start": date_start, "date_end": date_end}))

    async def assets(self, asset_type: Optional[str] = None) -> list[dict[str, Any]]:
        return await self._request("GET", "/api/v1/assets" + _build_qs({"asset_type": asset_type}))

    async def agents_query(self, persona: Persona, question: str) -> dict[str, Any]:
        return await self._request("POST", f"/api/v1/agents/{persona}/query", json={"question": question})
