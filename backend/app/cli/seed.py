"""Run pending data seeds.

Documented deployment command: ``make seed`` (or
``python -m app.cli.seed``). Runs every registered seed that has not yet been
recorded in ``seed_executions``. Idempotent and safe to rerun; concurrent runs
are serialized by a per-seed advisory lock. Seeds never delete business data.
"""

from __future__ import annotations

import sys

from app.seeds.registry import ALL_SEEDS
from app.seeds.runner import run_pending, session_scope


def main() -> int:
    with session_scope() as session:
        results = run_pending(session, ALL_SEEDS)
    applied = [sid for sid, did in results.items() if did]
    skipped = [sid for sid, did in results.items() if not did]
    for sid in applied:
        print(f"Seed '{sid}': applied.")
    for sid in skipped:
        print(f"Seed '{sid}': already executed; skipped.")
    print(f"Seeds complete: {len(applied)} applied, {len(skipped)} skipped.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
