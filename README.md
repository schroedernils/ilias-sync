# IliasSync

**Your courses. On your computer.**

A small desktop app that downloads ILIAS course materials into ordinary local folders and keeps them current. Built for macOS, Windows and Linux with Qt and [PFERD](https://github.com/Garmelon/PFERD).

The repository is currently **private** while the first preview is evaluated. The source is licensed under GPL-3.0-or-later for a future open-source release; a private repository is not publicly accessible open source yet. IliasSync is independent of the ILIAS project and universities.

## What it does

- Multiple university / ILIAS installations, each with a separate destination.
- Detect an installation's client ID, sign in, discover joined courses and groups, or select direct course/folder links.
- Standard local ILIAS login, compatible Shibboleth forms with an explicitly trusted identity-provider host, and Netscape browser-session import for MFA/custom SSO.
- Download supported documents, exercise files, course descriptions and links. Videos are opt-in.
- Deduplicate file objects linked from multiple locations. Preserve course/folder names in portable paths.
- Keep prior versions before updates, preserve your local edits in place, and save remote changes as conflict copies.
- Schedule with **launchd**, **Windows Task Scheduler**, or **systemd user timers**. The worker exits after each run; no background browser, resident polling daemon or telemetry.
- Assign whole courses, subfolders or individual files to your own local destination folders. Specific file rules override folder and course rules. New assignments publish safe copies on the next run and retain copies at previous destinations.
- System-following light/dark appearance, three-step setup, and grouped settings. Active runs offer Pause / Resume and Stop. Stop ends the current batch; disable automatic sync separately to remove the schedule.
- Battery deferral, a single network task, request spacing, metadata-based incremental downloads, native timer scheduling and persistent error backoff.

## Download and run

Get the platform archive from [Releases](https://github.com/schroedernils/ilias-sync/releases). Access currently requires repository permission. Verify its SHA-256 against `SHA256SUMS`.

- **macOS 13+**: open the DMG, drag IliasSync to Applications, then launch it. Separate Apple Silicon and Intel builds are provided. This preview is ad-hoc signed, **not Developer ID signed or notarized**. macOS may require an explicit Open action under System Settings → Privacy & Security; only approve a download you trust.
- **Windows 10/11 x64**: extract the whole ZIP to a permanent folder, then run `IliasSync.exe`. Keep `_internal` alongside it. The executable is **not Authenticode signed**; Windows may display a reputation warning.
- **Linux x64, glibc 2.35+**: extract the tarball and run `./IliasSync/IliasSync`. A graphical desktop and Qt's system dependencies are required. On Ubuntu: `sudo apt install libegl1 libxkbcommon-x11-0 libxcb-cursor0 libdbus-1-3`. Password storage needs a working, unlocked Secret Service (e.g. GNOME Keyring) or KWallet. Scheduled runs require a systemd user session.

Do not move the executable after enabling background sync; if you do, disable and re-enable the schedule from the new location. Source data and passwords are kept outside the executable folder.

The interface starts in German. Change it immediately under **Einstellungen → Sprache** (Deutsch / English).

## First sync

1. **Add ILIAS** → enter the installation's root HTTPS address, such as `https://ilias.example.edu` or `https://example.edu/ilias`.
2. **Check address** → verify the client ID. Some institutions require entering it manually; it is commonly present in a login URL as `client_id=…`.
3. Choose a sign-in method and a **dedicated local destination folder**. A folder inside Google Drive / OneDrive / another sync provider is possible; that provider is responsible for the subsequent cloud upload.
4. Choose all joined courses or specific course/folder links. **Sync now**.
5. Enable **Settings → Automatic sync** if desired. Scheduled runs defer on battery by default. Manual runs are always explicit and bypass this deferral.

For MFA/custom login: sign in through your own browser, export a Netscape-format `cookies.txt` for your ILIAS installation, and import it under **Browser session (MFA)**. Treat that export like a password and remove your extra export when finished. IliasSync imports only cookies applicable to the configured host. It does not read your browser profile or password manager. When cookies expire, background attempts stop until you import a fresh session; **a session import cannot make MFA permanently unattended**.

## Files and recovery

Downloads are staged in private application data, checked, then atomically published to your destination. The app never deletes downloaded files because an object disappears from ILIAS. Previous contents go under `Versions/<original path>/<hash>.<extension>`. These are normal files: copy a version to another folder to restore it. Local edits are never intentionally overwritten; remote updates get an `[ILIAS …]` conflict suffix. Different ILIAS objects are not merged just because their bytes or names match.

The app maintains a manifest outside the download folder. Back up both application data and the download destination. Versions are not automatically pruned; storage grows over time. A general-purpose cloud sync folder is **not** independently verified disaster recovery. The app does not confirm cloud upload completion. Network or permission failures retain existing files and are reported as needing attention.

## Compatibility boundary

This is an **early preview**, not a promise that every ILIAS installation works. PFERD supports common ILIAS layouts, but themes, plugins, versions and authentication differ. Standard uploaded files and supported exercise/media objects are the primary scope. Forums, online tests, surveys, SCORM, wikis and some external plugins are intentionally omitted and counted. Not-yet-released material is retained as unavailable, not bypassed. No access restrictions, enrollment, license acceptance, or submissions are automated. A new university can be configured without changing code, but a custom layout may require an adapter fix.

Platform CI tests and packaging are not proof of successful real-university login on every platform. See [verification](docs/VERIFICATION.md), [architecture](docs/ARCHITECTURE.md), [security](SECURITY.md) and [third-party notices](THIRD_PARTY_NOTICES.md).

## Develop

```sh
python3.12 -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
python -m pip install -e '.[dev]'
pytest
ruff check .
python -m ilias_sync
```

Use `ILIAS_SYNC_DATA_DIR=/absolute/test/folder` to isolate development state. No test needs real account credentials. `python -m ilias_sync --self-test` runs an offline runtime check. `--sync` is a headless, due-only one-shot job; `--sync --profile <UUID>` forces a manual run. CLI output is JSON Lines. The GUI uses a private event file, also compatible with Windows' windowed bootloader.

```sh
python scripts/build.py
```

Builds must run natively on their target OS/architecture. GitHub Actions runs tests and builds each release platform. Packages include dependency license notices and `SHA256SUMS`. Qt is dynamically bundled as an on-directory distribution so its libraries remain replaceable; see [license compliance](docs/LICENSES.md).

## Contribute

Report installation URL (without tokens), ILIAS version, OS and the visible error. Please never attach cookies, passwords, personal course material, raw login pages or unredacted application state. Small synthetic fixtures for unsupported HTML structures are especially useful. No automatic updater or telemetry is included in this preview.
