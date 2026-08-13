"""
crypto_utils.py
----------------
All cryptographic operations for the vault live here, isolated from the
GUI and database code so the "security core" can be reviewed, tested,
and audited on its own.

Two separate concerns, deliberately kept apart:

1. AUTHENTICATION  - "Is this the correct master password?"
   We never store the master password. We store a salted PBKDF2-HMAC-SHA256
   hash of it. On login we hash the attempt with the stored salt and compare.

2. ENCRYPTION       - "Protect the stored account passwords at rest."
   A symmetric key is derived from the master password (PBKDF2-HMAC-SHA256,
   independent salt) and used with Fernet (AES-128-CBC + HMAC-SHA256, from
   the `cryptography` library) to encrypt/decrypt each stored password.

   The encryption key is NEVER written to disk. It only ever lives in
   memory for the duration of an unlocked session (see app/session.py) and
   is re-derived from the master password every time the app is unlocked.
   This means: if you don't know the master password, the stored
   passwords are computationally infeasible to recover, even with full
   access to the database file.
"""

import base64
import hashlib
import hmac
import os

from cryptography.fernet import Fernet, InvalidToken

from app.constants import AUTH_HASH_ITERATIONS, KEY_DERIVATION_ITERATIONS, SALT_SIZE_BYTES


def generate_salt() -> bytes:
    """Cryptographically secure random salt."""
    return os.urandom(SALT_SIZE_BYTES)


# ---------------------------------------------------------------------------
# Master password authentication
# ---------------------------------------------------------------------------

def hash_master_password(password: str, salt: bytes) -> bytes:
    """
    Derives a PBKDF2-HMAC-SHA256 digest of the master password.
    This digest (plus salt) is what gets stored in the database -
    never the plaintext password.
    """
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        AUTH_HASH_ITERATIONS,
    )


def verify_master_password(password: str, salt: bytes, expected_hash: bytes) -> bool:
    """Constant-time comparison to avoid timing attacks."""
    candidate = hash_master_password(password, salt)
    return hmac.compare_digest(candidate, expected_hash)


# ---------------------------------------------------------------------------
# Encryption key derivation (for the stored account passwords)
# ---------------------------------------------------------------------------

def derive_encryption_key(password: str, salt: bytes) -> bytes:
    """
    Derives a 32-byte key from the master password, then base64-urlsafe
    encodes it, which is the format Fernet expects.
    """
    raw_key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        KEY_DERIVATION_ITERATIONS,
        dklen=32,
    )
    return base64.urlsafe_b64encode(raw_key)


def encrypt_text(plaintext: str, key: bytes) -> bytes:
    """Encrypts a plaintext string, returning ciphertext bytes to store."""
    fernet = Fernet(key)
    return fernet.encrypt(plaintext.encode("utf-8"))


def decrypt_text(ciphertext: bytes, key: bytes) -> str:
    """
    Decrypts ciphertext bytes back to a plaintext string.
    Raises ValueError if the key is wrong or data was tampered with.
    """
    fernet = Fernet(key)
    try:
        return fernet.decrypt(ciphertext).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Decryption failed: wrong key or corrupted data.") from exc
