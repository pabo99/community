"""Job type registration and payload validation.

This is the single source of truth for *which job types the queue accepts* and
*what shape their payloads must have*. It is deliberately decoupled from worker
dispatch (M1-11c): a job type being registered here means "the queue will
accept and store it", not "a handler exists to run it". M1-11c/M1-11d register
their types here (and separately wire execution handlers), so unknown types are
rejected at enqueue and never silently accumulate in the queue.

To avoid a circular dependency between the queue service and future worker
handlers, this module imports nothing from the worker package. Handlers depend
on this registry (one direction), never the reverse.

Validation steps for an enqueued payload:

1. The payload must be a JSON object (``dict``).
2. The job type must be registered (explicit allow-list policy).
3. The encoded payload must not exceed ``MAX_PAYLOAD_BYTES`` (UTF-8 bytes).
4. If the registered type has a Pydantic model, the payload must validate
   against it; the normalized/dumped object is stored.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Final

from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from app.services.jobs.errors import JobPayloadError, JobTypeError

# Maximum encoded payload size, measured in UTF-8 bytes (16 KiB).
MAX_PAYLOAD_BYTES: Final = 16 * 1024


class _Registration:
    """A registered job type and its optional payload schema."""

    __slots__ = ("job_type", "model")

    def __init__(self, job_type: str, model: type[BaseModel] | None) -> None:
        self.job_type = job_type
        self.model = model


# Module-level registry. Populated by register_job_type(...) at import time by
# the modules that define job types (M1-11d demo types, future real types).
_REGISTRY: dict[str, _Registration] = {}


def register_job_type(job_type: str, *, model: type[BaseModel] | None = None) -> None:
    """Register a job type the queue will accept.

    ``model`` is an optional Pydantic model validating/normalizing the payload.
    Registration is idempotent for an identical (type, model) pair and raises on
    a conflicting re-registration so collisions surface loudly.
    """
    if not job_type or len(job_type) > 128:
        raise ValueError("job_type must be a non-empty string of at most 128 characters")
    existing = _REGISTRY.get(job_type)
    if existing is not None and existing.model is not model:
        raise ValueError(f"job type '{job_type}' is already registered with a different schema")
    _REGISTRY[job_type] = _Registration(job_type, model)


def is_registered(job_type: str) -> bool:
    return job_type in _REGISTRY


def registered_types() -> frozenset[str]:
    return frozenset(_REGISTRY)


def validate_payload(job_type: str, payload: Mapping[str, object]) -> dict[str, object]:
    """Validate an enqueue request; return the normalized payload to persist.

    Raises ``JobTypeError`` for an unregistered type and ``JobPayloadError`` for
    a non-object payload, an oversize payload, or a schema validation failure.
    The error messages intentionally contain no payload content.
    """
    if not isinstance(payload, dict):
        raise JobPayloadError("payload must be a JSON object")

    if not is_registered(job_type):
        # Explicit allow-list policy: unknown types never enter the queue.
        raise JobTypeError(f"unknown job type '{job_type}'")

    # Enforce the size bound on the ENCODED bytes (what actually hits the DB).
    try:
        encoded = json.dumps(payload).encode("utf-8")
    except (TypeError, ValueError) as exc:
        # No payload content in the message; just the structural reason.
        raise JobPayloadError("payload is not JSON-serializable") from exc
    if len(encoded) > MAX_PAYLOAD_BYTES:
        raise JobPayloadError(f"payload exceeds the maximum size of {MAX_PAYLOAD_BYTES} bytes")

    registration = _REGISTRY[job_type]
    if registration.model is None:
        return payload

    try:
        validated = registration.model.model_validate(payload)
    except PydanticValidationError as exc:
        # Surface that validation failed without echoing field values.
        raise JobPayloadError(f"payload failed validation for job type '{job_type}'") from exc
    return validated.model_dump(mode="json")
