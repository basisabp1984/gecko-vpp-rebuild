"""EMS router: forecasts, optimisation, KPI."""

from __future__ import annotations

import hashlib
import json
import random
import time
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from gecko_vpp.common.envelope import build_success
from gecko_vpp.common.pagination import (
    DateRange,
    Pagination,
    SYNTH_DATE_END,
    date_range_dep,
    pagination_dep,
)
from gecko_vpp.deps import get_session, get_tenant_id
from gecko_vpp.models.core import Asset
from gecko_vpp.models.ems import (
    Forecast,
    ForecastActual,
    KpiDaily,
    OptimisationRun,
)
from gecko_vpp.models.market import RdnPrice
from gecko_vpp.models.regulatory import ForecastSubmission
from gecko_vpp.schemas.ems import (
    ForecastActualOut,
    ForecastOut,
    ForecastSubmissionOut,
    ForecastSubmitIn,
    KpiDailyOut,
    KpiPortfolioOut,
    OptimiseIn,
    OptimiseOut,
    RecommendationOut,
)

router = APIRouter(prefix="/api/v1/ems", tags=["ems"])


# ---- forecasts ----


@router.get("/forecasts", operation_id="ems.forecasts.list")
async def list_forecasts(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
    date_range: Annotated[DateRange, Depends(date_range_dep)],
    type: str | None = Query(None, alias="type"),
    asset_id: UUID | None = Query(None),
    pagination: Annotated[Pagination, Depends(pagination_dep)] = ...,  # type: ignore
) -> dict[str, Any]:
    q = (
        select(Forecast)
        .where(Forecast.date >= date_range.date_start)
        .where(Forecast.date <= date_range.date_end)
    )
    if type:
        q = q.where(Forecast.forecast_kind == type)
    if asset_id:
        q = q.where(Forecast.asset_id == asset_id)
    q = q.order_by(Forecast.date, Forecast.hour).offset(pagination.offset).limit(
        pagination.per_page
    )
    res = await session.execute(q)
    rows = list(res.scalars().all())
    data = [ForecastOut.model_validate(r).model_dump(mode="json") for r in rows]
    return build_success(data, tenant_id=tenant_id)


@router.get("/forecasts/actuals", operation_id="ems.forecasts.actuals")
async def list_forecast_actuals(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
    date_range: Annotated[DateRange, Depends(date_range_dep)],
    asset_id: UUID | None = Query(None),
    pagination: Annotated[Pagination, Depends(pagination_dep)] = ...,  # type: ignore
) -> dict[str, Any]:
    q = (
        select(ForecastActual)
        .where(ForecastActual.date >= date_range.date_start)
        .where(ForecastActual.date <= date_range.date_end)
    )
    if asset_id:
        q = q.where(ForecastActual.asset_id == asset_id)
    q = q.order_by(ForecastActual.date, ForecastActual.hour).offset(
        pagination.offset
    ).limit(pagination.per_page)
    res = await session.execute(q)
    rows = list(res.scalars().all())
    data = [ForecastActualOut.model_validate(r).model_dump(mode="json") for r in rows]
    return build_success(data, tenant_id=tenant_id)


@router.post(
    "/forecasts/submit",
    operation_id="ems.forecasts.submit",
    status_code=201,
)
async def submit_forecast(
    body: ForecastSubmitIn,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    from gecko_vpp.models.core import Tenant
    tres = await session.execute(
        select(Tenant).where(Tenant.id == UUID(tenant_id))
    )
    tenant_row = tres.scalar_one()

    sub = ForecastSubmission(
        tenant_id=UUID(tenant_id),
        submission_id=f"FS-{uuid4().hex[:12].upper()}",
        submitter_eic=body.submitter_eic or tenant_row.participant_eic,
        resource_eic=body.resource_eic,
        business_type=body.business_type,
        document_type=body.document_type,
        process_type=body.process_type,
        delivery_date=body.delivery_date,
        resolution_minutes=body.resolution_minutes,
        hourly_volumes_mwh=body.hourly_volumes_mwh,
        status="DRAFT",
    )
    session.add(sub)
    await session.flush()
    await session.refresh(sub)
    return build_success(
        ForecastSubmissionOut.model_validate(sub).model_dump(mode="json"),
        tenant_id=tenant_id,
    )


# ---- optimiser ----


@router.post("/optimise", operation_id="ems.optimise.run")
async def run_optimise(
    body: OptimiseIn,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    t0 = time.monotonic()

    target_date = body.date or SYNTH_DATE_END
    horizon = max(1, min(int(body.horizon_hours), 24))

    # Resolve asset_ids: if empty, take all tenant assets (limit 6).
    asset_ids: list[UUID] = list(body.asset_ids)
    if not asset_ids:
        ares = await session.execute(
            select(Asset.id).where(Asset.tenant_id == UUID(tenant_id)).limit(6)
        )
        asset_ids = [r[0] for r in ares.all()]

    # Pull RDN prices for target_date
    pres = await session.execute(
        select(RdnPrice.hour, RdnPrice.price_uah_mwh)
        .where(RdnPrice.date == target_date)
        .order_by(RdnPrice.hour)
        .limit(24)
    )
    prices: dict[int, Decimal] = {row[0]: Decimal(row[1]) for row in pres.all()}
    if not prices:
        # Fallback: use most recent date with prices
        latest = await session.execute(
            select(func.max(RdnPrice.date))
        )
        ld = latest.scalar_one()
        if ld:
            pres = await session.execute(
                select(RdnPrice.hour, RdnPrice.price_uah_mwh)
                .where(RdnPrice.date == ld)
                .order_by(RdnPrice.hour)
            )
            prices = {row[0]: Decimal(row[1]) for row in pres.all()}

    # Deterministic seed from canonical inputs.
    inputs_canonical = {
        "scenario": body.scenario,
        "horizon_hours": horizon,
        "asset_ids": sorted(str(a) for a in asset_ids),
        "date": target_date.isoformat(),
    }
    inputs_hash = hashlib.sha256(
        json.dumps(inputs_canonical, sort_keys=True).encode("utf-8")
    ).hexdigest()
    rng = random.Random(int(inputs_hash[:16], 16))

    # Compute price deciles for arbitrage scenario
    sorted_prices = sorted(prices.items(), key=lambda x: x[1]) if prices else []
    n = len(sorted_prices)
    cheap_hours = {h for h, _ in sorted_prices[: max(1, n // 4)]}
    expensive_hours = {h for h, _ in sorted_prices[max(0, n - max(1, n // 4)):]}
    median_price = (
        sorted_prices[n // 2][1] if sorted_prices else Decimal("4000")
    )

    recommendations: list[dict[str, Any]] = []
    uplift = Decimal("0")
    risk_flags: list[str] = []

    for aid in asset_ids:
        for h in range(1, horizon + 1):
            price = prices.get(h, median_price)
            if body.scenario == "arbitrage":
                if h in expensive_hours:
                    action = "discharge"
                    mw = Decimal(f"{rng.uniform(2.0, 4.5):.3f}")
                    uplift += (price - median_price) * mw
                elif h in cheap_hours:
                    action = "charge"
                    mw = Decimal(f"{rng.uniform(2.0, 4.5):.3f}")
                else:
                    continue
            elif body.scenario == "capacity":
                # Recommend full capacity in top 6 expensive hours
                if h in expensive_hours:
                    action = "discharge"
                    mw = Decimal(f"{rng.uniform(3.0, 5.0):.3f}")
                    uplift += price * mw * Decimal("0.05")
                else:
                    continue
            else:  # day_ahead — recommend a flat schedule
                action = "hold"
                mw = Decimal(f"{rng.uniform(1.0, 2.0):.3f}")
                uplift += median_price * mw * Decimal("0.01")
            recommendations.append({
                "asset_id": str(aid),
                "hour": h,
                "action": action,
                "mw": str(mw),
            })

    if any(p > Decimal("6500") for p in prices.values()):
        risk_flags.append("cap_exposure")
    if not prices:
        risk_flags.append("no_prices")

    duration_ms = int((time.monotonic() - t0) * 1000)
    if duration_ms > 1800:
        risk_flags.append("near_timeout")

    confidence = Decimal("85.00")

    run_row = OptimisationRun(
        tenant_id=UUID(tenant_id),
        scenario=body.scenario,
        inputs_hash=inputs_hash,
        inputs=inputs_canonical,
        recommendations={"items": recommendations},
        expected_uplift_uah=uplift,
        risk_flags=risk_flags,
        confidence_pct=confidence,
        duration_ms=duration_ms,
        completed_at=datetime.now(tz=timezone.utc),
    )
    session.add(run_row)
    await session.flush()
    await session.refresh(run_row)

    out = OptimiseOut(
        run_id=run_row.id,
        scenario=body.scenario,
        recommendations=[
            RecommendationOut(
                asset_id=UUID(r["asset_id"]),
                hour=r["hour"],
                action=r["action"],
                mw=Decimal(r["mw"]),
            )
            for r in recommendations
        ],
        expected_uplift_uah=uplift,
        uplift_uah=uplift,
        confidence_pct=confidence,
        confidence=0.85,
        risk_flags=risk_flags,
        duration_ms=duration_ms,
        inputs_hash=inputs_hash,
    )
    return build_success(out.model_dump(mode="json"), tenant_id=tenant_id)


# ---- KPI ----


@router.get("/kpi/daily", operation_id="ems.kpi.daily")
async def kpi_daily(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
    date_range: Annotated[DateRange, Depends(date_range_dep)],
) -> dict[str, Any]:
    q = (
        select(KpiDaily)
        .where(KpiDaily.date >= date_range.date_start)
        .where(KpiDaily.date <= date_range.date_end)
        .order_by(KpiDaily.date.desc())
        .limit(1000)
    )
    res = await session.execute(q)
    rows = list(res.scalars().all())
    data = [KpiDailyOut.model_validate(r).model_dump(mode="json") for r in rows]
    return build_success(data, tenant_id=tenant_id)


@router.get("/kpi/portfolio", operation_id="ems.kpi.portfolio")
async def kpi_portfolio(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
    range: str = Query("30d", description="30d | 7d | window"),
) -> dict[str, Any]:
    # parse range
    if range.endswith("d"):
        try:
            days = int(range[:-1])
        except ValueError:
            days = 30
    else:
        days = 30
    end = SYNTH_DATE_END
    start = end - timedelta(days=days - 1)

    res = await session.execute(
        select(
            func.coalesce(func.sum(KpiDaily.grn_saved_uah), 0),
            func.coalesce(func.sum(KpiDaily.grn_earned_uah), 0),
            func.coalesce(func.sum(KpiDaily.imbalance_mwh), 0),
            func.coalesce(func.sum(KpiDaily.co2_avoided_tn), 0),
            func.coalesce(func.avg(KpiDaily.availability_pct), 0),
            func.count(func.distinct(KpiDaily.asset_id)),
        ).where(KpiDaily.date.between(start, end))
    )
    grn_saved, grn_earned, imb, co2, avail, n_assets = res.one()

    payload = KpiPortfolioOut(
        range=range,
        grn_saved_uah=Decimal(grn_saved),
        grn_earned_uah=Decimal(grn_earned),
        revenue_uah=Decimal(grn_earned),
        imbalance_mwh=Decimal(imb),
        co2_avoided_tn=Decimal(co2),
        availability_pct=Decimal(avail),
        asset_count=int(n_assets),
    )
    return build_success(payload.model_dump(mode="json"), tenant_id=tenant_id)
