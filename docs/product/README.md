# IliasSync product direction

Product Director review · updated 28 October 2026 · direction and local improvements, not a release announcement.

**IliasSync should remove the work of checking, collecting and re-finding course files while making the limits of its checks clear.** A student should be able to answer “What changed?”, “Can I open it here?” and “Does anything need me?” in seconds, then leave the app.

This is a decision record for development. It does not establish validated demand, authorize a release, or turn planned capabilities into implemented features.

## Start here

| Record | Purpose |
| --- | --- |
| [Current review](REVIEW.md) | Actual capabilities, verification boundaries and remaining strategic gaps |
| [Research](RESEARCH.md) | Original studies, methods, limitations and implications |
| [Opportunities and acceptance criteria](OPPORTUNITIES.md) | What to improve, what to defer, and what counts as done |
| [Validation](VALIDATION.md) | Student discovery, comparative tasks, outcome measures and release evidence |

GitHub planning records created after checking repository identity, admin access and duplicates: [#1 — scope and legacy evidence](https://github.com/schroedernils/ilias-sync/issues/1), [#2 — changes/readiness discovery](https://github.com/schroedernils/ilias-sync/issues/2), [#3 — request and energy guardrails](https://github.com/schroedernils/ilias-sync/issues/3). These consolidate outcomes; they do not assign another implementation stream or a delivery date. Source changes already in progress remain with their current owner.

## People and purpose

The initial target is students using a supported ILIAS installation who regularly retrieve lecture notes and exercise sheets on a desktop or laptop. Prioritize students juggling several courses, intermittent connectivity and personally annotated copies. These are recruitment hypotheses, not established market segments. macOS, Windows and Linux remain intended platforms; support claims need platform-specific evidence.

Secondary users include students retaining materials after a semester and students who use assistive technology. Staff administration, assignments submitted to ILIAS, social learning and institutional analytics are outside the initial purpose.

The value proposition is **a dependable local course library with a clear account of changes and exceptions**. A normal filesystem, native document applications and the university platform remain useful parts of the workflow. IliasSync earns its place by removing recurring checking and uncertainty, not by moving every academic activity into itself.

Proposed positioning: “Deine Kursdateien am richtigen Ort. Änderungen im Blick. Auch ohne Netz weiterarbeiten.” The final sentence requires verified local availability; it must not be shown as an unconditional guarantee for links or cloud placeholders.

## Jobs and outcomes

| Situation | Desired progress | Work to eliminate |
| --- | --- | --- |
| Before class, a new exercise session or a study trip | Get the right available files without checking each course page | Repeated login, course traversal and manual downloading |
| A lecturer replaces a document | Identify the changed object and keep personal annotations | Comparing timestamps and guessing which copy is which |
| Returning after several days | See relevant changes accumulated while away | Remembering which courses and filenames were checked |
| Revising weeks later | Re-find the correct course document | Reconstructing an exact filename or reorganizing duplicates |
| A sync or login fails | Know what still works and what action restores checking | Reading logs or assuming the entire library disappeared |
| A semester ends | Keep useful files and stop irrelevant background checking | Deleting and rebuilding a personal filing system |

These jobs are derived from the product's task structure, Nils's workflow and external research. Current validation uses Nils plus independent agent reviews and deterministic scenarios; [the review protocol](VALIDATION.md) separates these forms of evidence. External student recruitment is optional, not a development prerequisite.

## Product contracts

1. **Scope every claim.** A completed attempt, a complete check of the selected supported content, a readable local copy and a cloud upload are different facts. Show the time and scope of the evidence. A selection, account, destination or relevant policy change invalidates applicability of old evidence, not the evidence itself.
2. **Preserve work.** Keep local edits, older versions and files no longer visible remotely. Changing folders must explain whether it moves a managed folder or creates another copy. No automatic destructive cleanup.
3. **Changes belong to the student.** Download time is not lecturer upload time; displayed is not read; opened is not understood. Meaningful changes require stable object identity and content evidence. Acknowledgement is deliberate and reversible.
4. **Be quiet until useful.** No success notification for an unchanged run. First establish an in-app changes workflow; optional digests may follow validation. A persistent problem needs a persistent explanation, not repeated alerts.
5. **Keep the library ordinary.** Files open in the default application and remain accessible outside IliasSync. Course names and user choices supply context; speculative classification must not silently move documents.
6. **Make exceptions actionable.** Distinguish unreleased, denied, missing, excluded and failed content where the source supports that distinction. Unknown reasons remain unknown. Explain recovery and retain the source route when safe.
7. **Optimize inside reliability and service limits.** Fast repeated checks are valuable, but performance cannot come from silent coverage loss, excessive university load or unmeasured energy claims.
8. **Default to local knowledge.** Change history and any future indexes stay on the device. No external AI, analytics account or extra university permission is needed for the core job.

The detailed contracts and their acceptance criteria are in [OPPORTUNITIES.md](OPPORTUNITIES.md). These are recommendations for adoption by the project owner; existing preservation requirements are already part of the product.

## Roadmap by evidence gate

There are no calendar or effort estimates: the checkout is actively changing and implementation capacity has not been estimated. Complexity below is relative, not a delivery promise.

| Gate | Outcome and work | Exit evidence | Deliberately deferred |
| --- | --- | --- | --- |
| **Now: trustworthy foundation** | Finish the active redesign; resolve the UX agent's reproducible persistence/recovery findings; scope completion evidence (O1); establish request and energy guardrails (O7) | Current-source regressions, independent UX recheck, accurate release/screenshot boundary, synthetic server-load tests | New dashboards, notifications, AI, another performance sprint |
| **Next: dependable daily use** | Clear task help and recovery; explicit local readiness (O2), a small “since my review” changes prototype (O3) when useful | O1 stable; owner feedback, independent agent walkthroughs and deterministic outcomes; compare a prototype to existing library and folders | Full-text engine, importance prediction, learning progress tracking |
| **Owner acceptance: prove the workflow** | Test recovery/version access (O4); Nils-and-agent scenarios, platform/accessibility checks and compatibility ledger | [Validation gates](VALIDATION.md), named build evidence, remaining exceptions explicit; no external recruitment requirement | Universal compatibility claims or unattended institutional rollout |
| **Later: only after demonstrated need** | Quiet digest (O5), semester pause (O6), local full-text experiment (O8) | Owner feedback or repeated scenario failures expose an unresolved job; prototype improves outcomes without hiding material | Custom calendars, note editors, cloud accounts, deadline extraction |

O2 and O3 can be evaluated in parallel; implementation should remain bounded. If Nils's feedback or agent scenarios expose a confusing scope contract, simplify it. If a changes prototype adds more acknowledgement work than it removes, retain a chronological view with an honest date range instead.

## Decisions and unresolved questions

| ID | Decision / recommendation | Reason and revisit condition |
| --- | --- | --- |
| D1 | Keep the current materials-first workspace | Search/context/opening already exist; a new home screen needs evidence of a separate job |
| D2 | Prioritize evidence semantics above visual polish | Prevent misplaced reliance; revisit wording with comprehension tests |
| D3 | Test review boundaries before adding notifications | Current recency is not an unseen-changes model; notification usefulness depends on meaningful events |
| D4 | Preserve native files and annotations | Local edits and retention are core value; do not trade them for a cleaner-looking mirror |
| D5 | Defer AI summaries and inferred urgency | No measured need offsets omission, privacy, computation and maintenance costs |
| D6 | Use milestone reviews and existing tracking | No extra recurring monitor created by this review; consolidate feedback at meaningful changes |
| D7 | Optimize with Nils and the agents; external recruitment is optional | Explicit owner instruction on 28 October; distinguish first-person feedback, expert review and synthetic tests |

Open questions: Is the main recurring problem discovery, re-finding, offline uncertainty or login friction? Do students want to acknowledge a course or individual changes? How often do source edits lack useful metadata? Does a cloud destination stay resident offline? How much old-version storage accumulates in one semester? What authentication recovery succeeds without technical help?

## Coordination and GitHub practice

The developer owns implementation; the UX researcher owns interaction review and accessibility findings; the Product Director owns outcomes, scope and prioritization. Separate chats were accessible in this session and received consolidated findings. Their reports are attributed evidence, not independent verification.

Keep this directory as the short product record. Link source evidence and the corresponding issue when a decision changes. Existing technical docs remain authoritative for implementation. Avoid copying a second detailed backlog into each file: issue status is authoritative for delivery, this roadmap for order and rationale.

Before a milestone review: inspect the current diff and relevant issue, recheck a risky scenario, then record **observed**, **reported**, **planned**, or **unverified**. Review after source/schema changes, a completed development milestone or a material research result. No claim of continuous monitoring is made.

Repository identity and admin access were verified for `schroedernils/ilias-sync`; it remains private. Existing issue templates already ask for the user problem and avoid sensitive data. Retain them. Product issues should be consolidated, self-contained and free of private course details. Do not add labels, milestones or dates merely to make tracking look elaborate.

All documentation in this directory starts as a local change. Publishing it, pushing source, merging or releasing remains a separate action requiring the owner's explicit authorization. New product issues may record the authorized planning work without pretending these local files are already on GitHub.
