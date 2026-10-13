"""Regression tests for the 5 audit findings on the BFF implementation.

Tests target pure logic without touching the DB:
- P1.4: advisory lock hash is deterministic across process restarts.
- P1.3: API-token principal uses scope (logic lives in dependencies;
  test asserts at the Principal-level that scope → permissions).
- P1.1: create_session signature accepts backend_session_token.
- P2:   get_by_backend_session query now filters by expiry (smoke).
"""

import hashlib
import subprocess
import sys

from app.core.authorization import Principal
from app.repositories.bff_session_repository import _hash_to_int64
from app.services import bff_session_service as bff

# ---------------------------------------------------------------------------
# P1.4 — advisory lock determinístico
# ---------------------------------------------------------------------------


def test_hash_to_int64_is_deterministic_in_process():
    """Calling twice in the same process gives the same key."""
    a = _hash_to_int64("backend-session-abc")
    b = _hash_to_int64("backend-session-abc")
    assert a == b


def test_hash_to_int64_fits_in_signed_int64():
    """PostgreSQL's pg_advisory_xact_lock takes a signed bigint."""
    for v in ("a", "some-uuid-like-string", "x" * 100):
        key = _hash_to_int64(v)
        assert -(2**63) <= key < (2**63)


def test_hash_to_int64_matches_sha256_prefix():
    """Proves the helper uses SHA-256 rather than the built-in hash()."""
    expected_bytes = hashlib.sha256(b"test").digest()[:8]
    expected = int.from_bytes(expected_bytes, "big", signed=True)
    assert _hash_to_int64("test") == expected


def test_hash_to_int64_stable_across_python_processes():
    """CRITICAL: multi-worker deployments rely on this.

    Python's built-in ``hash()`` is randomized per-process via
    PYTHONHASHSEED. Our helper must be deterministic so the advisory
    lock converges on the same key regardless of which Uvicorn worker
    handles the request.
    """
    code = (
        "from app.repositories.bff_session_repository import _hash_to_int64; "
        "print(_hash_to_int64('shared-input'))"
    )
    # Explicitly set random PYTHONHASHSEED per invocation.
    r1 = subprocess.run(
        [sys.executable, "-c", code],
        env={"PYTHONHASHSEED": "42", "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
        check=True,
    )
    r2 = subprocess.run(
        [sys.executable, "-c", code],
        env={"PYTHONHASHSEED": "99", "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
        check=True,
    )
    assert r1.stdout.strip() == r2.stdout.strip()


# ---------------------------------------------------------------------------
# P1.3 — API-token principal carries scope, not issuer's full permissions
# ---------------------------------------------------------------------------


def test_api_token_principal_only_sees_declared_scope():
    """Even when role is 'api_token', the principal's effective permissions
    are only the scope declared at issuance time."""
    from uuid import uuid4

    p = Principal(
        user_id=uuid4(),
        role="api_token",
        organization_id=None,
        permissions=frozenset({"calls.read"}),
    )
    assert p.has_permission("calls.read") is True
    # Would have been granted by superadmin's wildcard — must NOT leak now.
    assert p.has_permission("users.manage") is False
    assert p.has_permission("*") is False


def test_api_token_principal_can_be_empty_scope():
    """Empty scope is a valid (useless) token."""
    from uuid import uuid4

    p = Principal(
        user_id=uuid4(),
        role="api_token",
        organization_id=None,
        permissions=frozenset(),
    )
    assert p.has_permission("anything") is False


# ---------------------------------------------------------------------------
# P1.1 — create_session signature now requires backend_session_token
# ---------------------------------------------------------------------------


def test_create_session_signature_requires_real_token():
    """Signature regression: callers must pass backend_session_token.

    The field drives app.secure_session_token so PostgreSQL RLS policies
    using get_current_user() validate correctly. Missing it would
    reintroduce the synthetic-sentinel bug.
    """
    import inspect

    sig = inspect.signature(bff.create_session)
    assert "backend_session_token" in sig.parameters
    assert sig.parameters["backend_session_token"].default is inspect.Parameter.empty


def test_upgrade_legacy_session_signature_requires_real_token():
    """Same regression for the legacy-upgrade path."""
    import inspect

    sig = inspect.signature(bff.upgrade_legacy_session)
    assert "backend_session_token" in sig.parameters
    assert sig.parameters["backend_session_token"].default is inspect.Parameter.empty


# ---------------------------------------------------------------------------
# P2 — get_by_backend_session filters by expiry (static SQL check)
# ---------------------------------------------------------------------------


def test_get_by_backend_session_sql_filters_expiry():
    """Read the SQL source and assert the expiry filter is present.

    A pure-logic test would need a DB; asserting on the SQL string keeps
    the regression fast and precise. If someone removes the filter, this
    breaks immediately.
    """
    import inspect

    from app.repositories import bff_session_repository as mod

    source = inspect.getsource(mod.FrontendSessionRepository.get_by_backend_session)
    assert "idle_expires_at > NOW()" in source
    assert "absolute_expires_at > NOW()" in source
    assert "NOT is_revoked" in source
