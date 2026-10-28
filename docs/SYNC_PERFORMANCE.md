# Sync-Laufzeit

Am 27. Oktober 2026 lokal auf einem Apple-Silicon-Mac gegen eine bereits eingerichtete
ILIAS-Installation gemessen. Gleicher Kursbestand, gleiche Ziele, vorhandener Downloadcache.
Das sind Wiederholungsläufe ohne neue Dateidownloads, keine allgemeine Geschwindigkeitszusage.

| Variante | Sekunden |
| --- | ---: |
| Referenz: eine Aufgabe, eine Sekunde Pause nach Aufgaben | 406,74 |
| Vier Aufgaben ohne Pause | 84,38 |
| Acht Aufgaben ohne Pause | 67,54 |
| Inhaltsindex, direkte Objektrouten und aktuelle Materialzähler | 6,12 |

Der letzte Lauf prüfte 89 Inhaltsseiten frisch. 66 bereits leer bestätigte Termine
wurden über die aktuellen Materialzähler der Kursübersichten geprüft. Die gefundenen
Pfade, bekannten Dateien sowie alle Manifest-Prüfsummen und Zielpfade waren gleich
wie im vollständigen Referenzlauf. Ergebnis in allen Varianten: 65 unveränderte
Dateien, zwei nicht verfügbare Einträge, keine Warnungen oder Fehler.

Der Inhaltsindex spart erneutes Parsing und vermeidet doppelte oder unnötig umgeleitete
Abrufe. Er ersetzt keine aktuelle Serverprüfung durch eine Zeitspanne, in der Änderungen
ignoriert werden. Neue Ordner und geänderte Seiten werden regulär verarbeitet.
Erste Läufe, neue Kursbäume, Anmeldung, große Downloads und langsame Server können
länger dauern. Fehlen unterstützte Materialzähler, werden Terminseiten regulär gelesen.

Synthetische Tests decken neue Dateien in unveränderten Unterordnern, Dateiaktualisierung,
Versionsschutz, entfernte Ordner, fehlende lokale Dateien, Sitzungsablauf, begrenzte
Parallelität, Abbruch sowie neue Materialien in zuvor leeren Terminen ab. Private
Messdateien, Kursseiten und Zugangsdaten gehören nicht ins Repository oder in Releases.

Die anschließende Vergleichsserie mit inzwischen 66 Dateien umfasste drei abwechselnde
Läufe derselben vorherigen und überarbeiteten Version. Der Median sank von 7,01 auf
3,53 Sekunden (1,99-fach). Der Prüfumfang blieb bei 91 Requests gleich. Die Überarbeitung
verzahnt Kurssuche, Seitenabrufe und Verarbeitung; 64 statt 32 gleichzeitige Seitenprüfungen
waren schneller, 96 dagegen wieder langsamer. Eine weitere dreifache Beschleunigung wurde
damit nicht nachgewiesen.

## HTTP-Grenzen ab dem lokalen Entwicklungsstand vom 28. Oktober

Die obigen Universitätsmessungen gehören zum damaligen Stand und sind **keine Messung mit der neuen HTTP-Grenze**.
Die 64 vorbereiteten Seitenprüfungen bleiben eine Aufgabenwarteschlange. Tatsächlich gleichzeitig laufende HTTP-Anfragen
sind jetzt über Seiten, Downloads, Anmeldung und Weiterleitungen zusammen auf **acht pro Host** begrenzt. Ein Slot bleibt
bis zum Ende der Antwort oder einem expliziten Schließen belegt; wartende Anfragen lassen sich abbrechen. Die Zählung
erfolgt beim Senden der HTTP-Header, getrennt von Versuchen, und erfasst Statuscodes, Spitzenparallelität und Wartezeit.
Sie enthält Hostnamen, keine Zugangsdaten, Querystrings oder Antwortinhalte. Der technische Sync-Bericht zeigt die Werte.

Acht ist eine vorläufige lokale Obergrenze, keine universell verträgliche Vorgabe einer Hochschule. Sie begrenzt den
bisher unabhängigen 64er-Prefetch auf die schon vorhandene Größenordnung der Arbeitsslots. Für strengere Vorgaben kann
`ILIAS_SYNC_HTTP_LIMIT=1` bis `8` den Grenzwert senken; höhere Werte werden abgelehnt. Geplante Quellen laufen innerhalb
eines Workers nacheinander; der Prozesslock verhindert überlappende Jobs desselben App-Datenordners. Es gibt keine
Aussage über eine sichere Rate vieler verschiedener Installationen.

Bei HTTP 429/503 gilt ein gemeinsamer Host-Aufschub aus `Retry-After` (Sekunden oder HTTP-Datum), sonst ein begrenzter
exponentieller Abstand. GET/HEAD werden höchstens dreimal versucht; POST wird nicht automatisch erneut gesendet.
Drei aufeinanderfolgende Drosselantworten öffnen den Schutzschalter für den Lauf. Lange Aufschübe werden ohne schlafenden
Dauerprozess gespeichert und von neuen Läufen respektiert. Ein manueller Lauf umgeht den Serveraufschub ebenfalls nicht.
Bereits laufende Anfragen können noch enden, bevor andere von der Drosselung erfahren.

Die Regression nutzt ausschließlich einen lokalen HTTPS-Server mit synthetischem Kursbaum: 2 Kurse, 16 Unterordner/Dateien,
erster Download und unveränderter Folgelauf mit Grenzwert 1 beziehungsweise 8. Identitäten, Dateihashes, Prüfumfang und
Fehler müssen gleich sein. Separate lokale Fixtures prüfen Weiterleitungen, gestreamte Antworten, gemeinsame Budgets über
Sessions, 401 und Anmeldung, 429/503, persistentes `Retry-After`, Wiederholungsstürme und Abbruch. Akkuverschiebung und
sequenzielle Quellen sind Worker-Tests; Oberfläche/Start und inaktiver Fortschrittstimer werden getrennt geprüft.

**Metadatengrenze:** PFERDs `always-smart` darf eine vorhandene Datei bei gleichen Zeit-/Größenmetadaten ohne erneuten
Body-Download behalten. Ein frischer Seitenabruf prüft deshalb nicht jedes Remote-Byte. Eine explizite Fixture ersetzt den
Serverinhalt bei gleicher mtime und bestätigt diese Grenze; sie behauptet keine verpasste Änderung an einer echten Hochschule.
Es wurden keine Energie- oder Akkulaufzeitmessungen durchgeführt und keine Energieersparnisse aus Laufzeiten berechnet.

Die am 28.10.2026 ausgeführte lokale Fixture ergab (ein Lauf pro Variante, kein Universitätsbenchmark):

| HTTP-Grenze | Erster Lauf | Unveränderter Lauf | Anfragen erster / Folge | Gemessene Spitze |
| --- | ---: | ---: | ---: | ---: |
| 1 | 0,32 s | 0,16 s | 35 / 19 | 1 |
| 8 | 0,10 s | 0,04 s | 35 / 19 | 8 |

Beide Varianten veröffentlichten dieselben 16 Objekte mit denselben SHA-256-Werten; der Folgelauf meldete jeweils
16 unveränderte Dateien und keine Prüffehler. Vollständige synthetische Ergebnisse: [JSON](benchmarks/http-fixture-20261028.json).
Diese Werte hängen von den künstlichen Verzögerungen des lokalen Servers ab. Eine neue Realserver-Laufzeit mit der
Achtergrenze ist nicht gemessen; die früheren 3,53 Sekunden sind deshalb ausdrücklich keine aktuelle Zusage.
