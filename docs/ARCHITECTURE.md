# Architecture and energy policy

`gui.py` is Qt Widgets; no web engine or local web server is used. It starts one worker via QProcess, reads a bounded activity stream while work is active, and stops its 1-second activity timer after completion. There is no idle UI refresh loop. Closing an idle window exits the process. A running GUI job must finish before the window closes; it can be minimized.

The OS scheduler independently starts `--sync`: launchd StartInterval on macOS, current-user Task Scheduler on Windows, and a systemd user timer on Linux. No administrator/root service is installed. The one-shot worker loads source policy, acquires a cross-process lock, skips sources that are not due, and exits. No heartbeat, WebSocket, polling browser or resident tray process is required between jobs. Scheduler invocation itself has startup cost. No claim of zero energy use is made.

Policy: 6 hours by default, configurable 1/3/6/12/24 hours; due times calculated from run start (systemd adds up to 5 minutes of native timer jitter), eight concurrent PFERD tasks with no artificial task delay, sequential course roots, 90-minute job deadline; 2^n persisted backoff up to 48 hours; login failures halt automatic attempts until a manual sign-in/run. The task limit is not a hard HTTP-request limit: a task may make multiple requests. Battery deferral is enabled by default and based on OS-reported power state. An unavailable battery sensor is treated as a desktop. Sleeping/offline computers cannot download continuously; the next native trigger rechecks due sources. systemd OnUnitActiveSec is monotonic; this preview does not promise an exact wall-clock catch-up after power-off. macOS/Windows timers similarly follow OS login and power policies.

An installation profile has an opaque UUID, HTTPS root, login mode, username, client ID, download destination, media flag and selected course URLs. Passwords are not in profile JSON. Profiles use private caches/manifests under platformdirs' user application-data root. Distinct destinations may not overlap. Settings and manifests are atomically written and schema versioned. The first release supports schema 1 only and rejects unknown versions.

PFERD is a pinned dependency. The adapter supports dynamic local login form field names, explicitly guarded Shibboleth POST hosts, imported browser sessions, dashboard membership discovery, selected course/folder URLs, safe single-object cache keys, PDF/ZIP signature checks and status-aware HTTP errors. Navigation controls for showing/hiding sessions are removed before parsing to avoid the previously observed duplicate-folder loop. Courses linked from a course are not followed as new memberships; joined groups come from the dashboard.

Incremental parsing: a private, source-bound page index retains parsed navigation plans rather than cached freshness.
Each run fetches known content pages again, with at most 64 queued page tasks, overlapping membership discovery and traversal. A shared per-host HTTP budget allows eight active requests across pages, streams, authentication and redirects; responses retain their slot until EOF or close.

The first dashboard fetch establishes an authenticated session before speculative page tasks start. This ordering
prevents expired-session redirects from outstanding prefetched pages from interfering with a newly accepted login.
After bootstrap, known-page reads still overlap membership pagination and traversal; current navigation determines
which pages count toward the result. Authentication is not bypassed and no cached page substitutes for a fresh read.
Authenticated responses are compared using
content, navigation, download-target and description fingerprints; random UI IDs, hidden form tokens and assignment
countdowns do not invalidate parsing. Changed pages are parsed again with lxml, newly discovered pages are fetched,
and required failed reads retain PFERD's error/retry behavior. Detached pages may fail speculative reads without failing
the current reachable graph. Confirmed same-object redirect routes avoid routing round trips and fall back to the
original permalink on failure. The cache is saved only after a successful crawl and profile changes invalidate it.
Empty sessions can be checked through a fresh parent material summary only after their detail page was verified empty
and a positive sibling count proves the supported minimal-list convention. Missing or positive counts in unsupported
layouts fall back to ordinary traversal. Their discovered paths remain in the report. Plans for file downloads still
go through the existing mtime/cache decisions and publication checks, including missing-file restoration and conflicts.

Raw files stage into application data before publication. PFERD's temporary-file semantics keep interrupted downloads from replacing valid cached files. The archive verifies copies and uses exclusive publication for unmanaged destinations. Per-object manifests and a publication-intent journal make retries idempotent. The archive compares stat metadata before rehashing unchanged files to reduce disk/CPU activity, but verifies current content before replacing an existing managed version. Manifests are local state, not the only copy of downloaded data. Prior versions live in the destination and remain ordinary recoverable files. No automatic pruning/deletion is implemented.

The GUI displays a manifest file list and source results, including unavailable content and skipped-type counters. Generic failures are redacted. A generated HTML description or link is preserved separately under `Course info`. Cloud upload is outside this application; opening a file in a local Drive folder does not establish remote upload or a restore proof.

Presentation is separated from synchronization policy: `presentation.py` derives user-facing status and a report from
persisted facts; `library_widgets.py` contains Qt delegates and status/empty-state widgets. The manifest remains schema 1:
optional `changed_at` and `change` are written only on a real added/updated/conflict publication and are retained on no-op
runs. Old files acquire no invented history. The library defaults to material files, with explicit recent, course-information
and all-file views; stable generated identities classify course information. Native file opening uses validated manifest
paths and QDesktopServices. Unknown progress stays indeterminate. There is no new idle timer or network layer.


Active-run control: the worker writes a run UUID and process birth time to application state. Commands must match that UUID; stale commands cannot control a new run. An active worker checks commands every 250 ms; no monitor runs between jobs. Pausing gates new page requests, streamed chunks and publication boundaries. An already pending HTTP request may finish or time out; it does not make a partial download a published file. Stop cancels awaited work and allows synchronous atomic publication to finish before cancellation. A filesystem watcher allows an open GUI to detect a scheduled worker, then its active-only progress timer follows that worker. Paused time does not consume the worker's active deadline. Stopping a batch retains the configured schedule.


Folder routing: optional profile rules select absolute user-chosen destination roots for `course/<id>`, `path/<course-id>/<subpath>` or `file/<stable-object-id>`. The most specific rule wins. Published entries retain destination root, original logical path and rule fingerprint. A changed rule copies into the newly selected root and retains prior copies, local annotations and a prior-location record. Unmanaged identical files are not adopted. Ownership intent includes the destination root so a failed publication in one root cannot claim another root. Manifest metadata lets the folder-assignment tree reconstruct courses, subfolders and files after a sync; older entries use their original course-ID path as a fallback.

Folder naming: optional `include_course_ids` defaults to false; `folder_names` stores course/path aliases separately from
stable logical identities. Existing owned directory trees are renamed through a persisted recovery journal before
publication. Manifest and publication-intent paths follow the rename; an existing target directory is never merged.
Native daily calendars: macOS StartCalendarInterval, Windows CalendarTrigger/ScheduleByDay, and systemd OnCalendar.
The fixed-time worker flag bypasses interval due times while retaining login-required, locking and battery gates.

Attempt evidence: status and the most recent 20 outcomes persist separately from the manifest. Each attempt carries
a hash of material-affecting source configuration (excluding cosmetic name and enabled flag), plus the actual course
roots when available. A failed/stopped attempt never inherits the preceding result. The last fully successful check is
retained only for matching scope. Course discovery restores the preceding sync status if it fails. Retained archive totals
are not treated as current crawl coverage or proof of physical/offline availability.

Settings are drafts until Save. Native scheduling and configuration are rolled back after failed updates; recovery errors
are surfaced explicitly. Profile changes hold the worker lock, validate destinations before touching credentials, stage
imported sessions privately and independently attempt to restore configuration, cookies and vault after failure.
No transaction can guarantee restoration if the underlying storage itself remains unavailable.

View state (selected source, source-specific material view and window size) has its own file, separate from policy.
Read-only tables release Tab for focus navigation. Datetime labels share a bounded minute-precision timezone cache;
there is no timer or background collection scan while idle. Filters share the single main search and reload choices
when the manifest changes. Their visible result count uses the same eligibility predicate as the table.

HTTP policy: aiohttp 3.14.5 middleware bounds active responses per hostname, while trace hooks count actually sent headers.
Persisted host cooldowns survive one-shot workers. GET/HEAD retries obey Retry-After; POST is never automatically replayed.
Three consecutive throttles open a per-run circuit. Host metrics and attempted/planned roots are retained in attempt evidence
even when enumeration fails before files exist. See [measurement and override policy](SYNC_PERFORMANCE.md).
