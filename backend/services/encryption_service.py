import base64
import hashlib
from cryptography.fernet import Fernet
from config import settings

def _get_fernet() -> Fernet:
    """Derive a consistent 32-byte urlsafe base64 key from JWT_SECRET_KEY."""
    key_bytes = hashlib.sha256(settings.JWT_SECRET_KEY.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)

def encrypt_credential(plain_text: str) -> str:
    """Encrypt a plain text password or secret."""
    if not plain_text:
        return ""
    f = _get_fernet()
    return f.encrypt(plain_text.encode()).decode()

def decrypt_credential(cipher_text: str) -> str:
    """Decrypt an encrypted credential string."""
    if not cipher_text:
        return ""
    try:
        f = _get_fernet()
        return f.decrypt(cipher_text.encode()).decode()
    except Exception:
        return ""
