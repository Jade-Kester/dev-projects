"""
main_window.py
-----------------
The primary window shown once the vault is unlocked:

* Menu bar "Options" -> Change Master Password, Backup Database,
  Restore Database, Lock Vault.
* Search bar (website / username / email) with a Search button.
* Toolbar: Add New Entry | Delete Existing Entry | Edit Existing Entry,
  plus View/Hide Password acting on the selected row.
* Table: ID, Website, E-Mail, Password. Main Accounts and linked entries
  are marked directly in the Website column (see below) rather than in
  a separate column.

Website-column badges
======================
* A Main Account shows a "★ " prefix before its website name - plain
  text, since a single symbol doesn't need any special rendering.
* An entry linked to a Main Account shows "<website> — <Main Account>
  linked", with the Main Account's name in **bold**. A ttk.Treeview
  can't mix fonts within one cell, so for these rows a small composite
  overlay (regular/bold/regular Label widgets) is placed exactly on top
  of the website cell using `tree.bbox()`. The plain-text version is
  still the real cell value underneath, as a fallback and for search/
  copy - the overlay is a purely visual enhancement. Clicks on the
  overlay are forwarded to the underlying row (select / right-click
  menu) so it behaves like part of the table.

Making cells selectable, in the table itself
=============================================
The E-mail cell of the selected row, and the Password cell once
revealed, get the same overlay treatment but with a read-only ttk.Entry
instead of Labels, so the text can be drag-selected and Ctrl+C copied
directly in the table.

Security notes:
* Editing an entry re-prompts for the master password before the form
  opens (it would otherwise quietly decrypt and display the stored
  password to whoever has the app open, unlocked or not).
* A revealed password stays visible (via its overlay) until the Hide
  Password button is used, a different row is selected, or a
  data-changing action happens (add/edit/delete/search/lock/relaunch/
  restore) that rebuilds the table.
* The underlying table cell always displays literal placeholder dots,
  never the real password under a masking character - only the overlay,
  shown after re-authentication, ever holds the real value.
* Restoring a backup overwrites the live vault file; since a restored
  vault may carry a different master password than the one just used to
  authorize the restore, the app locks and returns to the unlock screen
  immediately afterward.
"""

import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Optional

from app import constants as c
from app.database import VaultDatabase
from app.gui import style
from app.gui.dialogs import (
    ChangeMasterPasswordDialog,
    DeleteEntryDialog,
    EntryFormDialog,
    ask_master_password,
    confirm_wipe_vault_warning,
)
from app.session import VaultSession

PASSWORD_MASK = "\u2022" * 10
MAIN_ACCOUNT_PREFIX = "\u2605 "  # "★ "


class MainWindow(tk.Toplevel):
    def __init__(self, parent: tk.Misc, db: VaultDatabase, session: VaultSession, on_lock: Callable[[], None]):
        super().__init__(parent)
        self.db = db
        self.session = session
        self.on_lock = on_lock

        # The single entry (if any) currently revealed via the password overlay.
        self._revealed_entry_id: Optional[int] = None
        # website of each main account, keyed by entry id - used to label linked rows.
        self._main_account_websites: dict[int, str] = {}
        # entry_id -> the composite "<website> — <Main Account> linked" overlay Frame.
        self._linked_overlays: dict[int, tk.Frame] = {}

        self.title(c.APP_NAME)
        self.geometry(c.MAIN_WINDOW_SIZE)
        self.minsize(820, 480)
        style.apply_style(self)
        style.apply_icon(self)

        self._build_menu()
        self._build_ui()
        self._refresh_table()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------
    # Menu bar
    # ------------------------------------------------------------------
    def _build_menu(self) -> None:
        menubar = tk.Menu(self)

        options_menu = tk.Menu(menubar, tearoff=0)
        options_menu.add_command(label="Change Master Password", command=self._open_change_password)
        options_menu.add_separator()
        options_menu.add_command(label="Backup Database", command=self._backup_database)
        options_menu.add_command(label="Restore Database", command=self._restore_database)
        options_menu.add_separator()
        options_menu.add_command(label="Wipe Vault", command=self._wipe_vault)
        options_menu.add_separator()
        options_menu.add_command(label="Lock Vault", command=self._lock_vault)

        menubar.add_cascade(label="Options", menu=options_menu)
        self.configure(menu=menubar)

    # ------------------------------------------------------------------
    # UI layout
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        root_frame = ttk.Frame(self, padding=16)
        root_frame.pack(fill="both", expand=True)

        # --- Search bar --------------------------------------------------
        search_row = ttk.Frame(root_frame)
        search_row.pack(fill="x")

        ttk.Button(search_row, text="\U0001F50D Search", style="Toolbar.TButton", command=self._on_search).pack(
            side="left"
        )
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_row, textvariable=self.search_var)
        search_entry.pack(side="left", fill="x", expand=True, padx=(8, 8))
        search_entry.bind("<Return>", lambda _e: self._on_search())
        ttk.Button(search_row, text="Clear", style="Toolbar.TButton", command=self._on_clear_search).pack(
            side="left"
        )

        # --- Toolbar -------------------------------------------------------
        toolbar = ttk.Frame(root_frame)
        toolbar.pack(fill="x", pady=(12, 8))

        ttk.Button(toolbar, text="+ Add New Entry", style="Accent.TButton", command=self._open_add_entry).pack(
            side="left"
        )
        ttk.Button(
            toolbar, text="Delete Existing Entry", style="Toolbar.TButton", command=self._open_delete_entry
        ).pack(side="left", padx=(8, 0))
        ttk.Button(
            toolbar, text="Edit Existing Entry", style="Toolbar.TButton", command=self._open_edit_entry
        ).pack(side="left", padx=(8, 0))

        ttk.Button(
            toolbar, text="\U0001F441 View Password", style="Toolbar.TButton", command=self._view_selected_password
        ).pack(side="right")
        ttk.Button(
            toolbar, text="Hide Password", style="Toolbar.TButton", command=self._hide_revealed_password
        ).pack(side="right", padx=(0, 8))

        # --- Table -----------------------------------------------------------
        table_frame = ttk.Frame(root_frame)
        table_frame.pack(fill="both", expand=True)

        columns = ("id", "website", "email", "password")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")

        # Heading anchor must match the column's data anchor, or the header
        # text (centered by default) visually drifts from the left-aligned
        # cell contents below it. ID is centered end-to-end; the rest are
        # left-aligned end-to-end.
        self.tree.heading("id", text="ID", anchor="center")
        self.tree.heading("website", text="Website", anchor="w")
        self.tree.heading("email", text="E-Mail", anchor="w")
        self.tree.heading("password", text="Password", anchor="w")

        self.tree.column("id", width=50, minwidth=50, anchor="center", stretch=False)
        self.tree.column("website", width=230, minwidth=160, anchor="w", stretch=True)
        self.tree.column("email", width=230, minwidth=160, anchor="w", stretch=True)
        self.tree.column("password", width=230, minwidth=160, anchor="w", stretch=True)

        # A Main Account's website is tinted to stand out slightly, in
        # addition to its "★ " prefix.
        self.tree.tag_configure("main_account_row", foreground=c.ACCENT_HOVER)

        # Scrolling has to reposition the overlays (their pixel coordinates
        # are only valid for the current scroll offset), so the scrollbar
        # is wired through a small wrapper instead of straight to yview.
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self._on_scrollbar_move)
        self.tree.configure(yscrollcommand=self._make_yscroll_hook(vsb))
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self.tree.bind("<<TreeviewSelect>>", self._on_row_selected)
        self.tree.bind("<Double-1>", self._on_row_double_click)
        self.tree.bind("<Button-3>", self._on_right_click)  # right-click context menu
        self.tree.bind("<Configure>", lambda _e: self._reposition_overlays())
        self.tree.bind("<MouseWheel>", lambda _e: self.after_idle(self._reposition_overlays))  # Windows/macOS
        self.tree.bind("<Button-4>", lambda _e: self.after_idle(self._reposition_overlays))     # Linux scroll up
        self.tree.bind("<Button-5>", lambda _e: self.after_idle(self._reposition_overlays))     # Linux scroll down

        self._build_context_menu()
        self._build_cell_overlays()

        self.status_label = ttk.Label(root_frame, text="", style="Secondary.TLabel")
        self.status_label.pack(anchor="w", pady=(8, 0))
        ttk.Label(
            root_frame,
            text="Tip: select a row, then click into its E-mail or (viewed) Password cell to drag-select "
                 "and copy the text - or right-click a row to copy directly. \u2605 marks a Main Account.",
            style="Secondary.TLabel",
        ).pack(anchor="w")

    def _build_cell_overlays(self) -> None:
        """
        Creates the two reusable overlay Entry widgets (email, password),
        parented to the Treeview itself so they visually sit on top of it.
        They start hidden (place_forget) until a row is selected / a
        password is revealed. The website column's overlays (one per
        linked entry, showing the bold Main Account name) are built
        per-row instead, in _refresh_table().
        """
        self.email_overlay_var = tk.StringVar()
        self.email_overlay = ttk.Entry(
            self.tree, textvariable=self.email_overlay_var, state="readonly", style="CellOverlay.TEntry"
        )

        self.password_overlay_var = tk.StringVar()
        self.password_overlay = ttk.Entry(
            self.tree, textvariable=self.password_overlay_var, state="readonly", style="CellOverlay.TEntry"
        )

    # ------------------------------------------------------------------
    # Scrolling helpers (keep overlays lined up with their cells)
    # ------------------------------------------------------------------
    def _on_scrollbar_move(self, *args) -> None:
        self.tree.yview(*args)
        self._reposition_overlays()

    def _make_yscroll_hook(self, scrollbar: ttk.Scrollbar):
        def _hook(*args):
            scrollbar.set(*args)
            self._reposition_overlays()
        return _hook

    # ------------------------------------------------------------------
    # Data loading / table population
    # ------------------------------------------------------------------
    def _refresh_table(self, query: Optional[str] = None) -> None:
        self._revealed_entry_id = None
        self.email_overlay.place_forget()
        self.password_overlay.place_forget()
        for overlay in self._linked_overlays.values():
            overlay.destroy()
        self._linked_overlays.clear()
        for row in self.tree.get_children():
            self.tree.delete(row)

        self._main_account_websites = {m["id"]: m["website"] for m in self.db.get_main_accounts()}

        entries = self.db.search_entries(query) if query else self.db.get_all_entries()
        for e in entries:
            label = e["email"] if e["email"] else e["username"]
            tags = ("main_account_row",) if e["is_main"] else ()
            self.tree.insert(
                "", "end", iid=str(e["id"]), tags=tags,
                values=(e["id"], self._website_cell_text(e), label, PASSWORD_MASK),
            )

            main_website = self._linked_main_website(e)
            if main_website is not None:
                self._linked_overlays[e["id"]] = self._create_linked_overlay(
                    e["id"], e["website"], main_website
                )

        count = len(entries)
        self.status_label.configure(text=f"{count} entr{'y' if count == 1 else 'ies'}")
        self._reposition_overlays()

    def _linked_main_website(self, entry: dict) -> Optional[str]:
        if entry["is_main"] or not entry["linked_main_id"]:
            return None
        return self._main_account_websites.get(entry["linked_main_id"])

    def _website_cell_text(self, entry: dict) -> str:
        """
        The real (plain-text) Website column value. For a linked entry
        this is also the fallback shown if its bold overlay isn't
        positioned yet/ever (e.g. it's momentarily scrolled out of view).
        """
        if entry["is_main"]:
            return f"{MAIN_ACCOUNT_PREFIX}{entry['website']}"
        main_website = self._linked_main_website(entry)
        if main_website:
            return f'{entry["website"]} \u2014 {main_website} linked'
        return entry["website"]

    def _create_linked_overlay(self, entry_id: int, entry_website: str, main_website: str) -> tk.Frame:
        """Builds the "<website> — <Main Account> linked" composite label, main-account name in bold."""
        normal_font = (c.FONT_FAMILY, 10)
        bold_font = (c.FONT_FAMILY, 10, "bold")

        frame = tk.Frame(self.tree, bg=c.ENTRY_BG, highlightthickness=0, bd=0)
        parts = [
            tk.Label(frame, text=f"{entry_website} \u2014 ", font=normal_font, bg=c.ENTRY_BG,
                      fg=c.TEXT_PRIMARY, anchor="w", padx=0, pady=0, bd=0),
            tk.Label(frame, text=main_website, font=bold_font, bg=c.ENTRY_BG,
                      fg=c.TEXT_PRIMARY, anchor="w", padx=0, pady=0, bd=0),
            tk.Label(frame, text=" linked", font=normal_font, bg=c.ENTRY_BG,
                      fg=c.TEXT_PRIMARY, anchor="w", padx=0, pady=0, bd=0),
        ]
        parts[0].pack(side="left", padx=(4, 0))
        parts[1].pack(side="left")
        parts[2].pack(side="left")

        # Clicks on the overlay should behave like clicking the row underneath it.
        for widget in (frame, *parts):
            widget.bind("<Button-1>", lambda _e, iid=entry_id: self._select_row(iid))
            widget.bind("<Button-3>", lambda e, iid=entry_id: self._show_context_menu_for(iid, e))

        return frame

    def _select_row(self, entry_id: int) -> None:
        iid = str(entry_id)
        if self.tree.exists(iid):
            self.tree.selection_set(iid)
            self.tree.focus(iid)

    def _show_context_menu_for(self, entry_id: int, event) -> None:
        self._select_row(entry_id)
        self.context_menu.tk_popup(event.x_root, event.y_root)

    def _selected_entry_id(self) -> Optional[int]:
        selection = self.tree.selection()
        if not selection:
            return None
        return int(selection[0])

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------
    def _on_search(self) -> None:
        query = self.search_var.get().strip()
        self._refresh_table(query if query else None)

    def _on_clear_search(self) -> None:
        self.search_var.set("")
        self._refresh_table()

    # ------------------------------------------------------------------
    # Add / Edit / Delete
    # ------------------------------------------------------------------
    def _open_add_entry(self) -> None:
        EntryFormDialog(self, self.db, self.session, on_saved=self._refresh_table)

    def _open_edit_entry(self) -> None:
        entry_id = self._selected_entry_id()
        if entry_id is None:
            messagebox.showinfo(c.APP_NAME, "Please select an entry in the table first.")
            return

        # The edit form pre-fills the real password, so it must be gated
        # behind the master password just like viewing one.
        if not ask_master_password(self, self.db, "Enter your master password to edit this entry."):
            return

        entry = self.db.get_entry(entry_id)
        EntryFormDialog(self, self.db, self.session, on_saved=self._refresh_table, existing_entry=entry)

    def _open_delete_entry(self) -> None:
        DeleteEntryDialog(self, self.db, on_deleted=self._refresh_table)

    # ------------------------------------------------------------------
    # Row selection -> overlay placement
    # ------------------------------------------------------------------
    def _on_row_selected(self, _event=None) -> None:
        entry_id = self._selected_entry_id()

        if entry_id is None:
            self.email_overlay.place_forget()
        else:
            entry = self.db.get_entry(entry_id)
            self.email_overlay_var.set(entry["email"] if entry else "")
            self._position_overlay(self.email_overlay, entry_id, "email")

        # Selecting a different row means a different secret - stop
        # showing whatever password was previously revealed.
        if entry_id != self._revealed_entry_id:
            self._revealed_entry_id = None
            self.password_overlay.place_forget()

    def _position_overlay(self, overlay: tk.Widget, entry_id: int, column: str) -> bool:
        """
        Places `overlay` exactly on top of (entry_id, column)'s cell.
        Returns False (and hides the overlay) if the row no longer exists
        or has scrolled out of view.
        """
        iid = str(entry_id)
        if not self.tree.exists(iid):
            overlay.place_forget()
            return False
        bbox = self.tree.bbox(iid, column)
        if not bbox:
            overlay.place_forget()
            return False
        x, y, w, h = bbox
        overlay.place(x=x, y=y, width=w, height=h)
        return True

    def _reposition_overlays(self) -> None:
        entry_id = self._selected_entry_id()
        if entry_id is not None:
            self._position_overlay(self.email_overlay, entry_id, "email")
        else:
            self.email_overlay.place_forget()

        if self._revealed_entry_id is not None:
            self._position_overlay(self.password_overlay, self._revealed_entry_id, "password")

        for linked_id, overlay in self._linked_overlays.items():
            self._position_overlay(overlay, linked_id, "website")

    # ------------------------------------------------------------------
    # Reveal / hide password
    # ------------------------------------------------------------------
    def _on_row_double_click(self, event) -> None:
        row_id = self.tree.identify_row(event.y)
        if not row_id:
            return
        self.tree.selection_set(row_id)
        column = self.tree.identify_column(event.x)
        if column == "#4":  # the "password" column
            self._view_selected_password()

    def _view_selected_password(self) -> None:
        entry_id = self._selected_entry_id()
        if entry_id is None:
            messagebox.showinfo(c.APP_NAME, "Please select an entry in the table first.")
            return
        self._reveal_password(entry_id)

    def _reveal_password(self, entry_id: int) -> Optional[str]:
        """
        Decrypts entry_id's password and shows it via the in-table overlay.
        Re-prompts for the master password unless it's already showing.
        It stays visible - through clicking other controls, scrolling,
        resizing, etc. - until Hide Password is clicked, a different row
        is selected, or the table is rebuilt (search/add/edit/delete/lock).
        Returns None if the user cancels the prompt.
        """
        if self._revealed_entry_id == entry_id:
            return self.password_overlay_var.get()

        if not ask_master_password(self, self.db, "Enter your master password to view this password."):
            return None

        try:
            plain = self.db.decrypt_entry_password(entry_id, self.session.key)
        except Exception:
            messagebox.showerror(c.APP_NAME, "Could not decrypt this password.")
            return None

        self._revealed_entry_id = entry_id
        self.password_overlay_var.set(plain)
        self._position_overlay(self.password_overlay, entry_id, "password")
        return plain

    def _hide_revealed_password(self) -> None:
        self._revealed_entry_id = None
        self.password_overlay_var.set("")
        self.password_overlay.place_forget()

    # ------------------------------------------------------------------
    # Copy to clipboard (right-click menu)
    # ------------------------------------------------------------------
    def _copy_to_clipboard(self, text: str, label: str) -> None:
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()  # flushes the clipboard so it survives even if the app loses focus
        self.status_label.configure(text=f"{label} copied to clipboard.")

    def _copy_selected_email(self) -> None:
        entry_id = self._selected_entry_id()
        if entry_id is None:
            return
        entry = self.db.get_entry(entry_id)
        if entry and entry["email"]:
            self._copy_to_clipboard(entry["email"], "E-mail")

    def _copy_selected_username(self) -> None:
        entry_id = self._selected_entry_id()
        if entry_id is None:
            return
        entry = self.db.get_entry(entry_id)
        if entry and entry["username"]:
            self._copy_to_clipboard(entry["username"], "Username")

    def _copy_selected_website(self) -> None:
        entry_id = self._selected_entry_id()
        if entry_id is None:
            return
        entry = self.db.get_entry(entry_id)
        if entry and entry["website"]:
            self._copy_to_clipboard(entry["website"], "Website")

    def _copy_selected_password(self) -> None:
        entry_id = self._selected_entry_id()
        if entry_id is None:
            messagebox.showinfo(c.APP_NAME, "Please select an entry in the table first.")
            return
        plain = self._reveal_password(entry_id)  # prompts for master password if not already revealed
        if plain is not None:
            self._copy_to_clipboard(plain, "Password")

    # ------------------------------------------------------------------
    # Right-click context menu
    # ------------------------------------------------------------------
    def _build_context_menu(self) -> None:
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Copy Website", command=self._copy_selected_website)
        self.context_menu.add_command(label="Copy Username", command=self._copy_selected_username)
        self.context_menu.add_command(label="Copy E-mail", command=self._copy_selected_email)
        self.context_menu.add_command(label="Copy Password", command=self._copy_selected_password)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="View Password", command=self._view_selected_password)
        self.context_menu.add_command(label="Hide Password", command=self._hide_revealed_password)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Edit Entry", command=self._open_edit_entry)
        self.context_menu.add_command(label="Delete Entry", command=self._open_delete_entry)

    def _on_right_click(self, event) -> None:
        row_id = self.tree.identify_row(event.y)
        if not row_id:
            return
        self.tree.selection_set(row_id)
        self.context_menu.tk_popup(event.x_root, event.y_root)

    # ------------------------------------------------------------------
    # Options menu actions
    # ------------------------------------------------------------------
    def _open_change_password(self) -> None:
        ChangeMasterPasswordDialog(self, self.db, on_changed=lambda: None)

    def _backup_database(self) -> None:
        default_name = f"password_vault_backup_{datetime.now():%Y%m%d_%H%M%S}.db"
        destination = filedialog.asksaveasfilename(
            parent=self,
            title="Backup Database",
            defaultextension=".db",
            initialfile=default_name,
            filetypes=[("Password Vault Backup", "*.db"), ("All files", "*.*")],
        )
        if not destination:
            return
        try:
            self.db.backup_to(destination)
        except OSError as exc:
            messagebox.showerror(c.APP_NAME, f"Could not save the backup:\n{exc}")
            return
        messagebox.showinfo(c.APP_NAME, f"Backup saved to:\n{destination}")

    def _restore_database(self) -> None:
        source = filedialog.askopenfilename(
            parent=self,
            title="Restore Database",
            filetypes=[("Password Vault Backup", "*.db"), ("All files", "*.*")],
        )
        if not source:
            return

        if not self.db.is_valid_vault_file(source):
            messagebox.showerror(c.APP_NAME, "That file doesn't look like a valid Password Vault backup.")
            return

        confirmed = messagebox.askyesno(
            "Restore Database",
            "This will REPLACE your current vault - all entries AND the master password - "
            "with the selected backup. This cannot be undone.\n\nContinue?",
            icon="warning",
            parent=self,
        )
        if not confirmed:
            return

        if not ask_master_password(
            self, self.db, "Enter your CURRENT master password to authorize this restore."
        ):
            return

        try:
            self.db.restore_from(source)
        except ValueError as exc:
            messagebox.showerror(c.APP_NAME, str(exc))
            return

        messagebox.showinfo(
            c.APP_NAME,
            "Vault restored. Please unlock with the restored backup's master password.",
        )
        # The restored file may use a different master password than the one
        # just used to authorize this - lock and send the user back to the
        # unlock screen rather than assuming the current session is still valid.
        self.destroy()
        self.on_lock()

    def _wipe_vault(self) -> None:
        # Two gates for the most destructive action in the app: first an
        # explicit, two-part acknowledgment of *what* is being deleted
        # (entries, and separately the master password itself), then the
        # current master password to confirm *who* is asking for it -
        # the same "prove it's really you" pattern used before deleting
        # a single entry or restoring a backup.
        if not confirm_wipe_vault_warning(self):
            return

        if not ask_master_password(
            self, self.db, "Enter your master password to confirm wiping the vault."
        ):
            return

        self.db.wipe_vault()
        messagebox.showinfo(
            c.APP_NAME,
            "Vault wiped. You'll be taken back to set up a new master password.",
        )
        self.destroy()
        self.on_lock()

    def _lock_vault(self) -> None:
        self._hide_revealed_password()
        self.destroy()
        self.on_lock()

    def _on_close(self) -> None:
        # Closing the main window closes the whole application.
        self.master.destroy()
