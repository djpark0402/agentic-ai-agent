import hashlib
import hmac as _hmac
import time
import uuid


def build_hmac_headers(
    body_bytes: bytes,
    api_key: str,
    secret: str,
    *,
    _timestamp: str | None = None,
    _nonce: str | None = None,
) -> dict[str, str]:
    """HMAC-SHA256 서명 헤더를 생성한다.

    규격:
      string_to_sign = "{ts}.{nonce}.{sha256(body)}"
      X-API-Key      = api_key
      X-Timestamp    = 초 단위 epoch
      X-Nonce        = UUID4
      X-Signature    = HMAC-SHA256(secret, string_to_sign) 소문자 hex 64자

    Body는 실제 전송되는 raw bytes와 일치해야 서명 검증이 성공한다.
    """
    timestamp = _timestamp or str(int(time.time()))
    nonce = _nonce or str(uuid.uuid4())

    body_hash = hashlib.sha256(body_bytes).hexdigest()
    string_to_sign = f"{timestamp}.{nonce}.{body_hash}"
    signature = _hmac.new(
        secret.encode(), string_to_sign.encode(), hashlib.sha256
    ).hexdigest()

    return {
        "X-API-Key": api_key,
        "X-Timestamp": timestamp,
        "X-Nonce": nonce,
        "X-Signature": signature,
    }
