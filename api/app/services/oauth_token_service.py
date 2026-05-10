from cryptography.fernet import Fernet
from app.core.settings import get_settings

_fernet_instance: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet_instance
    if _fernet_instance is None:
        key = get_settings().oauth_token_encryption_key
        if not key:
            raise RuntimeError("OAUTH_TOKEN_ENCRYPTION_KEY is not set in environment")
        _fernet_instance = Fernet(key.encode() if isinstance(key, str) else key)
    return _fernet_instance


def encrypt_token(token: str) -> str:
    return _get_fernet().encrypt(token.encode()).decode()


def decrypt_token(encrypted: str) -> str:
    return _get_fernet().decrypt(encrypted.encode()).decode()
