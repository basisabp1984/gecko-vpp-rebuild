"""Market router: RDN, VDR, BR, DD, bids, revenue, ancillary."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from gecko_vpp.common.envelope import build_success
from gecko_vpp.common.pagination import (
    DateRange,
    Pagination,
    date_range_dep,
    pagination_dep,
)
from gecko_vpp.deps import get_session, get_tenant_id
from gecko_vpp.models.market import (
    AncillaryActivation,
    Bid,
    BrSettlement,
    DdContract,
    RdnPrice,
    VdrTrade,
)
from gecko_vpp.schemas.market import (
    AncillaryActivationOut,
    BidOut,
    BidSubmitIn,
    BrSettlementOut,
    DdContractOut,
    RdnPriceOut,
    RevenueChannelOut,
    RevenueSummaryOut,
    VdrTradeOut,
)

router = APIRouter(prefix="/api/v1/market", tags=["market"])


@router.get("/rdn", operation_id="market.rdn.list")
async def list_rdn(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
    date_range: Annotated[DateRange, Depends(date_range_dep)],
) -> dict[str, Any]:
    q = (
        select(RdnPrice)
        .where(RdnPrice.date >= date_range.date_start)
        .where(RdnPrice.date <= date_range.date_end)
        .order_by(RdnPrice.date, RdnPrice.hour)
        .limit(1000)
    )
    res = await session.execute(q)
    rows = list(res.scalars().all())
    data = [RdnPriceOut.model_validate(r).model_dump(mode="json") for r in rows]
    return build_success(data, tenant_id=tenant_id)


@router.get("/vdr", operation_id="market.vdr.list")
async def list_vdr(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
    date_range: Annotated[DateRange, Depends(date_range_dep)],
) -> dict[str, Any]:
    q = (
        select(VdrTrade)
        .where(VdrTrade.delivery_date >= date_range.date_start)
        .where(VdrTrade.delivery_date <= date_range.date_end)
        .order_by(VdrTrade.executed_at.desc())
        .limit(1000)
    )
    res = await session.execute(q)
    rows = list(res.scalars().all())
    data = [VdrTradeOut.model_validate(r).model_dump(mode="json") for r in rows]
    return build_success(data, tenant_id=tenant_id)


@router.get("/br", operation_id="market.br.list")
async def list_br(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
    date_range: Annotated[DateRange, Depends(date_range_dep)],
) -> dict[str, Any]:
    q = (
        select(BrSettlement)
        .where(BrSettlement.date >= date_range.date_start)
        .where(BrSettlement.date <= date_range.date_end)
        .order_by(BrSettlement.date, BrSettlement.hour)
        .limit(1000)
    )
    res = await session.execute(q)
    rows = list(res.scalars().all())
    data = [BrSettlementOut.model_validate(r).model_dump(mode="json") for r in rows]
    return build_success(data, tenant_id=tenant_id)


@router.get("/dd", operation_id="market.dd.list")
async def list_dd(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    q = select(DdContract).order_by(DdContract.start_date.desc()).limit(500)
    res = await session.execute(q)
    rows = list(res.scalars().all())
    data = [DdContractOut.model_validate(r).model_dump(mode="json") for r in rows]
    return build_success(data, tenant_id=tenant_id)


@router.get("/bids", operation_id="market.bids.list")
async def list_bids(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
    date_range: Annotated[DateRange, Depends(date_range_dep)],
    market: str | None = Query(None),
    pagination: Annotated[Pagination, Depends(pagination_dep)] = ...,  # type: ignore
) -> dict[str, Any]:
    q = (
        select(Bid)
        .where(Bid.delivery_date >= date_range.date_start)
        .where(Bid.delivery_date <= date_range.date_end)
    )
    if market:
        q = q.where(Bid.market == market)
    q = q.order_by(Bid.submitted_at.desc()).offset(pagination.offset).limit(
        pagination.per_page
    )
    res = await session.execute(q)
    rows = list(res.scalars().all())
    data = [BidOut.model_validate(r).model_dump(mode="json") for r in rows]
    return build_success(data, tenant_id=tenant_id)


@router.post("/bids", operation_id="market.bids.submit", status_code=201)
async def submit_bid(
    body: BidSubmitIn,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    from gecko_vpp.config import get_settings
    settings = get_settings()
    # Default participant_eic = tenant's participant_eic
    from gecko_vpp.models.core import Tenant
    from uuid import UUID as _UUID

    tres = await session.execute(
        select(Tenant).where(Tenant.id == _UUID(tenant_id))
    )
    tenant_row = tres.scalar_one()
    p_eic = body.participant_eic or tenant_row.participant_eic

    new_bid = Bid(
        tenant_id=_UUID(tenant_id),
        bid_id=f"BID-{uuid4().hex[:12].upper()}",
        market=body.market,
        delivery_date=body.delivery_date,
        hour=body.hour,
        side=body.side,
        bid_type=body.bid_type,
        volume_mwh=body.volume_mwh,
        price_uah_mwh=body.price_uah_mwh,
        resource_eic=body.resource_eic,
        participant_eic=p_eic,
        submitted_at=datetime.now(tz=timezone.utc),
        state="ACTIVE",
    )
    session.add(new_bid)
    await session.flush()
    await session.refresh(new_bid)
    data = BidOut.model_validate(new_bid).model_dump(mode="json")
    return build_success(data, tenant_id=tenant_id)


@router.get("/revenue", operation_id="market.revenue.summary")
async def revenue_summary(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
    date_range: Annotated[DateRange, Depends(date_range_dep)],
) -> dict[str, Any]:
    # RDN revenue ≈ sum(price × volume) — synthetic approximation
    rdn_res = await session.execute(
        select(func.coalesce(
            func.sum(RdnPrice.price_uah_mwh * RdnPrice.volume_mwh), 0
        )).where(
            RdnPrice.date.between(date_range.date_start, date_range.date_end)
        )
    )
    rdn_uah = Decimal(rdn_res.scalar_one() or 0)

    vdr_res = await session.execute(
        select(func.coalesce(
            func.sum(VdrTrade.price_uah_mwh * VdrTrade.volume_mwh), 0
        )).where(
            VdrTrade.delivery_date.between(date_range.date_start, date_range.date_end)
        )
    )
    vdr_uah = Decimal(vdr_res.scalar_one() or 0)

    br_res = await session.execute(
        select(func.coalesce(func.sum(BrSettlement.settlement_uah), 0)).where(
            BrSettlement.date.between(date_range.date_start, date_range.date_end)
        )
    )
    br_uah = Decimal(br_res.scalar_one() or 0)

    anc_res = await session.execute(
        select(func.coalesce(func.sum(AncillaryActivation.revenue_energy_uah), 0))
    )
    anc_uah = Decimal(anc_res.scalar_one() or 0)

    # DD + green tariff: not in synth, leave at 0.
    dd_uah = Decimal("0")
    green_uah = Decimal("0")
    total = rdn_uah + vdr_uah + br_uah + dd_uah + anc_uah + green_uah

    def _share(x: Decimal) -> float:
        return float(round((x / total * 100) if total else 0, 2))

    summary = RevenueSummaryOut(
        rdn_uah=rdn_uah,
        vdr_uah=vdr_uah,
        br_uah=br_uah,
        dd_uah=dd_uah,
        ancillary_uah=anc_uah,
        green_tariff_uah=green_uah,
        total_uah=total,
        by_channel=[
            RevenueChannelOut(channel="RDN", revenue_uah=rdn_uah, share_pct=_share(rdn_uah)),
            RevenueChannelOut(channel="VDR", revenue_uah=vdr_uah, share_pct=_share(vdr_uah)),
            RevenueChannelOut(channel="BR", revenue_uah=br_uah, share_pct=_share(br_uah)),
            RevenueChannelOut(channel="DD", revenue_uah=dd_uah, share_pct=_share(dd_uah)),
            RevenueChannelOut(channel="ANC", revenue_uah=anc_uah, share_pct=_share(anc_uah)),
        ],
    )
    return build_success(summary.model_dump(mode="json"), tenant_id=tenant_id)


@router.get("/ancillary", operation_id="market.ancillary.list")
async def list_ancillary(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
    date_range: Annotated[DateRange, Depends(date_range_dep)],
) -> dict[str, Any]:
    q = (
        select(AncillaryActivation)
        .where(AncillaryActivation.started_at >= datetime.combine(
            date_range.date_start, datetime.min.time(), tzinfo=timezone.utc
        ))
        .order_by(AncillaryActivation.started_at.desc())
        .limit(500)
    )
    res = await session.execute(q)
    rows = list(res.scalars().all())
    data = [AncillaryActivationOut.model_validate(r).model_dump(mode="json") for r in rows]
    return build_success(data, tenant_id=tenant_id)
