# Redistributing and modifying this preview

The application source is GPL-3.0-or-later. Include the complete corresponding source for the precise tag, its LICENSE, build scripts, dependency version list and notices when redistributing application binaries. The private GitHub release is an evaluation distribution; maintain source access for every recipient. A later public release must make the corresponding tagged source publicly obtainable.

PySide/Qt are unmodified dynamically loaded libraries under their respective licenses, including LGPLv3. The on-directory package deliberately retains Qt/PySide shared libraries in `_internal` on Windows/Linux and in the app's Contents/Frameworks/Resources on macOS. Users may modify or replace these libraries for their own use; debugging/reverse engineering for those modifications is not prohibited. Source links and bundled license texts accompany the packages. Nothing in this project limits rights granted by upstream licenses.

To rebuild with modified compatible Qt/PySide libraries: obtain this exact source tag; build/install the desired Qt/PySide version for your OS and architecture in an isolated Python 3.12 environment; install the other pinned dependencies; run the tests; run `python scripts/build.py`. To replace a bundled compatible library directly, work on a copy of the directory distribution and replace its corresponding shared libraries and plugins. macOS integrity signatures may need to be recreated locally after modification (`codesign --force --deep --sign - /path/to/IliasSync.app`). The app is not notarized and does not impose a remote activation check.

The macOS application adds an open-source runtime compatibility library for pinned Qt 6.10.0, without changing upstream
library files. Its source is included under `src/ilias_sync/native/`; see [Cocoa compatibility](QT-COCOA-COMPAT.md).
When substituting another Qt version, review/remove the compatibility call in `native_compat.py` and its version guard,
then run native accessibility tests. The guard prevents accidental use of private method overrides on a different ABI;
the complete source is available to modify or remove it. It is not an activation or redistribution restriction.

Packaging includes the installed distributions' license files under `third-party-licenses`. Keep those notices together with the binaries. The Linux system libraries are supplied by the OS, not statically linked into IliasSync. Additional Qt third-party notices apply to their respective components. Review all bundled notices before further distribution; no proprietary Qt add-on is required by the application.
