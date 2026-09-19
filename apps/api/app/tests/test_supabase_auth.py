"""Supabase token verification: ES256 via JWKS (current projects) and the
legacy HS256 shared secret, with the algorithm/issuer/audience pinned so a
token cannot pick its own verification path."""

from __future__ import annotations

import time
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException

from app.api.deps import get_current_user
from app.core import supabase_auth

SUPABASE_USER = "6f9619ff-8b86-d011-b42d-00c04fc964ff"
PROJECT = "https://abcdefgh.supabase.co"
ISSUER = f"{PROJECT}/auth/v1"


@pytest.fixture(scope="module")
def ec_key():
    return ec.generate_private_key(ec.SECP256R1())


@pytest.fixture(autouse=True)
def _config(monkeypatch, ec_key):
    settings = SimpleNamespace(
        supabase_url=PROJECT, next_public_supabase_url="", supabase_jwt_secret="legacy-shared-secret-value-32-bytes!!"
    )
    monkeypatch.setattr("app.api.deps.get_settings", lambda: settings)

    class _FakeJwks:
        def get_signing_key_from_jwt(self, token):
            return SimpleNamespace(key=ec_key.public_key())

    monkeypatch.setattr(supabase_auth, "_jwks_client", lambda url: _FakeJwks())
    return settings


def _claims(**over):
    base = {"sub": SUPABASE_USER, "aud": "authenticated", "iss": ISSUER, "exp": int(time.time()) + 300}
    base.update(over)
    return base


def _es256(ec_key, **over):
    return jwt.encode(_claims(**over), ec_key, algorithm="ES256", headers={"kid": "k1"})


async def _user(token):
    return await get_current_user(f"Bearer {token}")


async def test_valid_es256_token_returns_user_id(ec_key):
    assert await _user(_es256(ec_key)) == SUPABASE_USER


async def test_expired_token_is_401(ec_key):
    with pytest.raises(HTTPException) as e:
        await _user(_es256(ec_key, exp=int(time.time()) - 10))
    assert e.value.status_code == 401


async def test_wrong_audience_is_401(ec_key):
    with pytest.raises(HTTPException) as e:
        await _user(_es256(ec_key, aud="anon"))
    assert e.value.status_code == 401


async def test_wrong_issuer_is_401(ec_key):
    with pytest.raises(HTTPException) as e:
        await _user(_es256(ec_key, iss="https://evil.supabase.co/auth/v1"))
    assert e.value.status_code == 401


async def test_token_signed_by_a_different_key_is_401():
    other = ec.generate_private_key(ec.SECP256R1())
    with pytest.raises(HTTPException) as e:
        await _user(jwt.encode(_claims(), other, algorithm="ES256", headers={"kid": "k1"}))
    assert e.value.status_code == 401


async def test_missing_sub_is_401(ec_key):
    claims = _claims()
    del claims["sub"]
    token = jwt.encode(claims, ec_key, algorithm="ES256", headers={"kid": "k1"})
    with pytest.raises(HTTPException) as e:
        await _user(token)
    assert e.value.status_code == 401


async def test_hs256_token_signed_with_the_public_key_is_rejected(ec_key):
    """Algorithm-confusion attack: HS256 'signed' using public key bytes as the secret."""
    public_pem = ec_key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    import base64
    import hashlib
    import hmac
    import json

    def b64(raw: bytes) -> bytes:
        return base64.urlsafe_b64encode(raw).rstrip(b"=")

    signing_input = (
        b64(json.dumps({"alg": "HS256", "typ": "JWT", "kid": "k1"}).encode())
        + b"."
        + b64(json.dumps(_claims()).encode())
    )
    signature = hmac.new(public_pem, signing_input, hashlib.sha256).digest()
    forged = (signing_input + b"." + b64(signature)).decode()
    with pytest.raises(HTTPException) as e:
        await _user(forged)
    assert e.value.status_code == 401


async def test_legacy_hs256_token_still_verifies_with_the_secret(_config):
    token = jwt.encode(_claims(), _config.supabase_jwt_secret, algorithm="HS256")
    assert await _user(token) == SUPABASE_USER


async def test_alg_none_and_garbage_are_401():
    for token in (
        jwt.encode(_claims(), key=None, algorithm="none"),
        "not.a.jwt",
    ):
        with pytest.raises(HTTPException) as e:
            await _user(token)
        assert e.value.status_code == 401


async def test_es256_without_project_url_is_a_500_not_a_pass(monkeypatch, ec_key, _config):
    _config.supabase_url = ""
    with pytest.raises(HTTPException) as e:
        await _user(_es256(ec_key))
    assert e.value.status_code == 500


async def test_missing_bearer_header_is_401():
    with pytest.raises(HTTPException) as e:
        await get_current_user(None)
    assert e.value.status_code == 401
