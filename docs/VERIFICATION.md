# Verification boundaries

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
