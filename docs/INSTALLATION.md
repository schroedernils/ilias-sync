# Installation und Anmeldung

Lade nur Pakete aus den [Projekt-Releases](https://github.com/schroedernils/ilias-sync/releases)
und prüfe die SHA-256-Prüfsumme. Während der privaten Alpha benötigen auch die
Downloads Repository-Zugriff. Ein fehlender Zugriff kann als GitHub-404 erscheinen.

## macOS

Ab macOS 13, separate Pakete für Apple Silicon und Intel. DMG öffnen, App nach
Programme ziehen. Die Alpha ist ad-hoc signiert, nicht Developer-ID-signiert oder
notarisiert. macOS kann eine explizite Freigabe unter Systemeinstellungen →
Datenschutz & Sicherheit verlangen. Prüfe Herkunft und Prüfsumme, bevor du einer
App vertraust; deaktivere keine systemweiten Schutzfunktionen.

## Windows

Windows 10/11 x64. ZIP vollständig in einen dauerhaften Ordner entpacken.
`IliasSync.exe` und `_internal` zusammen lassen. Die Alpha hat keine
Authenticode-Signatur; Windows kann eine Reputationswarnung anzeigen.

## Linux

x64, glibc 2.35+, grafische Sitzung. Beispiel für Ubuntu:

```sh
sudo apt install libegl1 libxkbcommon-x11-0 libxcb-cursor0 libdbus-1-3
```

Passwortspeicherung erfordert einen entsperrten Secret-Service- oder
KWallet-Passwortspeicher. Hintergrundläufe benötigen eine systemd-Benutzersitzung.
`install-desktop.sh` ist optional und erzeugt einen Menüeintrag für den aktuellen
Benutzer. Das entpackte App-Verzeichnis muss danach an seinem Ort bleiben.

## Anmeldung

Verwende die HTTPS-Startadresse deiner ILIAS-Installation, auch bei einem
Unterverzeichnis wie `https://example.edu/ilias`. „Adresse prüfen“ versucht die
Client-ID zu erkennen. Bei Bedarf steht sie im ILIAS-Anmeldelink als `client_id=…`.

- **Benutzername und Passwort:** Das Passwort liegt im System-Passwortspeicher.
- **Shibboleth SSO:** Den vertrauenswürdigen Identitätsanbieter eintragen. Nicht
  jede hochschulspezifische Weiterleitung ist unterstützt.
- **Browsersitzung (MFA):** In deinem eigenen Browser anmelden, einen
  Netscape-`cookies.txt`-Export erstellen und importieren. Nur zum ILIAS-Host
  passende Cookies werden übernommen. Die App liest dein Browserprofil und
  deinen Browser-Passwortspeicher nicht aus. Zusätzliche Exportkopien nach dem
  Import sicher aufbewahren oder entfernen. Bei abgelaufener Sitzung erneut
  anmelden und importieren. MFA wird dadurch nicht dauerhaft unbeaufsichtigt.

## Zeitplan

Standard: alle sechs Stunden, im Akkubetrieb verschoben. Der Computer muss wach
und angemeldet sein. Verschiebe die App nach der Einrichtung nicht; falls doch,
deaktiviere den Zeitplan und aktiviere ihn vom neuen Installationsort erneut.
Anwendungsdaten und Passwörter liegen außerhalb des App-Verzeichnisses.

„Beenden“ beendet den aktuellen Batch, nicht den nächsten geplanten Lauf. Zum
Abschalten des Zeitplans „Automatisch synchronisieren“ in den Einstellungen lösen.
