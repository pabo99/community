"""ORM models.

Importing this package registers all models on ``Base.metadata`` so Alembic
autogeneration and the test schema build see the full schema.
"""

from app.models.external_identity import (
    IDENTITY_PROVIDERS,
    PROVIDER_DISCORD,
    PROVIDER_GITHUB,
    PROVIDER_OMEGAUP,
    ExternalIdentity,
)
from app.models.person import Person
from app.models.platform_role import PLATFORM_ROLES, ROLE_SUPERADMIN, PlatformRole
from app.models.session import OAuthState, UserSession

__all__ = [
    "IDENTITY_PROVIDERS",
    "PLATFORM_ROLES",
    "PROVIDER_DISCORD",
    "PROVIDER_GITHUB",
    "PROVIDER_OMEGAUP",
    "ROLE_SUPERADMIN",
    "ExternalIdentity",
    "OAuthState",
    "Person",
    "PlatformRole",
    "UserSession",
]
