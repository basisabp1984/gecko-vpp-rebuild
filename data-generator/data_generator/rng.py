"""Seeded RNG factory.

Determinism contract (ARCHITECTURE.md §3.11.4): identical SYNTH_RNG_SEED →
identical generated data. NEVER call ``numpy.random.*`` directly; always go
through :func:`get_rng` so we control the seed graph.

Per-generator child seeds derived from the master seed + a string tag so two
generators that consume "the same" RNG can't accidentally interfere by being
re-ordered.
"""

from __future__ import annotations

import hashlib
from functools import lru_cache

import numpy as np

from data_generator.config import SYNTH_RNG_SEED


def _child_seed(parent_seed: int, tag: str) -> int:
    """Deterministic 64-bit child seed from parent seed + textual tag."""
    h = hashlib.sha256(f"{parent_seed}|{tag}".encode()).digest()
    return int.from_bytes(h[:8], "big") & 0x7FFF_FFFF_FFFF_FFFF


@lru_cache(maxsize=None)
def get_rng(tag: str) -> np.random.Generator:
    """Return a fresh np.random.Generator seeded deterministically for ``tag``.

    Cached so repeated calls with the same tag return the same generator
    state stream (call sites must not assume independence across calls of the
    same tag).
    """
    seed = _child_seed(SYNTH_RNG_SEED, tag)
    return np.random.default_rng(seed)


def reset_cache() -> None:
    """Drop all cached RNGs (used by --reset to ensure full determinism)."""
    get_rng.cache_clear()
