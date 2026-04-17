import hashlib
import hmac as _hmac
import json
import time
import uuid


def build_hmac_headers(
    body: dict,
    api_key: str,
    secret: str,
    *,
    _timestamp: str | None = None,
    _nonce: str | None = None,
) -> dict[str, str]:
    """HMAC-SHA256 서명 헤더를 생성한다.

    string_to_sign = "{timestamp}.{nonce}.{sha256(api_key)}.{sha256(body)}"
    """
    timestamp = _timestamp or str(int(time.time()))
    nonce = _nonce or str(uuid.uuid4())

    body_str = json.dumps(body, separators=(",", ":"), sort_keys=True)
    api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    body_hash = hashlib.sha256(body_str.encode()).hexdigest()

    string_to_sign = f"{timestamp}.{nonce}.{api_key_hash}.{body_hash}"
    signature = _hmac.new(
        secret.encode(), string_to_sign.encode(), hashlib.sha256
    ).hexdigest()

    return {
        "X-Timestamp": timestamp,
        "X-Nonce": nonce,
        "X-Signature": signature,
    }
