"""Job queue error types and controlled failure recording.

Two concerns live here:

1. **Exception hierarchy** for enqueue-time problems (``JobTypeError``,
   ``JobPayloadError``) raised by the queue service. Infrastructure failures
   (database/connection) are NOT wrapped — they propagate as the original
   SQLAlchemy exceptions so callers (the future worker loop) can distinguish a
   job-level problem from a platform-level one.

2. **Controlled error recording.** A job's ``last_error`` must never contain an
   arbitrary ``str(exception)``, a traceback, or any payload/secret content: an
   exception message can carry credentials, tokens, PII, or echoed input. We
   persist only a bounded, caller-supplied **error code** plus an optional
   short, caller-controlled detail that is sanitized and truncated. Handlers
   are expected to raise ``JobExecutionError`` with a safe code; any other
   exception is recorded under the generic ``UNHANDLED_EXCEPTION`` code with no
   message content copied from the exception.
"""

from __future__ import annotations

import re
from typing import Final

from app.models.job import MAX_LAST_ERROR_LENGTH


class JobError(Exception):
    """Base class for job queue errors."""


class JobTypeError(JobError):
    """The job type is unknown/unsupported (enqueue policy violation)."""


class JobPayloadError(JobError):
    """The payload is invalid (wrong shape, failed validation, or too large)."""


class JobExecutionError(JobError):
    """A handler failure carrying a safe, controlled error code.

    Handlers raise this to signal an expected failure with a code safe to
    persist. The optional ``detail`` is treated as untrusted and sanitized
    before storage; it must not contain secrets by construction (handlers
    control it), but we defensively bound and strip it anyway.
    """

    def __init__(self, code: str, detail: str | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.detail = detail


# Generic code used when a handler raised something other than
# JobExecutionError. We deliberately copy NO content from the exception.
UNHANDLED_EXCEPTION_CODE: Final = "UNHANDLED_EXCEPTION"
# Code recorded by stale-job recovery when it requeues/fails an expired lease.
LEASE_EXPIRED_CODE: Final = "LEASE_EXPIRED"

# An error code is a short, uppercase, machine-readable token. We constrain it
# so a code can never smuggle arbitrary text into last_error.
_CODE_RE: Final = re.compile(r"[A-Z0-9_.:-]+")
_MAX_CODE_LENGTH: Final = 64
_MAX_DETAIL_LENGTH: Final = MAX_LAST_ERROR_LENGTH - _MAX_CODE_LENGTH - 2


def _sanitize_code(code: str) -> str:
    """Reduce a code to the allowed charset, bounded length. Fallback if empty."""
    matches = _CODE_RE.findall(code.upper())
    cleaned = "".join(matches)[:_MAX_CODE_LENGTH]
    return cleaned or UNHANDLED_EXCEPTION_CODE


def _sanitize_detail(detail: str) -> str:
    """Collapse whitespace/newlines and bound length for a safe stored detail."""
    collapsed = re.sub(r"\s+", " ", detail).strip()
    return collapsed[:_MAX_DETAIL_LENGTH]


def format_last_error(code: str, detail: str | None = None) -> str:
    """Build the bounded, sanitized ``last_error`` string from a code + detail.

    Only the sanitized code and (optionally) a sanitized, bounded detail are
    included. No traceback, no exception type, no arbitrary ``str(exc)``.
    """
    safe_code = _sanitize_code(code)
    if not detail:
        return safe_code
    safe_detail = _sanitize_detail(detail)
    if not safe_detail:
        return safe_code
    combined = f"{safe_code}: {safe_detail}"
    return combined[:MAX_LAST_ERROR_LENGTH]


def error_code_for(exc: BaseException) -> tuple[str, str | None]:
    """Map an exception to a (code, detail) pair safe to persist.

    - ``JobExecutionError``: use its controlled code and detail.
    - anything else: generic code, NO content copied from the exception (its
      message could contain secrets/PII/payload data).
    """
    if isinstance(exc, JobExecutionError):
        return exc.code, exc.detail
    return UNHANDLED_EXCEPTION_CODE, None
