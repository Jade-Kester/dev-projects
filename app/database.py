"""
database.py
------------
SQLite persistence layer for the vault.

Design notes
============
* One `vault_meta` row holds the master-password verifier (salt + hash)
  and the salt used to derive the encryption key. No plaintext secret is
  ever stored here.
* `entries` holds one row per saved login. `password_enc` is always
  Fernet ciphertext (see app/crypto_utils.py) - never plaintext.
* "Main Accounts" are just entries with `is_main = 1`. An entry linked to
  a main account stores `linked_main_id` pointing at it, purely so the
  GUI can label/group entries and offer autofill. Each entry keeps its
  own encrypted copy of the email/password (rather than only a
  reference), so deleting a main account never breaks entries that were
  created from it.
"""

import shutil
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from typing import List, Optional

from app import crypto_utils


@dataclass
class Entry:
    id: int
    website: str
    username: str
    email: str
    is_main: bool
    linked_main_id: Optional[int]


class VaultDatabase:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_schema()

    # ------------------------------------------------------------------
    # Low-level helpers
    # ------------------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_schema(self) -> None:
        with closing(self._connect()) as conn, conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS vault_meta (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    auth_salt BLOB NOT NULL,
                    auth_hash BLOB NOT NULL,
                    key_salt BLOB NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    website TEXT NOT NULL,
                    username TEXT NOT NULL DEFAULT '',
                    email TEXT NOT NULL DEFAULT '',
                    password_enc BLOB NOT NULL,
                    is_main INTEGER NOT NULL DEFAULT 0,
                    linked_main_id INTEGER,
                    FOREIGN KEY (linked_main_id) REFERENCES entries(id) ON DELETE SET NULL
                )
                """
            )

    # ------------------------------------------------------------------
    # Master password / vault lifecycle
    # ------------------------------------------------------------------

    def is_vault_initialized(self) -> bool:
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT 1 FROM vault_meta WHERE id = 1").fetchone()
            return row is not None

    def create_master_password(self, password: str) -> None:
        """Called once, the very first time the app is run."""
        auth_salt = crypto_utils.generate_salt()
        auth_hash = crypto_utils.hash_master_password(password, auth_salt)
        key_salt = crypto_utils.generate_salt()
        with closing(self._connect()) as conn, conn:
            conn.execute(
                "INSERT INTO vault_meta (id, auth_salt, auth_hash, key_salt) VALUES (1, ?, ?, ?)",
                (auth_salt, auth_hash, key_salt),
            )

    def verify_master_password(self, password: str) -> bool:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT auth_salt, auth_hash FROM vault_meta WHERE id = 1"
            ).fetchone()
            if row is None:
                return False
            auth_salt, auth_hash = row
            return crypto_utils.verify_master_password(password, auth_salt, auth_hash)

    def get_encryption_key(self, password: str) -> bytes:
        """
        Re-derives the symmetric encryption key from the master password.
        Caller is expected to have already verified the password.
        """
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT key_salt FROM vault_meta WHERE id = 1").fetchone()
            key_salt = row[0]
        return crypto_utils.derive_encryption_key(password, key_salt)

    def change_master_password(self, old_password: str, new_password: str) -> None:
        """
        Verifies the old password, then re-encrypts every stored password
        with a freshly derived key (new salt) before swapping the master
        password verifier. Runs as a single transaction so the vault is
        never left in a half-migrated state.
        """
        if not self.verify_master_password(old_password):
            raise ValueError("Current master password is incorrect.")

        old_key = self.get_encryption_key(old_password)

        new_auth_salt = crypto_utils.generate_salt()
        new_auth_hash = crypto_utils.hash_master_password(new_password, new_auth_salt)
        new_key_salt = crypto_utils.generate_salt()
        new_key = crypto_utils.derive_encryption_key(new_password, new_key_salt)

        with closing(self._connect()) as conn, conn:
            rows = conn.execute("SELECT id, password_enc FROM entries").fetchall()
            for entry_id, password_enc in rows:
                plaintext = crypto_utils.decrypt_text(password_enc, old_key)
                new_cipher = crypto_utils.encrypt_text(plaintext, new_key)
                conn.execute(
                    "UPDATE entries SET password_enc = ? WHERE id = ?",
                    (new_cipher, entry_id),
                )
            conn.execute(
                "UPDATE vault_meta SET auth_salt = ?, auth_hash = ?, key_salt = ? WHERE id = 1",
                (new_auth_salt, new_auth_hash, new_key_salt),
            )

    # ------------------------------------------------------------------
    # Entry CRUD
    # ------------------------------------------------------------------

    def add_entry(
        self,
        website: str,
        username: str,
        email: str,
        password_plain: str,
        key: bytes,
        is_main: bool = False,
        linked_main_id: Optional[int] = None,
    ) -> int:
        cipher = crypto_utils.encrypt_text(password_plain, key)
        with closing(self._connect()) as conn, conn:
            cur = conn.execute(
                """
                INSERT INTO entries (website, username, email, password_enc, is_main, linked_main_id)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (website, username, email, cipher, int(is_main), linked_main_id),
            )
            return cur.lastrowid

    def update_entry(
        self,
        entry_id: int,
        website: str,
        username: str,
        email: str,
        password_plain: str,
        key: bytes,
        is_main: bool = False,
        linked_main_id: Optional[int] = None,
    ) -> None:
        """
        Updates an entry. If it's a Main Account (is_main=True), its new
        e-mail and password are also propagated to every entry linked to
        it, so a Main Account's credentials and its linked logins never
        drift out of sync. Website/username are intentionally NOT
        propagated - only the shared login (e-mail + password) is.
        """
        cipher = crypto_utils.encrypt_text(password_plain, key)
        with closing(self._connect()) as conn, conn:
            conn.execute(
                """
                UPDATE entries
                SET website = ?, username = ?, email = ?, password_enc = ?,
                    is_main = ?, linked_main_id = ?
                WHERE id = ?
                """,
                (website, username, email, cipher, int(is_main), linked_main_id, entry_id),
            )
            if is_main:
                conn.execute(
                    "UPDATE entries SET email = ?, password_enc = ? WHERE linked_main_id = ?",
                    (email, cipher, entry_id),
                )

    def count_linked_entries(self, main_id: int) -> int:
        """Used by the GUI to warn 'this will also update N linked account(s)'."""
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM entries WHERE linked_main_id = ?", (main_id,)
            ).fetchone()
        return row[0] if row else 0

    def delete_entry(self, entry_id: int) -> None:
        with closing(self._connect()) as conn, conn:
            # Unlink any entries that pointed at this one as their main account.
            conn.execute(
                "UPDATE entries SET linked_main_id = NULL WHERE linked_main_id = ?",
                (entry_id,),
            )
            conn.execute("DELETE FROM entries WHERE id = ?", (entry_id,))

    def get_all_entries(self) -> List[dict]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT id, website, username, email, is_main, linked_main_id "
                "FROM entries ORDER BY website COLLATE NOCASE ASC"
            ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def search_entries(self, query: str) -> List[dict]:
        like = f"%{query}%"
        with closing(self._connect()) as conn:
            rows = conn.execute(
                """
                SELECT id, website, username, email, is_main, linked_main_id
                FROM entries
                WHERE website LIKE ? COLLATE NOCASE
                   OR username LIKE ? COLLATE NOCASE
                   OR email LIKE ? COLLATE NOCASE
                ORDER BY website COLLATE NOCASE ASC
                """,
                (like, like, like),
            ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def get_entry(self, entry_id: int) -> Optional[dict]:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT id, website, username, email, is_main, linked_main_id "
                "FROM entries WHERE id = ?",
                (entry_id,),
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def get_main_accounts(self) -> List[dict]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT id, website, username, email, is_main, linked_main_id "
                "FROM entries WHERE is_main = 1 ORDER BY website COLLATE NOCASE ASC"
            ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def decrypt_entry_password(self, entry_id: int, key: bytes) -> str:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT password_enc FROM entries WHERE id = ?", (entry_id,)
            ).fetchone()
        if row is None:
            raise ValueError("Entry not found.")
        return crypto_utils.decrypt_text(row[0], key)

    # ------------------------------------------------------------------
    # Wipe vault
    # ------------------------------------------------------------------

    def wipe_vault(self) -> None:
        """
        Permanently deletes every entry AND the master password verifier,
        in a single transaction, returning the vault to its just-installed,
        uninitialized state. There is no undo - use this to start over
        completely, or before handing off/uninstalling the app.

        Also resets the entries table's AUTOINCREMENT counter (SQLite
        tracks it separately, in a hidden sqlite_sequence table, so
        deleting every row alone does NOT reset it) - otherwise the next
        entry created after a wipe would continue from the old highest ID
        instead of starting back at 1, which looks like a bug even though
        the data itself is genuinely gone.
        """
        with closing(self._connect()) as conn, conn:
            conn.execute("DELETE FROM entries")
            conn.execute("DELETE FROM vault_meta")
            conn.execute("DELETE FROM sqlite_sequence WHERE name = 'entries'")

    # ------------------------------------------------------------------
    # Backup / restore
    # ------------------------------------------------------------------
    # The database file is copied as-is: it's already fully encrypted at
    # rest (see the module docstring), so a backup file is exactly as
    # safe to store/transport as the live vault file. Restoring simply
    # overwrites the live file - after which the caller must re-lock and
    # re-unlock, since a restored backup may carry a different master
    # password than the one just used to authorize the restore.

    def backup_to(self, destination_path: str) -> None:
        shutil.copy2(self.db_path, destination_path)

    @staticmethod
    def is_valid_vault_file(path: str) -> bool:
        """Sanity-checks that `path` looks like a genuine Password Vault database."""
        try:
            conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        except sqlite3.Error:
            return False
        try:
            row = conn.execute(
                "SELECT auth_salt, auth_hash, key_salt FROM vault_meta WHERE id = 1"
            ).fetchone()
            conn.execute("SELECT id FROM entries LIMIT 1")  # confirms the table exists
            return row is not None
        except sqlite3.Error:
            return False
        finally:
            conn.close()

    def restore_from(self, source_path: str) -> None:
        if not self.is_valid_vault_file(source_path):
            raise ValueError("That file doesn't look like a valid Password Vault backup.")
        shutil.copy2(source_path, self.db_path)

    # ------------------------------------------------------------------
    @staticmethod
    def _row_to_dict(row) -> dict:
        return {
            "id": row[0],
            "website": row[1],
            "username": row[2],
            "email": row[3],
            "is_main": bool(row[4]),
            "linked_main_id": row[5],
        }
