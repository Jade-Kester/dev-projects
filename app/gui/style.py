"""
style.py
---------
Centralised ttk theming. Keeping styling in one place means every
window (login, main, dialogs) looks consistent, and the whole app can
be re-skinned by editing app/constants.py + this file only.
"""

import tkinter as tk
from tkinter import ttk

from app import constants as c


def apply_icon(window: tk.Misc) -> None:
    """
    Sets the window/taskbar icon. Wrapped in a try/except because
    .iconbitmap() with a .ico file only works reliably on Windows -
    on other platforms (or if the asset is missing) we just skip it
    rather than crash the app over a cosmetic detail.
    """
    try:
        window.iconbitmap(c.ICON_PATH_ICO)
    except Exception:
        pass


def apply_style(root: tk.Misc) -> ttk.Style:
    style = ttk.Style(root)
    # 'clam' is the most reliably themeable base theme across platforms.
    style.theme_use("clam")

    root.configure(bg=c.WINDOW_BG)

    style.configure(
        "TFrame",
        background=c.WINDOW_BG,
    )
    style.configure(
        "Panel.TFrame",
        background=c.PANEL_BG,
    )
    style.configure(
        "TLabel",
        background=c.WINDOW_BG,
        foreground=c.TEXT_PRIMARY,
        font=(c.FONT_FAMILY, 10),
    )
    style.configure(
        "Secondary.TLabel",
        background=c.WINDOW_BG,
        foreground=c.TEXT_SECONDARY,
        font=(c.FONT_FAMILY, 9),
    )
    style.configure(
        "Heading.TLabel",
        background=c.WINDOW_BG,
        foreground=c.TEXT_PRIMARY,
        font=(c.FONT_FAMILY, 16, "bold"),
    )

    # Buttons -----------------------------------------------------------
    style.configure(
        "Accent.TButton",
        background=c.ACCENT,
        foreground="white",
        borderwidth=0,
        focusthickness=0,
        padding=(14, 8),
        font=(c.FONT_FAMILY, 10, "bold"),
    )
    style.map(
        "Accent.TButton",
        background=[("active", c.ACCENT_HOVER), ("disabled", "#3a3f4d")],
    )

    style.configure(
        "Toolbar.TButton",
        background=c.PANEL_BG,
        foreground=c.TEXT_PRIMARY,
        borderwidth=0,
        padding=(10, 6),
        font=(c.FONT_FAMILY, 9, "bold"),
    )
    style.map(
        "Toolbar.TButton",
        background=[("active", c.ENTRY_BG), ("disabled", c.PANEL_BG)],
        foreground=[("disabled", c.TEXT_SECONDARY)],
    )

    style.configure(
        "Danger.TButton",
        background=c.DANGER,
        foreground="white",
        borderwidth=0,
        padding=(14, 8),
        font=(c.FONT_FAMILY, 10, "bold"),
    )
    style.map("Danger.TButton", background=[("active", c.DANGER_HOVER)])

    # Entries -------------------------------------------------------------
    style.configure(
        "TEntry",
        fieldbackground=c.ENTRY_BG,
        foreground=c.TEXT_PRIMARY,
        insertcolor=c.TEXT_PRIMARY,
        borderwidth=1,
        padding=6,
    )

    # An overlay Entry placed exactly on top of a Treeview cell (see
    # main_window.py) so its text is selectable/copyable in place. It
    # always sits on the currently-selected row, so its colors match
    # that row's selection highlight for a seamless look.
    style.configure(
        "CellOverlay.TEntry",
        borderwidth=0,
        padding=(6, 0),
    )
    style.map(
        "CellOverlay.TEntry",
        fieldbackground=[("readonly", c.ACCENT_SELECTED), ("!readonly", c.ACCENT_SELECTED)],
        foreground=[("readonly", "white"), ("!readonly", "white")],
    )

    style.configure(
        "TRadiobutton",
        background=c.WINDOW_BG,
        foreground=c.TEXT_PRIMARY,
        font=(c.FONT_FAMILY, 10),
    )
    style.map("TRadiobutton", background=[("active", c.WINDOW_BG)])

    style.configure(
        "TCombobox",
        fieldbackground=c.ENTRY_BG,
        background=c.ENTRY_BG,
        foreground=c.TEXT_PRIMARY,
    )

    # Treeview (the accounts table) --------------------------------------
    style.configure(
        "Treeview",
        background=c.ENTRY_BG,
        fieldbackground=c.ENTRY_BG,
        foreground=c.TEXT_PRIMARY,
        borderwidth=0,
        rowheight=28,
        font=(c.FONT_FAMILY, 10),
    )
    style.configure(
        "Treeview.Heading",
        background=c.PANEL_BG,
        foreground=c.TEXT_PRIMARY,
        borderwidth=0,
        font=(c.FONT_FAMILY, 10, "bold"),
    )
    style.map(
        "Treeview",
        background=[("selected", c.ACCENT_SELECTED)],
        foreground=[("selected", "white")],
    )
    style.map("Treeview.Heading", background=[("active", c.PANEL_BG)])

    return style


def style_entry_widget(widget) -> None:
    """For plain tk widgets (not ttk) that need manual dark styling."""
    widget.configure(
        bg=c.ENTRY_BG,
        fg=c.TEXT_PRIMARY,
        insertbackground=c.TEXT_PRIMARY,
        relief="flat",
        highlightthickness=1,
        highlightbackground="#3a3c4d",
        highlightcolor=c.ACCENT,
        font=(c.FONT_FAMILY, 10),
    )
