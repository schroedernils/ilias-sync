# Signed release updates

**Implementation status, 8 November 2026:** prepared locally; not published or
enabled in the installed 1.0.4 release. Production key provisioning awaits
explicit authorization. The complete local suite passed **547 tests, zero
skipped**, and an isolated Apple-Silicon package with a disposable test public
key passed its native-runtime self-test and DMG build. This is not a completed
old-to-new installation, native Windows run, or Linux package-manager handoff.

## User flow

- **macOS:** Sparkle asks whether to check automatically, with automatic download
  and installation offered separately. **Settings → Updates** changes those
  choices, and the app menu supports a manual check. Sparkle owns its native
  preferences; starting the app never resets them. System profiling is disabled.
- **Windows:** WinSparkle offers opt-in automatic checks and a native update
  prompt. The signed Setup package updates the existing installation after the
  user accepts. The GUI receives shutdown requests through a queued signal and
  rechecks synchronization before closing. WinSparkle's pre-installer callback
  independently checks the actual sync lock on its worker thread, so a stale GUI
  busy-state poll cannot authorize installing over an already running sync.
- **Linux:** checks require consent, run while the app is open, and authenticate
  the JSON before showing a release. On supported DEB installations, the app
  downloads the package, verifies its size, SHA-256 and Ed25519 signature, then
  offers **Install update**. That explicit action opens the graphical package
  manager. Portable installations and systems without a supported graphical
  installer are directed to the release page. No silent privilege escalation.

Update settings are separate from university passwords, materials and the
synchronization schedule. Native update handling receives the current busy state;
the GUI also rechecks the actual synchronization lock before accepting an update
shutdown. Linux repeats that check at package-manager handoff. An external
installer runs outside the GUI's lifetime; pending an installed integration test,
do not claim a lock is held for the entire external installation.

IliasSync publishes update feeds as assets of the same stable GitHub Release as
the packages. Feed endpoints are fixed; package URLs inside feeds point to a
specific version so that a concurrent new release cannot change the downloaded
package underneath its recorded signature.

| Client | Feed URL | Update package |
| --- | --- | --- |
| Sparkle 2.10.1, Apple Silicon | `https://github.com/schroedernils/ilias-sync/releases/latest/download/macOS-arm64.xml` | `IliasSync-VERSION-macOS-arm64.dmg` |
| Sparkle 2.10.1, Intel Mac | `https://github.com/schroedernils/ilias-sync/releases/latest/download/macOS-x64.xml` | `IliasSync-VERSION-macOS-x64.dmg` |
| WinSparkle 0.9.4, x64 | `https://github.com/schroedernils/ilias-sync/releases/latest/download/windows-x64.xml` | `IliasSync-VERSION-Windows-x64-Setup.exe` |
| Linux x64 | `https://github.com/schroedernils/ilias-sync/releases/latest/download/linux-x64.json` | `IliasSync-VERSION-Linux-x64.deb` |

Linux's detached metadata signature is at
`https://github.com/schroedernils/ilias-sync/releases/latest/download/linux-x64.json.sig`.
All URLs use HTTPS. Installed clients need unauthenticated access to these release
assets; a private repository's release downloads are not a public update service.

## Key contract and pending provisioning

Production key provisioning is **pending**. This implementation does not create
or upload a production key. A human must explicitly authorize uploading private
signing material before provisioning the GitHub secret. Tests use synthetic keys
in temporary directories only. The workflow intentionally fails until both
halves of the production key configuration exist and match.

One Ed25519 key is shared by all update targets:

- `updates/public-key.txt` contains standard base64 encoding of the **32 raw
  public-key bytes**, with an optional trailing newline. Commit this public key
  before building the first updater-enabled release and embed it in each client.
- GitHub Actions secret `UPDATE_SIGNING_KEY` contains standard base64 encoding
  of the **32-byte raw private seed**. This is neither PEM nor a 64-byte expanded
  private key. Store a protected backup outside the repository.
- Sparkle uses the public value as `SUPublicEDKey`; WinSparkle uses it with
  `win_sparkle_set_eddsa_public_key`; Linux must verify against its embedded copy.
  Clients must not download a new trust key from an update feed.

`scripts/update_feeds.py` reads the private seed from the environment only. It
never accepts it on the command line, writes it to disk, or prints it. Malformed,
missing or mismatched keys abort generation; there is no unsigned fallback.
Only the signing step receives the secret. Keep shell tracing and environment
dumps disabled. Losing this seed can prevent existing installations from trusting
future updates; key rotation requires a separately designed client migration.

The build/development environment and Linux verifier require
`cryptography==50.0.2`. The release workflow installs the same pinned signer.

## Signatures and feed formats

Every one of the six packages (both DMGs, Windows Setup and portable ZIP, Linux
DEB and portable tarball) receives a `<package-name>.sig` asset containing a
base64-encoded 64-byte signature plus a newline. Signatures use **pure Ed25519 on
the exact package bytes**, with no prehash. Existing `.sha256` sidecars and the
combined `SHA256SUMS` remain available. SHA-256 checksums alone do not authenticate
a release.

XML uses the namespace
`http://www.andymatuschak.org/xml-namespaces/sparkle`. Each enclosure includes the
version-specific HTTPS URL, byte length and `sparkle:edSignature`; version and
short version are item elements. Release notes are embedded and escaped as both
HTML and XML. The Windows feed offers the Setup installer, not the portable ZIP.
This follows [Sparkle's archive signing and appcast format](https://sparkle-project.org/documentation/publishing/)
and [WinSparkle's compatible EdDSA signing](https://github.com/vslavik/winsparkle/blob/v0.9.4/README.md).

**Both macOS feeds are signed using Sparkle 2.10.1's embedded signed-feed format;
set `SURequireSignedFeed` true.** The original XML bytes (including their final
newline) are signed unchanged. The generator appends this ASCII comment and one
trailing newline, matching `sign_update --disable-signing-warning`:

```xml
<!-- sparkle-signatures:
edSignature: BASE64_SIGNATURE_OF_ORIGINAL_XML_BYTES
length: ORIGINAL_XML_BYTE_LENGTH
-->
```

The comment is outside the signed range. The length is a UTF-8 **byte** count,
not a character count. Tests require byte-for-byte equality with the official
tool and successful `sign_update --verify --ed-key-file` verification when the
downloaded SDK is available on macOS, and require rejection after tampering.
Release notes are embedded in the signed XML; no unsigned remote notes link is
used. macOS items require `13.0.0`; Windows items require `10.0`.

The Windows XML itself remains unsigned; WinSparkle verifies the signed Setup
archive. Package signatures are always required on every platform. A detached
XML signature is not Sparkle's signed-feed format and is not emitted. Feed
signatures do not prevent withholding/replaying old updates; clients must retain
version checks. Update signing also does not provide Apple notarization or
Windows Authenticode signatures.

The Linux JSON has exactly this schema (`VERSION`, digests and signatures are
illustrative placeholders):

```json
{
  "schema": 1,
  "version": "VERSION",
  "platform": "Linux-x64",
  "url": "https://github.com/schroedernils/ilias-sync/releases/download/vVERSION/IliasSync-VERSION-Linux-x64.deb",
  "name": "IliasSync-VERSION-Linux-x64.deb",
  "size": 12345,
  "sha256": "64 lowercase hexadecimal characters",
  "signature": "base64 Ed25519 signature of the DEB bytes",
  "release_url": "https://github.com/schroedernils/ilias-sync/releases/tag/vVERSION"
}
```

`linux-x64.json.sig` authenticates the **exact UTF-8 JSON bytes**, including its
trailing newline. Verify this detached signature before trusting parsed metadata;
do not reserialize JSON before verification. Then validate schema, platform,
version, official HTTPS URL source, expected name, size, SHA-256 and the DEB's
Ed25519 signature before handing the package to the system installer. Reject
older/equal versions and all verification failures. If a newer release becomes
latest between the JSON and signature requests, the pair may mismatch; fail
closed and retry on a later check. Linux's portable archive remains a browser
download, with its package `.sig` available separately.

## Publishing procedure

Dispatch **Publish verified release** with the successful **Test and package**
run ID. The release workflow:

1. Requires a completed successful run from this repository's default branch,
   triggered by `push` or `workflow_dispatch`, and all four existing package jobs.
   Pull-request and fork builds cannot receive the signing secret through this
   publication path. Checks out that run's exact source SHA.
2. Requires a stable `MAJOR.MINOR.PATCH` version, release notes at
   `docs/releases/VERSION.md`, all six expected packages and matching `.sha256`
   sidecars. Unexpected input assets abort publication.
3. Validates the signing seed against the checked-out public key, rechecks every
   package checksum, and generates the feeds and signatures in `release-assets`.
   All keys and package inputs pass before any generated file is written.
4. Creates a **draft** release at the source SHA and uploads all 24 assets:
   six packages, six `.sha256` files, six package `.sig` files, `SHA256SUMS`, three
   XML feeds, Linux JSON and its detached signature.
5. Requires the stable draft's tag/source metadata and complete asset set to
   match. Resolves the draft's numeric ID with `gh release view` (the REST
   by-tag endpoint only promises published releases), then checks every uploaded asset's state, size and
   [GitHub-reported SHA-256 digest](https://docs.github.com/en/rest/releases/assets)
   against its local bytes. A missing digest fails closed as well.
6. Publishes with `gh release edit --draft=false --latest` only after those gates
   succeed. The existing latest release remains available throughout upload.

An upload or verification failure leaves the draft unpublished. Inspect and
repair/remove the draft deliberately before rerunning; the workflow does not
clobber releases or clean up failed drafts automatically. Do not manually publish
an incomplete draft. Use a new version for each public release.

For an offline generation check with an already securely supplied environment
variable and a matching **synthetic test** public key:

```sh
python scripts/update_feeds.py --assets /path/to/test-assets --version 2.3.4 --public-key /path/to/test-public-key.txt --release-notes /path/to/test-notes.md
python -m pytest tests/test_update_feeds.py -q
```

Generation is not evidence of an installed native update. Before the first live
rollout, test an old-to-new signed update on both Mac architectures and Windows,
plus Linux metadata/DEB verification and installer handoff. Run the SDK
interoperability tests with the pinned Sparkle 2.10.1 SDK present; those optional
tests skip on other hosts. Ship `SURequireSignedFeed` true with these signed Mac
feeds and the matching embedded public key.
