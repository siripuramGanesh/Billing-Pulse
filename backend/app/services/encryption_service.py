"""
Optional encryption at rest for sensitive claim fields (Phase 7 / HIPAA).
Uses Fernet (symmetric). Set ENCRYPT_SENSITIVE_FIELDS=true and ENCRYPTION_KEY (base64).
"""

from typing import Optional

from ..core.config import get_settings

_PREFIX = "enc:"
_fernet = None


def _get_fernet():
    global _fernet
    if _fernet is not None:
        return _fernet
    s = get_settings()
    if not s.ENCRYPT_SENSITIVE_FIELDS or not s.ENCRYPTION_KEY:
        return None
    try:
        from cryptography.fernet import Fernet
        _fernet = Fernet(s.ENCRYPTION_KEY.encode() if isinstance(s.ENCRYPTION_KEY, str) else s.ENCRYPTION_KEY)
        return _fernet
    except Exception:
        return None


def encrypt_value(plain: Optional[str]) -> Optional[str]:
    """Encrypt a string for storage. Returns None if plain is None; returns plain if encryption disabled."""
    if plain is None or plain == "":
        return plain
    f = _get_fernet()
    if not f:
        return plain
    try:
        return _PREFIX + f.encrypt(plain.encode()).decode()
    except Exception:
        return plain


def decrypt_value(stored: Optional[str]) -> Optional[str]:
    """Decrypt a stored string. If not prefixed or decrypt fails, return as-is (backward compat)."""
    if not stored or not stored.startswith(_PREFIX):
        return stored
    f = _get_fernet()
    if not f:
        return stored[len(_PREFIX):] if stored.startswith(_PREFIX) else stored
    try:
        return f.decrypt(stored[len(_PREFIX):].encode()).decode()
    except Exception:
        return stored
