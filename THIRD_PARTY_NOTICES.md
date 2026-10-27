# Third-party software

IliasSync source: GPL-3.0-or-later. Copyright 2026 Nils Schröder.

The packaged application contains unmodified, dynamically loaded libraries. Packaging collects license texts from each installed distribution into `third-party-licenses/`. That directory is part of each artifact, alongside this document and the full application LICENSE. Do not remove it when redistributing.

- **PFERD 3.9.4** — MIT. Copyright 2019–2024 Garmelon, I-Al-Istannen, danstooamerican, pavelzw, TheChristophe, Scriptim, thelukasprobst, Toorero, Mr-Pine, p-fruck, PinieP, Florian Raith. [Source](https://github.com/Garmelon/PFERD).
- **PySide6 Essentials / Shiboken6 / Qt 6.10** — LGPLv3 / GPLv3 and other component licenses; the included Qt modules are distributed unmodified. [Qt sources](https://download.qt.io/official_releases/qt/6.10/), [PySide sources](https://download.qt.io/official_releases/QtForPython/pyside6/), [licenses](https://doc.qt.io/qt-6/licenses-used-in-qt.html).
- **keyring**, **platformdirs**, **filelock**, **psutil** — see bundled upstream license texts and version manifest.
- **lxml 6.0.2** — BSD and included component licenses; see bundled license texts, including its libxml2/libxslt notices. [Source](https://github.com/lxml/lxml).
- **Lucide icons 0.468.0** — ISC, with upstream Feather/MIT notice where applicable. Selected unmodified SVG paths provide the action icons; color follows the UI palette. The complete supplied license is bundled under `ilias_sync/assets/icons/actions/LICENSE`. [Source](https://github.com/lucide-icons/lucide/tree/0.468.0).
- PFERD's dependencies include aiohttp, beautifulsoup4, certifi, rich and their dependencies. The complete installed runtime version list and detected license files are bundled.

PyInstaller's bootloader is distributed under its upstream license and exception. The application is packaged as a replaceable, directory-based dynamic Qt distribution, not statically linked Qt. Additional terms/attributions from individual included Qt components remain applicable. See `docs/LICENSES.md` for replacement/rebuild instructions.
