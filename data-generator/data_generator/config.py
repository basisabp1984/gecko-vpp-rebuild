"""Centralised configuration: reads .env, exposes constants.

The .env file lives at the repo root (`gecko-vpp-rebuild/.env`).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from uuid import UUID

from dotenv import load_dotenv


# Repo root is two levels up from this file:
#   gecko-vpp-rebuild/data-generator/data_generator/config.py
_REPO_ROOT = Path(__file__).resolve().parents[2]
_DOTENV_PATH = _REPO_ROOT / ".env"

load_dotenv(_DOTENV_PATH)


def _env(key: str, default: str | None = None) -> str:
    val = os.getenv(key, default)
    if val is None:
        raise RuntimeError(f"Missing env var: {key}")
    return val


# ---------------------------------------------------------------------------
# DB
# ---------------------------------------------------------------------------

POSTGRES_HOST = _env("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(_env("POSTGRES_PORT", "5433"))
POSTGRES_DB = _env("POSTGRES_DB", "gecko_vpp")
POSTGRES_USER = _env("POSTGRES_USER", "gecko")
POSTGRES_PASSWORD = _env("POSTGRES_PASSWORD", "dev_local_pwd_2026")

DATABASE_URL = (
    f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)


# ---------------------------------------------------------------------------
# Window & RNG seed
# ---------------------------------------------------------------------------

SYNTH_DATE_START = date.fromisoformat(_env("SYNTH_DATE_START", "2026-04-23"))
SYNTH_DATE_END = date.fromisoformat(_env("SYNTH_DATE_END", "2026-05-23"))
SYNTH_RNG_SEED = int(_env("SYNTH_RNG_SEED", "42"))


def date_range_inclusive(start: date, end: date) -> list[date]:
    """Inclusive list of dates from start to end."""
    n = (end - start).days + 1
    return [start + timedelta(days=i) for i in range(n)]


# ---------------------------------------------------------------------------
# Tenants (fixed UUIDs — match migration 012 + .env)
# ---------------------------------------------------------------------------

TENANT_PRODUCER_UUID = UUID(_env("TENANT_PRODUCER_UUID", "11111111-1111-1111-1111-111111111111"))
TENANT_CI_UUID = UUID(_env("TENANT_CI_UUID", "22222222-2222-2222-2222-222222222222"))
TENANT_STORAGE_UUID = UUID(_env("TENANT_STORAGE_UUID", "33333333-3333-3333-3333-333333333333"))


@dataclass(frozen=True)
class TenantSpec:
    code: str
    uuid: UUID
    segment: str
    display_name: str
    edrpou: str
    participant_eic: str
    region: str


TENANTS: tuple[TenantSpec, ...] = (
    TenantSpec(
        code="producer-1",
        uuid=TENANT_PRODUCER_UUID,
        segment="producer",
        display_name='ТОВ "Поляна Енерджі"',
        edrpou="12345601",
        participant_eic="10X-UA-PROD-001 ",  # CHAR(16) → pad with space
        region="Закарпатська",
    ),
    TenantSpec(
        code="ci-1",
        uuid=TENANT_CI_UUID,
        segment="c-i",
        display_name='ПАТ "Дніпровий Завод"',
        edrpou="12345602",
        participant_eic="10X-UA-C-I-0001 ",
        region="Дніпропетровська",
    ),
    TenantSpec(
        code="storage-1",
        uuid=TENANT_STORAGE_UUID,
        segment="storage",
        display_name='ТОВ "Запоріжжя Сторідж"',
        edrpou="12345603",
        participant_eic="10X-UA-STOR-001 ",
        region="Запорізька",
    ),
)


# Default BZN EIC (UA-IPS), 16-char from migration 012 seed
BZN_EIC_UA_IPS = "10Y1001C--00003F"


# ---------------------------------------------------------------------------
# Market caps (PRODUCT_BRIEF §11.21 + research_market_data_shape.md §1)
# ---------------------------------------------------------------------------

RDN_CAP_DEFAULT = 6300  # UAH/MWh
RDN_CAP_PEAK = 6900     # evening peak hours
RDN_CAP_OFFPEAK = 5600  # off-peak

# Cap-pinning: probability that an evening-peak hour pins
CAP_PINNING_PROBABILITY = 0.40  # per-hour, evening peak only
CAP_PINNING_HOURS = (17, 18, 19, 20, 21)
