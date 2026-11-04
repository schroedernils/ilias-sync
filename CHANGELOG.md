# Changelog

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
