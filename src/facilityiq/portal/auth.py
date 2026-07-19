"""Role-based authentication for the FacilityIQ portal.

Four roles with increasing privilege:

    viewer     -> Screen 1 (Health Overview) only
    technician -> + Screen 2 (Equipment Detail)
    manager    -> + Screen 3 (Maintenance Scheduling)
    admin      -> + Admin panel (user list, system status)

Credentials are stored as salted SHA-256 hashes. This is a POC credential
store — production deployment would swap this module for Azure AD / Entra ID
SSO without touching the portal code (authenticate() is the only interface).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

_SALT = "facilityiq-poc"


def _hash(password: str) -> str:
    return hashlib.sha256((_SALT + password).encode()).hexdigest()


@dataclass(frozen=True)
class User:
    username: str
    full_name: str
    role: str  # viewer | technician | manager | admin


ROLE_SCREENS: dict[str, list[str]] = {
    "viewer": ["overview"],
    "technician": ["overview", "detail"],
    "manager": ["overview", "detail", "maintenance"],
    "admin": ["overview", "detail", "maintenance", "admin"],
}

ROLE_RANK = {"viewer": 0, "technician": 1, "manager": 2, "admin": 3}

# username -> (password_hash, full_name, role)
_USERS: dict[str, tuple[str, str, str]] = {
    "admin": (_hash("admin@123"), "Facility Administrator", "admin"),
    "manager": (_hash("manager@123"), "Facilities Manager", "manager"),
    "tech": (_hash("tech@123"), "Maintenance Technician", "technician"),
    "viewer": (_hash("viewer@123"), "Executive Viewer", "viewer"),
}


def authenticate(username: str, password: str) -> User | None:
    """Return the User on valid credentials, None otherwise."""
    rec = _USERS.get((username or "").strip().lower())
    if rec is None:
        return None
    pw_hash, full_name, role = rec
    if _hash(password or "") != pw_hash:
        return None
    return User(username=username.strip().lower(), full_name=full_name, role=role)


def allowed_screens(role: str) -> list[str]:
    return ROLE_SCREENS.get(role, ["overview"])


def can_access(role: str, screen: str) -> bool:
    return screen in allowed_screens(role)


def list_users() -> list[User]:
    """Admin panel helper — never exposes hashes."""
    return [User(u, fn, r) for u, (_, fn, r) in sorted(_USERS.items())]
