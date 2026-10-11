"""Ordered registry of all data seeds run during deployment."""

from __future__ import annotations

from app.seeds.runner import Seed
from app.seeds.standard_catalog import STANDARD_CATALOG_SEED

ALL_SEEDS: list[Seed] = [
    STANDARD_CATALOG_SEED,
]
