# Changelog

## Unreleased

Bind preview packages and attempt history to a source build identity. Preserve attempted/planned course roots and failed-subtree evidence even before files are listed. Add a shared per-host HTTP budget across pages, streamed downloads, authentication and redirects, persisted Retry-After and bounded safe-method retries; keep POSTs non-replayed. Record actual sent-request counts and verify lower-concurrency coverage with a local HTTPS server.

Distinguish settings-file access/write failures from native scheduler failures and retain unsaved input for retry.

Make editing distinct from first-time setup; preserve manual course targets. Explain effective inherited folder paths,
independent resets and safe rename/copy consequences. Add editable daily times, transactional schedule/profile recovery,
separate topic-based help, scoped attempt history and structured known-cause reports. Unify search and inline filters,
refresh filter choices after sync and retain source-specific views. Improve compact/enlarged-text layouts, keyboard
focus and input contrast. Reuse minute-level date formatting for large file collections without changing crawl policy.
Add a version-gated Cocoa ownership compatibility layer for a Qt accessibility crash when reading selected table/tree
elements on macOS. Preserve native accessibility rather than disabling it; include source and a native regression test.

Rework the desktop around synchronization health and readable course materials. A dedicated status panel distinguishes
successful checks, unavailable downloads, preserved local edits and failed synchronization, with sign-in or retry recovery.
Add inline material search, filename-first rows with folder context, direct opening, recent-change ordering and a separate
course-information view. Store real publication change times without inventing history for older files. A readable sync
report explains excluded content separately from failures; technical activity is disclosed on demand. Keep the existing
worker, file protection, source configuration and native schedules compatible.

Hide technical course/group IDs in folder names by default, with an opt-in and editable course/subfolder names in folder
mapping. Existing owned folders are renamed with a recovery journal; annotations and local contents stay in place.
Move folder actions beside course selection. Add file-name/type/course/size filters and numeric size/name sorting.
Add daily fixed-time schedules alongside interval schedules, using native calendar triggers on all supported platforms.
Pipeline known page checks with membership discovery and traversal, with a measured bound of 64 concurrent metadata reads.

Keep the current synchronization step visible when filesystem notifications refresh the window. Show course counts,
folders, file checks, downloads and publication stages. Persist progress for windows observing scheduled runs and restore
the current step after pause/resume.

Use eight bounded PFERD tasks without the previous one-second delay after every task. Process course roots sequentially
to preserve course ownership and routing while overlapping folder checks and downloads within each course.

Add a source-bound incremental parsing index. Revalidate known content pages with bounded parallel reads, reuse
unchanged navigation plans, collapse duplicate reads, and reuse confirmed same-object routes. Supported session material
summaries cover previously verified empty sessions; new materials trigger normal detail traversal. Use lxml for page
parsing and batch persisted progress updates. Existing file integrity, versioning and conflict behavior remains in place.

## 0.1.0a2 — 2026-10-22

Preserve the main workspace layout; replace setup with three focused steps and group settings by appearance and synchronization. Complete system-following light/dark palettes, optional overrides, live scheme changes, wide fields and readable scroll surfaces. Active runs expose accessible pause/resume symbols and a red stop control, including OS-scheduled runs observed while the app is open. Cancellation occurs at safe async boundaries and does not interrupt an atomic file publication. Paused time is excluded from the worker deadline. Course selection shows counts, search and an explicit scrollbar; read-only membership overview pagination is followed. Folder mapping supports course, subfolder and file destinations with most-specific precedence, keeping prior copies after reassignment. Stronger headings and a compact empty workspace. Lucide action icons replace custom drawings; source editing appears on sidebar hover and in its right-click menu, also via F2. Settings uses a gear; folder actions sit beside the destination. The owner-supplied icon now replaces the placeholder in the UI, native bundles and Windows executable; Linux includes an optional desktop launcher. Settings gains a bilingual Info tab with usage, platform and privacy boundaries and reference links. Schema 1 gains optional profile rules and manifest metadata; existing profiles remain readable.

## 0.1.0a1 — 2026-10-22

First private preview: configurable ILIAS sources, Qt desktop UI, standard login and guarded SSO/session import, course selection/discovery, incremental downloads, archive/version/conflict protection, battery-aware native scheduling, headless one-shot jobs, tests and four native build targets across three operating systems. Schema 1. No migration from the earlier personal Google Drive script; that installation remains separate.
