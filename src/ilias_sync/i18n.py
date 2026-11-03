"""Small explicit UI catalog; file names and server-provided course names stay intact."""
LANGUAGE = "de"
DE = {
    'Pause this run; continue it later.': 'Unterbricht diesen Lauf. Du kannst ihn später fortsetzen.',
    'Continue the paused sync.': 'Setzt den pausierten Lauf fort.',
    'Checks the courses selected for synchronization.': 'Prüft die zur Synchronisierung ausgewählten Kurse.',
    'Filter files': 'Dateien filtern', 'Filters active': 'Filter aktiv', 'Reset filters': 'Filter zurücksetzen',
    'Search file names…': 'Dateinamen suchen …', 'File name': 'Dateiname', 'Course': 'Kurs', 'File type': 'Dateityp',
    'All courses': 'Alle Kurse', 'All file types': 'Alle Dateitypen', 'No extension': 'Ohne Dateiendung',
    'Any size': 'Alle Größen', 'Up to 1 MB': 'Bis 1 MB', '1–10 MB': '1–10 MB', 'Over 10 MB': 'Über 10 MB',
    '{visible} of {total} files': '{visible} von {total} Dateien', 'Close': 'Schließen',
    'Folder name': 'Ordnername', 'Show course IDs in folder names': 'Kurs-IDs im Ordnernamen anzeigen',
    'Invalid folder naming settings.': 'Ungültige Einstellungen für Ordnernamen.',
    'Use a folder name without path separators or special characters.': 'Verwende einen Ordnernamen ohne Pfadtrenner oder Sonderzeichen.',
    'A folder with this name already exists. Choose another name.': 'Ein Ordner mit diesem Namen existiert bereits. Wähle einen anderen Namen.',
    'At intervals': 'In Zeitabständen', 'At fixed times': 'Zu festen Uhrzeiten', 'Schedule': 'Zeitplan', 'Times': 'Uhrzeiten',
    'Daily sync times': 'Tägliche Sync-Uhrzeiten', 'Sync time': 'Sync-Uhrzeit', 'Add time': 'Hinzufügen', 'Remove': 'Entfernen',
    'Daily, in your local time zone.': 'Täglich, in deiner lokalen Zeitzone.',
    'Add at least one valid time (HH:MM).': 'Füge mindestens eine gültige Uhrzeit hinzu (HH:MM).',
    'Automatic sync: daily at {times}': 'Automatische Synchronisierung: täglich um {times} Uhr',
    "General": "Allgemein", "Info": "Info", "About & usage": "Über die App und Nutzung",
    "Settings": "Einstellungen", "Language": "Sprache", "Save": "Speichern", "Cancel": "Abbrechen",
    "Add ILIAS": "ILIAS hinzufügen", "Edit source": "Bearbeiten", "Choose courses": "Kurse auswählen",
    "Sync now": "Jetzt synchronisieren", "Open folder": "Ordner öffnen", "Details": "Details",
    "Sources": "Quellen", "ILIAS sources": "ILIAS-Quellen", "Downloaded files": "Heruntergeladene Dateien",
    "Synchronization status": "Synchronisierungsstatus", "Activity": "Verlauf", "File": "Datei", "Size": "Größe",
    "Connect ILIAS": "ILIAS verbinden", "Add your university to download course files.": "Füge deine Hochschule hinzu, um Kursdateien herunterzuladen.",
    "Add an ILIAS source": "ILIAS hinzufügen", "Edit ILIAS source": "ILIAS bearbeiten",
    "Name": "Name", "University / campus": "Hochschule / Campus", "ILIAS address": "ILIAS-Adresse",
    "Check address": "Adresse prüfen", "Sign-in": "Anmeldung", "Username & password": "Benutzername und Passwort",
    "Shibboleth SSO": "Shibboleth SSO", "Browser session (MFA)": "Browsersitzung (MFA)",
    "Client ID": "Client-ID", "Detected when checking the address": "Wird beim Prüfen der Adresse erkannt",
    "Username": "Benutzername", "Password": "Passwort", "Leave blank to keep saved password": "Leer lassen, um das gespeicherte Passwort zu behalten",
    "Saved in the system credential vault": "Wird im Passwortspeicher des Systems gesichert",
    "Trusted SSO host": "Vertrauenswürdiger SSO-Server", "Browser session": "Browsersitzung",
    "Choose cookies.txt…": "cookies.txt auswählen …", "Choose…": "Auswählen …", "Download folder": "Zielordner",
    "All joined courses, including new ones": "Alle beigetretenen Kurse, auch neue",
    "Courses": "Kurse", "Course links": "Kurslinks", "One course or folder URL per line": "Eine Kurs- oder Ordneradresse pro Zeile",
    "Download videos": "Videos herunterladen", "Uses more storage and data.": "Benötigt mehr Speicher und Datenvolumen.",
    "Import a cookies.txt export from your browser. When the session expires, import a new export.": "Importiere eine cookies.txt aus deinem Browser. Wenn die Sitzung abläuft, ist ein neuer Import nötig.",
    "Choose a dedicated download folder": "Eigenen Zielordner auswählen", "Import browser session": "Browsersitzung importieren",
    "Cookie files (*.txt);;All files (*)": "Cookie-Dateien (*.txt);;Alle Dateien (*)", "Address checked": "Adresse geprüft",
    "Enter the client ID or use a browser session.": "Client-ID eingeben oder eine Browsersitzung verwenden.",
    "Enter your university username.": "Gib deinen Hochschulbenutzernamen ein.",
    "Enter a password, or choose browser-session sign-in.": "Gib ein Passwort ein oder wähle eine Browsersitzung zur Anmeldung.",
    "Choose a browser session file.": "Wähle eine Datei mit deiner Browsersitzung aus.",
    "The credential vault or folder is unavailable.": "Passwortspeicher oder Zielordner nicht verfügbar. Prüfe den Zugriff.",
    "Select courses": "Kurse auswählen", "Select at least one course or folder, or enable course discovery.": "Wähle mindestens einen Kurs oder aktiviere alle beigetretenen Kurse.",
    "Not synchronized yet": "Noch nicht synchronisiert", "Up to date": "Aktuell", "Checking courses": "Kurse werden geprüft",
    "Completed with warnings": "Mit Hinweisen abgeschlossen", "Sign in again": "Erneut anmelden", "Needs attention": "Aktion erforderlich",
    "{count} files": "{count} Dateien", "{count} unavailable": "{count} nicht verfügbar", "{count} skipped": "{count} übersprungen",
    "{count} warnings": "{count} Hinweise", "{count} errors": "{count} Fehler",
    "The worker could not start.": "Synchronisierung konnte nicht gestartet werden. Starte die App erneut.",
    "Checking ILIAS…": "ILIAS wird geprüft …", "Checking {name}": "Prüfe {name}",
    "Downloading {name}": "Lade {name} herunter", "Saving files…": "Dateien werden gespeichert …",
    "Saving course information…": "Kursinformationen werden gespeichert …",
    "Checking known content pages…": "Bekannte Inhaltsseiten werden geprüft …",
    "Added": "Neu", "Updated": "Aktualisiert", "Unchanged": "Unverändert", "Conflict": "Konflikt",
    "Some items need attention. Existing files were kept.": "Einige Dateien benötigen Aufmerksamkeit. Vorhandene Dateien bleiben erhalten.",
    "The job exceeded its time limit and was stopped. It can be retried safely.": "Zeitlimit erreicht. Starte die Synchronisierung erneut.",
    "Sync is running": "Synchronisierung läuft", "Let the current sync finish before changing settings.": "Warte mit Änderungen, bis die Synchronisierung abgeschlossen ist.",
    "Automatic sync": "Automatisch synchronisieren", "Every {n} hours": "Alle {n} Stunden", "Every hour": "Stündlich",
    "Pause on battery power": "Im Akkubetrieb pausieren", "Automatic sync: off": "Automatische Synchronisierung: aus",
    "Automatic sync: every {n} hours": "Automatische Synchronisierung: alle {n} Stunden", "Automatic sync: hourly": "Automatische Synchronisierung: stündlich",
    "Runs while you are signed in and the computer is awake. Keep the app at its installed location.": "Läuft bei angemeldetem Benutzer, wenn der Computer wach ist. Verschiebe die App nach der Einrichtung nicht.",
    "The OS scheduler could not be updated. On Linux, a systemd user session is required.": "Zeitplan konnte nicht gespeichert werden. Unter Linux wird eine systemd-Benutzersitzung benötigt.",
    "About IliasSync": "Über IliasSync", "A download is running": "Download läuft",
    "Wait for the download to finish before closing. You can minimize this window.": "Warte vor dem Schließen, bis der Download fertig ist. Du kannst das Fenster minimieren.",
    "Another synchronization is already running.": "Eine andere Synchronisierung läuft bereits.",
    "Scheduled run deferred while on battery.": "Automatische Synchronisierung im Akkubetrieb pausiert.",
    "The job could not start. Check configuration and OS permissions.": "Start fehlgeschlagen. Prüfe Einstellungen und Zugriffsrechte.",
    "Sync could not complete. Existing files were retained. Check your connection and try again.": "Synchronisierung unvollständig. Dateien bleiben erhalten. Prüfe die Verbindung und versuche es erneut.",
    "Enter the HTTPS address of your ILIAS installation, without credentials.": "Gib die HTTPS-Adresse deines ILIAS ohne Zugangsdaten ein.",
    "Use the installation address, without a query or fragment.": "Gib die ILIAS-Startadresse ohne Suchparameter oder Sprungmarke ein.",
    "Unsupported sign-in method.": "Diese Anmeldemethode wird nicht unterstützt.", "Give this source a name.": "Gib der Quelle einen Namen.",
    "Choose an absolute destination folder.": "Wähle einen vollständigen Zielordnerpfad aus.",
    "Choose a dedicated download folder outside application data.": "Wähle einen eigenen Zielordner außerhalb der App-Daten.",
    "Detect or enter the ILIAS client ID first.": "Prüfe zuerst die Adresse oder gib die Client-ID ein.",
    "Enter the trusted identity-provider hostname for SSO.": "Gib den vertrauenswürdigen SSO-Server deiner Hochschule ein.",
    "Each source needs its own non-overlapping download folder.": "Jede Quelle benötigt einen eigenen Zielordner, der nicht in einem anderen Zielordner liegt.",
    "No secure credential store is available. On Linux, unlock a Secret Service or KWallet vault.": "Passwortspeicher nicht verfügbar. Entsperre unter Linux Secret Service oder KWallet.",
    "Sign in again. No password is stored for this source.": "Anmeldung fehlt. Hinterlege das Passwort unter Bearbeiten.",
    "Cookie file is unexpectedly large.": "Die Sitzungsdatei ist zu groß. Wähle einen cookies.txt-Export aus.",
    "Invalid cookie format.": "Ungültige Sitzungsdatei. Wähle einen cookies.txt-Export aus.",
    "No unexpired cookies for this ILIAS host were found.": "Keine gültige Sitzung für diese ILIAS-Adresse gefunden. Exportiere die Sitzung erneut.",
    "ILIAS rejected the sign-in. Update the saved credentials or import a browser session.": "Anmeldung abgelehnt. Prüfe deine Zugangsdaten oder importiere eine Browsersitzung.",
    "This university requires an interactive sign-in. Import a fresh browser session.": "Diese Hochschule erfordert eine Anmeldung im Browser. Importiere anschließend die Sitzung.",
    "SSO attempted to send credentials to an unapproved host. Check the identity provider.": "SSO-Server stimmt nicht mit der freigegebenen Adresse überein. Prüfe den Server unter Bearbeiten.",
    "Your browser session has expired. Import a new session to continue.": "Browsersitzung abgelaufen. Importiere unter Bearbeiten eine neue Sitzung.",
    "No standard ILIAS login form found. Use a browser session for this installation.": "Anmeldeformular nicht erkannt. Verwende für dieses ILIAS eine Browsersitzung.",
    "The login form points to another server. Choose SSO or a browser session.": "Die Anmeldung führt zu einem anderen Server. Wähle SSO oder eine Browsersitzung.",
    "This login form is not supported. Import a browser session.": "Anmeldeformular nicht unterstützt. Importiere eine Browsersitzung.",
    "Sign-in redirected outside this ILIAS. Use SSO or a browser session.": "Die Anmeldung verlässt dieses ILIAS. Wähle SSO oder eine Browsersitzung.",
    "Sign-in expired or was rejected by ILIAS.": "Anmeldung abgelaufen oder abgelehnt. Melde dich erneut an.",
    "A selected course belongs to a different ILIAS server.": "Ein ausgewählter Kurs gehört zu einem anderen ILIAS-Server. Prüfe die Kurslinks.",
    "A download returned a login page. Sign in again.": "Download erfordert eine neue Anmeldung. Melde dich erneut an.",
    "Preview. Files and supported videos are downloaded; forums, tests, SCORM and custom plugins may be excluded. No automatic updates or verified publisher signature.": "Vorabversion. Dateien und unterstützte Videos werden heruntergeladen. Foren, Tests, SCORM und eigene Erweiterungen können fehlen. Keine automatischen Updates und keine verifizierte Herausgebersignatur.",
    "No file selected": "Keine Datei ausgewählt", "Back": "Zurück", "Continue": "Weiter",
    "Your university": "Deine Hochschule", "Sign in to ILIAS": "Bei ILIAS anmelden", "Choose your files": "Deine Dateien",
    "Step {step} of 3": "Schritt {step} von 3", "Client ID…": "Client-ID …",
    "Use the start address of your university's ILIAS.": "Verwende die Startadresse des ILIAS deiner Hochschule.",
    "A folder in Google Drive or OneDrive works too.": "Auch ein Ordner in Google Drive oder OneDrive ist möglich.",
    "Appearance": "Darstellung", "Theme": "Erscheinungsbild", "Follow system": "Wie System", "Light": "Hell", "Dark": "Dunkel",
    "Synchronization": "Synchronisierung", "Interval": "Intervall",
    "Automatic runs continue when this window is closed. Your computer must be awake and signed in.": "Automatische Läufe funktionieren auch bei geschlossenem Fenster. Dein Computer muss wach und angemeldet sein.",
    "Pause": "Pausieren", "Resume": "Fortsetzen", "Stop": "Beenden", "Paused": "Pausiert", "Stopped": "Beendet", "Stopping…": "Wird beendet …",

    "Folder mapping": "Ordner zuordnen", "{count} courses and groups": "{count} Kurse und Gruppen",
    "Search courses…": "Kurse suchen …", "Missing a course? Paste its ILIAS link here.": "Kurs fehlt? ILIAS-Link hier einfügen.",
    "Choose destinations for courses, folders or individual files.": "Lege Ziele für Kurse, Unterordner oder einzelne Dateien fest.",
    "Search courses and files…": "Kurse und Dateien suchen …", "Course / content": "Kurs / Inhalt",
    "Course folder assignments": "Ordnerzuordnungen", "Select a course or file.": "Wähle einen Kurs oder eine Datei aus.",
    "Inherit parent destination": "Ziel vom übergeordneten Ordner übernehmen", "Choose folder…": "Ordner wählen …",
    "Reset": "Zurücksetzen", "Inherited": "Übernommen",
    "Changes apply on the next sync. Existing copies at previous destinations are kept.": "Gilt ab der nächsten Synchronisierung. Kopien an bisherigen Zielen bleiben erhalten.",
    "Course contents appear after the first sync.": "Kursinhalte erscheinen nach der ersten Synchronisierung.",
    "Invalid folder rules.": "Ungültige Ordnerzuordnungen.", "Invalid folder rule key.": "Ungültige Ordnerzuordnung.",

}


DE.update({
    'Weekly schedule': 'Wochenplan', 'Weekly sync schedule': 'Sync-Wochenplan', 'Your week': 'Deine Woche',
    'Monday': 'Montag', 'Tuesday': 'Dienstag', 'Wednesday': 'Mittwoch', 'Thursday': 'Donnerstag',
    'Friday': 'Freitag', 'Saturday': 'Samstag', 'Sunday': 'Sonntag', 'No sync': 'Kein Sync',
    'Add times with +. Days without times stay free.': 'Mit + eine Uhrzeit ergänzen. Ohne Uhrzeit bleibt der Tag frei.',
    'Add time on {day}': 'Uhrzeit am {day} hinzufügen', 'Sync time on {day}': 'Sync-Uhrzeit am {day}',
    'Remove time on {day}': 'Uhrzeit am {day} entfernen', 'Copy times': 'Zeiten kopieren', 'Another day': 'Anderer Tag',
    'Apply to Monday–Friday': 'Für Montag bis Freitag übernehmen', 'Apply to all days': 'Für alle Tage übernehmen',
    'Choose valid weekdays and times (HH:MM).': 'Wähle gültige Wochentage und Uhrzeiten (HH:MM).',
    'Add a time to at least one weekday.': 'Füge an mindestens einem Tag eine Uhrzeit hinzu.',
    'Choose one schedule mode.': 'Wähle eine Art der Zeitplanung.',
    'Automatic sync: weekly schedule': 'Automatische Synchronisierung nach Wochenplan',
    'Your plan applies when you save.': 'Erst Speichern übernimmt deinen Plan.',
    'Local time · your Mac must be awake, signed in and online.': 'Lokale Uhrzeit · dein Mac muss wach, angemeldet und online sein.',
    '1 file unavailable': '1 Datei nicht verfügbar', '1 local edit preserved': '1 lokale Änderung geschützt',
    '1 file': '1 Datei',
    'The last sync did not finish': 'Die letzte Synchronisierung wurde unterbrochen',
    'Your local files were kept. Start a new sync to check for updates.': 'Deine lokalen Dateien bleiben erhalten. Starte eine neue Synchronisierung, um nach Updates zu suchen.',
    'Loading your courses': 'Deine Kurse werden geladen',
    'Your existing files stay available during the sync.': 'Deine vorhandenen Dateien bleiben währenddessen verfügbar.',
    'Your universities': 'Deine Hochschulen',
    'Your course materials, ready when you are.': 'Dein Studium. Dein Material.',
    'Connect your university. Choose your courses. We will take it from there.': 'Verbinde dein ILIAS und wähle deine Kurse. Neue Materialien kommen automatisch in deinen Ordner.',
    'Saved in {folder}': 'Gespeichert in {folder}',
    'Library': 'Dein Material', 'Materials': 'Materialien', 'All files': 'Alle Dateien',
    'Recent changes': 'Zuletzt geändert', 'Course information': 'Kursinformationen', 'Library view': 'Ansicht der Dateien',
    'Search materials…': 'Materialien durchsuchen …', 'Search materials': 'Materialien durchsuchen',
    'Clear filters': 'Filter löschen', 'Open file': 'Öffnen', 'Open containing folder': 'Übergeordneten Ordner öffnen',
    'Changed': 'Geändert', 'New': 'Neu', 'No recorded change': 'Keine Änderung erfasst',
    'Separate ILIAS copy': 'Separate ILIAS-Kopie',
    'No matching materials': 'Keine passenden Dateien',
    'Try another search or clear the filters.': 'Versuche einen anderen Suchbegriff oder lösche die Filter.',
    'No recent changes yet': 'Noch keine Änderungen erfasst',
    'New and updated materials will appear here after a sync.': 'Neue und aktualisierte Materialien erscheinen hier nach der Synchronisierung.',
    'No course information yet': 'Noch keine Kursinformationen',
    'Course descriptions and links appear here after a sync.': 'Kursbeschreibungen und Links erscheinen hier nach der Synchronisierung.',
    'Your materials will appear here': 'Hier kommt dein Material hin',
    'Start a sync to download files from your courses.': 'Starte eine Synchronisierung, um Dateien aus deinen Kursen herunterzuladen.',
    'This file path is unavailable. Try synchronizing again.': 'Dieser Dateipfad ist nicht verfügbar. Synchronisiere erneut.',
    'This file is missing locally. Sync again to restore it.': 'Die Datei fehlt lokal. Synchronisiere erneut, um sie wiederherzustellen.',
    'The file could not be opened. Check its default application.': 'Die Datei konnte nicht geöffnet werden. Prüfe die zugeordnete Anwendung.',
    'Sign in to continue': 'Anmeldung erforderlich',
    'Check the saved sign-in details. Your local files are still available.': 'Prüfe deine gespeicherte Anmeldung. Deine lokalen Dateien bleiben verfügbar.',
    'Synchronization incomplete': 'Synchronisierung unvollständig',
    'Some files could not be checked. Your local files were kept. Try again.': 'Einige Dateien konnten nicht geprüft werden. Deine lokalen Dateien bleiben erhalten. Versuche es erneut.',
    'Synchronization stopped': 'Synchronisierung beendet',
    'Completed downloads were kept. You can continue with a new sync.': 'Fertige Downloads bleiben erhalten. Du kannst jederzeit neu synchronisieren.',
    'Ready for your first sync': 'Bereit für die erste Synchronisierung',
    'Choose your courses once. IliasSync keeps their materials available locally.': 'Wähle einmal deine Kurse aus. IliasSync hält ihre Materialien lokal bereit.',
    '{count} files unavailable': '{count} Dateien nicht verfügbar',
    '{count} local edits preserved': '{count} lokale Änderungen geschützt',
    'Some materials need attention': 'Einige Materialien brauchen Aufmerksamkeit',
    'See the report for details. Your local files were kept.': 'Mehr dazu im Bericht. Deine lokalen Dateien bleiben erhalten.',
    '{added} new · {updated} updated': '{added} neu · {updated} aktualisiert',
    'No new materials. {count} files available locally.': 'Keine neuen Materialien. {count} Dateien lokal verfügbar.',
    'Your materials are up to date': 'Dein Material ist aktuell',
    'Sync completed with notes': 'Synchronisiert mit Hinweisen',
    'Today at {time}': 'Heute, {time}', 'Not yet checked': 'Noch nicht geprüft',
    'Last checked: {time}': 'Letzte Prüfung: {time}',
    'View report': 'Bericht ansehen', 'Check sign-in': 'Anmeldung prüfen', 'Try again': 'Erneut versuchen',
    'Synchronizing your materials': 'Materialien werden synchronisiert',
    'Synchronization paused': 'Synchronisierung pausiert', 'Finishing safely…': 'Synchronisierung wird beendet …',
    'Something needs attention': 'Aktion erforderlich', 'Synchronization progress': 'Fortschritt der Synchronisierung',
    'Sync report': 'Sync-Bericht', 'Synchronization result': 'Ergebnis der Synchronisierung',
    'Technical activity': 'Technischer Verlauf', 'Show technical activity': 'Technischen Verlauf anzeigen',
    'No technical activity recorded in this window.': 'In diesem Fenster wurde kein technischer Verlauf erfasst.',
    'What needs attention': 'Was deine Aufmerksamkeit braucht', 'Files': 'Dateien',
    '{count} unchanged': '{count} unverändert', 'Local edits preserved': 'Lokale Änderungen geschützt',
    'Your edited files were kept. A separate ILIAS copy was saved beside them.': 'Deine bearbeiteten Dateien bleiben erhalten. Daneben wurde eine separate ILIAS-Kopie gespeichert.',
    'These downloads were not available for publication in this run. Any existing local copies were kept.': 'Diese Downloads konnten in diesem Lauf nicht übernommen werden. Vorhandene lokale Kopien bleiben erhalten.',
    'Forums': 'Foren', 'Tests': 'Tests', 'Groups you have not joined': 'Gruppen ohne Mitgliedschaft',
    'Videos': 'Videos', 'SCORM modules': 'SCORM-Module',
    'Not downloaded automatically': 'Nicht automatisch heruntergeladen',
    'These are excluded content types or inaccessible groups, not failed file downloads.': 'Dies sind ausgeschlossene Inhaltstypen oder nicht zugängliche Gruppen. Es handelt sich nicht um fehlgeschlagene Datei-Downloads.',
    'Checks requiring attention': 'Prüfungen mit Hinweisen', 'No completed result yet': 'Noch kein abgeschlossenes Ergebnis',
    'Run a sync to see what was downloaded and what needs attention.': 'Nach der Synchronisierung siehst du hier, was übernommen wurde und was Aufmerksamkeit braucht.',
})

DE.update({
 'Add a time for your daily sync.':'Füge eine Uhrzeit für die tägliche Synchronisierung hinzu.',
 'Affected material':'Betroffenes Material','Affected materials':'Betroffene Materialien','Attempt: {time}':'Versuch: {time}',
 'Automatic sync is off':'Automatische Synchronisierung ist ausgeschaltet',
 'Automatic sync waits for sign-in':'Automatische Synchronisierung wartet auf deine Anmeldung',
 'Changes apply when you save. Appearance is previewed until then.':'Änderungen gelten nach dem Speichern. Das Erscheinungsbild wird vorab angezeigt.',
 'Checking course: {course}':'Kurs wird geprüft: {course}',
 'Choose a different destination…':'Anderen Zielordner auswählen …','Collapse all':'Alle einklappen','Expand all':'Alle ausklappen',
 'Content not included':'Nicht übernommene Inhalte','Count':'Anzahl','Course information: {count}':'Kursinformationen: {count}',
 'Custom destination for this item':'Eigener Zielordner für dieses Element',
 'Destination changes create new copies at the next sync. Existing copies are kept. Name changes rename the managed folder and its local contents.':'Neue Zielordner gelten beim nächsten Sync; bisherige Kopien bleiben erhalten. Namen innerhalb der bisherigen Ablage werden samt lokalen Inhalten umbenannt.',
 'Effective destination after the next sync':'Wirksames Ziel beim nächsten Sync','Excluded content':'Ausgeschlossene Inhalte',
 'Excluded types and groups are not failed file downloads.':'Ausgeschlossene Inhalte und Gruppen sind keine fehlgeschlagenen Datei-Downloads.',
 'Help & about':'Hilfe & Über IliasSync','Hide filters':'Filter ausblenden',
 'Last automatic run deferred on battery. Next attempt follows the schedule.':'Letzter automatischer Lauf im Akkubetrieb verschoben. Der nächste Versuch folgt dem Zeitplan.',
 'Last check completed':'Letzte Prüfung abgeschlossen','Last complete check: {time}':'Letzte vollständige Prüfung: {time}',
 'Latest attempt':'Letzter Versuch','Legacy result: file totals may include course information.':'Älteres Ergebnis: Die Dateizahl kann Kursinformationen enthalten.',
 'Material files processed: {count}':'Bearbeitete Materialdateien: {count}',
 'Next check: when the operating system starts the scheduled run':'Nächste Prüfung: beim nächsten Start durch den Systemzeitplan',
 'Next planned check: {time}':'Nächste geplante Prüfung: {time}',
 'No excluded content recorded':'Keine ausgeschlossenen Inhalte erfasst','No file issues recorded':'Keine Dateiprobleme erfasst',
 'No filenames recorded in this older result.':'In diesem älteren Ergebnis sind keine Dateinamen erfasst.',
 'Not confirmed for publication in this run':'In diesem Lauf nicht zur Übernahme bestätigt',
 'Only this file is affected. Its filename stays unchanged.':'Gilt nur für diese Datei. Ihr Dateiname bleibt erhalten.',
 'Organize course folders':'Kursordner organisieren','Remove selected time':'Ausgewählte Zeit entfernen',
 'Schedules use the computer’s local time, including daylight saving changes. The OS decides when missed runs can resume; the computer must be awake, signed in and online.':'Uhrzeiten richten sich nach der lokalen Systemzeit inklusive Sommerzeit. Das Betriebssystem regelt verpasste Läufe. Der Computer muss wach, angemeldet und online sein.',
 'See the outcome above for the status of this attempt.':'Den Status dieses Versuchs findest du oben.',
 'Select a course, folder or file to see where it will be saved.':'Wähle einen Kurs, Ordner oder eine Datei, um das Speicherziel zu sehen.',
 'Server denied access':'Server hat den Zugriff verweigert','Server returned not found':'Server meldet: nicht gefunden',
 'Subfolders follow this destination unless they have their own destination.':'Unterordner verwenden dieses Ziel, sofern für sie kein eigenes Ziel festgelegt ist.',
 'Synchronization history':'Bisherige Synchronisierungen','The destination will be available after the next sync.':'Das Ziel steht nach der nächsten Synchronisierung bereit.',
 'Transfer failed':'Übertragung fehlgeschlagen','University settings':'Hochschule bearbeiten','Update selected time':'Ausgewählte Zeit ändern',
 'Use original name':'Originalnamen verwenden','Use parent destination':'Übergeordnetes Ziel verwenden',
 'Uses the parent destination':'Verwendet das Ziel des übergeordneten Ordners',
 'Uses the university download folder':'Verwendet den Zielordner der Hochschule','What is known':'Bekannter Grund',
 'No new materials. {count} files recorded in the last sync.':'Keine neuen Materialien. {count} Dateien beim letzten Sync erfasst.',
 'Additional saved links':'Weitere gespeicherte Links','Remove checked link':'Markierten Link entfernen',
 'The address changed. Check it again or enter its client ID manually.':'Die Adresse wurde geändert. Prüfe sie erneut oder trage die Client-ID manuell ein.',
 'Address check returned no result. Try again or continue with manual sign-in details.':'Die Adressprüfung hat kein Ergebnis geliefert. Wiederhole sie oder ergänze die Anmeldedaten manuell.',
 'Changing this name changes the custom destination. A new copy will be saved; existing files stay in the previous folder.':'Dieser Name ändert den eigenen Zielordner. Es wird eine neue Kopie angelegt; bisherige Dateien bleiben im alten Ordner.',
 'Restore saved destination':'Gespeichertes Ziel wiederherstellen',
})

DE.update({'Stop this sync': 'Diesen Sync beenden', 'Stops this run. Completed files and the schedule are kept.': 'Beendet nur diesen Lauf. Fertige Dateien und der Zeitplan bleiben erhalten.'})

DE.update({
 'Check the folder names':'Ordnernamen prüfen', 'Check folder names':'Ordnernamen prüfen',
 'No new materials. {count} files recorded in your archive.':'Keine neuen Materialien. {count} Dateien in deiner Ablage erfasst.',
 'The current run has no completed result yet.':'Für den laufenden Sync gibt es noch kein abgeschlossenes Ergebnis.',
})

DE.update({
 'See recent changes':'Änderungen ansehen',
 'Course list could not be loaded. Check your connection or sign-in and try again.':'Kursliste konnte nicht geladen werden. Prüfe Verbindung oder Anmeldung und versuche es erneut.',
 'Sign-in changed. Enter the new password or import a new session before saving.':'Die Anmeldung wurde geändert. Gib das neue Passwort ein oder importiere eine neue Sitzung, bevor du speicherst.',
 'Settings changed since the last check':'Einstellungen seit der letzten Prüfung geändert',
 'Start a sync to check the current courses and destinations.':'Starte eine Synchronisierung, um die aktuellen Kurse und Zielordner zu prüfen.',
 'Credential storage failed. Check the saved sign-in details before syncing again.':'Die Zugangsdaten konnten nicht sicher gespeichert werden. Prüfe die gespeicherte Anmeldung vor dem nächsten Sync.',
 'The previous system schedule could not be restored. Reapply the schedule before relying on automatic sync.':'Der bisherige Systemzeitplan konnte nicht wiederhergestellt werden. Speichere den Zeitplan erneut, bevor du dich auf automatische Läufe verlässt.',
 'The previous settings could not be restored. Check settings and reapply the schedule before relying on automatic sync.':'Die bisherigen Einstellungen konnten nicht wiederhergestellt werden. Prüfe die Einstellungen und speichere den Zeitplan erneut, bevor du dich auf automatische Läufe verlässt.',
 'No per-file counts recorded in this older result.':'In diesem älteren Ergebnis wurden keine einzelnen Dateizahlen erfasst.',
 'This item could not be checked':'Dieser Inhalt konnte nicht geprüft werden',
 'Course list':'Kursliste',
 'No file details recorded':'Keine Dateidetails erfasst',
 'Build: {id}':'Build: {id}',
 'Planned courses':'Vorgesehene Kurse',
 'The course list could not be fully checked.':'Die Kursliste konnte nicht vollständig geprüft werden.',
 'HTTP request measurements':'Messwerte zu HTTP-Anfragen',
 'Server pause until {time}.':'Serverpause bis {time}.',
 'Waiting for the server':'Warten auf den Server',
 'The server asked to retry later. Automatic sync will respect the requested time.':'Der Server bittet um einen späteren Versuch. Der automatische Sync berücksichtigt die angegebene Wartezeit.',
 'Existing settings could not be read. Check access to the application data folder and try again.':'Die bestehenden Einstellungen konnten nicht gelesen werden. Prüfe den Zugriff auf den App-Datenordner und versuche es erneut.',
 'Settings could not be saved. Check available space and folder permissions, then try again. Your changes are still shown.':'Die Einstellungen konnten nicht gespeichert werden. Prüfe freien Speicherplatz und Ordnerrechte und versuche es erneut. Deine Änderungen bleiben im Dialog sichtbar.',
 'No new materials in this run.':'Keine neuen Materialien in diesem Lauf.',
 'Choose a different destination…':'Zielordner ändern …',
 'Update selected time':'Zeit ändern', 'Remove selected time':'Zeit entfernen',
})

DE.update({'Help topics': 'Hilfethemen', 'Project & references': 'Projekt & Quellen'})

DE.update({
 'A new check is needed':'Neue Prüfung erforderlich',
 'This older result has no recorded course and destination scope. Sync once to confirm the current setup.':'Für dieses ältere Ergebnis sind Kursauswahl und Zielordner nicht erfasst. Synchronisiere einmal, um die aktuelle Einrichtung zu bestätigen.',
 'Invalid file content returned':'Dateiinhalt hat die Formatprüfung nicht bestanden',
 'Material files processed: {count}':'In diesem Lauf bestätigt: {count} Materialdateien',
 'Courses included in this check':'In dieser Prüfung enthaltene Kurse',
})

DE.update({
 'This time is already scheduled':'Diese Uhrzeit ist bereits eingeplant', 'Add a daily sync time':'Eine tägliche Sync-Uhrzeit hinzufügen',
 'The previous profile or sign-in could not be fully restored. Check university settings and sign-in before syncing again.':'Die bisherigen Hochschul- oder Anmeldedaten konnten nicht vollständig wiederhergestellt werden. Prüfe beides vor dem nächsten Sync.',
})

DE.update({'Change time':'Zeit ändern','Remove time':'Zeit entfernen'})

DE.update({
    'All materials': 'Alle Materialien', 'Library navigation': 'Bibliotheksnavigation',
    'Choose sync courses…': 'Sync-Kurse auswählen …', 'Show course': 'Kurs anzeigen',
    'All course materials': 'Alle Kursmaterialien', 'Across {count} universities': 'Aus {count} Hochschulen',
    'From one university': 'Aus einer Hochschule',
    'Search in this course…': 'Diesen Kurs durchsuchen …', 'Search this university…': 'Diese Hochschule durchsuchen …',
    'Search all universities…': 'Alle Hochschulen durchsuchen …',
    'University actions': 'Hochschule verwalten', 'University report': 'Bericht der Hochschule',
    'Hide sidebar': 'Seitenleiste ausblenden', 'Show sidebar': 'Seitenleiste einblenden', 'View': 'Ansicht',
    'Show synchronization details': 'Synchronisierungsdetails einblenden',
    'Hide synchronization details': 'Synchronisierungsdetails ausblenden', 'Hide details': 'Details ausblenden',
    'Sync all': 'Alle synchronisieren',
    'Checks all configured courses at this university; browsing a course does not change the sync selection.':
        'Prüft alle eingerichteten Kurse dieser Hochschule. Der angezeigte Kurs verändert die Sync-Auswahl nicht.',
    'Checks all enabled universities one after another.': 'Prüft alle aktivierten Hochschulen nacheinander.',
    'Universities need attention': 'Hochschulen benötigen Aufmerksamkeit',
    'Checks completed with notes': 'Prüfungen mit Hinweisen', 'Not all universities checked': 'Noch nicht alle Hochschulen geprüft',
    'University checks completed': 'Hochschulprüfungen abgeschlossen',
    'Each university has its own last check. Expand the details to see individual results.':
        'Jede Hochschule hat einen eigenen Prüfstand. Die einzelnen Ergebnisse stehen in den Details.',
    'Automatic checks follow each university’s schedule': 'Automatische Prüfungen gemäß Hochschulstatus · Details einblenden',
    'Materials synchronized': 'Materialien synchronisiert',
})


DE.update({
    'Renew sign-in': 'Anmeldung erneuern', 'Save and check': 'Speichern und prüfen',
    'Current university password': 'Aktuelles Hochschulpasswort',
    'The file was kept. Open its folder to choose another application.': 'Die Datei bleibt erhalten. Öffne ihren Ordner, um eine andere Anwendung auszuwählen.',
    'Sign-in confirmed': 'Anmeldung bestätigt', 'Check successful again': 'Prüfung wieder erfolgreich',
    'New check not confirmed': 'Erneute Prüfung nicht bestätigt',
    'Check again': 'Erneut prüfen', 'Check storage location': 'Speicherort prüfen',
    'Open ILIAS': 'ILIAS öffnen', 'Open ILIAS in browser': 'ILIAS im Browser öffnen',
    'Steps to recover': 'Schritte zur Behebung', 'Restore file': 'Datei wiederherstellen',
    'The problem is not resolved yet.': 'Das Problem ist noch nicht behoben.',
    'The new check completed. You can continue using your materials.': 'Die erneute Prüfung ist abgeschlossen. Du kannst deine Materialien weiter nutzen.',
    'ILIAS needs a new sign-in. Existing materials remain in your library; new downloads are waiting.':
        'ILIAS benötigt eine neue Anmeldung. Vorhandene Materialien bleiben in deiner Bibliothek; neue Downloads warten.',
    '1. Update the password or import a fresh browser session.': '1. Aktualisiere dein Passwort oder importiere eine neue Browsersitzung.',
    '2. Save and check. IliasSync tests the sign-in by checking this university.':
        '2. Speichern und prüfen: IliasSync prüft die Hochschule mit der neuen Anmeldung.',
    '3. The new result confirms whether syncing works again.': '3. Das neue Ergebnis zeigt, ob die Synchronisierung wieder funktioniert.',
    'Sign in to ILIAS in your browser, export a fresh cookies.txt session with your browser tool, then choose that file here. Signing in in the browser alone does not renew IliasSync’s session.':
        'Melde dich im Browser bei ILIAS an. Exportiere mit deinem Browserwerkzeug eine neue cookies.txt-Sitzung und wähle sie hier aus. Eine Anmeldung im Browser allein erneuert die Sitzung in IliasSync nicht.',
    'Enter the current university password. Save and check starts a new check to confirm the sign-in. If your university requires MFA, use Browser session instead.':
        'Gib dein aktuelles Hochschulpasswort ein. „Speichern und prüfen“ startet eine erneute Prüfung der Anmeldung. Falls deine Hochschule MFA erfordert, verwende eine Browsersitzung.',
    'Choose a fresh browser session file before checking again.': 'Wähle vor der erneuten Prüfung eine neue Datei mit deiner Browsersitzung aus.',
    'Enter the current password before checking again.': 'Gib vor der erneuten Prüfung dein aktuelles Passwort ein.',
    'Two folders would use the same name. Your existing files have been kept.':
        'Zwei Ordner würden denselben Namen verwenden. Deine vorhandenen Dateien bleiben erhalten.',
    '1. Choose another folder name or reset its custom name.': '1. Wähle einen anderen Ordnernamen oder setze den eigenen Namen zurück.',
    '2. Save the mapping, then IliasSync checks the university again.': '2. Speichere die Zuordnung. IliasSync prüft die Hochschule anschließend erneut.',
    'ILIAS asked for a pause. Retrying immediately would not fix it. Your materials remain accessible.':
        'ILIAS hat eine Pause angefordert. Sofortige Wiederholungen helfen hier nicht. Deine vorhandenen Materialien bleiben zugänglich.',
    '1. Wait until the server pause ends; the planned time is shown above.': '1. Warte das Ende der Serverpause ab. Die geplante Zeit steht im Status.',
    '2. Automatic checks resume at the next eligible scheduled time. With automation off, start a check yourself afterwards.':
        '2. Automatische Prüfungen gehen zum nächsten zulässigen Termin weiter. Ist die Automatik ausgeschaltet, starte danach selbst eine Prüfung.',
    'The device reported insufficient storage space.': 'Das Gerät hat zu wenig freien Speicher gemeldet.',
    'The device denied file access.': 'Das Gerät hat einen Dateizugriff verweigert.',
    '1. Free some storage space; IliasSync will not delete your files.': '1. Schaffe freien Speicher. IliasSync löscht dafür keine deiner Dateien.',
    '1. Check access to the download folder and IliasSync application data.': '1. Prüfe den Zugriff auf den Zielordner und die App-Daten von IliasSync.',
    '2. Review the download location if needed, then save and check again.': '2. Prüfe bei Bedarf den Zielordner. Speichere und starte eine erneute Prüfung.',
    'The connection could not be completed. Previously downloaded materials remain accessible.':
        'Die Verbindung konnte nicht hergestellt werden. Bereits heruntergeladene Materialien bleiben zugänglich.',
    'The check could not finish. The exact cause is not confirmed; existing materials have been kept.':
        'Die Prüfung konnte nicht abgeschlossen werden. Die genaue Ursache steht noch nicht fest; vorhandene Materialien bleiben erhalten.',
    '1. Check your internet or VPN connection and whether ILIAS opens in the browser.': '1. Prüfe deine Internet- oder VPN-Verbindung und ob sich ILIAS im Browser öffnen lässt.',
    '1. Check the recorded message and whether ILIAS opens in the browser.': '1. Prüfe die aufgezeichnete Meldung und ob sich ILIAS im Browser öffnen lässt.',
    '2. Check again. If it still fails, keep using your files and review the new result below.':
        '2. Prüfe erneut. Falls es weiter fehlschlägt, kannst du deine Dateien nutzen und unten das neue Ergebnis prüfen.',
    'Some downloads were unavailable. The rest of your materials can still be used.':
        'Einige Downloads waren nicht verfügbar. Deine übrigen Materialien kannst du weiter nutzen.',
    '1. Select an affected file below to see its path and the known reason.': '1. Wähle unten eine betroffene Datei aus, um ihren Pfad und den bekannten Grund zu sehen.',
    '2. Check its availability in ILIAS. A removed file or missing permission cannot be repaired by repeated syncing.':
        '2. Prüfe die Verfügbarkeit in ILIAS. Eine entfernte Datei oder fehlende Berechtigung lässt sich durch wiederholtes Synchronisieren nicht beheben.',
    '3. When access is restored, check the university again.': '3. Sobald der Zugriff wieder möglich ist, prüfe die Hochschule erneut.',
    'This file is missing from its recorded location. Other materials remain available.':
        'Diese Datei fehlt am erfassten Speicherort. Andere Materialien bleiben verfügbar.',
    '1. Check this university to download missing materials again.': '1. Prüfe diese Hochschule, um fehlende Materialien erneut herunterzuladen.',
    '2. If the file stays missing, check whether it is still available to you in ILIAS. Existing files are never deleted by this repair.':
        '2. Falls die Datei weiter fehlt, prüfe ihren Zugriff in ILIAS. Vorhandene Dateien werden bei dieser Wiederherstellung nicht gelöscht.',
    'Checks this university and downloads missing materials again. Existing files are kept.':
        'Prüft diese Hochschule und lädt fehlende Materialien erneut herunter. Vorhandene Dateien bleiben erhalten.',
    'The file is still missing. Check whether it is available in ILIAS before trying again.':
        'Die Datei fehlt weiterhin. Prüfe vor einer Wiederholung, ob sie in ILIAS verfügbar ist.',
})


DE.update({
    'Overview': 'Übersicht', 'Notifications': 'Benachrichtigungen', 'Workspace view': 'Ansicht',
    'Test notification': 'Testmitteilung',
    'macOS notification access is unavailable. In-app notices remain available.':
        'Der Zugriff auf macOS-Mitteilungen ist nicht verfügbar. Die Meldungen in der App bleiben verfügbar.',
    'macOS has denied notifications. Enable IliasSync in System Settings → Notifications.':
        'macOS hat Mitteilungen abgelehnt. Aktiviere IliasSync in Systemeinstellungen → Mitteilungen.',
    'Enable notifications above and allow IliasSync in macOS first.': 'Aktiviere oben die Mitteilungen und erlaube sie für IliasSync in macOS.',
    'Notifications for new sync problems are enabled.': 'Mitteilungen bei neuen Sync-Problemen sind aktiviert.',
    'Test notification handed to macOS.': 'Testmitteilung an macOS übergeben.',
    'macOS could not accept the test notification. Check System Settings → Notifications.':
        'macOS konnte die Testmitteilung nicht annehmen. Prüfe Systemeinstellungen → Mitteilungen.',
    'Recently updated': 'Zuletzt aktualisiert', 'Your materials': 'Deine Materialien',
    'Three recent materials': 'Drei aktuelle Materialien',
    'View all materials': 'Alle ansehen', 'View all materials ({count})': 'Alle ansehen ({count})',
    'No materials yet': 'Noch keine Materialien',
    'Start a sync to download your course materials.': 'Synchronisiere jetzt, um deine Kursmaterialien herunterzuladen.',
    'Last synchronization: {time} ({age})': 'Letzte Synchronisation: {time} ({age})',
    'Synchronized': 'Synchronisiert',
    'today': 'heute',
    'Not yet': 'Noch nicht',
    'Sync off': 'Automatik aus',
    'Waiting for sign-in': 'Wartet auf Anmeldung',
    'Paused until {time}': 'Pause bis {time}',
    'Deferred on battery': 'Auf Akku verschoben',
    'Next system run': 'Nächste Prüfung durch das System',
    'Next {time}': 'Nächste {time}',
    'Per university': 'Je Hochschule',
    'Ignore': 'Ignorieren',
    'Skip these unavailable files in future syncs. Existing local copies stay.':
        'Diese nicht verfügbaren Dateien werden künftig übersprungen. Vorhandene lokale Kopien bleiben.',
    'Last complete synchronization: {time} ({age})': 'Letzte vollständige Synchronisation: {time} ({age})',
    'Action required — see Details': 'Aktion erforderlich – siehe Details',
    'Synchronization': 'Synchronisierung',
    'Synchronization succeeded': 'Synchronisierung erfolgreich',
    'Last attempt: {time} ({age})': 'Letzter Versuch: {time} ({age})',
    'Not yet synchronized': 'Noch nicht synchronisiert',
    'just now': 'gerade eben', '{count} min ago': 'vor {count} Min.', '{count} h ago': 'vor {count} Std.',
    '{count} days ago': 'vor {count} Tagen',
    '{errors} errors · {notes} notes': '{errors} Fehler · {notes} Hinweise',
    '{count} hidden': '{count} ausgeblendet', 'No current problems': 'Keine aktuellen Probleme',
    'Notify me about new sync problems on this Mac': 'Bei neuen Sync-Problemen auf diesem Mac benachrichtigen',
    'Hidden notices stay in Details. Repeated problems do not trigger another notification.':
        'Ausgeblendete Meldungen bleiben in Details. Wiederholte Probleme lösen keine neue Mitteilung aus.',
    'New sync problems appear here. Your existing materials remain available.':
        'Neue Sync-Probleme erscheinen hier. Deine vorhandenen Materialien bleiben verfügbar.',
    'Download unavailable': 'Download nicht verfügbar', 'Connection unavailable': 'Verbindung nicht verfügbar',
    'Sync errors': 'Sync-Fehler', 'Sync notes': 'Sync-Hinweise', 'Check incomplete': 'Prüfung unvollständig',
    'Show again': 'Wieder anzeigen', 'Dismiss notice': 'Meldung ausblenden',
    'Hides this notice only. The sync result and recovery steps are kept.':
        'Blendet nur diese Meldung aus. Das Sync-Ergebnis und die Schritte zur Behebung bleiben erhalten.',
    '{count} attempts': '{count} Versuche', 'View details': 'Details ansehen', 'Current notices': 'Aktuelle Meldungen',
    'Dismissal hides a notice; it does not fix the problem or remove the report.':
        'Ausblenden verbirgt die Meldung. Das Problem und der Bericht bleiben bestehen.',
    'Allow notifications in macOS when prompted. If denied, enable IliasSync in System Settings → Notifications.':
        'Erlaube die Mitteilungen in macOS. Falls abgelehnt: IliasSync in Systemeinstellungen → Mitteilungen aktivieren.',
    'System notifications are available in the installed macOS app. Notices here always work.':
        'Systemmitteilungen sind in der installierten macOS-App verfügbar. Meldungen hier funktionieren immer.',
})


def set_language(language):
    global LANGUAGE
    LANGUAGE = language if language in {"de", "en"} else "de"


def t(text, **values):
    translated = DE.get(text, text) if LANGUAGE == "de" else text
    return translated.format(**values) if values else translated


def message(text):
    if text in DE:
        return t(text)
    if text.startswith("Checking "):
        return t("Checking {name}", name=text[9:])
    if text.startswith("Downloading "):
        return t("Downloading {name}", name=text[12:])
    for prefix in ("Added", "Updated", "Unchanged", "Conflict"):
        if text.startswith(prefix + ": "):
            return t(prefix) + text[len(prefix):]
    if ": sync could not complete." in text:
        return t("Sync could not complete. Existing files were retained. Check your connection and try again.")
    return t(text)
