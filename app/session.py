"""
session.py
-----------
Holds the transient, in-memory state for an unlocked vault session:
namely the derived encryption key. This key is NEVER written to disk.
Locking the vault (or closing the app) clears it, at which point every
stored password becomes unreadable again until the master password is
re-entered and the key is re-derived.
"""

from typing import Optional

from app.database import VaultDatabase


class VaultSession:
    def __init__(self, db: VaultDatabase):
        self.db = db
        self._encryption_key: Optional[bytes] = None

    @property
    def is_unlocked(self) -> bool:
        return self._encryption_key is not None

    def unlock(self, master_password: str) -> bool:
        """Verifies the master password and, if correct, derives and caches the key."""
        if not self.db.verify_master_password(master_password):
            return False
        self._encryption_key = self.db.get_encryption_key(master_password)
        return True

    def lock(self) -> None:
        self._encryption_key = None

    @property
    def key(self) -> bytes:
        if self._encryption_key is None:
            raise RuntimeError("Vault is locked; no encryption key available.")
        return self._encryption_key
