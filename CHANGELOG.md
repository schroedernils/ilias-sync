# Changelog

## 1.0.4 — 2026-11-06

- Fix clipped macOS popup menus by updating their rounded mask after final sizing and preserving Qt's screen-constrained position.
- Keep course IDs disabled by default; explain the option under Folder mapping.
- Use stable, readable numbers for same-named courses and readable `(ILIAS)` suffixes for necessary protection copies instead of hashes.
- Migrate untouched, app-owned legacy hash filenames safely at the next sync, with a journal for interrupted migrations. Existing originals, local edits and distinct object ownership remain protected.

## 1.0.3 — 2026-11-05

- Restore missing OS scheduling registrations automatically at app startup, using the saved interval, daily times or weekly plan unchanged.
- Reconnect automatic sync to the current executable after moving or reinstalling the app; leave intact timers and deliberately disabled automation alone.
- Allow saving unchanged schedule settings to repair a missing registration; retain settings and expose a direct recovery action if the system scheduler is unavailable.
- Check calendar preservation during native installer round-trips and exercise actual Windows task creation, removal and idempotent repair in CI.

## 1.0.2 — 2026-11-04

- Add a per-user Windows setup wizard with Start menu entry, optional desktop shortcut and registered uninstaller.
- Add an Ubuntu/Debian DEB package with desktop launcher, application icon and declared runtime dependencies.
- Verify installed executables, repeat installation and removal on native Windows/Linux CI runners; keep portable archives available.
- Use solid window, dialog and popup surfaces outside macOS to avoid transparency and mixed-background rendering on Windows/Linux.
- Place sync error descriptions directly beneath and aligned with the status heading, before timestamps and schedule details.
- Use the dark product screenshot as the fixed GitHub README preview.

## 1.0.1

- Fix macOS sidebar resizing by letting Qt own the expanded client area and preserving its native view hierarchy.
- Preserve the chosen sidebar width through sync completion, refresh, temporary window constraints and language changes.
- Add hidden Cocoa geometry and sync-result regressions; isolate CI test modules while verifying the full collection count.

## 1.0.0 — 2026-11-03

First regular desktop release for macOS (Apple Silicon and Intel), Windows x64 and Linux x64.

- Material library with university/course navigation, recent files, scoped search and date-first sorting.
- Unified synchronization controls, guided recovery, detailed reports and optional new-problem notifications.
- Seven-day schedules with editable times and copying to individual days or groups of days.
- Custom folder routing and names, local-edit protection and retained versions.
- Dark and soft light appearances, a consistent dark icon and concise contextual help.
- Fixes for sidebar resizing, transparent scrolling, help hover states and native macOS appearance changes.
- Native build checks, bundled dependency notices and verified SHA-256 release assets.

See [release notes](docs/releases/1.0.0.md) for installation, upgrade notes and compatibility limits.

## 0.1.0 Alpha 2 — 2026-10-22

Private preview with four native desktop packages, course/folder configuration and local file preservation.

## 0.1.0 Alpha 1 — 2026-10-22

Initial private preview.
