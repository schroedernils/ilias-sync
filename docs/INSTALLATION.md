# Installation und Anmeldung

Lade nur Pakete aus den [Projekt-Releases](https://github.com/schroedernils/ilias-sync/releases)
und prüfe die SHA-256-Prüfsumme. Die Pakete enthalten Python und Qt; eine separate Installation ist nicht nötig.

## macOS

Ab macOS 13, separate Pakete für Apple Silicon und Intel:

- **Mac mit M-Chip:** `macOS-arm64.dmg` enthält die native Apple-Silicon-App. Sie benötigt kein Rosetta.
- **Mac mit Intel-Prozessor:** `macOS-x64.dmg` verwenden.

Deinen Prozessor findest du unter Apple-Menü → **Über diesen Mac**. DMG öffnen,
App nach Programme ziehen. Falls auf einem Mac mit M-Chip eine Intel-Version installiert
war, IliasSync beenden und die App in Programme durch die ARM64-Version ersetzen.
Einstellungen und Materialordner bleiben erhalten; eine erneute Einrichtung ist nicht nötig.

Apple hat das Ende der allgemeinen Rosetta-Unterstützung nach macOS 27 angekündigt.
Die Intel-App wäre auf einem Apple-Silicon-Mac davon betroffen; verwende dort das native
Paket. Das ist keine Vorabzertifizierung für ein noch nicht geprüftes macOS 28.
[Apples Ankündigung](https://developer.apple.com/news/?id=w5ngl9k2)

Das macOS-Paket ist ad-hoc signiert, nicht Developer-ID-signiert oder
notarisiert. macOS kann eine explizite Freigabe unter Systemeinstellungen →
Datenschutz & Sicherheit verlangen. Prüfe Herkunft und Prüfsumme, bevor du einer
App vertraust; deaktivere keine systemweiten Schutzfunktionen.

## Windows

Windows 10/11 x64. **Empfohlen:** `IliasSync-1.1.3-Windows-x64-Setup.exe` öffnen
und dem Installationsassistenten folgen. Die App wird für deinen Benutzer unter
`%LOCALAPPDATA%\Programs\IliasSync` installiert, ohne Administratorrechte.
Danach findest du IliasSync im Startmenü; eine Desktop-Verknüpfung ist optional.
Ein erneuter Installer-Lauf aktualisiert dieselbe Installation.

**Portable Alternative:** ZIP zuerst über **Alle extrahieren** vollständig in
einen dauerhaften Ordner entpacken. `IliasSync.exe` und `_internal` zusammen lassen.
Ein Start direkt aus dem ZIP führt zu „Failed to load Python DLL“, weil Windows
dabei nur die EXE temporär entpackt.

Installer und App haben keine Authenticode-Signatur; Windows kann eine
Reputationswarnung anzeigen. Der Installer beseitigt diese Signaturgrenze nicht.

## Linux

x64, glibc 2.35+, grafische Sitzung. **Ubuntu 22.04+ / kompatible Debian-Systeme:**
DEB über die grafische Paketverwaltung installieren oder im Download-Ordner:

```sh
sudo apt install ./IliasSync-1.1.3-Linux-x64.deb
```

APT installiert die benötigten Systembibliotheken. Die App liegt unter
`/opt/iliassync`; ein Eintrag im App-Menü und der Befehl `ilias-sync` sind enthalten.
Weitere Versionen desselben Pakets aktualisieren die vorhandene Installation.
Auf Debian ist mindestens glibc 2.35 erforderlich, beispielsweise Debian 12+.

**Andere Distributionen / portable Nutzung:** TAR.GZ vollständig entpacken,
`./IliasSync/IliasSync` starten. Beispiel für die benötigten Bibliotheken auf Ubuntu:

```sh
sudo apt install libegl1 libxkbcommon-x11-0 libxcb-cursor0 libdbus-1-3
```

Passwortspeicherung erfordert einen entsperrten Secret-Service- oder
KWallet-Passwortspeicher. Hintergrundläufe benötigen eine systemd-Benutzersitzung.
Beim portablen Archiv erzeugt `install-desktop.sh` optional einen Menüeintrag für
den aktuellen Benutzer. Das entpackte App-Verzeichnis muss danach an seinem Ort
bleiben. Ein DEB ist kein Paket für RPM-basierte Distributionen.

## Aktualisieren und deinstallieren

Ab 1.1.0 gibt es unter **Einstellungen → Updates** automatische Updateprüfungen
nach Zustimmung und eine manuelle Prüfung im App-Menü beziehungsweise unter
**Hilfe**. Auf macOS kann das automatische Laden und Installieren separat
aktiviert werden. Windows verwendet das Setup, Linux nach geprüftem Download
die Paketverwaltung. Details stehen in [App-Updates](UPDATES.md).
Von 1.0.4 oder älter muss die aktuelle Version einmal regulär installiert werden; die bisherigen
Versionen enthalten noch keinen Updater. Die Einrichtung bleibt erhalten.

Beende die App und einen laufenden Sync vor einem Update. Unter Windows den neuen
Installer ausführen, unter Ubuntu/Debian das neue DEB installieren, unter macOS die
App in Programme ersetzen.

- **Windows:** Einstellungen → Apps → Installierte Apps → IliasSync → Deinstallieren.
- **Ubuntu/Debian:** Über die Paketverwaltung entfernen oder `sudo apt remove iliassync`.
- **macOS:** App aus Programme in den Papierkorb verschieben.

Installationsdateien und Menüeinträge werden entfernt. Deine Materialordner,
Einstellungen und Einträge im System-Passwortspeicher bleiben erhalten. Schalte vor
einer dauerhaften Deinstallation die automatische Synchronisierung in der App aus,
damit kein verwaister Zeitplan zurückbleibt. Ab Version 1.0.3 prüft die App beim
nächsten Start einen eingeschalteten Zeitplan und verbindet ihn bei Bedarf mit dem
aktuellen Installationsort. Ein fehlender Systemauftrag wird mit deinen gespeicherten
Uhrzeiten neu angelegt. Eine bewusst ausgeschaltete Automatik bleibt aus.

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
und angemeldet sein. Anwendungsdaten, Wochenplan und Passwörter liegen außerhalb des
App-Verzeichnisses. Ein normales Update oder eine Neuinstallation löscht diese Daten
nicht. Öffne die App nach einem Wechsel des Installationsorts einmal, damit der
Systemauftrag mit dem neuen Pfad verbunden wird. Ist die Aufgabenplanung gerade
nicht verfügbar, führt **Zeitplan prüfen** zu den erhaltenen Einstellungen. Ein erneutes
**Speichern** versucht die Reparatur auch bei unveränderten Uhrzeiten.

Wer auch die Benutzerdaten absichtlich entfernt, entfernt damit den gespeicherten
Zeitplan. Ein vollständiger Onboarding-Reset unterscheidet sich vom Ersetzen der App;
für eine spätere Wiederherstellung müssen die App-Daten gesichert werden.

„Beenden“ beendet den aktuellen Batch, nicht den nächsten geplanten Lauf. Zum
Abschalten des Zeitplans „Automatisch synchronisieren“ in den Einstellungen lösen.
