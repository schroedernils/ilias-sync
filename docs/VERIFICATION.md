# Verification boundaries

This preview has separate evidence gates:

1. Unit tests: archives, conflict handling, interruption/retry, path traversal, platform filenames, policy/backoff, keyring allowlist, session-import filtering, scheduler command generation.
2. Synthetic integration tests: discovery without favorites, nested file downloads, duplicate object IDs, locked/unreleased items, authenticated HTML/error responses and repeat publication. No real account data goes into CI fixtures.
3. Qt smoke tests: empty onboarding, source validation, file-list rendering, and no active idle progress timer. Native binaries run an offline self-test after packaging on each platform.
4. Packaging: macOS arm64 / x86_64, Windows x64, Linux x64. Each CI job tests on its runner before packaging and produces checksums, dependency versions and license files.
5. Real-university and power measurements: release notes must state exactly what was checked. One institution is not universal compatibility. A CI smoke test is not a physical-device installation, credential vault, power draw, two-device sync or cloud-upload test.

No university credentials, cookies, personal data or course PDFs are permitted in Git fixtures or release assets. App-owned version recovery is tested locally; cloud disaster recovery remains the user's chosen provider/backup responsibility. This release has no signing identity, notarization, Authenticode reputation or self-updater claim.


Alpha 2 was additionally checked with a built macOS review bundle and synthetic state: native folder picker selected a temporary destination and the saved rule was verified in the isolated profile; the folder tree expanded to a single file; an independent synthetic active worker was paused, resumed and stopped through the GUI and exited. Light/dark settings were changed live. Read-only discovery against the already configured Stuttgart account returned ten entries (seven courses and three groups); the original six visible rows were not the whole list. No account-bearing page or extracted reference resource is in Git. A successful discovery still does not prove complete file coverage.
