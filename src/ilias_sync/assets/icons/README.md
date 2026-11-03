# IliasSync identity

Supplied by the project owner in `IliasSync-Icon-Kit`, October 2026. Original
artwork is copied without redesign. Included with the project's GPL-3.0-or-later
distribution. `KIT-README-DE.md` records the supplied formats and provenance.

- macOS application: supplied `macOS/IliasSync-Dark.icns`, including its transparent
  outer margin and all native resolutions. The bundle and Qt runtime share the
  same artwork and stable `org.iliassync.desktop` application identity.
- Windows executable: an ICO container generated from the unmodified original dark
  16/32/64/128/256 PNGs. Runtime/taskbar icons use the same identity.
- Linux: multi-resolution window icon and an optional user-installed desktop
  launcher with the supplied icon. No tray daemon is introduced.
- UI header: supplied alpha-masked PNG, using the supplied dark variant consistently in both palettes.
  Action icons remain action-specific, with translated tooltips/accessibility names.
  They use unmodified Lucide 0.468.0 SVG paths and its bundled ISC/Feather-MIT license.
- Menu-bar template artwork is retained for a future menu-bar UI; the current app
  has no always-running tray process. Don't use a colored app tile as a template.

The kit has no native `.icon` document. Classic ICNS does not define separate
macOS Clear/Tinted/Dark appearances. Icon Composer source layers and asset catalogs
are retained for that future step; no native adaptive-icon claim is made.
