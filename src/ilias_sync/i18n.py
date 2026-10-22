"""Small explicit UI catalog; file names and server-provided course names stay intact."""
LANGUAGE = "de"
DE = {
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
    for prefix in ("Added", "Updated", "Unchanged", "Conflict"):
        if text.startswith(prefix + ": "):
            return t(prefix) + text[len(prefix):]
    if ": sync could not complete." in text:
        return t("Sync could not complete. Existing files were retained. Check your connection and try again.")
    return t(text)
