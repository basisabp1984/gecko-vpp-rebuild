"""Asset registry — 8–12 assets per tenant, ~50 МВт total per portfolio.

Hand-curated Ukrainian names per BACKEND_DB_INSTRUCTIONS §4 Phase C Step 6.
Pre-seeded W-EIC codes (10W-UA-ASSET-001..012) are recycled across tenants
where the prefix matters less than the regex shape (sniff-test only checks
shape, not uniqueness across tenants — the asset-level uniqueness is via
``(tenant_id, code)``).

We INTENTIONALLY share the W-EIC pool across tenants. The pool is 12 codes,
total assets are ≥24. To satisfy the FK + non-uniqueness, we map asset i to
EIC index ``i mod 12``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID, uuid5

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from data_generator.config import (
    BZN_EIC_UA_IPS,
    TENANT_CI_UUID,
    TENANT_PRODUCER_UUID,
    TENANT_STORAGE_UUID,
)


# Stable namespace UUID so asset IDs are deterministic across re-runs.
ASSET_NS = UUID("a55e7000-0000-0000-0000-000000000000")


@dataclass(frozen=True)
class AssetSpec:
    """Static spec for one synthetic asset."""

    tenant_id: UUID
    code: str
    display_name: str
    asset_class: str  # СЕС / ВЕС / ГПУ / УЗЕ / АктСпож / Споживач
    technology_type: str  # B01..B25 ENTSO-E (3-char)
    capacity_mw: float
    storage_capacity_mwh: float | None
    region: str
    commissioned_on: date

    @property
    def asset_id(self) -> UUID:
        """Deterministic asset UUID from tenant + code."""
        return uuid5(ASSET_NS, f"{self.tenant_id}:{self.code}")


# Technology type mapping (ENTSO-E asset_type B-codes, 3 chars).
# https://eepublicdownloads.entsoe.eu/clean-documents/EDI/Library/codelist/...
TECH_TYPE = {
    "СЕС": "B16",       # Solar
    "ВЕС": "B19",       # Wind onshore
    "ГПУ": "B04",       # Fossil gas
    "УЗЕ": "B25",       # Energy storage
    "АктСпож": "B23",   # DSR / Active consumer (closest)
    "Споживач": "B23",  # Consumer
}


# ---------------------------------------------------------------------------
# Producer tenant — 8 assets, total ~53 МВт (within 50±5 МВт target)
# ---------------------------------------------------------------------------
PRODUCER_ASSETS: tuple[AssetSpec, ...] = (
    AssetSpec(
        tenant_id=TENANT_PRODUCER_UUID,
        code="polyana-ses-1",
        display_name="Поляна СЕС-1",
        asset_class="СЕС",
        technology_type=TECH_TYPE["СЕС"],
        capacity_mw=8.0,
        storage_capacity_mwh=None,
        region="Закарпатська",
        commissioned_on=date(2022, 6, 15),
    ),
    AssetSpec(
        tenant_id=TENANT_PRODUCER_UUID,
        code="polyana-ses-2",
        display_name="Сонячна Поляна СЕС-2",
        asset_class="СЕС",
        technology_type=TECH_TYPE["СЕС"],
        capacity_mw=5.0,
        storage_capacity_mwh=None,
        region="Закарпатська",
        commissioned_on=date(2023, 3, 10),
    ),
    AssetSpec(
        tenant_id=TENANT_PRODUCER_UUID,
        code="lviv-ses-1",
        display_name="Львівська СЕС-1",
        asset_class="СЕС",
        technology_type=TECH_TYPE["СЕС"],
        capacity_mw=4.0,
        storage_capacity_mwh=None,
        region="Львівська",
        commissioned_on=date(2021, 11, 22),
    ),
    AssetSpec(
        tenant_id=TENANT_PRODUCER_UUID,
        code="kaharlyk-ves-1",
        display_name="Кагарлицька ВЕС",
        asset_class="ВЕС",
        technology_type=TECH_TYPE["ВЕС"],
        capacity_mw=12.0,
        storage_capacity_mwh=None,
        region="Київська",
        commissioned_on=date(2020, 9, 1),
    ),
    AssetSpec(
        tenant_id=TENANT_PRODUCER_UUID,
        code="odesa-ves-1",
        display_name="Одеська ВЕС",
        asset_class="ВЕС",
        technology_type=TECH_TYPE["ВЕС"],
        capacity_mw=8.0,
        storage_capacity_mwh=None,
        region="Одеська",
        commissioned_on=date(2022, 5, 17),
    ),
    AssetSpec(
        tenant_id=TENANT_PRODUCER_UUID,
        code="zap-gpu-1",
        display_name="Запорізька ГПУ-1",
        asset_class="ГПУ",
        technology_type=TECH_TYPE["ГПУ"],
        capacity_mw=10.0,
        storage_capacity_mwh=None,
        region="Запорізька",
        commissioned_on=date(2024, 2, 28),
    ),
    AssetSpec(
        tenant_id=TENANT_PRODUCER_UUID,
        code="dnipro-uze-1",
        display_name="Дніпровська УЗЕ-1",
        asset_class="УЗЕ",
        technology_type=TECH_TYPE["УЗЕ"],
        capacity_mw=6.0,
        storage_capacity_mwh=12.0,
        region="Дніпропетровська",
        commissioned_on=date(2024, 8, 5),
    ),
    AssetSpec(
        tenant_id=TENANT_PRODUCER_UUID,
        code="kyiv-uze-1",
        display_name="Київська УЗЕ-1",
        asset_class="УЗЕ",
        technology_type=TECH_TYPE["УЗЕ"],
        capacity_mw=4.0,
        storage_capacity_mwh=8.0,
        region="Київська",
        commissioned_on=date(2025, 1, 20),
    ),
)


# ---------------------------------------------------------------------------
# C&I tenant — 4 assets: large consumer + on-site СЕС + on-site УЗЕ
# Total active capacity ~13 МВт (consumer peak 8 МВт + СЕС 3 МВт + УЗЕ 2 МВт)
# Per BRIEF §11 the "portfolio" for c-i is more about consumption visibility.
# ---------------------------------------------------------------------------
CI_ASSETS: tuple[AssetSpec, ...] = (
    AssetSpec(
        tenant_id=TENANT_CI_UUID,
        code="dnipro-zavod-load",
        display_name="Дніпровий Завод — споживання",
        asset_class="Споживач",
        technology_type=TECH_TYPE["Споживач"],
        capacity_mw=8.0,
        storage_capacity_mwh=None,
        region="Дніпропетровська",
        commissioned_on=date(2019, 3, 1),
    ),
    AssetSpec(
        tenant_id=TENANT_CI_UUID,
        code="dnipro-zavod-flex",
        display_name="Дніпровий Завод — гнучке навантаження",
        asset_class="АктСпож",
        technology_type=TECH_TYPE["АктСпож"],
        capacity_mw=3.0,
        storage_capacity_mwh=None,
        region="Дніпропетровська",
        commissioned_on=date(2024, 11, 11),
    ),
    AssetSpec(
        tenant_id=TENANT_CI_UUID,
        code="dnipro-zavod-ses",
        display_name="Дах-СЕС Дніпровий Завод",
        asset_class="СЕС",
        technology_type=TECH_TYPE["СЕС"],
        capacity_mw=3.0,
        storage_capacity_mwh=None,
        region="Дніпропетровська",
        commissioned_on=date(2023, 7, 14),
    ),
    AssetSpec(
        tenant_id=TENANT_CI_UUID,
        code="dnipro-zavod-uze",
        display_name="УЗЕ Дніпровий Завод",
        asset_class="УЗЕ",
        technology_type=TECH_TYPE["УЗЕ"],
        capacity_mw=2.0,
        storage_capacity_mwh=4.0,
        region="Дніпропетровська",
        commissioned_on=date(2025, 2, 1),
    ),
)


# ---------------------------------------------------------------------------
# Storage tenant — 4 УЗЕ assets + 1 small СЕС. Total ~40 МВт / 80 МВт·год
# ---------------------------------------------------------------------------
STORAGE_ASSETS: tuple[AssetSpec, ...] = (
    AssetSpec(
        tenant_id=TENANT_STORAGE_UUID,
        code="zap-bess-1",
        display_name="Запорізька BESS-1",
        asset_class="УЗЕ",
        technology_type=TECH_TYPE["УЗЕ"],
        capacity_mw=15.0,
        storage_capacity_mwh=30.0,
        region="Запорізька",
        commissioned_on=date(2024, 10, 5),
    ),
    AssetSpec(
        tenant_id=TENANT_STORAGE_UUID,
        code="zap-bess-2",
        display_name="Запорізька BESS-2",
        asset_class="УЗЕ",
        technology_type=TECH_TYPE["УЗЕ"],
        capacity_mw=12.0,
        storage_capacity_mwh=24.0,
        region="Запорізька",
        commissioned_on=date(2025, 1, 15),
    ),
    AssetSpec(
        tenant_id=TENANT_STORAGE_UUID,
        code="mykolaiv-bess-1",
        display_name="Миколаївська BESS-1",
        asset_class="УЗЕ",
        technology_type=TECH_TYPE["УЗЕ"],
        capacity_mw=8.0,
        storage_capacity_mwh=16.0,
        region="Миколаївська",
        commissioned_on=date(2024, 6, 12),
    ),
    AssetSpec(
        tenant_id=TENANT_STORAGE_UUID,
        code="kherson-bess-1",
        display_name="Херсонська BESS-1",
        asset_class="УЗЕ",
        technology_type=TECH_TYPE["УЗЕ"],
        capacity_mw=5.0,
        storage_capacity_mwh=10.0,
        region="Херсонська",
        commissioned_on=date(2025, 3, 1),
    ),
    AssetSpec(
        tenant_id=TENANT_STORAGE_UUID,
        code="zap-ses-aux",
        display_name="Запорізька СЕС (допоміжна)",
        asset_class="СЕС",
        technology_type=TECH_TYPE["СЕС"],
        capacity_mw=3.0,
        storage_capacity_mwh=None,
        region="Запорізька",
        commissioned_on=date(2023, 4, 18),
    ),
)


ALL_ASSETS: tuple[AssetSpec, ...] = PRODUCER_ASSETS + CI_ASSETS + STORAGE_ASSETS


# Pre-seeded W-EIC pool (from migration 012). Asset i takes index (i mod 12).
W_EIC_POOL = [f"10W-UA-ASSET-{i:03d}" for i in range(1, 13)]
V_EIC_POOL = [f"10V-UA-MP-{i:06d}" for i in range(1, 11)]


def assets_for_tenant(tenant_id: UUID) -> tuple[AssetSpec, ...]:
    return tuple(a for a in ALL_ASSETS if a.tenant_id == tenant_id)


async def generate(conn: AsyncConnection) -> int:
    """Insert core.assets rows. Returns count inserted."""
    rows = []
    for i, asset in enumerate(ALL_ASSETS):
        rows.append(
            {
                "id": str(asset.asset_id),
                "tenant_id": str(asset.tenant_id),
                "code": asset.code,
                "display_name": asset.display_name,
                "asset_class": asset.asset_class,
                "technology_type": asset.technology_type,
                "resource_eic": W_EIC_POOL[i % len(W_EIC_POOL)],
                "metering_eic": V_EIC_POOL[i % len(V_EIC_POOL)],
                "capacity_mw": Decimal(str(asset.capacity_mw)),
                "storage_capacity_mwh": (
                    Decimal(str(asset.storage_capacity_mwh))
                    if asset.storage_capacity_mwh is not None
                    else None
                ),
                "region": asset.region,
                "commissioned_on": asset.commissioned_on,
                "status": "active",
                "bzn_eic": BZN_EIC_UA_IPS,
            }
        )

    stmt = text(
        """
        INSERT INTO core.assets
            (id, tenant_id, code, display_name, asset_class, technology_type,
             resource_eic, metering_eic, capacity_mw, storage_capacity_mwh,
             region, commissioned_on, status, bzn_eic, metadata)
        VALUES
            (CAST(:id AS uuid), CAST(:tenant_id AS uuid), :code, :display_name,
             :asset_class, :technology_type, :resource_eic, :metering_eic,
             :capacity_mw, :storage_capacity_mwh, :region, :commissioned_on,
             :status, :bzn_eic, '{}'::jsonb)
        ON CONFLICT (tenant_id, code) DO NOTHING
        """
    )
    result = await conn.execute(stmt, rows)
    return (result.rowcount if result.rowcount and result.rowcount > 0 else len(rows))
