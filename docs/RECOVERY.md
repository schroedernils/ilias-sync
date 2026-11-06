# Dateien und Wiederherstellung

## Wenn die Synchronisierung nicht weiterkommt

Die Statuszeile nennt das Problem und die passende nächste Aktion. Vorhandene Materialien bleiben nutzbar,
soweit die Dateien am Speicherort zugänglich sind. **Details** klappt die Schritte und den Bericht im Fenster auf.
In **Alle Materialien** ist die betroffene Hochschule benannt; im Bericht kannst du zwischen Hochschulen wechseln.

| Problem | Nächster Schritt | Woran du die Behebung erkennst |
| --- | --- | --- |
| Anmeldung abgelaufen/abgelehnt | **Anmeldung erneuern**, aktuelles Passwort eingeben oder eine frische `cookies.txt`-Sitzung importieren, **Speichern und prüfen** | Erst der anschließende erfolgreiche Lauf bestätigt **Anmeldung bestätigt**. Andere Downloadhinweise bleiben sichtbar. |
| Verbindung fehlgeschlagen | Internet/VPN und **ILIAS öffnen** prüfen, danach **Erneut prüfen** | Ein neues Ergebnis ersetzt den Fehler; ein weiterer Fehler bleibt mit nächsten Schritten sichtbar. |
| Ordnernamen kollidieren | **Ordnernamen prüfen**, Namen korrigieren/zurücksetzen, **Speichern und prüfen** | Die anschließende Prüfung bestätigt den neuen Zustand. |
| Dateizugriff verweigert / Speicher voll | **Speicherort prüfen**, Zugriffsrechte oder freien Speicher prüfen; bei Bedarf Ziel ändern, **Speichern und prüfen** | Ein neuer erfolgreicher Lauf bestätigt den Zugriff. Die App löscht keine Dateien, um Platz zu schaffen. |
| Datei fehlt lokal | Datei öffnen → **Datei wiederherstellen** | Die App prüft die Hochschule und anschließend auch, ob diese Datei vorhanden ist. Fehlt sie weiter, bleibt der Hinweis bestehen. |
| Serverpause | Angezeigten Termin abwarten, bei Bedarf **ILIAS öffnen** | Automatik setzt zum nächsten zulässigen Termin fort; bei ausgeschalteter Automatik danach selbst prüfen. |
| Einzelner Download nicht verfügbar | In **Details** die betroffene Datei und den bekannten Grund ansehen, Verfügbarkeit/Berechtigung in ILIAS prüfen | Nach wiederhergestelltem Zugriff erneut synchronisieren. Wiederholungen beheben keine fehlende Berechtigung oder entfernte Datei. |

Eine Anmeldung im Browser allein erneuert eine importierte IliasSync-Sitzung nicht. Dafür muss eine neue
Sitzungsdatei importiert werden. Beim normalen Bearbeiten behält ein leeres Passwortfeld das gespeicherte Passwort;
im Ablauf **Anmeldung erneuern** ist eine aktuelle Eingabe nötig. **Abbrechen** übernimmt keine Änderungen.
Eine gespeicherte Korrektur allein ist noch keine bestätigte Behebung. Die App prüft dafür neue Ergebniszeit,
Quellkonfiguration und Ausgang des anschließenden Laufs; frühere erfolgreiche Prüfungen genügen nicht.

Downloads werden in privaten App-Daten zwischengespeichert, geprüft und erst dann
atomar am Ziel veröffentlicht. Abbrüche lassen vollständig gespeicherte Dateien
stehen. Verschwindet ein Objekt in ILIAS, wird die lokale Kopie nicht gelöscht.

Ältere Inhalte liegen unter `Versions/<ursprünglicher Pfad>/<Hash>.<Endung>`.
Zur Wiederherstellung kopierst du die gewünschte Version in einen separaten
Ordner. Versionen sind normale Dateien und werden nicht automatisch bereinigt.
Der Speicherbedarf kann daher wachsen.

Normale Downloads behalten ihren Dateinamen. Liegt dort schon eine nicht zugeordnete
oder lokal bearbeitete Datei, wird die Serverversion separat als `Dateiname (ILIAS).pdf`
abgelegt. Weitere notwendige Kopien heißen beispielsweise `Dateiname (ILIAS 2).pdf`.
Das gilt auch für identische Dateien nach einem vollständigen Onboarding-Reset: Ohne
die frühere Zuordnung darf die App eine vorhandene Datei nicht später überschreiben.
Unterschiedliche ILIAS-Objekte werden nicht allein wegen gleicher Dateinamen oder
gleicher Inhalte zusammengelegt.

Ab 1.0.4 erhalten unveränderte, eindeutig von der App verwaltete Schutzkopien mit dem
alten `[ILIAS …]`-Hashnamen beim nächsten Sync einen lesbaren Namen. Ist der normale
Dateiname frei und nicht anderweitig zugeordnet, wird er verwendet; sonst bleibt der
lesbare Zusatz `(ILIAS)`. Eigene Bearbeitungen und vorhandene Originaldateien bleiben
unangetastet. Ein Wiederherstellungsjournal sichert die Umbenennung bei Unterbrechung ab.

Unter **Hochschule verwalten (…) → Ordner zuordnen** ist **Kurs-IDs im Ordnernamen
anzeigen** standardmäßig ausgeschaltet. Bei gleichnamigen Kursen unterscheiden
lesbare Zusätze wie `(2)` die Ordner; die Zuordnung bleibt für spätere Läufe gespeichert.
Die Option betrifft Kursordner, nicht den Schutz vorhandener Dateien.

Ordnerregeln gelten ab dem nächsten Lauf. Eine spezifische Datei-Zuordnung geht
vor einer Unterordner-Zuordnung, diese vor einer Kurs-Zuordnung. Kopien an alten
Zielen bleiben bei einer Änderung erhalten; das ist keine automatische Migration.

Die Zuordnung zwischen Serverobjekten und lokalen Dateien liegt in einem Manifest
außerhalb des Zielordners. Sichere **App-Daten und Downloadordner zusammen**.
Die App-Daten liegen standardmäßig im benutzerspezifischen
`IliasSync`-Anwendungsdatenverzeichnis des Systems. Ein Passwortspeicher und
Sitzungsexporte gehören nicht in veröffentlichte Fehlerberichte oder ein Git-Repo.

Google Drive, OneDrive und andere Clients können einen Zielordner hochladen.
IliasSync kontrolliert deren Uploadabschluss nicht und hat keine getestete
Cloud-Notfallwiederherstellung. Prüfe einen Wiederherstellungsweg unabhängig von
einem erfolgreichen Downloadlauf.
