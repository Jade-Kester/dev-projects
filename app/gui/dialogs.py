"""
dialogs.py
-----------
All the modal popup windows used by the main window:

* ask_master_password()   - generic re-authentication prompt, used before
                             revealing a password and before deleting an entry.
* confirm_no_recovery_warning() - final "this can't be recovered" gate
                             shown before a brand-new vault is created.
* confirm_wipe_vault_warning() - final "this deletes everything" gate
                             shown before Wipe Vault runs.
* ChangeMasterPasswordDialog
* EntryFormDialog          - shared Add/Edit entry form (radio buttons for
                             None / New Main Account / Existing Main Account).
* DeleteEntryDialog        - pick an entry, confirm, re-enter master password.
"""

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, Optional

from app import constants as c
from app.database import VaultDatabase
from app.gui import style
from app.session import VaultSession


# ---------------------------------------------------------------------------
# Master password re-authentication prompt
# ---------------------------------------------------------------------------

def ask_master_password(parent: tk.Misc, db: VaultDatabase, message: str) -> bool:
    """
    Blocking modal that asks the user to re-enter their master password.
    Returns True only if the password is verified correct.
    Used before revealing a password and before deleting an entry, per
    the vault's "extra safety" requirement.
    """
    result = {"ok": False}
    dialog = tk.Toplevel(parent)
    dialog.title("Confirm Master Password")
    dialog.configure(bg=c.WINDOW_BG)
    dialog.resizable(False, False)
    dialog.transient(parent)
    dialog.grab_set()

    frame = ttk.Frame(dialog, padding=20)
    frame.pack(fill="both", expand=True)

    ttk.Label(frame, text=message, wraplength=280, justify="left").pack(anchor="w", pady=(0, 10))
    ttk.Label(frame, text="Master Password").pack(anchor="w")
    pw_entry = ttk.Entry(frame, show="\u2022")
    pw_entry.pack(fill="x", pady=(2, 4))
    pw_entry.focus_set()

    error_label = ttk.Label(frame, text="", foreground=c.DANGER, background=c.WINDOW_BG)
    error_label.pack(anchor="w", pady=(0, 8))

    def submit(_event=None):
        pwd = pw_entry.get()
        if db.verify_master_password(pwd):
            result["ok"] = True
            dialog.destroy()
        else:
            error_label.configure(text="Incorrect master password.")
            pw_entry.delete(0, "end")

    def cancel():
        dialog.destroy()

    btn_row = ttk.Frame(frame)
    btn_row.pack(fill="x", pady=(6, 0))
    ttk.Button(btn_row, text="Cancel", style="Toolbar.TButton", command=cancel).pack(
        side="right", padx=(6, 0)
    )
    ttk.Button(btn_row, text="Confirm", style="Accent.TButton", command=submit).pack(side="right")

    dialog.bind("<Return>", submit)
    dialog.bind("<Escape>", lambda _e: cancel())

    dialog.update_idletasks()
    _center_on_parent(dialog, parent)
    parent.wait_window(dialog)
    return result["ok"]


def _center_on_parent(win: tk.Toplevel, parent: tk.Misc) -> None:
    win.update_idletasks()
    px, py = parent.winfo_rootx(), parent.winfo_rooty()
    pw, ph = parent.winfo_width(), parent.winfo_height()
    w, h = win.winfo_width(), win.winfo_height()
    x = px + (pw - w) // 2
    y = py + (ph - h) // 2
    win.geometry(f"+{max(x, 0)}+{max(y, 0)}")


# ---------------------------------------------------------------------------
# First-run "no recovery" warning
# ---------------------------------------------------------------------------

def confirm_no_recovery_warning(parent: tk.Misc) -> bool:
    """
    Final gate shown right before a brand-new vault is created. Password
    Vault has no account-recovery mechanism by design (see the
    conversation that led here) - this makes sure that trade-off is
    understood, not just buried in the README, before it can bite
    someone. Returns True only if the person explicitly acknowledges it
    via the checkbox and clicks through; False sends them back to adjust
    their password.
    """
    result = {"ok": False}
    dialog = tk.Toplevel(parent)
    dialog.title("Before You Continue")
    dialog.configure(bg=c.WINDOW_BG)
    dialog.resizable(False, False)
    dialog.transient(parent)
    dialog.grab_set()

    frame = ttk.Frame(dialog, padding=24)
    frame.pack(fill="both", expand=True)

    ttk.Label(
        frame,
        text="\u26A0 This Password Cannot Be Recovered",
        style="Heading.TLabel",
        wraplength=360,
        justify="left",
    ).pack(anchor="w", pady=(0, 10))

    warning_text = (
        "Password Vault has no \"Forgot Password\" option, no server, and no backup key. "
        "Your master password itself is never stored anywhere - only a one-way hash used to "
        "verify it later.\n\n"
        "If you forget it, every saved entry becomes permanently unreadable. The only way back "
        "in is to wipe the vault and start over from scratch.\n\n"
        "Make sure you'll remember it, or store it somewhere safe before continuing."
    )
    ttk.Label(frame, text=warning_text, wraplength=360, justify="left").pack(anchor="w", pady=(0, 16))

    ack_var = tk.BooleanVar(value=False)

    def _on_ack_toggled() -> None:
        create_btn.configure(state=("normal" if ack_var.get() else "disabled"))

    ttk.Checkbutton(
        frame,
        text="I understand this cannot be recovered.",
        variable=ack_var,
        command=_on_ack_toggled,
    ).pack(anchor="w", pady=(0, 16))

    def confirm() -> None:
        if not ack_var.get():
            return
        result["ok"] = True
        dialog.destroy()

    def cancel() -> None:
        dialog.destroy()

    btn_row = ttk.Frame(frame)
    btn_row.pack(fill="x")
    ttk.Button(btn_row, text="Go Back", style="Toolbar.TButton", command=cancel).pack(
        side="right", padx=(6, 0)
    )
    create_btn = ttk.Button(
        btn_row, text="Create Vault", style="Accent.TButton", command=confirm, state="disabled"
    )
    create_btn.pack(side="right")

    dialog.bind("<Escape>", lambda _e: cancel())

    dialog.update_idletasks()
    _center_on_parent(dialog, parent)
    parent.wait_window(dialog)
    return result["ok"]


# ---------------------------------------------------------------------------
# Wipe Vault warning
# ---------------------------------------------------------------------------

def confirm_wipe_vault_warning(parent: tk.Misc) -> bool:
    """
    Gate shown before Wipe Vault runs. This is the most destructive
    action in the app - it deletes every entry AND the master password
    itself, so the confirmation is deliberately heavier than a normal
    delete: two separate acknowledgments (data loss, and the master
    password reset) must both be checked before the button enables.
    The caller is still expected to re-verify the current master
    password afterward (see MainWindow._wipe_vault) - this dialog alone
    only confirms understanding, not identity.
    """
    result = {"ok": False}
    dialog = tk.Toplevel(parent)
    dialog.title("Wipe Vault")
    dialog.configure(bg=c.WINDOW_BG)
    dialog.resizable(False, False)
    dialog.transient(parent)
    dialog.grab_set()

    frame = ttk.Frame(dialog, padding=24)
    frame.pack(fill="both", expand=True)

    ttk.Label(
        frame,
        text="\u26A0 This Will Permanently Delete Everything",
        style="Heading.TLabel",
        wraplength=360,
        justify="left",
    ).pack(anchor="w", pady=(0, 10))

    # Wipe Vault lives in the Options menu, which is only reachable once
    # the vault is already unlocked - so it can't actually serve as a
    # recovery path for a forgotten master password (you'd need to be
    # logged in to see this menu in the first place). The wording below
    # is deliberately framed around the cases it *can* help with instead.
    warning_text = (
        "Wipe Vault erases the entire vault: every saved entry, and the master "
        "password itself. The app returns to its just-installed state, as if it had "
        "never been used - there is no undo.\n\n"
        "Use this if you want to start completely over, or before handing off or "
        "uninstalling this installation. If you just want a safety copy first, use "
        "Options > Backup Database instead and cancel this."
    )
    ttk.Label(frame, text=warning_text, wraplength=360, justify="left").pack(anchor="w", pady=(0, 14))

    entries_ack_var = tk.BooleanVar(value=False)
    password_ack_var = tk.BooleanVar(value=False)

    def _on_ack_toggled() -> None:
        both_checked = entries_ack_var.get() and password_ack_var.get()
        wipe_btn.configure(state=("normal" if both_checked else "disabled"))

    # NOTE: ttk.Checkbutton has no -wraplength option (unlike ttk.Label or
    # classic tk.Checkbutton) - passing one raises a TclError. Keep these
    # labels short enough to read on one line instead.
    ttk.Checkbutton(
        frame,
        text="I understand every saved entry will be permanently deleted.",
        variable=entries_ack_var,
        command=_on_ack_toggled,
    ).pack(anchor="w", pady=(0, 4))
    ttk.Checkbutton(
        frame,
        text="I understand the master password will be reset too.",
        variable=password_ack_var,
        command=_on_ack_toggled,
    ).pack(anchor="w", pady=(0, 16))

    def confirm() -> None:
        if not (entries_ack_var.get() and password_ack_var.get()):
            return
        result["ok"] = True
        dialog.destroy()

    def cancel() -> None:
        dialog.destroy()

    btn_row = ttk.Frame(frame)
    btn_row.pack(fill="x")
    ttk.Button(btn_row, text="Cancel", style="Toolbar.TButton", command=cancel).pack(
        side="right", padx=(6, 0)
    )
    wipe_btn = ttk.Button(
        btn_row, text="Wipe Vault", style="Danger.TButton", command=confirm, state="disabled"
    )
    wipe_btn.pack(side="right")

    dialog.bind("<Escape>", lambda _e: cancel())

    dialog.update_idletasks()
    _center_on_parent(dialog, parent)
    parent.wait_window(dialog)
    return result["ok"]


# ---------------------------------------------------------------------------
# Change master password
# ---------------------------------------------------------------------------

class ChangeMasterPasswordDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, db: VaultDatabase, on_changed: Callable[[], None]):
        super().__init__(parent)
        self.db = db
        self.on_changed = on_changed

        self.title("Change Master Password")
        self.configure(bg=c.WINDOW_BG)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        frame = ttk.Frame(self, padding=20)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Change Master Password", style="Heading.TLabel").pack(
            anchor="w", pady=(0, 12)
        )

        ttk.Label(frame, text="Current Master Password").pack(anchor="w")
        self.current_entry = ttk.Entry(frame, show="\u2022", width=32)
        self.current_entry.pack(fill="x", pady=(2, 10))

        ttk.Label(frame, text="New Master Password").pack(anchor="w")
        self.new_entry = ttk.Entry(frame, show="\u2022", width=32)
        self.new_entry.pack(fill="x", pady=(2, 10))

        ttk.Label(frame, text="Confirm New Master Password").pack(anchor="w")
        self.confirm_entry = ttk.Entry(frame, show="\u2022", width=32)
        self.confirm_entry.pack(fill="x", pady=(2, 4))

        self.error_label = ttk.Label(frame, text="", foreground=c.DANGER, background=c.WINDOW_BG)
        self.error_label.pack(anchor="w", pady=(0, 8))

        btn_row = ttk.Frame(frame)
        btn_row.pack(fill="x", pady=(6, 0))
        ttk.Button(btn_row, text="Cancel", style="Toolbar.TButton", command=self.destroy).pack(
            side="right", padx=(6, 0)
        )
        ttk.Button(
            btn_row, text="Update Password", style="Accent.TButton", command=self._submit
        ).pack(side="right")

        self.current_entry.focus_set()
        self.update_idletasks()
        _center_on_parent(self, parent)

    def _submit(self) -> None:
        current = self.current_entry.get()
        new = self.new_entry.get()
        confirm = self.confirm_entry.get()

        if len(new) < 8:
            self.error_label.configure(text="New password must be at least 8 characters.")
            return
        if new != confirm:
            self.error_label.configure(text="New passwords do not match.")
            return

        try:
            self.db.change_master_password(current, new)
        except ValueError as exc:
            self.error_label.configure(text=str(exc))
            return

        messagebox.showinfo(c.APP_NAME, "Master password updated successfully.")
        self.on_changed()
        self.destroy()


# ---------------------------------------------------------------------------
# Add / Edit entry
# ---------------------------------------------------------------------------

class EntryFormDialog(tk.Toplevel):
    """
    Shared form for adding a new entry or editing an existing one.
    Pass `existing_entry` (a dict from VaultDatabase.get_entry) to edit.
    """

    MODE_NONE = "none"
    MODE_NEW_MAIN = "new_main"
    MODE_EXISTING_MAIN = "existing_main"

    def __init__(
        self,
        parent: tk.Misc,
        db: VaultDatabase,
        session: VaultSession,
        on_saved: Callable[[], None],
        existing_entry: Optional[dict] = None,
    ):
        super().__init__(parent)
        self.db = db
        self.session = session
        self.on_saved = on_saved
        self.existing_entry = existing_entry
        self.is_edit = existing_entry is not None

        self.title("Edit Entry" if self.is_edit else "Add New Entry")
        self.configure(bg=c.WINDOW_BG)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.main_accounts = self.db.get_main_accounts()
        # When editing, a main account can't "become linked" to itself.
        if self.is_edit:
            self.main_accounts = [m for m in self.main_accounts if m["id"] != existing_entry["id"]]

        self._build_ui()
        if self.is_edit:
            self._prefill()

        self.update_idletasks()
        _center_on_parent(self, parent)

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        frame = ttk.Frame(self, padding=20)
        frame.pack(fill="both", expand=True)

        title = "Edit Entry" if self.is_edit else "Add New Entry"
        ttk.Label(frame, text=title, style="Heading.TLabel").pack(anchor="w", pady=(0, 12))

        ttk.Label(frame, text="Website").pack(anchor="w")
        self.website_entry = ttk.Entry(frame, width=38)
        self.website_entry.pack(fill="x", pady=(2, 8))

        ttk.Label(frame, text="Username").pack(anchor="w")
        self.username_entry = ttk.Entry(frame, width=38)
        self.username_entry.pack(fill="x", pady=(2, 8))

        ttk.Label(frame, text="E-mail").pack(anchor="w")
        self.email_entry = ttk.Entry(frame, width=38)
        self.email_entry.pack(fill="x", pady=(2, 8))

        ttk.Label(frame, text="Password").pack(anchor="w")
        pw_row = ttk.Frame(frame)
        pw_row.pack(fill="x", pady=(2, 10))
        self.password_entry = ttk.Entry(pw_row, show="\u2022")
        self.password_entry.pack(side="left", fill="x", expand=True)
        self.show_pw_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            pw_row,
            text="Show",
            variable=self.show_pw_var,
            command=self._toggle_password_visibility,
        ).pack(side="left", padx=(8, 0))

        if self.is_edit and self.existing_entry["is_main"]:
            linked_count = self.db.count_linked_entries(self.existing_entry["id"])
            if linked_count:
                plural = "account" if linked_count == 1 else "accounts"
                ttk.Label(
                    frame,
                    text=(
                        f"This is a Main Account with {linked_count} linked {plural}. "
                        "Changing the e-mail/password here updates them too."
                    ),
                    foreground=c.ACCENT_HOVER,
                    background=c.WINDOW_BG,
                    wraplength=320,
                    justify="left",
                ).pack(anchor="w", pady=(0, 6))

        # --- Main account association ----------------------------------
        ttk.Separator(frame).pack(fill="x", pady=10)
        ttk.Label(frame, text="Main Account Association", style="Secondary.TLabel").pack(anchor="w")

        self.link_mode_var = tk.StringVar(value=self.MODE_NONE)
        ttk.Radiobutton(
            frame, text="None", variable=self.link_mode_var, value=self.MODE_NONE,
            command=self._on_mode_changed,
        ).pack(anchor="w")
        ttk.Radiobutton(
            frame, text="New Main Account", variable=self.link_mode_var, value=self.MODE_NEW_MAIN,
            command=self._on_mode_changed,
        ).pack(anchor="w")
        ttk.Radiobutton(
            frame, text="Existing Main Account", variable=self.link_mode_var,
            value=self.MODE_EXISTING_MAIN, command=self._on_mode_changed,
        ).pack(anchor="w")

        self.main_account_combo = ttk.Combobox(frame, state="readonly", width=36)
        self.main_account_combo.pack(fill="x", pady=(6, 0))
        self.main_account_combo.pack_forget()  # hidden until "Existing Main Account" chosen
        self.main_account_combo.bind("<<ComboboxSelected>>", lambda _e: self._on_main_account_selected())

        self.no_main_accounts_label = ttk.Label(
            frame, text="No Main Accounts available, please create one first.",
            foreground=c.DANGER, background=c.WINDOW_BG,
        )
        # shown/hidden dynamically, not packed yet

        self.error_label = ttk.Label(frame, text="", foreground=c.DANGER, background=c.WINDOW_BG)
        self.error_label.pack(anchor="w", pady=(10, 0))

        btn_row = ttk.Frame(frame)
        btn_row.pack(fill="x", pady=(10, 0))
        ttk.Button(btn_row, text="Cancel", style="Toolbar.TButton", command=self.destroy).pack(
            side="right", padx=(6, 0)
        )
        ttk.Button(
            btn_row,
            text="Save Changes" if self.is_edit else "Add Entry",
            style="Accent.TButton",
            command=self._submit,
        ).pack(side="right")

    # ------------------------------------------------------------------
    def _prefill(self) -> None:
        e = self.existing_entry
        self.website_entry.insert(0, e["website"])
        self.username_entry.insert(0, e["username"])
        self.email_entry.insert(0, e["email"])
        try:
            plain_pw = self.db.decrypt_entry_password(e["id"], self.session.key)
        except Exception:
            plain_pw = ""
        self.password_entry.insert(0, plain_pw)

        if e["is_main"]:
            # Editing a main account itself: keep it simple, no self-linking options.
            self.link_mode_var.set(self.MODE_NEW_MAIN)
        elif e["linked_main_id"]:
            self.link_mode_var.set(self.MODE_EXISTING_MAIN)
        else:
            self.link_mode_var.set(self.MODE_NONE)
        self._on_mode_changed(prefill_main_id=e.get("linked_main_id"))

    def _toggle_password_visibility(self) -> None:
        self.password_entry.configure(show="" if self.show_pw_var.get() else "\u2022")

    def _on_mode_changed(self, prefill_main_id: Optional[int] = None) -> None:
        mode = self.link_mode_var.get()
        self.no_main_accounts_label.pack_forget()
        self.main_account_combo.pack_forget()

        if mode == self.MODE_EXISTING_MAIN:
            if not self.main_accounts:
                self.no_main_accounts_label.pack(anchor="w", pady=(6, 0))
                self.link_mode_var.set(self.MODE_NONE)
                return

            labels = [f'{m["website"]} - {m["username"]}' for m in self.main_accounts]
            self.main_account_combo.configure(values=labels)
            self.main_account_combo.pack(fill="x", pady=(6, 0))

            if prefill_main_id is not None:
                for idx, m in enumerate(self.main_accounts):
                    if m["id"] == prefill_main_id:
                        self.main_account_combo.current(idx)
                        self._on_main_account_selected()
                        break
            else:
                self._set_fields_locked(False)  # nothing selected yet
        elif mode == self.MODE_NEW_MAIN:
            self._set_fields_locked(False)
        else:  # MODE_NONE
            self._set_fields_locked(False)
            self.email_entry.delete(0, "end")
            self.password_entry.delete(0, "end")

    def _on_main_account_selected(self) -> None:
        idx = self.main_account_combo.current()
        if idx < 0:
            return
        main = self.main_accounts[idx]
        try:
            plain_pw = self.db.decrypt_entry_password(main["id"], self.session.key)
        except Exception:
            plain_pw = ""

        self.email_entry.configure(state="normal")
        self.email_entry.delete(0, "end")
        self.email_entry.insert(0, main["email"])

        self.password_entry.configure(state="normal")
        self.password_entry.delete(0, "end")
        self.password_entry.insert(0, plain_pw)

        self._set_fields_locked(True)

    def _set_fields_locked(self, locked: bool) -> None:
        state = "disabled" if locked else "normal"
        self.email_entry.configure(state=state)
        self.password_entry.configure(state=state)

    # ------------------------------------------------------------------
    def _submit(self) -> None:
        website = self.website_entry.get().strip()
        username = self.username_entry.get().strip()
        email = self.email_entry.get().strip()
        password = self.password_entry.get()
        mode = self.link_mode_var.get()

        if not website:
            self.error_label.configure(text="Website is required.")
            return
        if not password:
            self.error_label.configure(text="Password is required.")
            return

        is_main = mode == self.MODE_NEW_MAIN
        linked_main_id = None
        if mode == self.MODE_EXISTING_MAIN:
            idx = self.main_account_combo.current()
            if idx < 0:
                self.error_label.configure(text="Please select a Main Account.")
                return
            linked_main_id = self.main_accounts[idx]["id"]

        key = self.session.key
        if self.is_edit:
            self.db.update_entry(
                self.existing_entry["id"], website, username, email, password, key,
                is_main=is_main, linked_main_id=linked_main_id,
            )
        else:
            self.db.add_entry(
                website, username, email, password, key,
                is_main=is_main, linked_main_id=linked_main_id,
            )

        self.on_saved()
        self.destroy()


# ---------------------------------------------------------------------------
# Delete entry
# ---------------------------------------------------------------------------

class DeleteEntryDialog(tk.Toplevel):
    """Pick an entry from a dropdown, confirm, then re-enter the master password."""

    def __init__(self, parent: tk.Misc, db: VaultDatabase, on_deleted: Callable[[], None]):
        super().__init__(parent)
        self.db = db
        self.on_deleted = on_deleted
        self.entries = self.db.get_all_entries()

        self.title("Delete Existing Entry")
        self.configure(bg=c.WINDOW_BG)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        frame = ttk.Frame(self, padding=20)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Delete Existing Entry", style="Heading.TLabel").pack(
            anchor="w", pady=(0, 12)
        )

        if not self.entries:
            ttk.Label(frame, text="There are no entries to delete.").pack(anchor="w")
            ttk.Button(frame, text="Close", style="Toolbar.TButton", command=self.destroy).pack(
                anchor="e", pady=(16, 0)
            )
            self.update_idletasks()
            _center_on_parent(self, parent)
            return

        ttk.Label(frame, text="Select an account to delete:").pack(anchor="w")
        self.labels = [f'{e["website"]} - {e["username"] or e["email"]} (ID {e["id"]})' for e in self.entries]
        self.combo = ttk.Combobox(frame, state="readonly", values=self.labels, width=40)
        self.combo.pack(fill="x", pady=(4, 12))

        btn_row = ttk.Frame(frame)
        btn_row.pack(fill="x")
        ttk.Button(btn_row, text="Cancel", style="Toolbar.TButton", command=self.destroy).pack(
            side="right", padx=(6, 0)
        )
        ttk.Button(btn_row, text="Delete", style="Danger.TButton", command=self._on_delete_clicked).pack(
            side="right"
        )

        self.update_idletasks()
        _center_on_parent(self, parent)

    def _on_delete_clicked(self) -> None:
        idx = self.combo.current()
        if idx < 0:
            messagebox.showwarning(c.APP_NAME, "Please select an account first.")
            return
        entry = self.entries[idx]

        confirmed = messagebox.askyesno(
            "Confirm Delete",
            f'Are you sure you want to delete the "{entry["website"]}" account '
            f'({entry["username"] or entry["email"]})?',
            parent=self,
        )
        if not confirmed:
            return

        if not ask_master_password(
            self, self.db, "Enter your master password to confirm this deletion."
        ):
            return

        self.db.delete_entry(entry["id"])
        self.on_deleted()
        self.destroy()
