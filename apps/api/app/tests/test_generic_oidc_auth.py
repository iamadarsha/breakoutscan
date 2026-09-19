"""Any OIDC provider (Firebase shown here) is enabled by configuration alone,
and its opaque subject ids map to stable UUIDs for the uuid user_id columns."""

from __future__ import annotations

import time
import uuid
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException

from app.api.deps import get_current_user
from app.core import supabase_auth
from app.core.auth_tokens import user_id_from_claims

FIREBASE_ISSUER = "https://securetoken.google.com/my-project"
FIREBASE_UID = "kS9dLq2mZpX7vB1nR4tYc8WfHjA3"  # 28 chars, not a UUID


@pytest.fixture(scope="module")
def key():
    return ec.generate_private_key(ec.SECP256R1())


@pytest.fixture(autouse=True)
def _config(monkeypatch, key):
    settings = SimpleNamespace(
        supabase_url="https://abcdefgh.supabase.co", next_public_supabase_url="", supabase_jwt_secret="",
        auth_issuer=FIREBASE_ISSUER, auth_audience="my-project",
        auth_jwks_url="https://example.test/jwks",
    )
    monkeypatch.setattr("app.api.deps.get_settings", lambda: settings)

    class _FakeJwks:
        def get_signing_key_from_jwt(self, token):
            return SimpleNamespace(key=key.public_key())

    monkeypatch.setattr(supabase_auth, "_jwks_client", lambda url: _FakeJwks())
    monkeypatch.setattr("app.core.auth_tokens._jwks_client", lambda url: _FakeJwks())
    return settings


def _token(key, **over):
    claims = {"sub": FIREBASE_UID, "aud": "my-project", "iss": FIREBASE_ISSUER, "exp": int(time.time()) + 300}
    claims.update(over)
    return jwt.encode(claims, key, algorithm="ES256", headers={"kid": "k"})


async def _user(token):
    return await get_current_user(f"Bearer {token}")


async def test_firebase_style_token_verifies_and_maps_to_a_stable_uuid(key):
    first = await _user(_token(key))
    again = await _user(_token(key))
    assert first == again
    assert str(uuid.UUID(first)) == first  # a real UUID the DB column accepts
    assert first == user_id_from_claims({"sub": FIREBASE_UID, "iss": FIREBASE_ISSUER})


async def test_same_uid_from_a_different_issuer_is_a_different_user():
    a = user_id_from_claims({"sub": FIREBASE_UID, "iss": "https://securetoken.google.com/a"})
    b = user_id_from_claims({"sub": FIREBASE_UID, "iss": "https://securetoken.google.com/b"})
    assert a != b


def test_supabase_uuid_subjects_pass_through_unchanged():
    sub = "6f9619ff-8b86-d011-b42d-00c04fc964ff"
    assert user_id_from_claims({"sub": sub, "iss": "x"}) == sub


async def test_wrong_audience_is_401(key):
    with pytest.raises(HTTPException) as e:
        await _user(_token(key, aud="another-project"))
    assert e.value.status_code == 401


async def test_untrusted_issuer_is_401(key):
    with pytest.raises(HTTPException) as e:
        await _user(_token(key, iss="https://evil.example/"))
    assert e.value.status_code == 401


async def test_token_signed_by_another_key_is_401():
    other = ec.generate_private_key(ec.SECP256R1())
    with pytest.raises(HTTPException) as e:
        await _user(_token(other))
    assert e.value.status_code == 401


async def test_missing_audience_config_fails_closed_with_500(key, _config):
    _config.auth_audience = ""
    with pytest.raises(HTTPException) as e:
        await _user(_token(key))
    assert e.value.status_code == 500
