"""Admin Program/Edition management API (M1-09).

All endpoints require platform superadmin authorization (reusing M1-07's
``require_superadmin``); state-changing endpoints additionally require the
double-submit CSRF check (``require_csrf``). ORM models are never returned
directly — explicit Pydantic response schemas are used throughout.

No DELETE endpoints (M1-08 uses ON DELETE RESTRICT to preserve history). No
lifecycle transition state machine. Project endpoints and omegaUp
synchronization are out of scope.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.authz import require_superadmin
from app.auth.dependencies import require_csrf
from app.db.session import get_db
from app.schemas.edition import EditionCreate, EditionResponse, EditionUpdate
from app.schemas.program import ProgramCreate, ProgramResponse, ProgramUpdate
from app.services.program import ConflictError, ProgramService, ValidationError

# Every route depends on require_superadmin -> 401 anonymous, 403 non-admin.
router = APIRouter(
    prefix="/api/admin",
    tags=["admin-programs"],
    dependencies=[Depends(require_superadmin)],
)


def _conflict(exc: ConflictError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


def _unprocessable(exc: ValidationError) -> HTTPException:
    # 422 Unprocessable Content (status code 422); the numeric literal avoids a
    # Starlette deprecation of the older constant name.
    return HTTPException(status_code=422, detail=str(exc))


# --- Programs ----------------------------------------------------------------


@router.get("/programs", response_model=list[ProgramResponse])
def list_programs(db: Session = Depends(get_db)) -> list[ProgramResponse]:
    service = ProgramService(db)
    return [ProgramResponse.model_validate(p) for p in service.list_programs()]


@router.post(
    "/programs",
    response_model=ProgramResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_program(payload: ProgramCreate, db: Session = Depends(get_db)) -> ProgramResponse:
    service = ProgramService(db)
    try:
        program = service.create_program(
            slug=payload.slug,
            name=payload.name,
            kind=payload.kind,
            description=payload.description,
        )
    except ConflictError as exc:
        raise _conflict(exc) from exc
    return ProgramResponse.model_validate(program)


@router.get("/programs/{program_id}", response_model=ProgramResponse)
def read_program(program_id: uuid.UUID, db: Session = Depends(get_db)) -> ProgramResponse:
    service = ProgramService(db)
    program = service.get_program(program_id)
    if program is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Program not found.")
    return ProgramResponse.model_validate(program)


@router.patch(
    "/programs/{program_id}",
    response_model=ProgramResponse,
    dependencies=[Depends(require_csrf)],
)
def update_program(
    program_id: uuid.UUID, payload: ProgramUpdate, db: Session = Depends(get_db)
) -> ProgramResponse:
    service = ProgramService(db)
    program = service.get_program(program_id)
    if program is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Program not found.")
    updated = service.update_program(
        program,
        name=payload.name,
        kind=payload.kind,
        description=payload.description,
        provided=set(payload.model_fields_set),
    )
    return ProgramResponse.model_validate(updated)


# --- Editions ----------------------------------------------------------------


@router.get(
    "/programs/{program_id}/editions",
    response_model=list[EditionResponse],
)
def list_editions(program_id: uuid.UUID, db: Session = Depends(get_db)) -> list[EditionResponse]:
    service = ProgramService(db)
    if service.get_program(program_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Program not found.")
    editions = service.list_editions_for_program(program_id)
    return [EditionResponse.model_validate(e) for e in editions]


@router.post(
    "/programs/{program_id}/editions",
    response_model=EditionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_edition(
    program_id: uuid.UUID, payload: EditionCreate, db: Session = Depends(get_db)
) -> EditionResponse:
    service = ProgramService(db)
    program = service.get_program(program_id)
    if program is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Program not found.")
    try:
        edition = service.create_edition(
            program=program,
            slug=payload.slug,
            name=payload.name,
            status=payload.status,
            starts_on=payload.starts_on,
            ends_on=payload.ends_on,
            source=payload.source,
            external_id=payload.external_id,
        )
    except ConflictError as exc:
        raise _conflict(exc) from exc
    return EditionResponse.model_validate(edition)


@router.get("/editions/{edition_id}", response_model=EditionResponse)
def read_edition(edition_id: uuid.UUID, db: Session = Depends(get_db)) -> EditionResponse:
    service = ProgramService(db)
    edition = service.get_edition(edition_id)
    if edition is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Edition not found.")
    return EditionResponse.model_validate(edition)


@router.patch(
    "/editions/{edition_id}",
    response_model=EditionResponse,
    dependencies=[Depends(require_csrf)],
)
def update_edition(
    edition_id: uuid.UUID, payload: EditionUpdate, db: Session = Depends(get_db)
) -> EditionResponse:
    service = ProgramService(db)
    edition = service.get_edition(edition_id)
    if edition is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Edition not found.")
    try:
        updated = service.update_edition(
            edition,
            name=payload.name,
            status=payload.status,
            starts_on=payload.starts_on,
            ends_on=payload.ends_on,
            provided=payload.provided_fields(),
        )
    except ValidationError as exc:
        raise _unprocessable(exc) from exc
    return EditionResponse.model_validate(updated)
