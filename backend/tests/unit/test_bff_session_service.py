"""Unit tests for the BFF session service.

We test the pure-Python helpers (hash, expiry checks, recent-auth
window) and the cookie-name selection logic. The DB-touching paths are
covered in integration tests.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.models.bff_session import FrontendSession
from app.services import bff_session_service as bff

# ---------------------------------------------------------------------------
# Hash helpers
# ---------------------------------------------------------------------------


def test_hash_cookie_value_is_deterministic():
    a = bff.hash_cookie_value("abc123")
    b = bff.hash_cookie_value("abc123")
    assert a == b
    assert len(a) == 64  # hex-encoded SHA-256


def test_hash_cookie_value_differs_per_input():
    assert bff.hash_cookie_value("a") != bff.hash_cookie_value("b")


def test_hash_csrf_token_matches_hash_cookie_value():
    """Both helpers use the same SHA-256 algorithm."""
    assert bff.hash_csrf_token("xyz") == bff.hash_cookie_value("xyz")


# ---------------------------------------------------------------------------
# Cookie name selection
# ---------------------------------------------------------------------------


class _StubURL:
    def __init__(self, scheme: str):
        self.scheme = scheme


class _StubRequest:
    def __init__(self, scheme: str = "https"):
        self.url = _StubURL(scheme)


def test_cookie_name_uses_host_prefix_for_https():
    name = bff.cookie_name_for_request(_StubRequest("https"))
    assert name.startswith("__Host-")
    assert name == bff.COOKIE_NAME_PROD


def test_cookie_name_falls_back_for_http_dev():
    name = bff.cookie_name_for_request(_StubRequest("http"))
    assert not name.startswith("__Host-")
    assert name == bff.COOKIE_NAME_DEV


# ---------------------------------------------------------------------------
# Expiry logic
# ---------------------------------------------------------------------------


def _make_session(*, idle_offset_s: int, absolute_offset_s: int, recent_age_s: int = 0):
    """Build an in-memory FrontendSession for pure-logic tests."""
    now = datetime.now(UTC)
    return FrontendSession(
        id=uuid4(),
        cookie_hash="x",
        user_id=uuid4(),
        organization_id=None,
        backend_session_id=uuid4(),
        csrf_token_hash="x",
        created_at=now,
        last_seen_at=now,
        idle_expires_at=now + timedelta(seconds=idle_offset_s),
        absolute_expires_at=now + timedelta(seconds=absolute_offset_s),
        recent_auth_at=now - timedelta(seconds=recent_age_s),
        auth_method="password",
        upgraded_from_legacy=False,
        ip_address=None,
        user_agent=None,
        is_revoked=False,
        revoked_at=None,
        revoked_reason=None,
    )


def test_session_not_expired_within_both_windows():
    sess = _make_session(idle_offset_s=300, absolute_offset_s=3600)
    assert bff.is_session_expired(sess) is False


def test_session_expired_when_idle_window_passed():
    sess = _make_session(idle_offset_s=-1, absolute_offset_s=3600)
    assert bff.is_session_expired(sess) is True


def test_session_expired_when_absolute_window_passed():
    sess = _make_session(idle_offset_s=300, absolute_offset_s=-1)
    assert bff.is_session_expired(sess) is True


# ---------------------------------------------------------------------------
# Recent-auth window
# ---------------------------------------------------------------------------


def test_recent_auth_within_default_window():
    sess = _make_session(idle_offset_s=300, absolute_offset_s=3600, recent_age_s=60)
    assert bff.is_recently_authenticated(sess) is True


def test_recent_auth_outside_default_window():
    # default window is 5 min = 300s
    sess = _make_session(idle_offset_s=300, absolute_offset_s=3600, recent_age_s=600)
    assert bff.is_recently_authenticated(sess) is False


def test_recent_auth_respects_custom_window():
    sess = _make_session(idle_offset_s=300, absolute_offset_s=3600, recent_age_s=60)
    # 30s window — the 60s-old auth fails
    assert bff.is_recently_authenticated(sess, max_age_seconds=30) is False
    # 120s window — passes
    assert bff.is_recently_authenticated(sess, max_age_seconds=120) is True
