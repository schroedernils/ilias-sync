# Entwicklung

Python 3.12 oder 3.13. Betriebssystemabhängige Pakete müssen auf dem Zielsystem gebaut werden.

```sh
python3.12 -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
python -m pip install -e '.[dev]'
pytest
ruff check .
python -m ilias_sync
```

`ILIAS_SYNC_DATA_DIR=/absoluter/test/ordner` isoliert Entwicklungsdaten. Verwende
synthetische Kurse und keine echten Zugangsdaten in Tests, Screenshots oder CI.

| Befehl | Verhalten |
| --- | --- |
| `python -m ilias_sync --self-test` | Isolierter Offline-Runtime-Test einschließlich Icon- und Qt-Plugins |
| `python -m ilias_sync --sync` | Fällige Quellen einmal synchronisieren, danach beenden |
| `python -m ilias_sync --sync --profile <UUID>` | Manueller Lauf; umgeht Fälligkeit und Akkupause |
| `python -m ilias_sync --discover --profile <UUID>` | Beigetretene Kurse lesen |
| `python scripts/build.py` | Natives Paket mit Lizenztexten und Prüfsumme bauen |
| `python scripts/capture_product.py` | Reproduzierbare Qt-Screenshots mit synthetischen Beispielen |
| `python3 -m http.server 4173 --directory website` | Statische Projektwebsite lokal ansehen |

CLI-Ereignisse sind JSON Lines. Die GUI nutzt eine private Ereignisdatei, auch
unter Windows mit dessen windowed Bootloader. Hintergrundläufe importieren kein Qt.

Die CI prüft macOS arm64/Intel, Windows x64 und Linux x64. Die Pakete führen einen
Offline-Test mit ihrer eingefrorenen Runtime aus. Qt bleibt dynamisch geladen und
austauschbar. Siehe [Lizenzhinweise](LICENSES.md), [Architektur](ARCHITECTURE.md)
und [Prüfgrenzen](VERIFICATION.md).

Die Website hat keine Build-Abhängigkeiten, externen Fonts oder Trackingdienste.
GitHub Pages veröffentlicht ausschließlich `website/`, nicht App-Konfiguration,
REA-Extrakte oder andere Repository-Inhalte. Screenshots bleiben synthetisch.
Die App- und Website-Workflows sind getrennt.
