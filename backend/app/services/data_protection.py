import base64
import hashlib
import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from ..config import settings


def _resolve_fernet_key() -> bytes:
    if settings.ENCRYPTION_KEY:
        return settings.ENCRYPTION_KEY.encode("utf-8")
    digest = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


_fernet = Fernet(_resolve_fernet_key())


def encrypt_json_payload(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=True)
    return _fernet.encrypt(raw.encode("utf-8")).decode("utf-8")


def decrypt_json_payload(cipher_text: str) -> dict[str, Any]:
    try:
        decrypted = _fernet.decrypt(cipher_text.encode("utf-8")).decode("utf-8")
        data = json.loads(decrypted)
        if isinstance(data, dict):
            return data
        return {}
    except (InvalidToken, json.JSONDecodeError, UnicodeDecodeError):
        return {}
