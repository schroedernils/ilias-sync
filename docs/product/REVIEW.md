# Strategic quality review and observed baseline

## Current follow-up — 28 October 2026

Nils explicitly asked for continued improvements to user flow and information using himself and the agents; he cannot recruit classmates. The [validation protocol](VALIDATION.md) now treats owner feedback, expert agent walkthroughs and deterministic scenario checks as the active method. External student sessions are optional, not a prerequisite. Population-wide comprehension and demand are still unmeasured.

The checkout has advanced to local commit `918db2e` and later active edits. Its recorded work includes scoped checks/legacy handling, source/build identity and measured host-level HTTP limits. Those are already implemented foundations, rather than new proposals to recreate. See the owning [verification record](../VERIFICATION.md), [performance record](../SYNC_PERFORMANCE.md) and tests for current evidence. The earlier observations below remain dated baseline evidence, not a claim that their defects are still current.

This round directly improves `info.py` in a coordinated write scope: task-based help for finding materials, interpreting change history, reading results, restoring sign-in, managing copies/versions, offline use and stopping/scheduling. Help topics use short safe paragraphs and direct installation/recovery/support links. App behavior remains bounded: no invented unread tracking, cloud completion or offline certification. The developer owns broader GUI changes; the UX agent owns independent interaction review. No university access or real settings changes are needed for these checks.

The directly coordinated `HelpDialog` changes integrate paragraph rendering and compact, wrapping topic rows. Initial renders exposed clipped topic names and horizontal scrolling; shorter navigation labels and reduced row padding corrected them. The local renderer inspected German/English, light/dark and compact/default examples (16 captured states). New tests check topic navigation, all text and accessibility descriptions, readable paragraph structure, literal-markup escaping, scroll reachability and support links. The current non-HTTP test run passed **177 tests**, and Ruff/whitespace checks passed. The loopback HTTP group was deliberately excluded from this run; no new HTTP, real-university, installation or spoken-screen-reader claim follows from it. Existing-package behavior is distinct from this source change.

## Historical baseline — 27 October 2026

The original review edited only new files in `docs/product/`; no application implementation, existing documentation, user settings or university data was changed by that pass.

## Repository and delivery evidence

The configured remote and GitHub metadata identify `schroedernils/ilias-sync`, a private, non-archived repository with default branch `main`. Connected identity `schroedernils` has admin/maintain/push/triage access. Issue and open-PR searches returned no records at initial inspection; issue creation requires a final duplicate check. The local base was `b352f322422039bb5687c731d235d4535010bbd7`, with extensive pre-existing uncommitted implementation/documentation changes. That SHA alone does not identify the reviewed redesign.

GitHub release metadata was read directly: `v0.1.0-alpha.2` was published 22 October 2026, targeting `f9670b9ef93e5112beb79e9c0c1ccdd0109024df`, with four native packages and checksum files. This proves release presence, not execution of each package by this reviewer. The redesign and performance work inspected here are local changes beyond that release. The project version still reads `0.1.0a2`; a version label alone cannot distinguish those builds.

No release, push, merge, remote documentation commit, or visibility change is part of this review. Three consolidated GitHub planning issues were created after a second empty duplicate search and explicit collaborator-permission verification: [#1](https://github.com/schroedernils/ilias-sync/issues/1), [#2](https://github.com/schroedernils/ilias-sync/issues/2), [#3](https://github.com/schroedernils/ilias-sync/issues/3). The strategy files remain local until authorized publication.

## What is already present

| Capability observed in source/docs | Assessment |
| --- | --- |
| Source/course selection, route precedence, local publication, version/conflict preservation | Strong foundation; protect it rather than rebuilding it |
| OS-scheduled one-shot workers, battery deferral, backoff, bounded active job | Fits a quiet utility; actual schedule/energy still needs platform evidence |
| Filename-first materials, course context, search, filtering, native open actions | Directly supports the main retrieval job; not a new roadmap proposal |
| `changed_at`/`change`, recent view, separate generated information | Useful awareness foundation; not yet a “since review” model |
| Status classification, last-success separation, bounded attempt history and report | Directionally correct; evidence scope and local residency are distinct gaps |
| Source-bound page index and fresh known-page fetches | Performance improvement with documented coverage safeguards; not universal remote-content proof |
| Existing security/report templates, install/recovery/verification docs | Keep useful docs; avoid parallel competing instructions |

Reviewed owning sources include `storage.py` (`Archive`, `record_attempt`), `engine.py` (`make_crawler`, `synchronize`), `page_index.py` (`PageIndex`, `PageData`), `presentation.py` (`sync_summary`, `schedule_expectation`) and `gui.py` (`refresh`, `apply_file_filters`, file opening), plus tests and existing docs.

## Independent probes performed

An ephemeral Python/Qt check used a temporary `ILIAS_SYNC_DATA_DIR`, the offscreen Qt backend, synthetic course URLs and no credentials/network calls. Two manifest records were created with `changed_at=1` and current time, with no corresponding output files. A completed status used `last_success=100`. Then the source was changed from automatic discovery to one explicit course. PFERD's policy was separately called on a temporary file with a deterministic integer mtime.

| Observation from the successful probe | Meaning / limit |
| --- | --- |
| Recent view displayed both records, including epoch timestamp 1 | The filter is “has recorded change”, not a review boundary or time window |
| `last_success` remained 100 after changing selected scope | History persists, appropriately, but applicability to the new scope is not modeled there |
| Both records remained listed while local files did not exist | The manifest is a library/history index, not an independent local-residency check; listing is not itself a bug |
| `ALWAYS_SMART` returned no download for equal remote/local mtime without ETag evidence | Metadata can skip body downloads; this does not show that any real lecturer update has been missed |

An initial probe was corrected to supply a required synthetic client ID; a second was corrected to use integer mtime because datetime microsecond rounding changed the comparison. The final combined probe passed all three assertions. These are bounded behavioral checks, not a real-university or student usability study. This table records the initial observation; subsequent scope work is distinguished below.

## Strategic findings

**P0 — Complete scope-evidence acceptance (O1).** Initial inspection lacked a stored signature. During this session the developer added `source_scope`, persisted it through attempt recording, stopped transferring `last_success` between different signatures, and added a mismatch message in `MainWindow.refresh`. This is meaningful progress already implemented locally. Remaining questions: statuses without signatures bypass the guard; the signature hashes cosmetic fields such as source name; actual attempted roots can differ from configuration in automatic mode. [#1](https://github.com/schroedernils/ilias-sync/issues/1) tracks verification and these boundaries, not the already-added signature as new work. Preserve historical evidence without representing it as current coverage.

A second isolated probe of the added guard verified: changing the course selection displayed the settings-changed explanation; a stopped attempt in a different scope did not inherit `last_success`; removing the historical scope field bypassed the mismatch guard; and changing only the source name changed the signature. The last two cases remain acceptance work. Assertions used observed state transitions rather than assuming the UI language. At this check, SHA-256 was `e3c83bd8d322e1910c780a87402f4b3933abaffcffcc7b1a72da70fc2c5c8310` for `storage.py` and `9bea60b4c969c6233d24fb6d96a279eb1956676996076b1517c267aebebd74d5` for `gui.py`; later edits can change the result.

**P1 — Define a review boundary for awareness (O3).** `apply_file_filters` checks `bool(changed_at)` for recent materials. The existing persisted dates and stable identities make a small experiment feasible. Avoid treating generated pages, route copies and local repairs as academic updates. A hash only proves byte change, not meaning or urgency.

**P1 — Verify local readiness separately (O2).** The table enumerates the manifest; missing-file recovery occurs when opening or on sync. Current wording was already being corrected to “recorded in your archive” and “last check completed”. This avoids a misleading claim, but does not implement readiness verification. Cloud eviction, mounted volumes and links need separate behavior/evidence.

**P0 for wider rollout — Put performance inside a request budget (O7).** `PAGE_REQUESTS=64` plus eight PFERD work slots is observed configuration, not an established safe university-wide default. The documented few-second warm runs are useful local evidence. They do not establish server impact at scale, new-download throughput or energy savings. Require instrumentation and synthetic throttling tests before broader concurrency claims.

**Release integrity — Separate local features from downloadable Alpha 2.** The working README includes local redesign/performance behavior alongside Alpha-2 download links, while source version remains unchanged. Existing screenshots may also lag active text corrections: the inspected synthetic `app-light.png` still used an unconditional current/local-availability phrase while current presentation code used bounded historical wording. Refresh screenshots and align claims to a named build at the release milestone; do not publish planned functions as shipped.

## Coordination evidence and limits

The chats **“Prüfung auf „lila“ beheben”** and **“Review IliasSync redesign UX”** were discoverable. Their summaries/visible messages were inspected. The developer reported completed local redesign work, 129 passing tests, 37 rendered states and native macOS file opening; these are **attributed reports**, not tests rerun or a binary installation verified by this Product Director. The UX review remained active and reported a reproduced credential-persistence problem in an otherwise rejected settings edit. Treat that finding as owned by the UX/development review until its current-source reproduction and fix are verified; do not call it resolved here.

Both chats received one consolidated strategic handoff covering scope, recency, metadata limits and separate local/cloud evidence. No extra recurring monitoring was established. The repository can carry the durable product record; review meaningful milestones rather than interrupting each edit.

## Independent judgment

Continue the materials-first redesign: its existing search/context/opening work advances a real task. Finish correctness and recovery before expanding it. The most promising differentiation is a local library that remembers what changed and tells the truth about what it checked. Another visual dashboard, an AI layer or further speed work without request/coverage guardrails would currently dilute that direction.

The next decision should use [the bounded opportunities](OPPORTUNITIES.md) and [validation tasks](VALIDATION.md), not a count of added features. Student demand, semantic-importance detection, universal compatibility, current native-platform acceptance, energy use and tested cloud restoration remain unproven.

## Verification performed by this reviewer

`python -m pytest -q tests/test_presentation.py tests/test_product_workflows.py` passed **32 tests** in the existing local virtual environment after the scope addition. These are the relevant existing presentation/workflow regressions, not a rerun of the developer's full suite or new physical-platform evidence. The isolated baseline and follow-up scope probes described above also passed. Documentation links and whitespace were checked separately. No implementation tests were added and no real account was accessed by these probes.
