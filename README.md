<div align="center">
  <img src="docs/images/icon.svg" width="80" height="80" alt="IliasSync">
  <h1>IliasSync</h1>
  <p><strong>Deine ILIAS-Kursdateien. Lokal gespeichert. Automatisch aktuell.</strong></p>
  <p>Für macOS, Windows und Linux. Mit deinen Ordnern und deinem Zeitplan.</p>
</div>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/images/app-dark.png">
  <img src="docs/images/app-light.png" alt="IliasSync zeigt lokal gespeicherte Skripte und Übungsblätter sowie die Auswahl von Kursen und Ordnern.">
</picture>

<p align="center"><sub>Echte App-Oberfläche mit erfundenen Kursen und Dateien.</sub></p>

<p align="center">
  <a href="https://github.com/schroedernils/ilias-sync/releases/tag/v0.1.0-alpha.2">Downloads</a> ·
  <a href="#in-drei-schritten-starten">Einrichtung</a> ·
  <a href="https://github.com/schroedernils/ilias-sync/issues/new/choose">Problem melden</a> ·
  <a href="docs/DEVELOPMENT.md">Entwicklung</a>
</p>

> **Private Alpha:** Das Repository und seine Downloads benötigen derzeit eine GitHub-Freigabe. Die öffentliche Öffnung ist geplant. Diese Vorabversion ist noch nicht an jeder Hochschule geprüft.

## Was IliasSync für dich übernimmt

- **Dateien herunterladen:** Skripte, Folien und Übungsblätter aus deinen ausgewählten ILIAS-Kursen lokal ablegen und Änderungen nachladen.
- **Ordnung behalten:** Eigene Zielordner für ganze Kurse, Unterordner oder einzelne Dateien. Auch ein Google-Drive- oder OneDrive-Ordner ist möglich.
- **Nach Zeitplan arbeiten:** Automatische Läufe über das Betriebssystem, standardmäßig alle sechs Stunden. Im Akkubetrieb pausiert. Zwischen den Läufen bleibt kein Sync-Prozess aktiv.
- **Kontrolle behalten:** Einen Lauf pausieren, fortsetzen oder beenden. Bereits gespeicherte Dateien bleiben erhalten.
- **Lokal bleiben:** Kein zusätzliches IliasSync-Konto und keine App-Telemetrie. Passwörter liegen im Passwortspeicher deines Systems.

Die Oberfläche startet auf Deutsch. Unter **Einstellungen → Allgemein** kannst du zu Englisch wechseln und Hell, Dunkel oder **Wie System** wählen.

## Herunterladen

Alle Pakete stehen im [aktuellen Alpha-Release](https://github.com/schroedernils/ilias-sync/releases/tag/v0.1.0-alpha.2). Prüfe die Datei gegen `SHA256SUMS` im selben Release. Python und Qt sind enthalten; Java wird nicht benötigt.

| System | Paket | Installation |
| --- | --- | --- |
| **macOS 13+** | DMG für Apple Silicon oder Intel | Öffnen, IliasSync nach Programme ziehen und starten. |
| **Windows 10/11 x64** | ZIP | Vollständig in einen festen Ordner entpacken, `IliasSync.exe` starten. `_internal` muss daneben bleiben. |
| **Linux x64** | tar.gz; glibc 2.35+ | Entpacken und `./IliasSync/IliasSync` starten. Optional `install-desktop.sh` für einen Menüeintrag ausführen. |

**Signaturstatus:** macOS ist ad-hoc signiert und nicht notarisiert. Windows hat keine Authenticode-Signatur. Es gibt noch keinen automatischen Updater. Details zu Linux-Bibliotheken, System-Passwortspeichern und Hintergrundläufen: [Installation](docs/INSTALLATION.md).

## In drei Schritten starten

1. **ILIAS hinzufügen:** Die HTTPS-Startadresse deiner Hochschule eintragen und prüfen.
2. **Anmelden:** Hochschulzugang, unterstütztes SSO oder eine eigene Browsersitzung verwenden. Einen festen Zielordner auswählen.
3. **Kurse wählen und synchronisieren:** Alle beigetretenen Kurse oder eine Auswahl. Bei Bedarf den Zeitplan unter **Einstellungen → Allgemein** aktivieren.

Du kannst mehrere ILIAS-Quellen hinzufügen. Fahre links über eine Quelle, um den Stift zum **Bearbeiten** einzublenden, oder nutze Rechtsklick → **Bearbeiten**. Mit der Tastatur geht auch F2. Am Zielpfad stehen **Ordner zuordnen** und **Ordner öffnen** als Symbole mit Tooltips. Das Zahnrad öffnet die Einstellungen.

Bei MFA oder einer eigenen Anmeldeseite kann ein Netscape-`cookies.txt`-Export nötig sein. Die App importiert nur Cookies für den eingestellten ILIAS-Host und liest dein Browserprofil nicht selbst. Eine Sitzung kann ablaufen; dann ist ein neuer Import nötig. Behandle solche Exporte wie ein Passwort. [Mehr zur Anmeldung](docs/INSTALLATION.md#anmeldung).

## Deine Dateien und Ordner

<img src="docs/images/folders.png" width="800" alt="Ordnerzuordnung mit Kursen, Unterordnern und einzelnen Dateien.">

Die spezifischste Ordnerregel gewinnt: eine Dateiregel vor einer Unterordnerregel, eine Unterordnerregel vor einer Kursregel. Neue Ziele gelten ab dem nächsten Lauf; bisherige Kopien bleiben erhalten. Semester und Abkürzungen werden nicht aus beliebigen Kursnamen erraten.

Verschwindet ein Inhalt aus ILIAS, löscht IliasSync deine lokale Kopie nicht automatisch. Ältere Dateiinhalte werden unter `Versions/` aufbewahrt. Bei erkannten lokalen Änderungen bekommt die neue Serverversion einen eigenen Konfliktnamen. [Dateierhalt und Wiederherstellung](docs/RECOVERY.md).

Ein Cloud-Zielordner ist möglich. **Den Upload übernimmt dein Cloud-Client; IliasSync bestätigt ihn nicht.** Sichere App-Daten und Zielordner. Eine Cloud-Synchronisierung allein ist kein geprüfter Wiederherstellungsplan.

## Was du vor der Nutzung wissen solltest

**Kompatibilität:** ILIAS-Versionen, Hochschuldesigns, Plugins und SSO/MFA unterscheiden sich. Eine eigene Adresse ist konfigurierbar, aber nicht jede Installation funktioniert ohne Anpassung. Foren, Tests, Umfragen, SCORM und manche externen Inhalte sind kein vollständiges Offline-Abbild. Übersprungene und nicht verfügbare Inhalte werden im Ergebnis ausgewiesen.

**Serverlast:** Ein PFERD-Arbeitsslot und eine Sekunde Abstand zwischen Aufgabenstarts begrenzen die Parallelität. Das ist kein festes HTTP-Anfragelimit. Automatische Läufe sind frühestens stündlich möglich. Die Vorgaben deiner Hochschule gehen vor.

**Nutzungsrechte:** IliasSync ist unabhängig und kein offizielles Angebot einer Hochschule oder des ILIAS-Projekts. Nutze nur berechtigte Zugänge und beachte Hochschulregeln sowie Rechte an Kursmaterialien, besonders bei Cloud-Ablage und Weitergabe. Die Softwarelizenz erteilt keine Rechte an heruntergeladenen Inhalten.

[Nutzung, Plattformen & Quellen](docs/USAGE.md) · [Was tatsächlich geprüft wurde](docs/VERIFICATION.md) · [Sicherheit](SECURITY.md)

## Feedback und Beiträge

Eine Hochschule funktioniert nicht? [Erstelle einen Fehlerbericht](https://github.com/schroedernils/ilias-sync/issues/new/choose) mit Betriebssystem, App-Version, ILIAS-Version und den Schritten bis zum Fehler. **Keine Passwörter, Cookies, privaten Kursunterlagen oder ungeschwärzten Kontodaten anhängen.**

Beiträge zu Fehlerbehebungen, Übersetzungen und synthetischen Testfällen sind willkommen. Lies zuerst [CONTRIBUTING.md](CONTRIBUTING.md). Technischer Einstieg: [Entwicklung](docs/DEVELOPMENT.md) und [Architektur](docs/ARCHITECTURE.md).

## Lizenz und Grundlage

IliasSync steht unter [GPL-3.0-or-later](LICENSE). Die Downloadbibliothek [PFERD](https://github.com/Garmelon/PFERD) steht unter MIT. Qt und weitere Bibliotheken behalten ihre jeweiligen Lizenzen; [alle Hinweise](THIRD_PARTY_NOTICES.md) liegen auch den Paketen bei.

[Ilias Downloader Tool](https://iliasdownloadertool.de/) und [ILIAS-Sync2Folder](https://viperinius.github.io/ILIAS-Sync2Folder/) dienen als Kontext für Dateiorganisation und Kompatibilitätsgrenzen. Ihr Code und ihre Grafiken werden nicht eingebunden. [Einordnung der Referenzen](docs/USAGE.md#was-wir-aus-anderen-projekten-lernen).
