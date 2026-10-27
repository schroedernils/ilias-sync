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
