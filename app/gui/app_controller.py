"""
app_controller.py
-------------------
Owns the single, hidden Tk root that the whole application's mainloop
runs on. Everything the user actually sees (the login screen, the main
vault window) is a Toplevel spawned and destroyed by this controller.

Using exactly one Tk root avoids the flakiness of running multiple
nested mainloops, which is a common source of bugs in Tkinter apps that
have a "login screen -> main screen" flow.

Window handoff order matters (Windows-specific quirk)
=======================================================
_swap_window() destroys the outgoing window BEFORE constructing the
incoming one, and explicitly lifts/focuses the new window afterward.
Building the new window first and destroying the old one second (the
previous approach) reliably caused the new window to appear minimized
on Windows: destroying a Toplevel that still holds input focus can hand
focus back to the OS instead of the sibling Toplevel already sitting
behind it, and the new window's initial map request gets treated as a
background one. Destroy-then-create-then-lift avoids that entirely.
"""

import tkinter as tk
from typing import Callable

from app.database import VaultDatabase
from app.gui import style
from app.gui.login_window import LoginWindow
from app.session import VaultSession


class VaultApp:
    def __init__(self, db: VaultDatabase):
        self.root = tk.Tk()
        self.root.withdraw()  # the root itself is never shown directly
        style.apply_icon(self.root)  # sets the default icon inherited by every Toplevel

        self.db = db
        self.session = VaultSession(db)

        self._current_window: tk.Toplevel | None = None
        self.show_login()

    # ------------------------------------------------------------------
    def show_login(self) -> None:
        """Shows the master-password screen (create or unlock)."""
        self.session.lock()
        self._swap_window(lambda: LoginWindow(self.root, self.db, self.session, on_unlocked=self.show_main))

    def show_main(self) -> None:
        """Shows the main vault window. Requires an unlocked session."""
        # Local import avoids a circular import (main_window -> app_controller
        # isn't needed, but this keeps import order obviously one-directional).
        from app.gui.main_window import MainWindow

        self._swap_window(lambda: MainWindow(self.root, self.db, self.session, on_lock=self.show_login))

    def _swap_window(self, build_window: Callable[[], tk.Toplevel]) -> None:
        if self._current_window is not None and self._current_window.winfo_exists():
            self._current_window.destroy()

        new_window = build_window()
        self._current_window = new_window

        # Belt-and-braces: make sure the new window actually ends up
        # visible, on top, and focused rather than minimized/behind
        # other windows - see the module docstring above.
        new_window.deiconify()
        new_window.lift()
        new_window.focus_force()
        new_window.after(50, lambda: (new_window.lift(), new_window.focus_force()))

    def run(self) -> None:
        self.root.mainloop()
