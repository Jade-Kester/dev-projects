# Changelog

All notable changes to this project are documented here. Versions follow
[Semantic Versioning](https://semver.org/) — while the major version stays
at `0`, the project should be considered pre-1.0 / actively evolving.
This is the first upload of the project to GitHub; the versions below
(`v0.1.0` → `v0.7.2`) are its full development history to date.

## [0.7.2]

### Fixed
- **Wipe Vault didn't reset entry IDs.** SQLite tracks each
  `AUTOINCREMENT` table's last-used ID separately, in a hidden
  `sqlite_sequence` table - deleting every row from `entries` alone
  doesn't touch it, so the next entry created after a wipe continued
  numbering from wherever the old vault had left off instead of
  starting back at 1. `wipe_vault()` now also resets that counter, so a
  freshly wiped vault behaves identically to a genuinely fresh install.

## [0.7.1]

### Fixed
- **Crash on opening Wipe Vault**: `ttk.Checkbutton` doesn't support a
  `-wraplength` option (unlike `ttk.Label` or classic `tk.Checkbutton`) -
  passing one raised a TclError the moment the dialog tried to build.
  The offending checkbox label is now short enough to read on one line
  instead.
- Wipe Vault's warning text incorrectly framed a forgotten master
  password as a reason to use it. Wipe Vault lives in the Options menu,
  which is only reachable once the vault is already unlocked, so it
  can't actually serve as a recovery path for someone locked out - the
  wording now points at cases it genuinely helps with instead (starting
  over, or handing off/uninstalling the app).
- After entering the master password on the unlock screen, the newly
  opened main window would sometimes appear minimized on Windows.
  Root cause: the app was constructing the new window *before*
  destroying the old one, and destroying a Toplevel that still holds
  input focus can leave the new sibling window's initial map request
  treated as a background one. The window hand-off is now
  destroy-old -> build-new -> explicitly lift and focus the new one.

## [0.7.0]

### Added
- **Wipe Vault**, in the Options menu: permanently deletes every entry
  AND the master password itself, returning the app to its just-installed
  state. Gated behind two separate acknowledgment checkboxes (one for the
  data loss, one specifically for the master password being reset) plus
  a re-entry of the current master password - the heaviest confirmation
  of any action in the app, matching how destructive it is.
- README now documents exactly where `vault.db` lives on each OS
  (`%APPDATA%\PasswordVault\vault.db` on Windows, and the macOS/Linux
  equivalents), and explains why the file alone - even backed up,
  copied, or leaked - is useless without the master password.

## [0.6.0]

### Added
- A final, explicit warning shown before a brand-new vault is created:
  Password Vault has no "Forgot Password" option, no server, and no
  backup key, so a forgotten master password means every saved entry
  becomes permanently unreadable. The warning requires ticking an
  acknowledgment checkbox before "Create Vault" is even clickable;
  declining sends the person back to reconsider their password instead
  of silently proceeding. A shorter version of the same warning is also
  shown inline on the account-creation screen itself, not just this
  final gate.

## [0.5.1]

### Fixed
- Website column was noticeably wider than E-Mail and Password, left over
  from when it also had to fit the now-removed Main Account column's
  text. Website, E-Mail, and Password are now equal width, and resize
  equally as the window is resized.

## [0.5.0]

### Added
- **Database Backup / Restore**, now implemented (previously stubbed).
  Backup copies the vault file as-is - it's already fully encrypted at
  rest, so the backup file is exactly as safe as the live one. Restore
  validates the selected file actually looks like a Password Vault
  database, requires typed confirmation and the *current* master
  password to authorize, then replaces the live vault and returns to
  the unlock screen (a restored backup may carry a different master
  password than the one just used to authorize the restore).

### Changed
- **Editing a Main Account's e-mail/password now updates every account
  linked to it.** Previously a linked entry only ever matched its Main
  Account at the moment it was created; editing the Main Account
  afterward left linked entries with stale credentials. Website/username
  are intentionally not propagated - only the shared login is.
- **Main Account indicators moved into the Website column**, replacing
  the separate "Main Account" column:
  - A Main Account now shows a "★" (star) before its website name.
  - A linked entry now shows "<website> — <Main Account> linked"
    directly in the Website column, with the Main Account's name in
    bold.

## [0.4.0]

### Changed
- Replaced the separate "Details" panel with **in-table selection**: the
  E-mail cell of the selected row, and the Password cell once revealed,
  now overlay a real, read-only text field exactly on top of that
  Treeview cell. You can drag-select and Ctrl+C directly in the table -
  no separate panel required. The overlay tracks the cell through
  scrolling and window resizing, and disappears when it no longer
  applies (row deselected, table rebuilt, etc.).

## [0.3.0]

### Fixed
- **Security:** Editing an entry now re-prompts for the master password
  before the form opens. Previously the Edit dialog silently decrypted
  and pre-filled the stored password without any re-authentication.
- The Hide Password button now actually does something: a revealed
  password used to be masked again by almost any click (selecting a row,
  pressing another button), making the button redundant. A revealed
  password now stays visible until Hide Password is clicked, or the
  table is rebuilt by a search/add/edit/delete/lock.

### Added
- A "Details" panel below the table with read-only but *selectable*
  fields for the selected row's Website, Username, E-mail, and Password,
  so those values could be drag-selected and copied manually. (Replaced
  in v0.4.0 by selection directly in the table.)
- A **Main Account** column in the table: Main Accounts are marked with
  a "★ Main Account" badge, and entries linked to one show
  "`<Website> — <Main Account> linked`".

## [0.2.0]

### Added
- Right-click context menu on the accounts table: copy website, username,
  e-mail, or password directly to the clipboard. Copying a password still
  requires the master password if it isn't already revealed.
- Double-click an e-mail cell to copy it instantly; double-click a password
  cell to reveal it.
- Custom cyan padlock application icon (`assets/icon.ico`), applied to the
  window/taskbar and baked into the PyInstaller build.
- GitHub-ready project polish: `LICENSE` (MIT), badges and a table of
  contents in `README.md`, and this changelog.

### Changed
- Recolored the entire UI from purple/violet to a cyan accent theme.
- Fixed table column header/data misalignment: the ID column was already
  centered correctly, but the Website, E-Mail, and Password headers were
  center-anchored while their data was left-anchored. All headers now match
  their column's data alignment, and columns resize proportionally with
  the window.

## [0.1.0] - Initial build

### Added
- Master password creation/confirmation on first run, and an unlock
  prompt on every subsequent launch.
- Options menu: change master password (re-encrypts the entire vault)
  and lock vault. Database backup/restore stubbed in for a future release.
- Search bar filtering by website, username, and/or e-mail.
- Add / Edit / Delete entries, including a Main Account system: `None`,
  `New Main Account`, or `Existing Main Account` (autofills and locks the
  e-mail/password fields from the selected Main Account).
- Table of entries (ID, Website, E-Mail, Password) with passwords hidden
  as dots by default; viewing one requires the master password, and it
  re-hides on selecting another row, searching, or relaunching the app.
- Salting and hashing (PBKDF2-HMAC-SHA256, 390,000 iterations) for the
  master password, and Fernet/AES encryption at rest for every stored
  password, using a key independently derived from the master password
  and never written to disk.
- PyInstaller build spec for a single-file Windows `.exe`.
