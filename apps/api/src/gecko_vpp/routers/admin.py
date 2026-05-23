"""Admin router (cross-tenant). Uses admin session — sets app.is_admin='true'."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from gecko_vpp.common.envelope import build_success
from gecko_vpp.common.pagination import SYNTH_DATE_END
from gecko_vpp.deps import get_admin_session
from gecko_vpp.models.core import Asset, Tenant
from gecko_vpp.models.dispatch import Setpoint, Telemetry
from gecko_vpp.models.ems import KpiDaily
from gecko_vpp.models.market import BrSettlement, RdnPrice, VdrTrade
from gecko_vpp.schemas.admin import (
    AdminAnalyticsOut,
    AdminAnalyticsRow,
    AdminOperationsOut,
    AdminOperationsRow,
    AdminPortfolioOut,
    TenantPortfolioRow,
)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get("/portfolio", operation_id="admin.portfolio")
async def admin_portfolio(
    session: Annotated[AsyncSession, Depends(get_admin_session)],
) -> dict[str, Any]:
    # All tenants
    tres = await session.execute(select(Tenant).order_by(Tenant.code))
    tenants = list(tres.scalars().all())

    rows: list[TenantPortfolioRow] = []
    total_cap = Decimal("0")
    total_rev = Decimal("0")
    end = SYNTH_DATE_END
    start = end - timedelta(days=29)

    for t in tenants:
        # asset count + capacity
        ares = await session.execute(
            select(
                func.count(Asset.id),
                func.coalesce(func.sum(Asset.capacity_mw), 0),
            ).where(Asset.tenant_id == t.id)
        )
        asset_count, capacity = ares.one()

        # revenue approx — sum of RDN + VDR + BR for the tenant
        rdn_res = await session.execute(
            select(func.coalesce(
                func.sum(RdnPrice.price_uah_mwh * RdnPrice.volume_mwh), 0
            )).where(RdnPrice.tenant_id == t.id).where(
                RdnPrice.date.between(start, end)
            )
        )
        vdr_res = await session.execute(
            select(func.coalesce(
                func.sum(VdrTrade.price_uah_mwh * VdrTrade.volume_mwh), 0
            )).where(VdrTrade.tenant_id == t.id).where(
                VdrTrade.delivery_date.between(start, end)
            )
        )
        br_res = await session.execute(
            select(func.coalesce(func.sum(BrSettlement.settlement_uah), 0))
            .where(BrSettlement.tenant_id == t.id)
            .where(BrSettlement.date.between(start, end))
        )
        rev = Decimal(rdn_res.scalar_one() or 0) + Decimal(vdr_res.scalar_one() or 0) + Decimal(br_res.scalar_one() or 0)

        rows.append(TenantPortfolioRow(
            tenant_id=t.id,
            code=t.code,
            display_name=t.display_name,
            segment=t.segment,
            asset_count=int(asset_count),
            capacity_mw=Decimal(capacity),
            revenue_30d_uah=rev,
        ))
        total_cap += Decimal(capacity)
        total_rev += rev

    out = AdminPortfolioOut(
        tenants=rows,
        total_capacity_mw=total_cap,
        total_revenue_30d_uah=total_rev,
    )
    return build_success(out.model_dump(mode="json"))


@router.get("/operations", operation_id="admin.operations")
async def admin_operations(
    session: Annotated[AsyncSession, Depends(get_admin_session)],
) -> dict[str, Any]:
    tres = await session.execute(select(Tenant).order_by(Tenant.code))
    tenants = list(tres.scalars().all())
    end = SYNTH_DATE_END
    start = end - timedelta(days=1)

    rows: list[AdminOperationsRow] = []
    for t in tenants:
        sp_res = await session.execute(
            select(func.count(Setpoint.id)).where(Setpoint.tenant_id == t.id)
            .where(Setpoint.effective_from >= start)
        )
        tel_res = await session.execute(
            select(
                func.count(),
                func.coalesce(func.avg(Telemetry.availability_pct), 0),
            )
            .where(Telemetry.tenant_id == t.id)
            .where(Telemetry.date >= start)
        )
        tel_count, avg_avail = tel_res.one()
        rows.append(AdminOperationsRow(
            tenant_id=t.id,
            code=t.code,
            setpoints_24h=int(sp_res.scalar_one() or 0),
            telemetry_rows_24h=int(tel_count or 0),
            avg_availability_pct=Decimal(avg_avail or 0),
        ))
    out = AdminOperationsOut(rows=rows)
    return build_success(out.model_dump(mode="json"))


@router.get("/analytics", operation_id="admin.analytics")
async def admin_analytics(
    session: Annotated[AsyncSession, Depends(get_admin_session)],
) -> dict[str, Any]:
    tres = await session.execute(select(Tenant).order_by(Tenant.code))
    tenants = list(tres.scalars().all())
    end = SYNTH_DATE_END
    start = end - timedelta(days=29)

    rows: list[AdminAnalyticsRow] = []
    for t in tenants:
        res = await session.execute(
            select(
                func.coalesce(func.sum(KpiDaily.co2_avoided_tn), 0),
                func.coalesce(func.sum(KpiDaily.grn_earned_uah), 0),
                func.coalesce(func.avg(KpiDaily.opportunity_score), 0),
            )
            .where(KpiDaily.tenant_id == t.id)
            .where(KpiDaily.date.between(start, end))
        )
        co2, grn, opp = res.one()
        rows.append(AdminAnalyticsRow(
            tenant_id=t.id,
            code=t.code,
            co2_avoided_tn_30d=Decimal(co2 or 0),
            grn_earned_uah_30d=Decimal(grn or 0),
            opportunity_score_avg=Decimal(opp or 0),
        ))
    out = AdminAnalyticsOut(rows=rows)
    return build_success(out.model_dump(mode="json"))
