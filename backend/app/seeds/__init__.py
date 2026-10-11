"""Data seeds.

A seed is an idempotent, version-controlled population of baseline data (e.g.
the standard program catalog). The :mod:`app.seeds.runner` executes pending
seeds exactly once per database, recording success in ``seed_executions`` in the
same transaction as the seed's operations.

Seeds are NOT a database reset mechanism: they only insert what is missing and
never delete business data.
"""
