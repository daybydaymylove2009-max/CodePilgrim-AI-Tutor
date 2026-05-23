from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet

from app.core.config import settings


def _get_fernet_key() -> bytes:
    raw = f"{settings.SECRET_KEY}:{settings.API_KEY_ENCRYPTION_SALT}".encode()
    digest = hashlib.sha256(raw).digest()
    return base64.urlsafe_b64encode(digest)


def _get_fernet() -> Fernet:
    return Fernet(_get_fernet_key())


def encrypt_api_key(plain_key: str) -> str:
    f = _get_fernet()
    return f.encrypt(plain_key.encode()).decode()


def decrypt_api_key(encrypted: str) -> str:
    f = _get_fernet()
    return f.decrypt(encrypted.encode()).decode()


def mask_api_key(key: str) -> str:
    if len(key) <= 7:
        return "***"
    return f"{key[:3]}...{key[-4:]}"
