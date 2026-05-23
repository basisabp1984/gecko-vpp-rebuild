"""012 seed core lookups

Revision ID: 012_seed
Revises: 011_idx_grants
Create Date: 2026-05-23

Seeds:
  - core.tenants — 3 fixed-UUID rows (UUIDs match .env TENANT_*_UUID values
    so the FastAPI app + synth + tests all share the same identifiers).
  - core.eic_codes — Y/X/V starter set (BZN + 3 participant + 8 metering
    point codes). Per-asset W codes will be inserted by the synth generator
    when it creates `core.assets`.

This migration uses UPSERT (`ON CONFLICT DO UPDATE`) for tenants so
re-running on a fresh DB is safe and re-running on an existing DB is also
safe (idempotent reseed).

NOTE on RLS: migration 010 forced RLS on every table including core.tenants.
The migration role (`gecko` superuser) bypasses RLS even under FORCE? No —
FORCE means even owners cannot bypass. So we need to SET LOCAL the
session vars before inserting. We use `app.is_admin='true'` for migrations.
"""
from __future__ import annotations

from alembic import op

revision: str = "012_seed"
down_revision: str | None = "011_idx_grants"
branch_labels = None
depends_on = None


# UUIDs mirror .env at repo root. Single source of truth for tenant IDs
# across the API, synth, frontend, and tests.
TENANT_PRODUCER = "11111111-1111-1111-1111-111111111111"
TENANT_CI = "22222222-2222-2222-2222-222222222222"
TENANT_STORAGE = "33333333-3333-3333-3333-333333333333"


def upgrade() -> None:
    # SET LOCAL admin flag so the FORCE RLS policy allows our inserts.
    op.execute("SET LOCAL app.is_admin = 'true'")
    op.execute(f"SET LOCAL app.tenant_id = '{TENANT_PRODUCER}'")

    # --- tenants (UPSERT on code) ---
    op.execute(
        f"""
        INSERT INTO core.tenants
            (id, code, display_name, segment, edrpou, participant_eic, region, is_demo)
        VALUES
            ('{TENANT_PRODUCER}', 'producer-1', 'ТОВ "Поляна Енерджі"',
             'producer', '12345601', '10X-UA-PROD-001', 'Закарпатська', TRUE),
            ('{TENANT_CI}',       'ci-1',       'ПАТ "Дніпровий Завод"',
             'c-i',      '12345602', '10X-UA-C-I-0001', 'Дніпропетровська', TRUE),
            ('{TENANT_STORAGE}',  'storage-1',  'ТОВ "Запоріжжя Сторідж"',
             'storage',  '12345603', '10X-UA-STOR-001', 'Запорізька', TRUE)
        ON CONFLICT (code) DO UPDATE SET
            display_name    = EXCLUDED.display_name,
            segment         = EXCLUDED.segment,
            edrpou          = EXCLUDED.edrpou,
            participant_eic = EXCLUDED.participant_eic,
            region          = EXCLUDED.region;
        """
    )

    # --- eic_codes (UPSERT on eic primary key) ---
    # Mix:
    #   Y (areas/BZN)        — 2
    #   X (parties/participants) — 3
    #   V (metering points)  — 10
    # Per-asset W codes will be inserted by synth alongside core.assets.
    op.execute(
        """
        INSERT INTO core.eic_codes (eic, code_type, display_name, issuer) VALUES
            -- Y: bidding zones
            ('10Y1001C--00003F', 'Y', 'Україна, єдина BZN (з 2022)',          'ENTSO-E'),
            ('10YUA-WEPS-----0', 'Y', 'Україна WEPS (історично)',             'ENTSO-E'),
            -- X: participants (one per tenant)
            ('10X-UA-PROD-001',  'X', 'ТОВ "Поляна Енерджі" — учасник ринку', '10X-UA-NEC-001A'),
            ('10X-UA-C-I-0001',  'X', 'ПАТ "Дніпровий Завод" — учасник',      '10X-UA-NEC-001A'),
            ('10X-UA-STOR-001',  'X', 'ТОВ "Запоріжжя Сторідж" — учасник',    '10X-UA-NEC-001A'),
            -- V: metering points (placeholder set; synth assigns to assets)
            ('10V-UA-MP-000001', 'V', 'Точка обліку 01',                      '10X-UA-NEC-001A'),
            ('10V-UA-MP-000002', 'V', 'Точка обліку 02',                      '10X-UA-NEC-001A'),
            ('10V-UA-MP-000003', 'V', 'Точка обліку 03',                      '10X-UA-NEC-001A'),
            ('10V-UA-MP-000004', 'V', 'Точка обліку 04',                      '10X-UA-NEC-001A'),
            ('10V-UA-MP-000005', 'V', 'Точка обліку 05',                      '10X-UA-NEC-001A'),
            ('10V-UA-MP-000006', 'V', 'Точка обліку 06',                      '10X-UA-NEC-001A'),
            ('10V-UA-MP-000007', 'V', 'Точка обліку 07',                      '10X-UA-NEC-001A'),
            ('10V-UA-MP-000008', 'V', 'Точка обліку 08',                      '10X-UA-NEC-001A'),
            ('10V-UA-MP-000009', 'V', 'Точка обліку 09',                      '10X-UA-NEC-001A'),
            ('10V-UA-MP-000010', 'V', 'Точка обліку 10',                      '10X-UA-NEC-001A'),
            -- W: asset resource codes (placeholder pool; synth picks from these
            -- when creating core.assets so the FK to core.eic_codes is satisfied)
            ('10W-UA-ASSET-001', 'W', 'Ресурс асет 01',                       '10X-UA-NEC-001A'),
            ('10W-UA-ASSET-002', 'W', 'Ресурс асет 02',                       '10X-UA-NEC-001A'),
            ('10W-UA-ASSET-003', 'W', 'Ресурс асет 03',                       '10X-UA-NEC-001A'),
            ('10W-UA-ASSET-004', 'W', 'Ресурс асет 04',                       '10X-UA-NEC-001A'),
            ('10W-UA-ASSET-005', 'W', 'Ресурс асет 05',                       '10X-UA-NEC-001A'),
            ('10W-UA-ASSET-006', 'W', 'Ресурс асет 06',                       '10X-UA-NEC-001A'),
            ('10W-UA-ASSET-007', 'W', 'Ресурс асет 07',                       '10X-UA-NEC-001A'),
            ('10W-UA-ASSET-008', 'W', 'Ресурс асет 08',                       '10X-UA-NEC-001A'),
            ('10W-UA-ASSET-009', 'W', 'Ресурс асет 09',                       '10X-UA-NEC-001A'),
            ('10W-UA-ASSET-010', 'W', 'Ресурс асет 10',                       '10X-UA-NEC-001A'),
            ('10W-UA-ASSET-011', 'W', 'Ресурс асет 11',                       '10X-UA-NEC-001A'),
            ('10W-UA-ASSET-012', 'W', 'Ресурс асет 12',                       '10X-UA-NEC-001A')
        ON CONFLICT (eic) DO UPDATE SET
            display_name = EXCLUDED.display_name,
            issuer       = EXCLUDED.issuer;
        """
    )


def downgrade() -> None:
    op.execute("SET LOCAL app.is_admin = 'true'")
    op.execute("DELETE FROM core.eic_codes")
    op.execute("DELETE FROM core.tenants")
