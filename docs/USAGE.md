# Nutzung, Kompatibilität und verwandte Projekte

Stand: 22. Oktober 2026. Dies sind Produktinformationen und Quellen zur Einordnung,
keine Zusage, dass eine bestimmte Nutzung rechtlich erlaubt ist.

## Was vor dem ersten Lauf wichtig ist

IliasSync ist ein unabhängiges Projekt und kein offizielles Angebot einer
Hochschule oder des ILIAS-Projekts. Nutze ausschließlich deinen berechtigten
Zugang. Beachte Hochschulregeln, Kurslizenzen und Urheberrechte. Die GPL-Lizenz
der App erteilt keine Nutzungsrechte an Kursmaterialien. Auch eine mögliche
Privatkopie ist keine pauschale Erlaubnis für vollständige Kursarchive,
Weitergabe oder Cloud-Veröffentlichung. Prüfe insbesondere die Freigaben eines
Google-Drive-/OneDrive-Zielordners. [§ 53 UrhG](https://www.gesetze-im-internet.de/urhg/__53.html)
enthält Voraussetzungen und Einschränkungen; daneben können weitere Regeln gelten.

Die App automatisiert weder Beitritte noch Prüfungsabgaben oder das Akzeptieren
von Vereinbarungen und umgeht keine Zugriffssperren. Nicht freigegebene Inhalte
werden nicht als erfolgreiche Downloads gezählt. Beachte Vorgaben des Betreibers
zu automatisierten Zugriffen; pausiere den Lauf bei Problemen oder Rückfragen.

## Serverlast und Energie

Der Adapter verwendet **einen PFERD-Arbeitsslot** und **eine Sekunde Abstand
zwischen Aufgabenstarts** (`tasks=1`, `task_delay=1`). Das ist kein hartes
HTTP-Anfragelimit: Eine Aufgabe kann mehrere Requests auslösen. Es wird kein
Leistungsvorteil durch hundert parallele Downloads versprochen.

Automatische Läufe sind frühestens stündlich möglich, standardmäßig alle sechs
Stunden. Im Akkubetrieb werden sie standardmäßig verschoben. Nach Fehlern steigt
der Abstand bis zum nächsten geplanten Versuch. Der Prozess beendet sich nach
dem Lauf; es gibt keinen ständig aktiven Sync-Daemon. Die geöffnete Oberfläche
fragt Fortschritt nur während eines aktiven Laufs ab. Eine gemessene
Stromverbrauchs- oder universelle Serververträglichkeitsgarantie ist das nicht.

## Betriebssysteme und Grenzen

| System | Paket | Voraussetzung |
| --- | --- | --- |
| macOS 13+ | DMG, Apple Silicon / Intel | Ad-hoc signiert, nicht notarisiert |
| Windows 10/11 | ZIP, x64 | Ganzes Verzeichnis behalten; keine Authenticode-Signatur |
| Linux | tar.gz, x64 | glibc 2.35+, Qt-Systembibliotheken, Secret Service/KWallet; systemd-Benutzersitzung für Zeitpläne |

Python, Qt und PFERD sind in den Paketen enthalten; Java wird nicht benötigt.
Die CI baut und prüft diese Plattformen. Das beweist keine Anmeldung bei jeder
Hochschule. Eigene Themes, Plugins, SSO/MFA und auslaufende Sitzungen können
Anpassungen oder eine neue Anmeldung erfordern. Foren, Tests, SCORM und externe
Dienste sind kein vollständiges Offline-Abbild.

Kurse, Unterordner und einzelne Dateien lassen sich eigenen Zielen zuordnen.
Semesterbezeichnungen werden nicht aus beliebigen Kursnamen erraten. Lokale
Versionen ersetzen keinen vollständigen Backup- und Wiederherstellungstest.
Die App bestätigt keine Cloud-Uploads; dafür ist dein Cloud-Client zuständig.

## Was wir aus anderen Projekten lernen

- [Ilias Downloader Tool](https://iliasdownloadertool.de/) beschreibt lokale
  Dateiablage, individuelle Ordnernamen und Ignorieren sowie den inoffiziellen
  Status und das Risiko übermäßiger Parallelität. Die dort genannte Java-Laufzeit
  ist eine Anforderung dieses Tools, nicht von IliasSync. Eine gelistete Hochschule
  ist kein aktueller Kompatibilitätsnachweis für unsere App.
- [ILIAS-Sync2Folder](https://viperinius.github.io/ILIAS-Sync2Folder/) dokumentiert
  Kursauswahl, Semesterordner, eigene Kursnamen und Aktualisierungen. Es nennt
  ausdrücklich Grenzen bei anderen Hochschulen und Kursnamensmustern. Seine
  Installationsanleitung beschreibt `setup.exe`; daraus folgt keine macOS- oder
  Linux-Unterstützung. [Release v2.1.0.0](https://github.com/Viperinius/ILIAS-Sync2Folder/releases/tag/v2.1.0.0)
  stammt von 2018. Diese Dokumentation ist Kontext, kein aktueller Funktionstest.
- [PFERD](https://github.com/Garmelon/PFERD) ist die tatsächlich eingebundene
  Downloadbibliothek (MIT). Die beiden anderen Projekte dienen nur als Referenz;
  ihr Code oder ihre Grafiken werden nicht eingebunden. Das Downloader Tool weist
  GPL-2.0 aus, Sync2Folder MIT. Deren Lizenzen werden nicht als pauschale
  Haftungsfreistellung oder Erlaubnis zum Download von Kursinhalten übernommen.

Die App selbst steht unter GPL-3.0-or-later. Siehe [Lizenz](../LICENSE),
[Fremdsoftware](../THIRD_PARTY_NOTICES.md) und [Prüfgrenzen](VERIFICATION.md).
