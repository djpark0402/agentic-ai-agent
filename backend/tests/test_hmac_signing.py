import hashlib
import hmac
import json
import time
import uuid

import pytest

from app.signing import build_hmac_headers


FAKE_SECRET = "test-secret-key-12345"
FAKE_API_KEY = "sk-proj-abc123"
FAKE_BODY = {"model": "gpt-5", "messages": [{"role": "user", "content": "hello"}]}


class TestBuildHmacHeaders:
    def test_returns_required_headers(self):
        headers = build_hmac_headers(FAKE_BODY, FAKE_API_KEY, FAKE_SECRET)
        assert "X-Timestamp" in headers
        assert "X-Nonce" in headers
        assert "X-Signature" in headers

    def test_timestamp_is_recent(self):
        headers = build_hmac_headers(FAKE_BODY, FAKE_API_KEY, FAKE_SECRET)
        ts = int(headers["X-Timestamp"])
        assert abs(ts - int(time.time())) < 5

    def test_nonce_is_uuid4(self):
        headers = build_hmac_headers(FAKE_BODY, FAKE_API_KEY, FAKE_SECRET)
        nonce = headers["X-Nonce"]
        parsed = uuid.UUID(nonce, version=4)
        assert str(parsed) == nonce

    def test_nonce_is_unique(self):
        h1 = build_hmac_headers(FAKE_BODY, FAKE_API_KEY, FAKE_SECRET)
        h2 = build_hmac_headers(FAKE_BODY, FAKE_API_KEY, FAKE_SECRET)
        assert h1["X-Nonce"] != h2["X-Nonce"]

    def test_signature_is_hex(self):
        headers = build_hmac_headers(FAKE_BODY, FAKE_API_KEY, FAKE_SECRET)
        sig = headers["X-Signature"]
        assert len(sig) == 64  # SHA256 hex digest
        int(sig, 16)  # should not raise

    def test_signature_is_deterministic_with_fixed_inputs(self):
        ts = "1700000000"
        nonce = "aaaaaaaa-bbbb-4ccc-dddd-eeeeeeeeeeee"
        body_str = json.dumps(FAKE_BODY, separators=(",", ":"), sort_keys=True)
        api_key_hash = hashlib.sha256(FAKE_API_KEY.encode()).hexdigest()
        body_hash = hashlib.sha256(body_str.encode()).hexdigest()
        string_to_sign = f"{ts}.{nonce}.{api_key_hash}.{body_hash}"
        expected = hmac.new(
            FAKE_SECRET.encode(), string_to_sign.encode(), hashlib.sha256
        ).hexdigest()

        headers = build_hmac_headers(
            FAKE_BODY, FAKE_API_KEY, FAKE_SECRET,
            _timestamp=ts, _nonce=nonce,
        )
        assert headers["X-Signature"] == expected

    def test_different_body_produces_different_signature(self):
        body_a = {"model": "gpt-5", "messages": [{"role": "user", "content": "hello"}]}
        body_b = {"model": "gpt-5", "messages": [{"role": "user", "content": "bye"}]}
        h1 = build_hmac_headers(body_a, FAKE_API_KEY, FAKE_SECRET)
        h2 = build_hmac_headers(body_b, FAKE_API_KEY, FAKE_SECRET)
        assert h1["X-Signature"] != h2["X-Signature"]

    def test_different_secret_produces_different_signature(self):
        h1 = build_hmac_headers(FAKE_BODY, FAKE_API_KEY, "secret-a")
        h2 = build_hmac_headers(FAKE_BODY, FAKE_API_KEY, "secret-b")
        assert h1["X-Signature"] != h2["X-Signature"]
