# Pinned Qt Cocoa ownership compatibility

The installed Qt 6.10.0 Cocoa bridge crashed on macOS 27.0.1 while the native accessibility hierarchy
read the selected item in the folder dialog. The stack was `libqcocoa` → AppKit accessibility attribute
access → `AXCopyHierarchy`; ordinary offscreen screenshots had passed. Accessibility remains enabled.

Qt's [current source](https://github.com/qt/qtbase/blob/dev/src/plugins/platforms/cocoa/qcocoaaccessibilityelement.mm)
assigns synthesized row/cell elements their parent's interface ID. Its corrected teardown releases the native
arrays without deleting those Qt-owned interfaces. The pinned 6.10 source still deletes them from native teardown.
The application uses the same ownership correction through a small, locally compiled Objective-C compatibility
library. It overrides only `QMacAccessibilityElement`'s cache cleanup and teardown, preserving native element
release and superclass teardown. No interface role, selected child, screen-reader permission or system setting is disabled.

`native_compat.py` installs it after Cocoa initialization and before constructing windows. It accepts only Qt 6.10.0,
checks the expected runtime methods/ivars, retains the loaded library and fails visibly if initialization is unavailable.
This intentionally requires review when upgrading Qt; remove it after verifying a fixed official runtime. The native
implementation is an interim compatibility measure that depends on private Qt implementation details, not a new general API.

`python scripts/build_qt_compat.py` compiles the library using the installed Xcode command-line tools. `scripts/build.py`
does this automatically before packaging; PyInstaller bundles and signs it with the app. Other platforms skip it. The
Objective-C source is included and the generated native binary is ignored by Git.

The macOS regression test creates a real Qt table interface and destroys 25 native placeholder cells that borrow
its ID. The table interface must remain valid and refer to the same widget after every destruction. This checks the
ownership fault directly; it does not establish spoken VoiceOver behavior or general assistive-technology certification.
