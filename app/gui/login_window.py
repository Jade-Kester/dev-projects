"""
login_window.py
-----------------
The screen shown on every launch:

* First run ever  -> "Create your master password" (asks twice, must
  match), followed by a final "this cannot be recovered" warning that
  must be explicitly acknowledged before the vault is actually created.
* Every run after -> "Enter master password" (single field + Unlock).

On success, tells the owning VaultApp controller to switch to the main
window. This class is a Toplevel (not its own Tk root) so the whole
application only ever runs a single Tk mainloop - see app/gui/app_controller.py.
"""

import tkinter as tk
from tkinter import messagebox, ttk

from app import constants as c
from app.database import VaultDatabase
from app.gui import style
from app.gui.dialogs import confirm_no_recovery_warning
from app.session import VaultSession


class LoginWindow(tk.Toplevel):
    def __init__(self, master: tk.Misc, db: VaultDatabase, session: VaultSession, on_unlocked):
        super().__init__(master)
        self.db = db
        self.session = session
        self.on_unlocked = on_unlocked

        self.title(c.APP_NAME)
        self.geometry(c.LOGIN_WINDOW_SIZE)
        self.resizable(False, False)
        style.apply_style(self)
        style.apply_icon(self)

        self.first_run = not self.db.is_vault_initialized()
        self._build_ui()
        self.bind("<Return>", lambda _event: self._on_submit())
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        container = ttk.Frame(self, padding=30)
        container.pack(fill="both", expand=True)

        ttk.Label(container, text="\U0001F510", font=("Segoe UI Emoji", 36)).pack(pady=(10, 6))
        ttk.Label(container, text=c.APP_NAME, style="Heading.TLabel").pack()

        if self.first_run:
            ttk.Label(
                container,
                text="Create a master password to secure your vault.",
                style="Secondary.TLabel",
                wraplength=300,
                justify="center",
            ).pack(pady=(6, 18))

            ttk.Label(container, text="New Master Password").pack(anchor="w")
            self.pw_entry = ttk.Entry(container, show="\u2022")
            self.pw_entry.pack(fill="x", pady=(2, 10))

            ttk.Label(container, text="Confirm Master Password").pack(anchor="w")
            self.confirm_entry = ttk.Entry(container, show="\u2022")
            self.confirm_entry.pack(fill="x", pady=(2, 4))

            self.strength_label = ttk.Label(container, text="", style="Secondary.TLabel")
            self.strength_label.pack(anchor="w", pady=(0, 4))
            self.pw_entry.bind("<KeyRelease>", self._update_strength_hint)

            ttk.Label(
                container,
                text="This cannot be recovered if forgotten - there is no \"Forgot Password\" option.",
                foreground=c.DANGER,
                background=c.WINDOW_BG,
                wraplength=300,
                justify="left",
            ).pack(anchor="w", pady=(0, 10))

            ttk.Button(
                container, text="Create Vault", style="Accent.TButton", command=self._on_submit
            ).pack(fill="x", pady=(10, 0))

            self.pw_entry.focus_set()
        else:
            ttk.Label(
                container,
                text="Enter your master password to unlock the vault.",
                style="Secondary.TLabel",
                wraplength=300,
                justify="center",
            ).pack(pady=(6, 18))

            ttk.Label(container, text="Master Password").pack(anchor="w")
            self.pw_entry = ttk.Entry(container, show="\u2022")
            self.pw_entry.pack(fill="x", pady=(2, 4))

            self.error_label = ttk.Label(container, text="", foreground=c.DANGER, background=c.WINDOW_BG)
            self.error_label.pack(anchor="w", pady=(0, 10))

            ttk.Button(
                container, text="Unlock", style="Accent.TButton", command=self._on_submit
            ).pack(fill="x", pady=(10, 0))

            self.pw_entry.focus_set()

    # ------------------------------------------------------------------
    def _update_strength_hint(self, _event=None) -> None:
        pwd = self.pw_entry.get()
        score = _password_strength_score(pwd)
        labels = ["Very weak", "Weak", "Okay", "Strong", "Very strong"]
        self.strength_label.configure(text=f"Strength: {labels[score]}" if pwd else "")

    def _on_submit(self) -> None:
        if self.first_run:
            self._handle_create()
        else:
            self._handle_login()

    def _handle_create(self) -> None:
        pwd = self.pw_entry.get()
        confirm = self.confirm_entry.get()

        if len(pwd) < 8:
            messagebox.showerror(c.APP_NAME, "Master password must be at least 8 characters long.")
            return
        if pwd != confirm:
            messagebox.showerror(c.APP_NAME, "Passwords do not match.")
            return

        # Final, explicit warning: there is no account recovery by design.
        # Declining sends the person back to adjust/reconsider their password
        # rather than silently proceeding.
        if not confirm_no_recovery_warning(self):
            return

        self.db.create_master_password(pwd)
        self.session.unlock(pwd)
        self._launch_main_window()

    def _handle_login(self) -> None:
        pwd = self.pw_entry.get()
        if self.session.unlock(pwd):
            self._launch_main_window()
        else:
            self.error_label.configure(text="Incorrect master password. Try again.")
            self.pw_entry.delete(0, "end")

    def _launch_main_window(self) -> None:
        self.on_unlocked()

    def _on_close(self) -> None:
        # Closing the login/create-vault window closes the whole app.
        self.master.destroy()


def _password_strength_score(pwd: str) -> int:
    """Very small heuristic just to nudge users toward a stronger master password."""
    if not pwd:
        return 0
    score = 0
    if len(pwd) >= 8:
        score += 1
    if len(pwd) >= 12:
        score += 1
    if any(ch.isdigit() for ch in pwd):
        score += 1
    if any(ch.isupper() for ch in pwd) and any(ch.islower() for ch in pwd):
        score += 1
    if any(not ch.isalnum() for ch in pwd):
        score += 1
    return min(score, 4)
