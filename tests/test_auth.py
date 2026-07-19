"""Unit tests: portal role-based authentication."""

from facilityiq.portal.auth import (
    allowed_screens, authenticate, can_access, list_users,
)


def test_valid_login_each_role():
    for user, pw, role in [("admin", "admin@123", "admin"),
                           ("manager", "manager@123", "manager"),
                           ("tech", "tech@123", "technician"),
                           ("viewer", "viewer@123", "viewer")]:
        u = authenticate(user, pw)
        assert u is not None and u.role == role


def test_wrong_password_rejected():
    assert authenticate("admin", "wrong") is None


def test_unknown_user_rejected():
    assert authenticate("mallory", "admin@123") is None


def test_empty_credentials_rejected():
    assert authenticate("", "") is None
    assert authenticate("admin", "") is None


def test_username_case_and_whitespace_normalized():
    assert authenticate("  Admin ", "admin@123") is not None


def test_role_screen_escalation():
    assert allowed_screens("viewer") == ["overview"]
    assert "detail" in allowed_screens("technician")
    assert "maintenance" not in allowed_screens("technician")
    assert "maintenance" in allowed_screens("manager")
    assert "admin" in allowed_screens("admin")


def test_can_access_denies_above_role():
    assert not can_access("viewer", "admin")
    assert not can_access("technician", "maintenance")
    assert can_access("admin", "overview")


def test_unknown_role_gets_viewer_access_only():
    assert allowed_screens("nonsense") == ["overview"]


def test_list_users_has_no_secrets():
    users = list_users()
    assert len(users) == 4
    for u in users:
        assert not hasattr(u, "password")
        assert set(u.__dict__) == {"username", "full_name", "role"}
