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
stehen. Verlinkt ILIAS dieselbe Datei in einem Materialordner und einer Sitzung,
hat der Materialordner Vorrang. Ist ein bereits heruntergeladenes Blatt nach
einer vollständigen Prüfung nicht mehr gelistet, bleibt es an seinem Platz und
erscheint unter Materialien mit dem Hinweis **Lokal behalten**. Das gilt auch
für frühere Blätter in derselben Aufgabensammlung.

Wähle unter **Materialien** eine Datei und öffne **Versionen**. Dort kannst du die
aktuelle Fassung und die von IliasSync gesicherten Fassungen öffnen. Bei älteren
Archivkopien zeigt die App das Speicherdatum. Über **Archivordner öffnen** erreichst
du auch Archivdateien, die sich keiner aktuellen Datei eindeutig zuordnen lassen.
Neue Sicherungen tragen einen Zeitstempel im Dateinamen. Zur Wiederherstellung
kopierst du die gewünschte Fassung aus `Versions/` in einen separaten Ordner.

Normale Downloads behalten ihren Dateinamen. Eine bytegleiche vorhandene Datei
kann die App zum Öffnen verwenden. Ändert sich die Serverfassung später, legt die
App sie als separate Kopie ab und erhält das Original. Das gilt auch nach einem
vollständigen Reset. Unterschiedliche ILIAS-Objekte behalten jeweils ihre eigene
Zuordnung, auch bei gleichen Namen oder Inhalten.

Unveränderte, eindeutig verwaltete Kopien wechseln beim nächsten Sync zurück zum
normalen Dateinamen, sobald dieser frei ist. Ist er belegt, bleibt der Zusatz
`(ILIAS)`. Ein Wiederherstellungsjournal sichert die Umbenennung bei Unterbrechung ab.

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
