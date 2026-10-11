"""ORM models.

Importing this package registers all models on ``Base.metadata`` so Alembic
autogeneration and the test schema build see the full schema.
"""

from app.models.edition import (
    EDITION_PERIODS,
    EDITION_SOURCES,
    EDITION_STATUSES,
    Edition,
)
from app.models.external_identity import (
    IDENTITY_PROVIDERS,
    PROVIDER_DISCORD,
    PROVIDER_GITHUB,
    PROVIDER_OMEGAUP,
    ExternalIdentity,
)
from app.models.person import Person
from app.models.platform_role import PLATFORM_ROLES, ROLE_SUPERADMIN, PlatformRole
from app.models.program import PROGRAM_ICONS, Program
from app.models.project import Project
from app.models.seed_execution import SeedExecution
from app.models.session import OAuthState, UserSession

__all__ = [
    "EDITION_PERIODS",
    "EDITION_SOURCES",
    "EDITION_STATUSES",
    "IDENTITY_PROVIDERS",
    "PLATFORM_ROLES",
    "PROGRAM_ICONS",
    "PROVIDER_DISCORD",
    "PROVIDER_GITHUB",
    "PROVIDER_OMEGAUP",
    "ROLE_SUPERADMIN",
    "Edition",
    "ExternalIdentity",
    "OAuthState",
    "Person",
    "PlatformRole",
    "Program",
    "Project",
    "SeedExecution",
    "UserSession",
]
