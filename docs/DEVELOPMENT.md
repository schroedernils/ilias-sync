# Entwicklung

Python 3.12 ist die geprüfte Build-Umgebung; der Quellcode unterstützt außerdem Python 3.13. Betriebssystemabhängige Pakete müssen auf dem Zielsystem gebaut werden.

```sh
python3.12 -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
python -m pip install -e '.[dev]'
pytest
ruff check .
python scripts/build_qt_compat.py  # macOS: Cocoa ownership compatibility; other systems: no-op
python -m ilias_sync
```

`ILIAS_SYNC_DATA_DIR=/absoluter/test/ordner` isoliert Entwicklungsdaten. Verwende
synthetische Kurse und keine echten Zugangsdaten in Tests, Screenshots oder CI.

`python scripts/test.py` führt dieselbe vollständige pytest-Sammlung wie die CI aus,
mit einem frischen Prozess pro Testmodul. Die ausgeführte Fallzahl wird gegen die
Gesamtsammlung geprüft; Qt-Testfenster sammeln sich so nicht zwischen Modulen an.

| Befehl | Verhalten |
| --- | --- |
| `python -m ilias_sync --self-test` | Isolierter Offline-Runtime-Test einschließlich Icon- und Qt-Plugins |
| `python -m ilias_sync --repair-schedule` | Registriert ausschließlich einen bereits eingeschalteten gespeicherten Zeitplan bei Bedarf neu; verändert keine Uhrzeiten |
| `python -m ilias_sync --sync` | Fällige Quellen einmal synchronisieren, danach beenden |
| `python -m ilias_sync --sync --profile <UUID>` | Manueller Lauf; umgeht Fälligkeit und Akkupause |
| `python -m ilias_sync --discover --profile <UUID>` | Beigetretene Kurse lesen |
| `python scripts/build.py` | Natives Paket, Windows-Setup bzw. Linux-DEB mit Lizenztexten und Prüfsummen bauen |
| `python scripts/verify_install.py` | Nur auf isolierten CI-Runnern: Installer, installierte Runtime, erneute Installation und Deinstallation prüfen |
| `python scripts/capture_product.py` | Reproduzierbare Qt-Screenshots mit synthetischen Beispielen |
| `python scripts/review_interface.py` | Helle/dunkle UX-Zustände inklusive Fehler, Pause, Erststart und kompakter Fenster; Ausgabe unter `.local/redesign-review` |

CLI-Ereignisse sind JSON Lines. Die GUI nutzt eine private Ereignisdatei, auch
unter Windows mit dessen windowed Bootloader. Hintergrundläufe importieren kein Qt.

Die CI prüft macOS arm64/Intel, Windows x64 und Linux x64. Die Pakete führen einen
Offline-Test mit ihrer eingefrorenen Runtime aus. Qt bleibt dynamisch geladen und
austauschbar. Siehe [Lizenzhinweise](LICENSES.md), [Architektur](ARCHITECTURE.md)
und [Prüfgrenzen](VERIFICATION.md).

## Release erstellen

Die isolierte macOS-Vorschau öffnet Beispieldaten und verändert weder die installierte
App noch deren Zeitplan. Synchronisierung ist darin durch einen Vorschauhinweis ersetzt:

```sh
.venv/bin/python scripts/capture_product.py --native --preview --language de
```

Aktuelle englische Produktbilder ohne private Desktop-Inhalte entstehen mit
`.venv/bin/python scripts/capture_product.py --native`. Die native Aufnahme prüft
den echten macOS-Compositor; die normale Aufnahme ohne `--native` rendert Qt offscreen.

Die vorbereitete Updater-Integration benötigt einen bewusst eingerichteten
öffentlichen Prüfschlüssel unter `updates/public-key.txt`. Der private Schlüssel
gehört ausschließlich in den freigegebenen Signierprozess, niemals in Quellcode,
Build-Artefakte oder Logs. Paketierung und Veröffentlichung brechen ohne passende
Konfiguration ab. Einrichtung, Freigabestand, signierte Updatefeeds und Prüfgrenzen
stehen in [UPDATES.md](UPDATES.md).

Version in `pyproject.toml` und `src/ilias_sync/__init__.py` gemeinsam erhöhen, Release-Notizen unter `docs/releases/<version>.md` ergänzen und alle Änderungen prüfen. Der Workflow **Test and package** baut auf vier nativen Zielen zwei DMGs, Windows-Setup und ZIP sowie Linux-DEB und TAR.GZ. Windows benötigt Inno Setup 6 (auf dem CI-Image vorhanden), Linux `dpkg-deb` und für die Installationsprüfung `desktop-file-validate`. Erst nach erfolgreichem Abschluss wird **Publish verified release** mit dessen Run-ID gestartet. Der Veröffentlichungsworkflow prüft Quelle, Version, alle vier Jobs und alle sechs Pakete mit ihren Prüfsummen. Kein Paket wird lokal für ein fremdes Betriebssystem vorgetäuscht.
