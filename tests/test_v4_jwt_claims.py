"""JWT NumericDate security regressions; no network or provider calls."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

import pytest

from api.v4.auth import _verify_jwt


SECRET = "local-test-only-signing-secret-with-strong-length-0123456789"
TENANT = "tenant_clock"


def _base64url(value: dict) -> str:
    raw = json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _signed_token(claims: dict) -> str:
    header = _base64url({"alg": "HS256", "typ": "JWT"})
    body = _base64url(claims)
    msg = f"{header}.{body}"
    signature = hmac.new(SECRET.encode(), msg.encode(), hashlib.sha256).digest()
    return msg + "." + base64.urlsafe_b64encode(signature).rstrip(b"=").decode("ascii")


def _claims() -> dict:
    now = int(time.time())
    return {"tenant_id": TENANT, "user_id": "u1", "exp": now + 3600, "iat": now - 10}


def test_normal_signed_token_accepted():
    token = _signed_token(_claims())
    assert _verify_jwt(token, SECRET, TENANT)["user_id"] == "u1"


def test_valid_nbf_claim_in_past_is_accepted():
    claims = _claims()
    claims["nbf"] = int(time.time()) - 10
    assert _verify_jwt(_signed_token(claims), SECRET, TENANT) is not None


@pytest.mark.parametrize("claim,value", [
    ("nbf", "future"),
    ("iat", "future"),
    ("nbf", True),
    ("iat", "tomorrow"),
    ("exp", "tomorrow"),
    ("exp", True),
    ("exp", None),
])
def test_signed_tokens_with_invalid_temporal_claims_rejected(claim, value):
    claims = _claims()
    claims[claim] = int(time.time()) + 3600 if value == "future" else value
    assert _verify_jwt(_signed_token(claims), SECRET, TENANT) is None


def test_expired_signed_token_rejected():
    claims = _claims()
    claims["exp"] = int(time.time()) - 1
    assert _verify_jwt(_signed_token(claims), SECRET, TENANT) is None


def test_wrong_tenant_remains_rejected():
    assert _verify_jwt(_signed_token(_claims()), SECRET, "tenant_other") is None
