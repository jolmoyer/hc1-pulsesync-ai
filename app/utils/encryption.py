"""Application-level PHI encryption using Fernet (AES-128-CBC + HMAC-SHA256).

Key is loaded from the PHI_ENCRYPTION_KEY environment variable.
For key rotation in production, use MultiFernet with ordered key list.
"""
from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings


class PHIEncryptor:
    """Encrypt and decrypt PHI strings using Fernet symmetric encryption."""

    def __init__(self) -> None:
        settings = get_settings()
        key = settings.phi_encryption_key.encode()
        self._fernet = Fernet(key)

    def encrypt(self, plaintext: str) -> str:
        """Return URL-safe base64-encoded ciphertext."""
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str | None:
        """Decrypt ciphertext. Returns None on decryption failure instead of raising."""
        try:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        except (InvalidToken, Exception):
            return None
