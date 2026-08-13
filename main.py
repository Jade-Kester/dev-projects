#!/usr/bin/env python3
"""
Password Vault - entry point.

Run with:  python main.py
Build an .exe with PyInstaller - see README.md for the exact command.
"""

import sys
import traceback
from tkinter import messagebox

from app.constants import DB_PATH
from app.database import VaultDatabase
from app.gui.app_controller import VaultApp


def main() -> None:
    try:
        db = VaultDatabase(DB_PATH)
        app = VaultApp(db)
        app.run()
    except Exception as exc:  # last-resort guard so the user sees *something*
        traceback.print_exc()
        try:
            messagebox.showerror("Password Vault - Fatal Error", str(exc))
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
