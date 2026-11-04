# Verification boundaries

## Linux surface rendering — Ubuntu 26.04 ARM64

The former stylesheet requested translucent surfaces without a native backdrop on Linux. The
updated theme uses opaque window, dialog and popup surfaces outside Cocoa and reserves space for
overlaid title-bar controls only on Cocoa. A before/after check on the same composited X11 test
display changed the background behind the app: the sampled main-window and settings colors
changed in 1.0.1 and stayed identical in the corrected build, in both color schemes.

Main window, settings, dropdowns and the university menu were also checked in a logged-in
Ubuntu 26.04 GNOME/Wayland session using synthetic materials. The full local suite passed on
macOS (**304 passed**) and in the Ubuntu ARM64 guest (**301 passed, 3 platform skips**). The
opaque-surface regressions passed on the guest's X11 and Wayland backends. This does not verify
a Windows desktop or publish a new release.

## Sidebar correction — 1.0.1

The 1.0.0 sidebar defect was reproduced by native dragging in the installed macOS app and an isolated
three-file example. The native backdrop changed the full-size content-view style behind Qt's back;
the splitter's requested sizes and its actual pane frames could then disagree. Plain Qt rendering and
Qt-managed client-area flags were compared directly. The correction configures the client area through
Qt before Cocoa creates the window and stops reinserting or changing Qt's view/layer hierarchy.

Native example-window dragging was checked in both directions; the owner also confirmed the corrected
probe. A separate hidden Cocoa regression covers **108 pane transitions** across three window sizes,
three theme states and overview/materials/details, including library refresh after each move. Sync-result
tests cover success, warnings, failure and stop, plus constrained-window recovery, hiding/showing and
language-change reconstruction. Direct installed-package evidence is recorded separately below when complete.

The complete local collection passed **302 tests**, both as one pytest session and in isolated modules.
The [four-platform build](https://github.com/schroedernils/ilias-sync/actions/runs/41810759330) passed:
macOS arm64/Intel **302 passed** each, Windows **295 passed / 7 platform skips**, Linux **299 passed /
3 platform skips**. All packaged offline self-tests passed. Source is
`418b0a08711b7e1a7492a8bec41e36b53657b4fc`; installed macOS build is `418b0a08711b-8109a828caad`.

That downloaded CI package was installed in `/Applications/IliasSync.app`, passed its offline self-test
and strict ad-hoc signature verification, and was checked by native dragging. The sidebar was narrowed
from the previous setting; a real configured-university sync completed successfully with **75 unchanged
files** and kept the chosen divider position. This single-account run is not a performance benchmark or
general compatibility proof. Settings and the native schedule remained byte-identical to the pre-install
snapshot; the previous app bundle is retained privately for rollback.

The temporary sidebar probe uses synthetic files and an offline simulated sync. It is not an account
or university compatibility test and is not part of the released app.

## Release 1.0.0 — 3 November 2026

- Local complete suite: **296 tests passed**. Ruff and whitespace checks passed.
- Synthetic UI review: **101 states**, including compact windows, both appearances, active sync,
  sign-in recovery and empty states. Product screenshots were regenerated from synthetic courses.
- Targeted native state checks cover repeated Aqua/Dark Aqua transitions and **200 backdrop updates**
  without resetting the window style, moving its frame or replacing Qt's content view. Hidden native
  test windows are not visual proof; installed interaction checks are tracked separately.
- The macOS package passed its offline executable self-test at version **1.0.0** and strict ad-hoc
  signature validation. Build identifiers distinguish it from older alpha installations.
- All four release packages passed the [native build matrix](https://github.com/schroedernils/ilias-sync/actions/runs/41697340947)
  and packaged offline self-tests: macOS arm64 and Intel **296 passed** each; Windows **290 passed,
  6 skipped**; Linux **294 passed, 2 skipped**. Platform-specific skips remain visible in the job logs.
- [Release 1.0.0](https://github.com/schroedernils/ilias-sync/releases/tag/v1.0.0) was published from
  `f6a09e0ce3e7ad5fb742ebc5475615e070c4b7c9` (package build `f6a09e0ce3e7-f4ca74959c2a`).
  The [publishing workflow](https://github.com/schroedernils/ilias-sync/actions/runs/41700704134) verified
  the source run, semantic version, all four package names and SHA-256 sums. Public anonymous repository
  and latest-release access was checked after publication.
- The downloaded release macOS arm64 package also passed its offline self-test and strict ad-hoc
  signature verification locally; its bundled icon matches the supplied dark icon byte for byte.
  The new sidebar correction has synthetic drag and hidden AppKit state regressions; direct dragging
  in the installed 1.0.0 app remains unverified in this pass.
- No universal ILIAS/SSO compatibility, macOS notarization, Windows Authenticode signature, spoken
  screen-reader validation or physical Windows/Linux desktop usability study is claimed.
- Repository history was checked for credential files, private keys and common GitHub-token formats
  before publication. This is a bounded check, not a security audit.

Older sections below describe their dated builds and do not replace the 1.0.0 checks.

## Weekday schedule editor — 1 November 2026

- Complete suite: **262 tests passed in 38.98 seconds**; focused editor tests and Ruff/whitespace checks
  also passed after the final native time-field style adjustment. **103 synthetic states** rendered with
  bounded controls, including populated/empty weekly schedules, 520×640, dark/light and enlarged text.
- Calendar tests cover separate weekday times, free days, exact minute boundaries, next-week rollover,
  nonexistent spring-forward times, server cooldown and sign-in waiting. Native configuration tests verify
  launchd Monday/Sunday numbering, weekly Windows XML and systemd weekday expressions without daily fallback.
  The previous daily settings/job are restored if installing a new weekly job fails.
- Installed macOS build **`efc6b1a12ae0-2ccb90b86858`** passed packaged/installed offline self-tests and
  strict ad-hoc signature verification. Native inspection showed Monday through Sunday with the real
  existing 11:00/14:00/17:00 daily times copied into the draft, accessible day-specific add/remove controls,
  Copy times and a permanently visible next-run preview and Save/Cancel footer. Native adding/removing of
  a test time worked, then Cancel discarded the draft. The editor remains open for the user.
- SHA-256 checks confirmed the real settings file and launchd plist were unchanged after installation and
  draft testing. Private copies and prior app bundles are retained in `.local/weekly-plan-20261101/`.
- No new actual weekly times were chosen for the user, no real scheduler policy was changed, and no timed
  weekly OS execution was claimed. Windows/Linux execution and spoken screen-reader output were not tested.

## Unified workspace and notifications — 1 November 2026

- Final complete suite: **253 tests passed in 31.63 seconds**. Ruff and whitespace checks passed.
- Synthetic Qt review: **101 states** with control bounds verified, including 820×560, 980×700 and
  1280×800, both palettes, overview/materials/notifications/details and running/paused/error states.
- Installed build **`f42bfaca53be-8be63d20774c`** passed packaged and installed offline self-tests and
  strict ad-hoc signature verification. Previous app bundles are retained privately under
  `.local/unified-workspace-20261101/`.
- Native macOS inspection confirmed three recent materials, **View all (59)**, scoped full browsing,
  persistent bottom Sync now, last-sync absolute/relative time, and notification/detail navigation.
  A real unavailable-download notice was dismissed and restored; the sync outcome continued to show
  two unavailable downloads throughout. No teaching materials were downloaded or changed by this UI check.
- Native inspection exposed and fixed a macOS directory-watch loop caused by touching the notice lock
  during idempotent refreshes. Replayed attempts now return before acquiring a write lock, and permission
  feedback survives refresh. Regression tests cover both conditions.
- macOS notification permission for IliasSync was initially off/denied. The app preference and the
  app-specific macOS permission were enabled for the requested feature. The installed **Test notification**
  action then reported **Test notification handed to macOS** (native authorization and request accepted).
  This is submission evidence, not visual proof of a delivered desktop banner. Real new-error alert delivery
  during a later scheduled sync was not exercised; deterministic tests cover new/repeated/recovered issues,
  dismissal, cancellation, generic lock-screen content and notification failures.
- No live ILIAS synchronization, credentials entry, scheduler change, push, merge or release was performed
  for this UI redesign. The existing two unavailable-download notes remain visible.

## Evidence gates

This preview has separate evidence gates:

1. Unit tests: archives, conflict handling, interruption/retry, path traversal, platform filenames, policy/backoff, keyring allowlist, session-import filtering, scheduler command generation.
2. Synthetic integration tests: discovery without favorites, nested file downloads, duplicate object IDs, locked/unreleased items, authenticated HTML/error responses and repeat publication. No real account data goes into CI fixtures.
3. Qt smoke tests: empty onboarding, source validation, file-list rendering, and no active idle progress timer. Native binaries run an offline self-test after packaging on each platform.
4. Packaging: macOS arm64 / x86_64, Windows x64, Linux x64. Each CI job tests on its runner before packaging and produces checksums, dependency versions and license files.
5. Real-university and power measurements: release notes must state exactly what was checked. One institution is not universal compatibility. A CI smoke test is not a physical-device installation, credential vault, power draw, two-device sync or cloud-upload test.

No university credentials, cookies, personal data or course PDFs are permitted in Git fixtures or release assets. App-owned version recovery is tested locally; cloud disaster recovery remains the user's chosen provider/backup responsibility. This release has no signing identity, notarization, Authenticode reputation or self-updater claim.


Alpha 2 was additionally checked with a built macOS review bundle and synthetic state: native folder picker selected a temporary destination and the saved rule was verified in the isolated profile; the folder tree expanded to a single file; an independent synthetic active worker was paused, resumed and stopped through the GUI and exited. Light/dark settings were changed live. Read-only discovery against the already configured Stuttgart account returned ten entries (seven courses and three groups); the original six visible rows were not the whole list. No account-bearing page or extracted reference resource is in Git. A successful discovery still does not prove complete file coverage.

## Workflow redesign — local evidence, 27 October 2026

The local macOS arm64 source passed **157 tests**, Ruff and whitespace checks. The synthetic Qt renderer produced
**53 states** across light/dark, German/English, compact windows and enlarged text. This is implementation and rendered
UI evidence, not a usability study or screen-reader certification. A temporary 5,000-file collection on this Mac took
0.31 seconds to construct and first paint, and 0.017 seconds to search (single local measurement, not a platform SLA).
Its idle progress timer remained stopped. No live crawl was started merely to validate the redesign.

| Requested workflow | Direct evidence |
| --- | --- |
| Add a university | Synthetic three-step setup saves a complete profile with a mocked vault |
| Edit without losing configuration | Direct-tab save preserves routing, manual links, enabled state and naming policy |
| Select/manage courses | Retains non-discovered manual targets until explicitly unchecked |
| Choose nested destination | Preview is checked against the same canonical routing function used by sync |
| Inheritance/overrides | Parent propagation, selected override reset, name reset, cancellation and collision rejection |
| Interval scheduling | Existing native-command tests plus settings draft/save/rollback tests |
| Add/edit/remove fixed times | Selection, duplicate prevention, editing, removal and Cancel tested; DST preview checked |
| Search/filter | Shared search, combined predicates, count consistency and refreshed course/type choices |
| Find/open updated material | Recent ordering, actual Enter-to-open dispatch and missing-file recovery |
| Interpret success | Last-attempt and applicable-last-success semantics, configuration scope and neutral legacy state |
| Unavailable material | Warning separate from errors/exclusions; no unverified cause or automatic destructive removal |
| Detailed report | Structured issues/exclusions/activity and bounded 20-attempt history |
| Failure/interruption recovery | No reused old result, preserved archive tests, independent rollback after injected failures |
| Keyboard | Main shortcuts, actual sort-header clicks, table Tab exit and selectable full paths |
| Resize/long content | Compact/enlarged-text renders, control-bound checks and a long unbroken source title |

A native Cocoa accessibility read exposed a Qt crash that the offscreen tests did not catch. The local compatibility
layer has a deterministic native A/B regression: uncorrected placeholder destruction invalidates the table interface;
25 corrected destructions preserve it. See [the bounded workaround](QT-COCOA-COMPAT.md). On 28 October the installed macOS app passed native dialog checks: folder selection/search, inherited file paths,
draft names and ID toggling/reset/Cancel, general settings, daily time add/edit/duplicate prevention/remove/Cancel,
separate topic help, a failed-attempt report, shared search with 1-of-53 count/reset and Enter opening the PDF in Preview.
The previous accessibility-triggered folder-dialog crash did not recur. Settings stayed byte-identical and all 66 files
matched the fresh pre-review hashes. These checks do not establish spoken screen-reader behavior.

The packaged macOS runtime passed its offline self-test and strict code-signature verification. Signing is ad hoc,
not notarization. Windows/Linux native installation and spoken screen-reader behavior have not been verified in this pass.
The existing account configuration and 66 published files were snapshotted locally before installing. After the package
replacement, all 66 files matched their recorded SHA-256 hashes and settings were byte-identical. Native scheduling was generated/tested with fixtures; no example daily
schedule was activated on the real account.

## GitHub quality issues — 28 October 2026

The source passed **174 tests** after the issue work; Ruff and whitespace checks passed. The 53-state renderer was rerun.
Issue #1 now has direct regressions for material-policy scope changes versus cosmetic changes, unknown legacy scope,
scoped last-success claims, changed-scope failure/cancellation and restart, and a failed subtree before any file is
listed. Attempted roots, planned roots and incomplete membership enumeration are separately recorded. Failed attempts
keep this evidence without fabricating publication results. Read-only discovery still preserves previous sync outcomes.
Build metadata binds locally packaged previews to a Git revision and source fingerprint; release Alpha 2 is explicitly
separate in the README. No source was pushed and no release was created.

Issue #3 has loopback-only HTTP/HTTPS integration tests for streamed-body leases, redirects, shared sessions, login,
401, 429/503, Retry-After dates and persistence, retry storms, queued cancellation and full-crawler comparison at limits
1/8. The fixture measured equal request counts, scope, file identities and hashes; see [the measurement record](SYNC_PERFORMANCE.md).
Battery deferral does no crawl, configured sources run sequentially, and existing tests check idle timers/no resident loop.
No power measurement or institutional compatibility claim follows from these tests. An explicit equal-mtime fixture
records the limitation that metadata-based file reuse can retain old bytes when the server changes bytes alone.

The owner deferred tests with other people. Issue #2's student discovery and unseen-change/offline-readiness validation
remain open; no recruitment, diary, participant metrics or offline-residency assurance was performed or invented.

## Final local acceptance — 28 October 2026

The integrated source passed **192 tests**, Ruff and whitespace checks. All 53 synthetic interface states were rendered
again after the final fixes; the help-specific pass additionally reviewed 16 DE/EN/light/dark compact views. Independent
agent probes reproduced and rechecked publication-checkpoint cancellation, a publication write failure, server pause
with fixed times, and the prototype's selected-root symlink boundary. They are engineering checks, not a student study.

Final help includes ten task-oriented topics, escaped paragraphs and a wrapped compact topic list. The report chooses
exclusions when those are the only detailed items, without inventing a required action. Failed/cancelled attempts retain
check scope through publication and final result writes. A fixed-time plan skips calendar triggers inside a server pause
and states the pause separately rather than inventing an execution at the cooldown timestamp.

The issue-2 comparison lives only under `experiments/` and `scripts/prototype_changes.py`, with a temporary fixture ledger.
Seven deterministic tests and six rendered scenarios cover captured checkpoints, equal times/restart/undo, no events
for baseline/route-only/repair/generated content, distinct IDs, and conservative local reads. It is not connected to
production publication or an offline-residency guarantee. The remaining product decision can be made with Nils and
agent walkthroughs; participants/recruitment are not a development prerequisite.

Final installed preview: **`f48d26581507-552975ab651a`**, from clean source revision `f48d265815078b4eb623879c0301fd9dc326316b`.
Its packaged offline self-test and strict ad-hoc signature check passed. The native Help dialog displayed that exact ID;
wrapped topics, separate paragraphs, keyboard topic navigation and cloud/schedule explanations were inspected. The final
Folder mapping dialog opened under native accessibility, and an empty search cleared selection/disabled the stale editor;
Cancel returned to the library. After these checks, settings remained byte-identical to the fresh 28 October snapshot and
all 66 recorded file hashes matched, with no missing files. The preceding app bundle remains a recoverable local backup.
GitHub issues #1/#3 contain the local implementation evidence; #2 records the isolated prototype and owner/agent method.
They stay open for integration/remaining explicit gates. No push, merge or release was performed.

## Material-first library and guided recovery — 29 October 2026

The integrated source passed **231 tests in 13.90 seconds**, including the loopback HTTP integration suite.
Ruff and whitespace checks passed. The renderer covered **87 synthetic interface states**, including 820×560,
980×700 and 1280×800 shared libraries, individual courses, type filters, inline error details, and focused sign-in
renewal in both palettes. At the standard test font, the unchanged library fits at least 5/9/11 complete material
rows at those heights. Expanded reports intentionally use part of that space and remain scrollable.

New regressions cover colliding source/course/object identities, custom destination roots, global course filtering,
pointer and arrow-key navigation in Qt tests, preserved selection through refresh, navigation during work,
enabled-source batching/stop, scope persistence and compact geometry. Recovery tests cover cancelled correction,
required fresh sign-in input, automatic verification after Save, successful versus failed/stale verification, later
failures replacing earlier repair confirmation, warning preservation, a file still missing after a successful crawl,
and keeping the failed file as the action's subject after another row is selected. Exact legacy authentication
messages pause scheduled retry consistently with the UI. Unknown exception text does not establish a cause.

A synthetic 5,000-file/two-university benchmark measured first paint **0.355 s**, search **0.018 s** and course
navigation **0.047 s** (single local run, not a live sync or an energy/participant measurement). Classifying file
icons does not open materials or hydrate cloud placeholders.

Final installed package: **`51b1e3440881-50624687621d`**, built from clean source revision
`51b1e34408811e44179532f740f64d288f05ec44`. Its source fingerprint matches the current implementation; the
packaged and installed offline self-tests and strict ad-hoc signature verification passed. The preceding app bundles
are retained privately under `.local/library-ui-native-20261029/`.

Native inspection in this session's preceding package verified the material-first library with the actual expired
session, the direct Renew sign-in action, focused secure password field, visible step guidance, fresh-input validation,
and Cancel returning to the unchanged library. No credential was entered and no live authenticated check was run.
The Mac locked during the final course-pointer check. Therefore the final build's native course/report walkthrough
remains unobserved; automated Qt pointer/keyboard tests and the installed Cocoa offline self-test passed. No spoken
VoiceOver, native Windows/Linux or additional external participant test is claimed.

The user's current settings (including their daily schedule) remained byte-identical, and SHA-256 comparisons of all
**66 existing archive files** found no missing or modified files after installation and native cancellation. Private
snapshots and the comparison receipt are excluded from Git. No push, merge or release was performed.

## Authentication recovery event correction — 29 October 2026

The live failure was recorded correctly as `Sign in again`/`login_required`, but a translated transient worker message
overrode it with generic Needs attention/Check again. Worker errors now retain typed recovery fields and raw semantic
messages until presentation. A completed current attempt replaces the transient error; an older success cannot replace
a busy/start failure. Regressions exercise DE/EN, legacy and structured events, unrecognized authentication details,
refresh, process completion, and the actual sign-in action. **237 tests passed in 14.03 seconds**, Ruff and whitespace
checks passed, and all 87 synthetic review states rendered with bounded controls.

Installed build **`483a4dc9cb40-0c5aad99c2a2`** passed packaged/installed offline self-tests and strict ad-hoc signature
verification. Native inspection showed the real expired-session result with the larger filled red alert mark, framed
error area and **Anmeldung erneuern** action. The action opened the focused secure-password dialog with **Speichern
und prüfen**. No credential was entered or live sign-in attempted. Current settings and all 66 archive file hashes were
unchanged; the preceding app is retained privately under `.local/auth-action-fix-20261029/`.

## Expired-session prefetch race — 29 October 2026

A one-dashboard check established that the stored password was accepted by the institution. An isolated live
comparison with the same 90-page warm index reproduced a failed dashboard when speculative reads started before
authentication (279 responses, 37 redirects to login, 61 unauthenticated HTML responses). Bootstrapping the dashboard
first succeeded with one authentication and all eight subsequent sample reads accepted. Only structural booleans,
status counts and timings were recorded; no credential, cookie value or response body was exported as evidence.

The adapter now fetches the dashboard before starting prefetch. A regression with an expired session and a warm index
requires one successful authentication and no speculative private request before it. The overlap regression now checks
membership pagination after bootstrap, including retention of files from a removed course. **238 tests passed in
14.83 seconds**, with Ruff and whitespace checks clean.

The full live check in a copied cache/isolated destination completed in 21.76 s, covering 69 files, no errors, two
unavailable items and complete enumeration. Installed build **`9c69fd5bb0b4-1100c340e258`** passed packaged/installed
offline self-tests and strict ad-hoc signature verification. The normal installed-app sync then completed against the
existing archive in 36.19 s: **53 unchanged material files and 3 added material files**, plus 12 unchanged/1 updated
generated course-information files, zero errors and two unavailable downloads. `login_required` is false.

Native inspection showed 56 material files, the completed-with-notes result instead of sign-in recovery, and the next
planned daily check. Actual pointer navigation from a course to the university and inline report expand/collapse worked.
The app was left on the university's materials. Settings remained byte-identical; none of the preceding 66 files went
missing. The one updated generated file retained its prior contents in Versions, verified by SHA-256. Private snapshots,
isolated fixtures, metrics and the preceding app bundle remain excluded from Git under `.local/`.
