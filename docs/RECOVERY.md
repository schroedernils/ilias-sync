# Dateien und Wiederherstellung

Downloads werden in privaten App-Daten zwischengespeichert, geprüft und erst dann
atomar am Ziel veröffentlicht. Abbrüche lassen vollständig gespeicherte Dateien
stehen. Verschwindet ein Objekt in ILIAS, wird die lokale Kopie nicht gelöscht.

Ältere Inhalte liegen unter `Versions/<ursprünglicher Pfad>/<Hash>.<Endung>`.
Zur Wiederherstellung kopierst du die gewünschte Version in einen separaten
Ordner. Versionen sind normale Dateien und werden nicht automatisch bereinigt.
Der Speicherbedarf kann daher wachsen.

Bei erkannten lokalen Bearbeitungen wird die neue Serverversion separat mit
`[ILIAS …]` im Namen abgelegt. Unterschiedliche ILIAS-Objekte werden nicht allein
wegen gleicher Dateinamen oder gleicher Inhalte zusammengelegt.

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
