"""GECKO VPP synthetic data generator.

Populates Postgres with 30 days (2026-04-23 → 2026-05-23) of realistic
Ukrainian-energy synthetic data covering every §11 acceptance criterion
from PRODUCT_BRIEF v0.4.

Entry point:  ``python -m data_generator.main``
Coverage:     ``python -m data_generator.coverage``
"""

__version__ = "0.1.0"
