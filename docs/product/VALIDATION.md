# Product validation and quality gates

Updated 28 October 2026 · owner-and-agent validation is the active method; **no external student study results exist**.

## Active review method: Nils and the agents

The owner cannot recruit classmates and explicitly asked to continue optimizing flows and information with himself and the agents. External recruitment, diaries and participant counts are **not development or local acceptance prerequisites**. The historical study outline below is optional future research, not an outstanding assignment for the owner.

Use real owner feedback as first-person evidence, independent agent walkthroughs as expert evaluation, and deterministic synthetic scenarios as behavioral verification. Never invent novice-user success rates or describe an agent as a student participant. Broader student demand and population-level comprehension remain unknown, but that does not prevent reversible improvements to the current app.

For each bounded change: identify the user's task, walk the current start → action → feedback → recovery path, remove one avoidable ambiguity, and verify the affected outcome with realistic synthetic state. Have another agent inspect the result without duplicating file ownership. Use the existing tasks T1–T9 as scenarios rather than recruitment gates. Confirm material improvements with Nils during ordinary use when feedback is available; do not stop progress to schedule a formal user session.

Decision rules: implemented behavior and accurate copy must agree; keyboard navigation and cancellation must work; failures explain a useful next action; preservation regressions pass; compact/light/dark states remain readable. A task can pass its deterministic contract while its learnability remains an expert judgment. Record that distinction. The speculative 15-second/5-minute targets below are not agent-measured usability results.

## Optional future discovery

Recruit an initial **6–8 consenting students** for formative discovery, deliberately varying ILIAS institution/login, operating system, course load, cloud/local destination, and accessibility needs. This is a small qualitative sample, not statistically representative. Include less technical students; the product owner's workflow is valuable but cannot stand in for the population.

Use a 30–45 minute session. Ask for the last real occasion they downloaded a sheet, discovered a replacement, could not find a document, or studied without a connection. Reconstruct trigger → actions → workaround → consequence. Ask what they actually did before asking what feature they want. Offer synthetic reproductions or student-controlled demonstrations; do not collect credentials, browser sessions or course PDFs.

Questions: “How did you learn it existed?”, “How did you decide this was the latest copy?”, “What changed in your own copy?”, “What would have happened if you had not checked?”, “Show the last search you abandoned.” Separate missing files from missing announcements: IliasSync does not currently capture every educational communication channel.

With volunteers, run a two-week lightweight diary: a short entry only when they check for material, fail to find it, notice a change or recover a failure. Record course pseudonym, trigger, tool, time estimate, outcome and workaround. No continuous screen capture or automatic file logging. Debrief unexpected cases. Count repeated problems per participant, not entries as independent people.

Advance an opportunity when a recurring consequential job is observed and an existing behavior does not adequately solve it. Narrow or reject it when the proposed solution adds maintenance or acknowledgement without eliminating work. Do not use “most respondents liked it” as a substitute for task evidence.

## Scenario set and optional comparative test

For current work, agents compare the existing library and a bounded change using the scenarios below, with Nils's observed workflows supplying context. If external testing later becomes practical, the optional design is 6–8 participants per round, counterbalanced order and matched documents with equal training. Small samples reveal failure mechanisms; they do not establish population rates, percentiles or statistically reliable product uplift.

Prepare a synthetic semester with duplicate filenames across courses, old material, a new sheet, a replaced PDF, unchanged bytes with altered server metadata, a local annotation, a denied item, an external link and a failed subtree. Include old manifests without change dates and a background update during review. Ground truth is an independent fixture manifest, never the app's own success result.

| Task | Prompt / injected condition | Successful outcome | Initial decision rule |
| --- | --- | --- | --- |
| T1: changes | “Find what appeared or changed while you were away” across several completed/no-op runs | Correct documents and course context, no false new-content inference | Aim ≤15 seconds after orienting; any wrong document requires investigation |
| T2: trust | Present complete, partial, expired-session, stopped and stale-scope states | Student describes checked scope/time and remaining uncertainty | No participant should confidently interpret a deliberately incomplete case as complete; each failure blocks that design variant |
| T3: offline | “Choose the files you can use on the train,” then disconnect | Actual documents open; links/placeholders/unknowns correctly identified | Zero false positive readiness in scripted cases |
| T4: missing target | Missing file, unmounted drive, unreadable target or evicted cloud file | Clear diagnosis; safe repair or explicit uncertainty | No fallback destination or destructive overwrite; no credential request for a purely local problem |
| T5: recovery | Server replaces a personally annotated sheet | Student identifies personal/server copies and opens a prior version | Preserve all expected hashes; aim recovery without help in ≤2 minutes |
| T6: review boundary | Acknowledge a review while another change arrives | Newer event remains visible; undo works; “read” is not inferred | All deterministic race/restart/clock scenarios pass |
| T7: setup/scope | Configure source/course/destination, then change the selection | First relevant file opens; student understands what will be checked | Aim ordinary supported setup ≤5 minutes; report auth delays separately |
| T8: background | Sleep/wake, battery deferral, offline, throttling, locked worker and expiry | Honest planned timing, bounded retry/load, safe cancellation | No false guarantee of exact run time; measure actual requests and idle processes |
| T9: retained object | Complete crawl loses an object; partial crawl misses a subtree | Retained copy remains; reason/coverage distinguish removal, denial and unknown | Never infer deletion or permission loss solely from incomplete discovery |

The time targets are **initial product hypotheses**, not literature-derived standards or achieved results. Report individual times, errors, assistance and median/range. If a task fails, record why before adjusting the threshold. Use a fresh task to verify the repair; do not keep testing until participants memorize it.

## Goals → signals → metrics

Adapted from [Rodden, Hutchinson & Fu's HEART framework](https://research.google/pubs/measuring-the-user-experience-on-a-large-scale-user-centered-metrics-for-web-applications/). The measures below can be collected by an observer and a voluntary local diary; no analytics service is required.

| Goal | Signal / measure | Interpretation and guardrail |
| --- | --- | --- |
| Find the right material quickly | Time to first correct open; wrong-copy choices; help requests | Include failures; faster wrong answers are worse |
| Rely appropriately | Correct interpretation of scope/time; confident incorrect answers in incomplete scenarios | Pair confidence with correctness; maximum confidence is not the objective |
| Get started independently | Time to first useful file; completion without facilitator help; failure cause | Separate authentication/institution failures from interface failures |
| Keep expected files accessible | Readable expected fixture files / independently enumerated selected supported files | Report exclusions, unknown enumeration and cloud residency separately; a manifest cannot prove its own completeness |
| Recover without losing work | Recovery completion, time and checksums of protected files | Zero unintended replacement/deletion in deterministic preservation cases |
| Remove routine checking | Diary checks of ILIAS before/after, with reason and missed-material incidents | Fewer checks are good only if necessary information is still found |
| Remain lightweight | Request count/peak concurrency; run wall time; startup cost; idle worker count; measured energy where available | Match scope and source conditions; wall time alone is not power use |
| Sustain usefulness | Willingness to keep the schedule; repeat successful file access; brief satisfaction/effort question | Voluntary follow-up; no daily-open, streak, session-length or notification-click target |

Keep a simple per-round record: build SHA or source fingerprint, package hash, date, scenario, independent expected result, actual result, assistance, severity and evidence class. Store participant notes locally with consent and minimal identifiers; agree deletion timing before collection. Publish aggregate/redacted findings only. Do not record private file paths, credentials, course contents or reading histories in GitHub.

## Engineering and release gates

**Deterministic correctness:** Current-source regression checks cover selected scope changes, denied/unreleased objects, failed discovery, metadata limitations, new contents in old folders, missing local files, annotations, routing copies, interruption/retry, disk full/unmounted destination, event acknowledgement races and schema migration. Require zero unintended loss/overwrite in these cases. Passing finite fixtures does not establish universal reliability.

**Compatibility ledger:** One row per actually tested institution/version or layout, auth method, app/build, OS, destination type and task. Mark discovery, enumeration, downloads, update, expiry recovery, scheduled run and offline open separately: pass/fail/unknown, with date. Use anonymized institution labels unless consent/public support warrants naming. A public university URL is not permission to publish account details. Never equate one institution with universal ILIAS support.

**Accessibility:** Keyboard-only setup, table selection/opening, filters, dialogs, errors and escape from the table; high text scale/compact layout; status meaning without color. Then VoiceOver on macOS, NVDA on Windows and an appropriate Linux reader/backend against the packaged runtime. Verify names, roles, current state, announcements and focus recovery. Native Qt support and screenshots alone are insufficient evidence.

**Recovery rehearsal:** Back up app metadata and file tree, restore into an isolated profile, open current/older/annotated copies and re-run without duplicate or destructive publication. Separately test files-only recovery and explain lost provenance. A provider's upload completion is not a completed disaster-recovery test.

**Local owner acceptance:** O1 semantics resolved, active UX safety regressions closed, selected deterministic cases pass, build identity clear, supported login recovered, request bounds verified in a synthetic server, and known platform gaps disclosed. Nils and the agents can validate the local workflow without external participants; do not label that a general student study or universal compatibility.

**Wider release:** Relevant native CI packages and actual installation/accessibility checks, documented compatibility matrix, safe restoration and a named build's accurate README/screenshots/release notes. macOS signing/notarization, Windows signing and updater status remain explicit release decisions. A local fix is not a shipped fix. The owner's release authorization is still required.

## What would change the roadmap

- If checking is already effortless but re-finding repeatedly fails, prioritize O8 after a comparison with OS search.
- If participants ignore acknowledgement or describe it as homework, prefer a clear date range and saved position over an inbox.
- If most confusion concerns login/setup, fix that before digest experiments.
- If people still miss forum/deadline announcements, clarify the product boundary and source navigation before claiming broader awareness.
- If cloud residency cannot be verified without provider integration, scope the readiness claim to tested local files and keep other states explicitly unknown.
- If wider concurrency increases server pressure, choose the measured conservative policy even when it costs some latency.
