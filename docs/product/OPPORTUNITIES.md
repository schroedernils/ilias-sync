# Opportunities and implementation contracts

Updated 28 October 2026. Proposed priorities; implemented foundations are recorded separately in [REVIEW.md](REVIEW.md). Nils explicitly chose owner feedback plus agent reviews and synthetic scenarios. External student recruitment and diary studies below are optional future methods, not development gates.

## How priorities were chosen

Reliability and preservation are constraints, not competing feature scores. Then compare user frequency, consequence, evidence, feasibility and added effort. **High/medium/low are judgments**, not measured demand. Complexity is relative to the current Qt/PFERD/manifest architecture; no staffing, effort or delivery-date estimates have been made. Each opportunity must survive its validation test.

| ID | Outcome | Expected frequency / impact | Evidence confidence | Complexity / burden | Recommendation |
| --- | --- | --- | --- | --- | --- |
| O1 | Understand what was actually checked | Every run / high consequence | High for code gap; medium for user interpretation | Medium; mostly evidence model | P0 foundation |
| O2 | Know what can open without a connection | Daily or before travel / high | Medium; external survey plus local architectural gap | Medium–high; cloud residency complicates it | P1 bounded capability |
| O3 | Find changes since a deliberate review | Several times weekly / potentially high | Medium mechanism; low direct demand evidence | Medium; persistent event/checkpoint model | P1 prototype, then decide |
| O4 | Recover and distinguish personal/server copies | Infrequent / very high when needed | High preservation requirement; medium interaction evidence | Medium; archive already exists | P1 pilot readiness |
| O5 | Learn about meaningful changes without opening the app | Unknown / medium | Medium adjacent evidence; low app evidence | Medium; scheduler/OS/privacy burden | Later experiment |
| O6 | Retain a semester while stopping irrelevant checks | Semester transitions / medium | Low; inferred lifecycle job | Low–medium with explicit course pause | Later interview/prototype |
| O7 | Check efficiently within university and energy limits | Every automated run / high ecosystem consequence | High observed configuration; limits unmeasured | Medium; request-level policy | P0 before wider rollout |
| O8 | Re-find content with poorly remembered filenames | Unknown / potentially high | Medium adjacent research; low unmet-need evidence | High; extraction/index lifecycle | Defer pending failed tasks |

## O1 — Evidence scoped to the selected work

**Problem:** An earlier completed run can be mistaken for proof of the current selection's completeness. During this review the developer added `source_scope` to attempt records and a mismatch guard. Remaining acceptance includes legacy states without a signature, actual discovered scope and avoiding cosmetic invalidation. A historical check must remain historical evidence. Tracked in [#1](https://github.com/schroedernils/ilias-sync/issues/1); do not duplicate the active implementation.

**Smallest useful behavior:** Keep the current workspace. Explain latest attempt, last complete check applicable to the current selection, exceptions, and whether a new check is due after configuration changes. Prefer a short answer with progressive detail over four permanent status badges.

**Technical fit:** Source UUID, selected targets, relevant policy and destination/routing configuration already exist. Bind evidence to a normalized scope or equivalent revision. An automatically discovered course set can change between runs; record actual attempted roots as well as configured intent. Retained archive entries are not the denominator of current coverage. A failed listing cannot establish that nothing exists.

**Acceptance criteria:**

- Changing selected courses, account/server, destination or material-affecting options makes old completion inapplicable until a new adequate check; cosmetic changes do not. Show old evidence with its original scope when inspected.
- Preserve latest-attempt and last-complete facts independently through error, cancellation and restart. Do not attach a previous result to a new failed attempt.
- A complete check means selected, supported, reachable content at that time; exclusions, blocked items and unknown coverage are explicit. Never present a completeness percentage without an established denominator.
- Failed subtrees retain an exception even if no files were enumerated from them. Preserve a local copy whose server object becomes denied or disappears; absence after an incomplete crawl is not proof of deletion.
- Metadata-based download decisions are described honestly. Fresh page retrieval is not a byte-for-byte validation of every remote file.
- A cloud destination never receives an IliasSync cloud-upload-success claim.

**Privacy/coherence:** Local metadata only; no additional permissions. Store identifiers/URLs privately and expose safe routes only when requested. **Validation:** T2/T7/T9 in [VALIDATION.md](VALIDATION.md). If students still infer universal coverage, simplify the language before adding new indicators.

## O2 — Readiness for the files needed offline

**Problem:** The manifest records publication history; later deletion, missing volumes and cloud eviction can invalidate physical availability. A `.url` shortcut is not its destination's offline contents.

**Smallest useful behavior:** An explicit “check local files” operation for the selected course/files, with a timestamp and results: readable local material, missing/unreadable, link requiring a connection, or residency unverified. Do not promise a new “offline mode” with continuous disk polling.

**Technical fit:** Existing roots, paths, hashes and `prior_locations` are useful. A filesystem `exists()` or `is_file()` check is insufficient for cloud residency; reading may itself cause hydration. Start with tested ordinary local directories. Treat unsupported cloud providers conservatively; provider-specific pinning requires a separate bounded feasibility study.

**Acceptance criteria:**

- Explain the checked selection and time; later results do not imply continuous validity.
- Report missing, unreadable, external-link and unknown-residency cases without removing manifest entries or overwriting annotations.
- Disconnect networking and actually open representative files on each claimed destination/platform before calling the workflow verified.
- An unmounted target volume is explained as unavailable; do not silently create a substitute directory and claim success.
- Repair is explicit and safe, preserving local edits and older versions. “Check locally” does not contact ILIAS or quietly download cloud content.
- User cancellation remains responsive; large libraries do not cause ongoing idle scanning. Distinguish presence/readability checking from full hash integrity checking.

**Value/frequency:** Particularly useful before travel and class; prevalence is unverified. **Privacy:** Filenames stay local; no provider OAuth is required for the initial capability. **Validation:** T3/T4. Reject an implementation whose availability badge is merely `Path.exists()`.

## O3 — Changes since my last review

**Problem:** Current `recent` filtering includes all records with `changed_at`; it is a useful chronology, but not a bounded account of unseen changes. A no-change run after two changed runs must not erase the student's awareness of them.

**Prototype:** Reuse the current library: “Seit deinem Überblick” with course context, “neu” versus “aktualisiert”, an explicit “Bis hier überblickt” action and undo. Test it against an honest time-range filter before building a notification feed.

**Technical fit:** `identity`, content hash, `changed_at` and `change` already exist. A per-object latest timestamp alone loses multiple revisions. Use an ordered publication event/checkpoint model or equivalent durable snapshot semantics if the task needs history. Keep it local and bounded; acknowledgement metadata does not replace archived file versions.

**Acceptance criteria:**

- An initial import is a baseline, not hundreds of urgent updates. Older entries lacking change metadata stay unknown, not newly uploaded.
- Changed bytes for a stable object create a content-change event; an unchanged rerun, generated course HTML, routing copy or restored missing local copy does not masquerade as new teaching content.
- Different object IDs remain distinct even with identical names or hashes. Label a newly discovered object as such; do not infer a lecturer upload date from local discovery.
- Changes survive application restarts, background runs and course switches until explicitly acknowledged or filtered. Launching the app or opening a file does not mean “read”.
- Acknowledgement applies only through a captured event boundary. An update arriving during review stays visible; avoid wall-clock-only comparisons that lose equal-time events or clock changes.
- Offer undo and an all-materials route. Retention/compaction never silently erases unacknowledged events. Summarizing multiple updates must say that intermediate versions exist, rather than inventing semantic differences.
- A content hash establishes byte change, not pedagogical importance. Do not rank a correction as unimportant because it changes few bytes.

**Privacy/control:** No reading telemetry, scoring or guilt-inducing unread count. Course-level acknowledgement may remove effort but must be tested. **Validation:** T1/T6 through independent agent scenarios and Nils's normal use; an external diary is optional. Stop if acknowledgement costs outweigh avoided checking.

## O4 — Recovery students can actually perform

**Problem:** Version files and conflict copies already preserve data. Hash directories and conflict suffixes do not themselves establish that a student can identify and recover the right document.

**Bounded behavior:** Explain personal copy versus downloaded server copy; allow revealing version locations and restoring a chosen version as a separate copy. Start with one file's recovery, not a general backup manager.

**Acceptance criteria:** An annotated document survives a server replacement, retry and application restart; the student can identify both copies and open an older version without shell commands; recovery creates no destructive replacement; manifest plus files restore in an isolated profile is rehearsed; missing app metadata is a separate recovery scenario. Retention/storage growth is explained, with no automatic cleanup.

**Technical fit/complexity:** Medium; build on `Archive`, `Versions/` and publication intents. A user-facing history needs reliable provenance and readable dates, not just names. **Privacy:** Local operations only. **Validation:** T5; protect hashes/contents in deterministic fixtures. This is more valuable than a broad document editor.

## O5 — A quiet digest, only if the pilot needs one

**Problem hypothesis:** Some students may still manually open ILIAS just to check changes. An in-app view cannot remove that check when the app stays closed.

**Experiment:** Let pilot volunteers choose one summary time or no alerts. Summarize confirmed content changes by course, with a route to the existing changes view. Errors needing reauthentication can remain visible and produce one transition alert if enabled. No per-file alerts or notification for unchanged runs; suppress repeated identical failures.

**Acceptance criteria:** Opt-in, quiet controls, easy disable, no course/document names on a locked screen by default, deduplication across retries, baseline import suppressed, and no false urgency. The one-shot OS worker should remain sufficient; a permanent resident process needs independent justification. Evidence from smartphone batching is not a desktop scheduling specification. **Validation:** diary comparison of manual checks, unwanted interruptions and missed materials. Do not ship merely because notification APIs are available.

## O6 — Semester pause without reorganization

**Problem hypothesis:** Old memberships continue to cost attention and requests after their academic purpose ends.

**Experiment:** Explicitly pause selected courses while retaining files and allowing manual resumption. Ask students about the last semester transition before designing a semester hierarchy. Do not infer terms from titles, rename folders automatically or silently drop newly joined courses from an “all courses” promise.

**Acceptance criteria:** Paused versus failed versus empty is clear; resumption preserves identity and paths; retained courses remain searchable; no deletion. **Tradeoff:** Automatic all-membership mode requires an explicit exclusion/intent model. **Validation:** transition scenario and measured request reduction; defer if source-level pause already solves the observed job.

## O7 — University-friendly operation as product quality

**Problem:** The local page index permits 64 simultaneous page reads in addition to PFERD task policy. A fast single-user run does not prove an acceptable burst at a university or at wider adoption.

**Acceptance criteria:** Bound actual in-flight HTTP requests per host across traversal, prefetch, authentication and retry; respect server throttling and `Retry-After` where provided; avoid retry storms; prevent background sources launching together without policy; preserve coverage at reduced concurrency; record request count, peak concurrency and time in synthetic/load-safe fixtures. Document institution overrides and validate a conservative default without guessing a universal “safe” number. Cancellation frees outstanding work.

Measure background startup and idle behavior separately from sync duration. Benchmark initial and unchanged runs, no network, expiry and battery deferral. Do not promise battery savings from wall time alone. **Validation:** T8 and instrumented synthetic server scenarios. No stress tests against live university infrastructure.

## O8 — Local content search as an experiment

**Problem hypothesis:** A student remembers a concept but not a filename or week. Current metadata search may fail.

**Smallest experiment:** Test a disposable, local PDF-text index on consenting/synthetic documents only after observing failed metadata tasks. Compare against existing app search and the OS's file/content search. Support course restriction and explain which files were not indexed; report extraction failures. OCR and semantic search are separate costs.

**Acceptance criteria before adoption:** Demonstrated reduction in correct-document retrieval time; no increase in wrong-file choices; bounded disk/CPU work; index updates follow changes and removals; deletion/privacy controls; no downloaded parser plugins or cloud model dependency by default. Unindexed must not look like nonexistent. Defer if Spotlight/Windows Search or course context resolves the task adequately.

## Rejected for the current roadmap

AI summaries and automatic deadline extraction can omit consequential information and require expensive correctness/privacy validation; no direct need evidence currently justifies them. “Important” scoring would need trustworthy ground truth unavailable in the crawler. Uploads/submissions change the product's safety boundary. A built-in notes editor, calendar, chat, generic cloud backend or cross-device reading state would duplicate mature tools and expand account/data responsibilities. Automatic deduplication by filename/hash risks merging distinct academic objects. A new analytics service, gamification and engagement targets do not support the core outcome.

Reconsider only with observed recurring unmet jobs, a bounded prototype and an explicit decision record. A requested capability is evidence to investigate, not an instruction to expand the product indiscriminately.
