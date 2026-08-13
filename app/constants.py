"""
Central place for app-wide constants: paths, sizes, colors, security parameters.
Keeping these in one file makes the app easy to re-theme or re-target
(e.g. changing the data directory for a future cross-platform build).
"""

import os
import sys

APP_NAME = "Password Vault"
APP_VERSION = "0.7.2"


def get_app_data_dir() -> str:
    """
    Returns a per-user, per-OS directory to store the vault database.

    Windows -> %APPDATA%\\PasswordVault
    macOS   -> ~/Library/Application Support/PasswordVault
    Linux   -> ~/.local/share/PasswordVault

    Keeping this logic isolated makes the eventual cross-platform port trivial.
    """
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    elif sys.platform == "darwin":
        base = os.path.join(os.path.expanduser("~"), "Library", "Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME", os.path.join(os.path.expanduser("~"), ".local", "share"))

    app_dir = os.path.join(base, "PasswordVault")
    os.makedirs(app_dir, exist_ok=True)
    return app_dir


DB_FILENAME = "vault.db"
DB_PATH = os.path.join(get_app_data_dir(), DB_FILENAME)


def resource_path(relative_path: str) -> str:
    """
    Resolves a path to a bundled asset (e.g. the app icon) correctly both
    when running from source and when running as a PyInstaller-frozen
    .exe, where bundled files are unpacked to a temp folder at sys._MEIPASS.
    """
    if hasattr(sys, "_MEIPASS"):
        base = sys._MEIPASS
    else:
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(base, relative_path)

# --- Security parameters -----------------------------------------------
# PBKDF2 iteration counts. High enough to be slow for brute-force attempts,
# low enough to feel instant to a real user (~0.1-0.3s on modern hardware).
AUTH_HASH_ITERATIONS = 390_000     # for verifying the master password
KEY_DERIVATION_ITERATIONS = 390_000  # for deriving the AES/Fernet encryption key
SALT_SIZE_BYTES = 16

# --- UI ------------------------------------------------------------------
# Dark slate base with a cyan accent, matching assets/icon.ico.
WINDOW_BG = "#12141c"
PANEL_BG = "#1a1d29"
ACCENT = "#06b6d4"          # cyan-500 - buttons, focus rings
ACCENT_HOVER = "#22d3ee"    # cyan-400 - hover state (brighter)
ACCENT_SELECTED = "#0e7490"  # cyan-700 - table row selection (darker, keeps white text readable)
DANGER = "#e74c3c"
DANGER_HOVER = "#ff6b5b"
SUCCESS = "#2ecc71"
TEXT_PRIMARY = "#f2f2f7"
TEXT_SECONDARY = "#93a0ad"
ENTRY_BG = "#232735"
FONT_FAMILY = "Segoe UI"

MAIN_WINDOW_SIZE = "900x520"
LOGIN_WINDOW_SIZE = "380x420"

ICON_PATH_ICO = resource_path("assets/icon.ico")
