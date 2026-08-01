"""Tests for Clerk JWT authentication — ``app.core.auth.get_principal``.

These tests mock ``PyJWKClient`` and ``jwt.decode`` at the module level so
that no network calls to Clerk are required.  The real ``get_principal``
function runs, exercising the claim-extraction logic.
"""

from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient
from jwt.exceptions import InvalidTokenError

from app.core.auth import get_principal
from app.main import app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _jwt_mocks(claims: dict):
    """Return a pair of context-managers that mock JWKS lookup and JWT decode.

    Usage::

        p0, p1 = _jwt_mocks({"sub": "u1", "o": {"id": "org", "rol": "admin"}})
        with p0, p1:
            ...
    """
    key = MagicMock()
    key.key = "test_rsa_public_key"
    jwks_client = MagicMock()
    jwks_client.get_signing_key_from_jwt.return_value = key
    jwks_fn = MagicMock(return_value=jwks_client)
    return (
        patch("app.core.auth.jwks", jwks_fn),
        patch("app.core.auth.decode", return_value=claims),
    )


def _request(headers=None):
    """Make ``GET /products`` through the *real* auth path (no principal override)."""
    app.dependency_overrides.pop(get_principal, None)
    client = TestClient(app)
    return client.get("/api/v1/products", headers=headers or {})


# ---------------------------------------------------------------------------
# Clerk v2 compact 'o' claim
# ---------------------------------------------------------------------------

class TestV2CompactClaim:
    """Verify extraction of org id/role from the Clerk v2 compact ``o`` claim."""

    def test_extracts_org_id_and_role(self, db):
        p0, p1 = _jwt_mocks({"sub": "u1", "o": {"id": "org_x", "rol": "admin"}})
        with p0, p1:
            r = _request({"Authorization": "Bearer tok"})
        assert r.status_code == 200

    def test_strips_org_prefix_from_role(self, db):
        """``org:manager`` in the token should become ``manager`` in the Principal."""
        p0, p1 = _jwt_mocks({"sub": "u1", "o": {"id": "org_x", "rol": "org:manager"}})
        with p0, p1:
            r = _request({"Authorization": "Bearer tok"})
        assert r.status_code == 200

    def test_role_without_prefix_works(self, db):
        """A raw role string like ``inventory`` should be accepted as-is."""
        p0, p1 = _jwt_mocks({"sub": "u1", "o": {"id": "org_x", "rol": "inventory"}})
        with p0, p1:
            r = _request({"Authorization": "Bearer tok"})
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Legacy claim fallback
# ---------------------------------------------------------------------------

class TestLegacyFallback:
    """When the compact ``o`` claim is absent, fall back to top-level claims."""

    def test_legacy_org_id_and_org_role(self, db):
        p0, p1 = _jwt_mocks({
            "sub": "u2",
            "org_id": "org_legacy",
            "org_role": "org:owner",
        })
        with p0, p1:
            r = _request({"Authorization": "Bearer tok"})
        assert r.status_code == 200

    def test_legacy_role_prefix_stripped(self, db):
        p0, p1 = _jwt_mocks({
            "sub": "u2",
            "org_id": "org_legacy",
            "org_role": "org:viewer",
        })
        with p0, p1:
            r = _request({"Authorization": "Bearer tok"})
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Invalid / missing tokens
# ---------------------------------------------------------------------------

class TestJWTRejection:
    """Verify that bad or missing credentials are correctly rejected."""

    def test_missing_auth_header_returns_401(self, db):
        r = _request()
        assert r.status_code == 401

    def test_non_bearer_scheme_returns_401(self, db):
        r = _request({"Authorization": "Basic dXNlcjpwYXNz"})
        assert r.status_code == 401

    def test_invalid_signature_returns_401(self, db):
        key = MagicMock()
        key.key = "k"
        jwks_fn = MagicMock()
        jwks_fn.return_value.get_signing_key_from_jwt.return_value = key
        with patch("app.core.auth.jwks", jwks_fn), \
             patch("app.core.auth.decode", side_effect=InvalidTokenError("bad")):
            r = _request({"Authorization": "Bearer invalid"})
        assert r.status_code == 401

    def test_missing_org_and_role_returns_403(self, db):
        """Token with ``sub`` but no organization info."""
        p0, p1 = _jwt_mocks({"sub": "u3"})
        with p0, p1:
            r = _request({"Authorization": "Bearer tok"})
        assert r.status_code == 403

    def test_missing_role_returns_403(self, db):
        """Token with org id but no role."""
        p0, p1 = _jwt_mocks({"sub": "u3", "o": {"id": "org_x"}})
        with p0, p1:
            r = _request({"Authorization": "Bearer tok"})
        assert r.status_code == 403

    def test_missing_org_id_returns_403(self, db):
        """Token with role but no org id."""
        p0, p1 = _jwt_mocks({"sub": "u3", "o": {"rol": "admin"}})
        with p0, p1:
            r = _request({"Authorization": "Bearer tok"})
        assert r.status_code == 403
