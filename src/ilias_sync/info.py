"""Task-oriented help using the same actions and boundaries as the desktop UI."""
from html import escape

from . import __version__, i18n


def info_sections():
    de = i18n.LANGUAGE == "de"
    sections = [
        ("Material finden" if de else "Find materials",
         "Die Übersicht zeigt bis zu drei zuletzt aktualisierte Dateien. Alle ansehen öffnet die vollständige Materialliste. "
         "Wähle links Alle Materialien, eine Hochschule oder einen Kurs. Die Navigation verändert deine Sync-Auswahl nicht. Suche nach Dateinamen, Kursen oder Hochschulen; "
         "Cmd+F auf dem Mac oder Strg+F öffnet die Suche. Wähle eine Datei und drücke Enter oder klicke doppelt, "
         "um sie in deiner Standard-App zu öffnen.\n\n"
         "Kein Treffer? Leere die Suche und setze aktive Filter zurück. Das Filtersymbol neben Datei grenzt "
         "nach Kurs, Dateityp und Größe ein. Kursbeschreibungen und Links findest du unter Kursinformationen.\n\n"
         "Noch keine Dateien? Öffne das Menü Hochschule verwalten (…) und wähle Sync-Kurse auswählen. Starte danach Jetzt synchronisieren. Fehlt ein Kurs in der Auswahl, "
         "kannst du dort seinen ILIAS-Kurs- oder Ordnerlink ergänzen."
         if de else
         "Overview shows up to three recently updated files. View all opens the complete material list. "
         "Select All materials, a university or a course on the left. Browsing never changes your sync selection. Search by filename, course or university; Cmd+F on Mac or Ctrl+F "
         "focuses search. Select a file and press Enter or double-click to open it in your default app.\n\n"
         "No match? Clear search and reset active filters. The filter beside File narrows the list by course, "
         "type and size. Course descriptions and links are in Course information.\n\n"
         "No files yet? Open University actions (…) and choose Choose sync courses, then Sync now. If a course is missing from the selection, "
         "you can add its ILIAS course or folder link there."),
        ("Änderungen" if de else "Changes",
         "Wähle Zuletzt geändert, um erfasste neue und aktualisierte Materialien nach Änderungszeit zu sehen. "
         "Der Kurs unter dem Dateinamen hilft, gleich benannte Dateien auseinanderzuhalten.\n\n"
         "Die Ansicht ist ein Änderungsverlauf, keine Liste ungelesener Dateien. Sie wird durch Öffnen oder einen "
         "Lauf ohne Änderungen nicht geleert. Die Zeit zeigt, wann IliasSync die Änderung gespeichert hat, "
         "nicht unbedingt den Uploadzeitpunkt in ILIAS. Ältere Dateien ohne erfasste Änderung haben keine erfundene Zeit.\n\n"
         "Neu oder aktualisiert beschreibt die gespeicherte Datei, nicht ihre Wichtigkeit. Hinweise zu "
         "separaten Kopien und nicht verfügbaren Downloads stehen im Sync-Bericht."
         if de else
         "Choose Recent changes to see recorded new and updated materials in change-time order. "
         "The course below each filename helps distinguish files with the same name.\n\n"
         "This is a change history, not an unread list. Opening files or running an unchanged sync does not clear it. "
         "The time records when IliasSync saved the change, which may differ from the ILIAS upload time. "
         "Older files without recorded changes have no invented timestamp.\n\n"
         "New or updated describes the saved file, not its importance. The Sync report explains "
         "separate copies and unavailable downloads."),
        ("Sync-Ergebnis" if de else "Sync results",
         "Die letzte Prüfung beschreibt den damaligen Lauf und die dafür ausgewählten Kurse und Speicherziele. "
         "Nach einer Änderung dieser Auswahl starte erneut Jetzt synchronisieren. Ein abgeschlossenes Ergebnis "
         "bestätigt keinen späteren Cloud-Upload und keine dauerhafte Verfügbarkeit jeder Datei.\n\n"
         "Jetzt synchronisieren bleibt unten im Sync-Bereich erreichbar. Während eines Laufs kannst du dort pausieren, fortsetzen oder über den roten Button beenden. "
         "Bei Hinweisen oder einem unvollständigen Lauf öffne den Tab Details. Unter Aktion erforderlich siehst du, "
         "welche Datei oder welcher Kurs nicht geprüft oder gespeichert werden konnte. Ausgeschlossene Inhalte "
         "wie Foren und Tests stehen separat; das sind keine fehlgeschlagenen Dateidownloads.\n\n"
         "Oben im Bericht kannst du frühere Versuche auswählen. Die Zahlen gehören jeweils zu diesem Versuch, "
         "nicht zur gesamten Ablage. Beginne mit dem Ergebnis und den betroffenen Materialien; "
         "der technische Verlauf ist nur bei Bedarf nötig.\n\n"
         "Unter Benachrichtigungen kannst du neue Probleme ansehen und macOS-Mitteilungen aktivieren. Wiederholte Meldungen werden gebündelt. "
         "Meldung ausblenden verwirft nur die Meldung; Fehlerstatus und Bericht bleiben bestehen. Unter Details kannst du sie wieder anzeigen. "
         "Nach einer Behebung wird dasselbe Problem bei erneutem Auftreten wieder gemeldet."
         if de else
         "The last check describes that run and its selected courses and destinations. After changing that "
         "selection, use Sync now again. A completed result does not confirm a later cloud upload or "
         "permanent availability of every file.\n\n"
         "Sync now stays in the bottom sync section. During a run, pause, resume or use the red stop button there. "
         "For notes or an incomplete run, open the Details tab. Needs attention shows which file or "
         "course could not be checked or saved. Excluded content such as forums and tests is listed separately; "
         "these are not failed file downloads.\n\n"
         "Select earlier attempts at the top of the report. Counts belong to that attempt, not your whole archive. "
         "Start with the outcome and affected materials; technical activity is there if you need it.\n\n"
         "Notifications lists new problems and lets you enable macOS notifications. Repeated notices are grouped. Dismiss notice hides only "
         "the notice; the error status and report remain. Show it again in Details. After recovery, a recurring problem is reported again."),
        ("Anmeldung" if de else "Sign-in",
         "Wähle Anmeldung erneuern direkt an der Fehlermeldung. Die App öffnet die Anmeldung der betroffenen Hochschule. "
         "Gib dein aktuelles Passwort ein oder importiere eine neue Sitzung. Im normalen Bearbeiten behält ein leeres Passwortfeld "
         "das gespeicherte Passwort; bei dieser Wiederherstellung ist eine neue Eingabe nötig.\n\n"
         "Bei Browsersitzung (MFA) melde dich in deinem Browser erneut bei ILIAS an und importiere einen frischen "
         "Netscape-cookies.txt-Export. Die App liest dein Browserprofil nicht selbst. Auch eine importierte Sitzung kann ablaufen.\n\n"
         "Speichern und prüfen startet die erneute Prüfung direkt. Erst deren Ergebnis bestätigt die Anmeldung; falls es weiter fehlschlägt, bleiben die nächsten Schritte sichtbar. Abbrechen lässt deine bisherige Anmeldung unverändert. Bei abgelaufener Anmeldung pausieren automatische "
         "Anmeldeversuche; die manuelle Prüfung zeigt den neuen Status. Bereits gespeicherte Dateien werden deshalb nicht gelöscht. Gib Passwörter "
         "oder Sitzungsexporte niemals in einem Fehlerbericht weiter."
         if de else
         "Choose Renew sign-in beside the error to open the affected university's sign-in settings. "
         "Enter your current password or import a fresh session. A blank password keeps the saved password during normal editing; recovery requires fresh input.\n\n"
         "For Browser session (MFA), sign in to ILIAS in your browser again and import a fresh Netscape "
         "cookies.txt export. The app does not read your browser profile itself. Imported sessions can expire too.\n\n"
         "Save and check immediately starts a new check. Only its result can confirm the sign-in; failed attempts keep the next steps visible. Cancel leaves the old sign-in unchanged. Automatic sign-in attempts pause after an expired session; the manual check establishes the new status. "
         "Previously saved files are not deleted because sign-in failed. Never share passwords "
         "or session exports in a bug report."),
        ("Dateien" if de else "Files",
         "Über Hochschule verwalten (…) → Ordner zuordnen kannst du Ziele für Kurse, Unterordner oder einzelne Dateien wählen. "
         "Die spezifischste Regel gilt: Datei vor Unterordner, Unterordner vor Kurs. Die Vorschau zeigt "
         "das wirksame Ziel des ausgewählten Elements.\n\n"
         "Ein neuer Zielort erzeugt beim nächsten Sync neue Kopien; vorhandene Kopien am alten Ort bleiben. "
         "Das Umbenennen eines verwalteten Ordners nimmt dagegen dessen lokale Inhalte mit. "
         "Abbrechen verwirft ungespeicherte Änderungen.\n\n"
         "Bei erkannten eigenen Bearbeitungen bleibt deine Datei erhalten; die neue Serverfassung bekommt "
         "eine separate ILIAS-Kopie. Ersetzte frühere Inhalte liegen unter Versions im jeweiligen Zielordner. "
         "Kopiere eine gewünschte Fassung zur Wiederherstellung in einen separaten Ordner. "
         "Versionen und verschwundene Serverdateien werden nicht automatisch gelöscht."
         if de else
         "Use University actions (…) → Folder mapping to choose destinations for courses, subfolders or individual files. "
         "The most specific rule wins: file before subfolder, subfolder before course. "
         "The preview shows the selected item's effective destination.\n\n"
         "A new destination creates new copies on the next sync; existing copies at the old location remain. "
         "Renaming a managed folder instead moves its local contents with it. Cancel discards unsaved changes.\n\n"
         "When local edits are detected, your file is kept and the new server version gets a separate ILIAS copy. "
         "Replaced earlier contents are stored under Versions in the relevant destination. "
         "To recover a version, copy it into a separate folder. Versions and files removed from ILIAS "
         "are not automatically deleted."),
        ("Offline & Cloud" if de else "Offline & cloud",
         "Heruntergeladene Dokumente kannst du auch außerhalb von IliasSync mit deiner normalen Datei-App öffnen. "
         "Prüfe vor dem Arbeiten ohne Netz, ob sich die benötigten Dateien tatsächlich öffnen lassen. "
         "Ein Eintrag in der Liste allein ist kein Offline-Nachweis; ein Link braucht häufig weiterhin Internet.\n\n"
         "Bei Google Drive, OneDrive oder anderen Cloud-Ordnern übernimmt der Cloud-Client Upload und lokale "
         "Verfügbarkeit. Markiere benötigte Dateien dort bei Bedarf als offline verfügbar. IliasSync bestätigt "
         "weder den Uploadabschluss noch, ob der Cloud-Client eine Datei später nur online vorhält.\n\n"
         "Fehlt eine Datei lokal, prüfe zunächst den Zielordner und bei externen Laufwerken die Verbindung. "
         "Ein erneuter Sync kann fehlende Kopien wiederherstellen, soweit der Inhalt noch zugänglich ist. "
         "Für eine Sicherung brauchst du Downloadordner und App-Daten zusammen."
         if de else
         "You can open downloaded documents outside IliasSync with your usual file app. Before working "
         "without a connection, check that the files you need actually open. A list entry alone does not "
         "prove offline availability; links often still need internet access.\n\n"
         "For Google Drive, OneDrive or other cloud folders, the cloud client handles uploads and local "
         "availability. Mark needed files as available offline there if necessary. IliasSync confirms "
         "neither completed uploads nor whether the cloud client later keeps a file online-only.\n\n"
         "If a local file is missing, check its destination and the connection to any external drive first. "
         "Another sync can restore missing copies if the content is still accessible. "
         "Back up the download folders and application data together."),
        ("Zeitplan" if de else "Schedule",
         "Unter Einstellungen → Zeitplan aktivierst du automatische Läufe und wählst ein Intervall oder "
         "einen Wochenplan. Im Wochenplan ergänzt + eine Uhrzeit direkt am Wochentag. Du kannst die Uhrzeit direkt bearbeiten und mit × entfernen. "
         "Tage ohne Uhrzeit bleiben frei. Zeiten kopieren neben der Akkuoption übernimmt die Zeiten für einen anderen Tag, Montag bis Freitag oder alle Tage. "
         "Bisherige tägliche Zeiten erscheinen für alle sieben Tage. Standard sind sechs Stunden und Aufschieben im Akkubetrieb. "
         "Erst Speichern übernimmt deine Änderungen; Abbrechen verwirft sie.\n\n"
         "Pausieren unterbricht den laufenden Sync; Fortsetzen setzt ihn fort. Diesen Sync beenden beendet "
         "nur diesen Lauf. Fertig gespeicherte Dateien und der Zeitplan bleiben erhalten. "
         "Zum Abschalten künftiger Läufe deaktiviere Automatisch synchronisieren und speichere.\n\n"
         "Der Computer muss wach, angemeldet und für neue Downloads online sein. Eine angezeigte nächste "
         "Uhrzeit ist geplant, keine Ausführungsgarantie. Zwischen den Läufen bleibt kein Sync-Prozess aktiv. "
         "Nach einer abgelaufenen Anmeldung ist zuerst eine neue Anmeldung nötig. "
         "Updates und normale Neuinstallationen behalten deinen Zeitplan. Nach einem Ortswechsel öffne die App einmal; "
         "sie verbindet die eingeschaltete Automatik mit der neuen Installation und repariert einen fehlenden Systemauftrag. "
         "Bei Zeitplan prüfen bleiben deine Uhrzeiten erhalten; erneutes Speichern versucht die Reparatur."
         if de else
         "In Settings → Schedule, enable automatic runs and choose an interval or a weekly schedule. Use + beside a weekday to add a time, "
         "edit it directly, and remove it with ×. Days without times remain free. Copy times beside the battery option applies a day's times to another day, Monday–Friday or all days. "
         "Existing daily times appear on all seven days. "
         "Defaults are six hours and deferral on battery. Save applies changes; Cancel discards them.\n\n"
         "Pause suspends the running sync; Resume continues it. Stop this sync ends only that run. "
         "Completed files and the schedule are kept. To stop future runs, turn off Automatic sync and save.\n\n"
         "Your computer must be awake, signed in and online for new downloads. The next displayed time "
         "is planned, not guaranteed. No sync process stays active between runs. "
         "An expired session needs a new sign-in first. "
         "Updates and normal reinstalls keep your schedule. After moving the app, open it once; it reconnects enabled "
         "automation to the current installation and repairs a missing OS job. Review schedule keeps your times; save again to retry."),
        ("Nutzung" if de else "Use",
         "IliasSync ist ein unabhängiges Projekt, kein Angebot von ILIAS oder deiner Hochschule. "
         "Lade nur Inhalte herunter, auf die du berechtigt zugreifen darfst. Beachte die Regeln deiner Hochschule "
         "und die Rechte an Kursmaterialien. Eine Softwarelizenz erteilt keine Rechte an diesen Inhalten. "
         "Prüfe vor einer Cloud-Ablage, ob du die Materialien dort speichern und mit wem du sie teilen darfst."
         if de else
         "IliasSync is an independent project, not a service from ILIAS or your university. "
         "Only download content you are entitled to access. Follow your institution's rules and content rights. "
         "The software license grants no rights to course materials. Check permission before storing or sharing them in a cloud folder."),
        ("Kompatibilität" if de else "Compatibility",
         "Vorabversion für macOS 13+, Windows 10/11 x64 und Linux x64 (glibc 2.35+). "
         "Keine eigene Python- oder Java-Installation nötig. Hochschuldesigns, Plugins und SSO/MFA unterscheiden sich; "
         "nicht jede Installation ist geprüft. Foren, Tests und SCORM sind kein vollständiges Offline-Abbild. "
         "macOS ist ad-hoc signiert und nicht notarisiert; Windows hat keine Herausgebersignatur."
         if de else
         "Preview for macOS 13+, Windows 10/11 x64 and Linux x64 (glibc 2.35+). "
         "No separate Python or Java installation needed. Themes, plugins and SSO/MFA vary; "
         "not every institution is verified. Forums, tests and SCORM are not a complete offline archive. "
         "macOS is ad-hoc signed, not notarized; Windows has no publisher signature."),
        ("Datenschutz" if de else "Privacy",
         "Zugangsdaten bleiben im Passwortspeicher des Systems. Sitzungsimporte liegen in privaten App-Daten. "
         "Keine App-Telemetrie, kein eigenes Cloudkonto. Ein Cloud-Client lädt Dateien eigenständig hoch. "
         "GPL-3.0-or-later; die jeweiligen Lizenzen der enthaltenen Bibliotheken gelten zusätzlich."
         if de else
         "Credentials stay in the system vault. Imported sessions are kept in private application data. "
         "No app telemetry or proprietary cloud account. Your cloud client handles uploads independently. "
         "GPL-3.0-or-later; bundled libraries retain their own licenses."),
    ]
    return sections


def info_html():
    result = f"<h2>IliasSync {escape(__version__)}</h2>"
    result += "".join(topic_html(title, body) for title, body in info_sections())
    return result + info_links()


def topic_html(title, body):
    """Keep short task paragraphs readable without interpreting content as markup."""
    return '<h3>' + escape(title) + '</h3>' + ''.join(
        '<p>' + escape(paragraph) + '</p>' for paragraph in body.split('\n\n') if paragraph.strip())


def info_links():
    de = i18n.LANGUAGE == 'de'
    links = [("Installation & Anmeldung" if de else "Installation & sign-in",
              "https://github.com/schroedernils/ilias-sync/blob/main/docs/INSTALLATION.md"),
             ("Dateien & Wiederherstellung" if de else "Files & recovery",
              "https://github.com/schroedernils/ilias-sync/blob/main/docs/RECOVERY.md"),
             ("Problem melden" if de else "Report a problem",
              "https://github.com/schroedernils/ilias-sync/issues/new/choose"),
             ("Projekt / README" if de else "Project / README", "https://github.com/schroedernils/ilias-sync"),
             ("PFERD", "https://github.com/Garmelon/PFERD"),
             ("Ilias Downloader Tool", "https://iliasdownloadertool.de/"),
             ("ILIAS-Sync2Folder", "https://viperinius.github.io/ILIAS-Sync2Folder/")]
    access = ('Die Projektlinks benötigen während der privaten Alpha GitHub-Zugriff. '
              'Ein fehlender Zugriff kann als 404 erscheinen.' if de else
              'During the private alpha, project links need GitHub access. Missing access may appear as a 404.')
    privacy = ('Für einen Fehlerbericht genügen App-/Build-Version, Betriebssystem und die Schritte zum Problem. '
               'Entferne Passwörter, Cookies, private Dateipfade und Kursinhalte aus Texten und Bildern.' if de else
               'For a bug report, include the app/build version, operating system and steps to the problem. '
               'Remove passwords, cookies, private file paths and course contents from text and images.')
    return '<h3>' + ('Projekt & Quellen' if de else 'Project & references') + '</h3><p>' + '<br>'.join(
        f'<a href="{escape(url, quote=True)}">{escape(name)}</a>' for name, url in links) + '</p>' + (
            '<p>' + escape(access) + '</p><p>' + escape(privacy) + '</p>')
