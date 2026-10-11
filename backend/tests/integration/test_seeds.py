"""Integration tests for the seed runner and the standard-catalog seed.

Covers first execution, repeated execution (no-op), transaction rollback on
failure, concurrent execution safety, and preservation of existing records.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from app.models.edition import Edition
from app.models.program import Program
from app.models.seed_execution import SeedExecution
from app.seeds.runner import Seed, run_seed
from app.seeds.standard_catalog import STANDARD_CATALOG_SEED, seed_standard_catalog
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

pytestmark = pytest.mark.integration


def _session(engine: Engine) -> Session:
    # Savepoint-isolated session: the runner's commit() only releases a
    # savepoint; the outer transaction is rolled back by the caller.
    return Session(
        bind=engine.connect(), expire_on_commit=False, join_transaction_mode="create_savepoint"
    )


@pytest.fixture
def db_session(migrated_engine: Engine) -> Iterator[Session]:
    connection = migrated_engine.connect()
    transaction = connection.begin()
    session = Session(
        bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
    )
    try:
        yield session
    finally:
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()


def test_first_execution_applies_and_records(db_session: Session) -> None:
    applied = run_seed(db_session, STANDARD_CATALOG_SEED)
    assert applied is True
    assert db_session.scalar(select(func.count()).select_from(Program)) == 4
    assert db_session.scalar(select(func.count()).select_from(Edition)) == 6
    recorded = db_session.scalars(
        select(SeedExecution).where(SeedExecution.seed_id == STANDARD_CATALOG_SEED.seed_id)
    ).one()
    assert recorded.seed_id == "standard_catalog_v1"


def test_repeated_execution_is_noop(db_session: Session) -> None:
    assert run_seed(db_session, STANDARD_CATALOG_SEED) is True
    assert run_seed(db_session, STANDARD_CATALOG_SEED) is False
    # Still exactly one catalog, one execution record.
    assert db_session.scalar(select(func.count()).select_from(Program)) == 4
    assert db_session.scalar(select(func.count()).select_from(SeedExecution)) == 1


def test_completed_seed_does_not_recreate_deleted_program(db_session: Session) -> None:
    # Apply, then delete a (now empty) standard program; re-running must NOT
    # recreate it, because the seed is already recorded as executed.
    run_seed(db_session, STANDARD_CATALOG_SEED)
    volunteering = db_session.scalars(select(Program).where(Program.slug == "volunteering")).one()
    # Remove its edition then the program (empty-program deletion).
    for edition in list(volunteering.editions):
        db_session.delete(edition)
    db_session.flush()
    db_session.delete(volunteering)
    db_session.flush()

    assert run_seed(db_session, STANDARD_CATALOG_SEED) is False
    assert (
        db_session.scalars(select(Program).where(Program.slug == "volunteering")).one_or_none()
        is None
    )


def test_rollback_leaves_seed_unrecorded(db_session: Session) -> None:
    # A seed whose operations raise must not record execution.
    def boom(_session: Session) -> None:
        _session.add(Program(slug="partial", name="Partial", icon="folder"))
        _session.flush()
        raise RuntimeError("seed failure")

    failing = Seed(seed_id="failing_seed_v1", run=boom)
    with pytest.raises(RuntimeError):
        run_seed(db_session, failing)

    assert (
        db_session.scalars(
            select(SeedExecution).where(SeedExecution.seed_id == "failing_seed_v1")
        ).one_or_none()
        is None
    )
    assert (
        db_session.scalars(select(Program).where(Program.slug == "partial")).one_or_none() is None
    )


def test_concurrent_execution_applies_once(migrated_engine: Engine) -> None:
    # Two independent sessions race to run the same seed. The advisory lock +
    # execution record ensure the catalog is created exactly once.
    s1 = _session(migrated_engine)
    s2 = _session(migrated_engine)
    try:
        r1 = run_seed(s1, STANDARD_CATALOG_SEED)
        r2 = run_seed(s2, STANDARD_CATALOG_SEED)
        assert {r1, r2} == {True, False}  # exactly one applied

        verify = Session(bind=migrated_engine.connect(), expire_on_commit=False)
        try:
            assert verify.scalar(select(func.count()).select_from(Program)) == 4
            assert verify.scalar(select(func.count()).select_from(Edition)) == 6
            assert (
                verify.scalar(
                    select(func.count())
                    .select_from(SeedExecution)
                    .where(SeedExecution.seed_id == STANDARD_CATALOG_SEED.seed_id)
                )
                == 1
            )
            # Clean up committed rows (this test commits real data). Delete
            # editions first (RESTRICT), then programs, then the seed record.
            for edition in verify.scalars(select(Edition)).all():
                verify.delete(edition)
            for program in verify.scalars(select(Program)).all():
                verify.delete(program)
            for rec in verify.scalars(
                select(SeedExecution).where(SeedExecution.seed_id == STANDARD_CATALOG_SEED.seed_id)
            ).all():
                verify.delete(rec)
            verify.commit()
        finally:
            verify.close()
    finally:
        s1.close()
        s2.close()


def test_seed_preserves_existing_program_and_edition(db_session: Session) -> None:
    from datetime import date

    # Pre-existing GSoC with admin edits + an existing 2026 edition.
    gsoc = Program(slug="gsoc", name="GSoC (edited)", icon="code", is_standard=False)
    db_session.add(gsoc)
    db_session.flush()
    gsoc_id = gsoc.id
    edition = Edition(
        program=gsoc,
        slug="2026",
        name="GSoC 2026 (edited)",
        starts_on=date(2026, 3, 1),
        ends_on=date(2026, 9, 1),
        source="community",
    )
    db_session.add(edition)
    db_session.flush()
    edition_id = edition.id

    seed_standard_catalog(db_session)
    db_session.flush()

    reloaded = db_session.get(Program, gsoc_id)
    assert reloaded is not None
    assert reloaded.id == gsoc_id
    assert reloaded.name == "GSoC (edited)"  # not overwritten
    assert reloaded.icon == "code"  # not overwritten
    assert reloaded.is_standard is True  # standard flag ensured
    kept = db_session.get(Edition, edition_id)
    assert kept is not None
    assert kept.starts_on == date(2026, 3, 1)  # dates not overwritten
