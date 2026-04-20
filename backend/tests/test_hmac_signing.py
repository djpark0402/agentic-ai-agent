import hashlib
import hmac
import time
import uuid

from app.signing import build_hmac_headers


FAKE_SECRET = "test-secret-key-12345"
FAKE_API_KEY = "ak_test_abc123"
FAKE_BODY = b'{"model":"solar","messages":[{"role":"user","content":"hello"}]}'


class TestBuildHmacHeaders:
    def test_returns_required_headers(self):
        headers = build_hmac_headers(FAKE_BODY, FAKE_API_KEY, FAKE_SECRET)
        assert headers["X-API-Key"] == FAKE_API_KEY
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

    def test_signature_is_lowercase_hex_64(self):
        headers = build_hmac_headers(FAKE_BODY, FAKE_API_KEY, FAKE_SECRET)
        sig = headers["X-Signature"]
        assert len(sig) == 64
        assert sig == sig.lower()
        int(sig, 16)  # should not raise

    def test_signature_matches_spec(self):
        """string_to_sign = "{ts}.{nonce}.{sha256(body)}" 규격 검증."""
        ts = "1700000000"
        nonce = "aaaaaaaa-bbbb-4ccc-dddd-eeeeeeeeeeee"
        body_hash = hashlib.sha256(FAKE_BODY).hexdigest()
        expected = hmac.new(
            FAKE_SECRET.encode(),
            f"{ts}.{nonce}.{body_hash}".encode(),
            hashlib.sha256,
        ).hexdigest()

        headers = build_hmac_headers(
            FAKE_BODY, FAKE_API_KEY, FAKE_SECRET, _timestamp=ts, _nonce=nonce,
        )
        assert headers["X-Signature"] == expected

    def test_different_body_produces_different_signature(self):
        body_a = b'{"model":"solar","messages":[{"role":"user","content":"hello"}]}'
        body_b = b'{"model":"solar","messages":[{"role":"user","content":"bye"}]}'
        h1 = build_hmac_headers(body_a, FAKE_API_KEY, FAKE_SECRET)
        h2 = build_hmac_headers(body_b, FAKE_API_KEY, FAKE_SECRET)
        assert h1["X-Signature"] != h2["X-Signature"]

    def test_different_secret_produces_different_signature(self):
        h1 = build_hmac_headers(FAKE_BODY, FAKE_API_KEY, "secret-a")
        h2 = build_hmac_headers(FAKE_BODY, FAKE_API_KEY, "secret-b")
        assert h1["X-Signature"] != h2["X-Signature"]
