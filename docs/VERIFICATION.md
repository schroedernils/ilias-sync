# Verification boundaries

## Signed app updates — 1.1.0

The [four-platform build](https://github.com/schroedernils/ilias-sync/actions/runs/42478249110)
passed at `55e32a81bc67bfdb6c4ccaf8929f984070764463`. The complete local collection
passed **547 tests with zero skips**. Native CI results were macOS arm64 and Intel
**543 passed / 4 skipped** each, Windows **436 passed / 111 skipped**, and Linux
**540 passed / 7 skipped**. Windows excludes the 98 Linux/POSIX-only updater cases;
the native Windows updater and installer are tested on Windows itself. Optional
SDK and platform-specific checks account for the remaining skips.

Both Mac jobs performed a real Sparkle update in an isolated app: read a signed
feed, download the signed archive, verify it, replace the disposable old host,
then run the installed application's offline self-test. A separate Apple-Silicon
local probe passed the same flow. The test driver deliberately suppresses
relaunch and quits its fixture host to complete Sparkle's install-on-quit path.

Windows exercised the actual WinSparkle DLL, authenticated a downloaded Setup
payload, handed it to the installer and checked the installed executable. Native
Windows and Linux installer/reinstall/uninstall round-trips retained a weekly
schedule and test material. Linux additionally verified the built DEB's size,
SHA-256 and Ed25519 signature. Its graphical package-manager interaction is covered
with controlled Qt handoff tests, not a physical Linux desktop walkthrough.

The production signing key was provisioned with explicit owner authorization;
only its public verification key is committed. [Release 1.1.0](https://github.com/schroedernils/ilias-sync/releases/tag/v1.1.0)
was published by the [verified publication workflow](https://github.com/schroedernils/ilias-sync/actions/runs/42494846943),
after all 24 uploaded packages, signature/checksum sidecars and feeds matched their
local SHA-256 digests. Public latest-feed URLs were fetched without credentials;
both Mac feed signatures, Linux metadata and the official arm64 DMG signature
verified against the embedded public key. Every feed advertises 1.1.0.

The official arm64 DMG passed strict code-signature and packaged-runtime checks
locally, build `55e32a81bc67-a0be4d80c7d1`. German/dark and English/light synthetic
Settings → Updates views were inspected. Replacement of the owner's installed
1.0.4 and the final installed manual-check walkthrough await an unlocked Mac;
these are not claimed by the CI evidence above. No notarization, Authenticode,
universal university compatibility or spoken screen-reader certification follows.

## Readable names and popup sizing — 1.0.4

The report was traced to two independent mechanisms. The rounded Cocoa menu mask
could retain an early, smaller geometry. Popup masks now follow resizing and the
animation leaves Qt's screen-constrained position unchanged. Regression tests add
actions after showing the popup and verify the final action bounds remain in its mask.

Course IDs were already disabled in the reported configuration. The shown PDF name
was an app-owned protection copy beside an untracked existing file, not the course-ID
option. Protection copies now use readable numbered `(ILIAS)` suffixes. Tests retain
untracked identical files and local edits, distinguish remote-object ownership, reuse
publication intents and recover an interrupted legacy-name migration before cleanup.
Same-named course numbers are persisted separately so later course discovery does not
reassign existing directories. Previews remain read-only.

The complete local suite passed **335 tests** in 41 isolated modules, alongside Ruff
and whitespace checks. Release-specific package and native menu evidence follows
when complete. No unattended original-file adoption or duplicate deletion is introduced.
An isolated real Cocoa popup check also covered all four university actions. The
captured menu shows every label in full after final sizing; no account or material
data was used by that check.

The [four-platform 1.0.4 build](https://github.com/schroedernils/ilias-sync/actions/runs/42259119938)
passed at `3856066eded6339e35023f0819588ece30fa93fd`: macOS arm64 and Intel **335 passed**
each, Linux **332 passed / 3 skips**, Windows **326 passed / 9 skips**. Native installer
round-trips also passed. The synthetic UI review rendered **101 states**; an additional
real Cocoa MainWindow check opened the actual management action and captured all four
menu rows inside the final rounded mask.

The native Mac package was installed and passed strict signature verification and its
installed offline self-test, build `3856066eded6-278649ab7a3b`. The reported library's
62 unmodified, app-owned legacy protection copies were migrated under the sync lock
without network downloads. Each new copy's hash was checked, existing plain-name
originals were retained, and private metadata backups plus a migration receipt were kept.
Settings and the app's launchd schedule stayed byte-identical. The app reopened the same
library; the reported PDF now uses a readable `(ILIAS)` suffix.

[Release 1.0.4](https://github.com/schroedernils/ilias-sync/releases/tag/v1.0.4) was published by
the [verified publication workflow](https://github.com/schroedernils/ilias-sync/actions/runs/42260588129).
The installed Mac DMG matches its entry in the published six-package `SHA256SUMS`.

## Schedule retention — 1.0.3

Saved calendar settings already live outside the application bundle and installer payload.
The missing behavior was reconciling the OS registration with that saved policy after a
job was removed or the executable moved. Startup now checks only enabled automation,
leaves matching registrations alone and reinstalls missing/stale jobs without changing
the stored policy. An unchanged Save can also repair registration. Scheduler failures
retain the saved times and expose a recovery action directly to Schedule settings.

The complete local collection passed **322 tests** in 40 isolated modules, with Ruff
and whitespace checks. New regressions cover intervals, daily and weekly calendars,
removed registrations, changed paths, disabled automation, unchanged Save and rollback.
Native installer verification now asserts that an enabled saved weekly calendar stays
byte-identical through install/reinstall/removal. Windows also exercises actual task
creation and two repairs: the second must leave the intact registration alone.
The first Windows installer run exposed console output with an incorrect UTF-16
declaration; the parser now accepts the actual console encoding as well as true UTF-16.
The exported task from an isolated Windows VM was recognized correctly after the fix.
Compact dark/light recovery states were rendered and the direct recovery button checked.

The corrected [four-platform build](https://github.com/schroedernils/ilias-sync/actions/runs/42014094026)
passed at `9c3446a49c2d215a3fe599bf9e8e108905f7353f`: macOS arm64 and Intel
**322 passed** each, Windows **313 passed / 9 skips**, Linux **319 passed / 3 skips**.
Windows and Linux installed-runtime, reinstall and uninstall checks retained the
weekly calendar byte for byte. Windows task repair was also idempotent with the actual
OS scheduler, rather than only mocked XML. The [publishing workflow](https://github.com/schroedernils/ilias-sync/actions/runs/42014960684)
published [1.0.3](https://github.com/schroedernils/ilias-sync/releases/tag/v1.0.3) from that run.

That exact arm64 package was installed on the Mac and passed its installed offline
self-test and strict signature checks, build `9c3446a49c2d-58a470d0e331`. All 114 Mach-O
files contain arm64. Opening the updated app retained the existing weekly calendar and
launchd plist byte for byte; the matching OS registration remained active. The package
hash was checked against the published six-package `SHA256SUMS`. No live sync was
needed for this update check; account data and materials were left in place.

## Apple Silicon and Rosetta — 4 November 2026

The reported macOS 28 warning was traced to an installed **1.0.1 x86_64** app on an
Apple-Silicon Mac. It was replaced with the existing official **1.0.2 arm64** release
package; no new binary release or framework migration was needed. All **114 Mach-O
files** in that bundle contain arm64, with no Intel-only native library or helper.
DMG SHA-256, strict ad-hoc signature checks and the installed offline self-test passed
at build `85a1ebfa5985-ea8fd2bc3549`. The native app reopened the existing library.
Settings and the launchd schedule stayed byte-identical; no live sync was started.

This removes the Rosetta dependency from this installation. It is not a macOS 28
runtime certification. [Apple's announcement](https://developer.apple.com/news/?id=w5ngl9k2)
identifies macOS 27 as the last release with general Rosetta support. Installation
instructions now distinguish M-chip/arm64 from Intel/x64 explicitly.

## Installer and surface corrections — 1.0.2

Windows packaging now builds an Inno Setup installer alongside the portable ZIP. Linux
packaging builds a DEB alongside the portable TAR.GZ. The release gate requires all six
packages from four native targets and verifies every SHA-256 sidecar before publishing.
Windows/Linux CI also installs the actual package, checks the installed offline runtime,
repeats installation, removes the app and checks retention of an isolated data sentinel.
The DEB desktop entry is validated; Windows checks its Start-menu shortcut and uninstall
registration. These checks do not establish real account or credential-vault compatibility.

The UI correction aligns error descriptions immediately beneath the heading, before timing
metadata. Linux/Windows use solid window, dialog and popup surfaces, including the setup
dialog from the reported Windows screenshot. Product screenshots are regenerated from
synthetic materials; the README always selects the dark overview. Earlier Linux guest
checks below apply to the same opaque-surface correction. Release-specific CI and direct
Windows guest evidence are recorded separately when complete.

Local release preparation passed **307 tests** in 39 isolated modules, Ruff and
whitespace checks. The synthetic interface review rendered **101 states**, including
setup, dark/light, compact windows and recovery. The regenerated dark overview,
light setup and error footer were inspected. This is synthetic Qt evidence, not a
Windows desktop or installed-package proof.

Release-specific verification is now complete. The [four-target build](https://github.com/schroedernils/ilias-sync/actions/runs/41874873713)
passed at `85a1ebfa5985d3130757e8c2b6232fdd08120c4c`: macOS arm64 and Intel
**307 passed** each, Windows **298 passed / 9 platform skips**, Linux **304 passed /
3 platform skips**. Both installed-package round-trips passed, including runtime,
repeat install, removal, launcher/registration checks and the retained data sentinel.

The exact Windows setup from that run was also installed for the user in the existing
SwiftVM Windows 11 guest (Arm64 host OS, x64 app emulation). Its SHA-256 matches the
published manifest; installed offline self-test passed at **1.0.2**, build
`85a1ebfa5985-6b71463f5c04`. The main window and the previously broken first-run setup
dialog were inspected directly in both dark and light appearances using isolated
settings. No university login, credential storage or live sync was performed in Windows.
The installed app was then opened normally; the isolated preview processes were closed.

[Release 1.0.2](https://github.com/schroedernils/ilias-sync/releases/tag/v1.0.2) was published by
the [verified publishing workflow](https://github.com/schroedernils/ilias-sync/actions/runs/41876627914).
All six package names, six checksum sidecars and `SHA256SUMS` were checked against
the published release metadata. The public latest-release URL points to `v1.0.2`.
This does not add notarization, Authenticode signing, a self-updater or native ARM
Windows/Linux release packages.

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
