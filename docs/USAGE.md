# Nutzung, Kompatibilität und verwandte Projekte

Stand: 27. Oktober 2026. Dies sind Produktinformationen und Quellen zur Einordnung,
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

Der Adapter verwendet **acht PFERD-Arbeitsslots** ohne zusätzliche Wartezeit
zwischen Aufgaben (`tasks=8`, `task_delay=0`). Inhalte innerhalb eines Kurses
werden parallel geprüft; Kurse werden weiterhin nacheinander verarbeitet.
Ein lokaler Inhaltsindex prüft bekannte Seiten bei jedem Lauf frisch mit bis zu
64 parallelen Seitenabrufen. Kurssuche und Verarbeitung laufen dabei überlappend.
Unveränderte Parserergebnisse werden wiederverwendet,
doppelte Abrufe zusammengefasst und bestätigte Objektrouten direkt aufgerufen.
Bei unterstützten Kursübersichten reichen die aktuellen Materialzähler aus,
um bereits leer bestätigte Termine auf neue Materialien zu prüfen. Unbekannte
Termine und unbekannte Darstellungen werden regulär geprüft.
Die Kurssuche, Dateiprüfung und sichere lokale Veröffentlichung bleiben erhalten.
Erste Läufe und neue Ordner benötigen mehr Arbeit als unveränderte Folgeläufe;
Downloads hängen zusätzlich von Größe und Verbindung ab. [Messung](SYNC_PERFORMANCE.md).

Automatische Läufe können stündlich oder in größeren Intervallen sowie zu mehreren
festen täglichen Uhrzeiten stattfinden, standardmäßig alle sechs Stunden.
Im Akkubetrieb werden sie standardmäßig verschoben. Nach Fehlern steigt bei
Intervallplänen der Abstand bis zum nächsten Versuch; feste Uhrzeiten bleiben bestehen.
Der Prozess beendet sich nach
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

## Ordnernamen, Dateiliste und feste Uhrzeiten

Unter **Ordner zuordnen** lassen sich Kurs- und Unterordnernamen bearbeiten. Technische
Kurs-IDs sind standardmäßig ausgeblendet und können dort eingeschaltet werden.
Bei bestehenden verwalteten Ordnern gilt der neue Name ab dem nächsten Sync. Ordner
werden mit ihren lokalen Inhalten umbenannt; bestehende fremde Zielordner werden nicht
zusammengeführt oder überschrieben. Geänderte Zielorte behalten weiterhin ihre bisherigen Kopien.

Die Ordneraktionen stehen rechts neben **Kurse auswählen**. Das Filtersymbol neben
**Datei** blendet Kurs-, Dateityp- und Größenfilter unter der gemeinsamen Suche ein. Klicks auf **Datei**
oder **Größe** wechseln die auf- und absteigende Sortierung; Größen werden numerisch verglichen.

Die Hauptansicht zeigt die Materialien mit Dateinamen und darunter ihrem Kurs-/Ordnerkontext.
Die Suche lässt sich auch mit Cmd+F bzw. Strg+F fokussieren. Doppelklick, Enter oder **Öffnen**
öffnet eine ausgewählte Datei. Im Kontextmenü lässt sich der zugehörige Ordner öffnen.
**Zuletzt geändert** zeigt neu hinzugefügte oder aktualisierte Dateien in zeitlicher Reihenfolge.
Änderungszeiten werden erst ab dieser Version erfasst; bestehende Dateien erhalten keine erfundenen Zeitstempel.
Kursbeschreibungen und Links stehen separat unter **Kursinformationen**, **Alle Dateien** zeigt beides.

Der Status unterscheidet vollständige Prüfungen, nicht verfügbare Downloads, geschützte lokale Änderungen
und Fehler. **Sync-Bericht** erklärt das Ergebnis und ausgeschlossene Inhalte wie Foren und Tests getrennt.
Der Bericht enthält die letzten 20 Versuche und trennt betroffene Dateien, ausgeschlossene Inhalte
und technischen Verlauf in Tabs. Ein unbekannter Grund wird nicht als fehlende Berechtigung ausgegeben.
**Anmeldung prüfen** öffnet bei abgelaufener
Anmeldung direkt den passenden Einrichtungsschritt; **Erneut versuchen** startet einen neuen Lauf.

Unter **Einstellungen → Zeitplan** kann statt eines Intervalls **Zu festen Uhrzeiten**
gewählt werden. Mehrere tägliche Uhrzeiten werden in der lokalen Zeitzone gespeichert.
Computer und Benutzer müssen wie bisher für den Lauf verfügbar sein. Fehlende Anmeldung
und der gewählte Akkuschutz gelten auch für feste Uhrzeiten. Zeitpläne werden erst beim
Speichern der Einstellungen im Betriebssystem eingerichtet.

Ein ausgewählter Zeitpunkt lässt sich ändern oder entfernen; doppelte Uhrzeiten werden verhindert.
Die Vorschau zeigt den nächsten geplanten Termin, keine Ausführungsgarantie bei Schlaf, fehlendem Netz
oder gesperrter Anmeldung. Allgemeine Einstellungen und Zeitplan bleiben bis **Speichern** Entwürfe;
**Abbrechen** verwirft auch eine Vorschau des Erscheinungsbilds. **Hilfe & Info** ist ein eigener Lesedialog.

Die letzte Prüfung gilt für die damaligen Kurse und Speicherziele. Nach einer Änderung dieser Auswahl
fordert die Hauptansicht eine neue Prüfung an. Ein umbenannter Hochschultitel allein macht das Ergebnis
nicht ungültig. Ältere Ergebnisse ohne erfassten Geltungsbereich erhalten keine aktuelle Erfolgsaussage.
Ein fehlgeschlagener Versuch übernimmt niemals die Dateizahlen eines früheren erfolgreichen Laufs.

Im Ordnerdialog zeigt die rechte Seite das wirksame Ziel samt Vererbung für das ausgewählte Element.
**Übergeordnetes Ziel verwenden** entfernt nur dessen eigene Zielregel. **Originalnamen verwenden**
setzt die Namensanpassung zurück. Ein neuer expliziter Zielort bedeutet neue Kopien beim nächsten Sync;
lokale Inhalte am bisherigen Ort bleiben erhalten. Erkannte Namenskollisionen verhindern das Speichern.
Bestehende Hochschulen werden direkt über Tabs bearbeitet; manuelle Kurs-/Ordnerlinks bleiben beim
erneuten Speichern der Kursauswahl erhalten, bis sie ausdrücklich abgewählt werden.

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
