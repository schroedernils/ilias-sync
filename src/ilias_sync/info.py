"""Short, translated product facts, distinct from a university's own rules."""
from html import escape

from . import __version__, i18n


def info_sections():
    de = i18n.LANGUAGE == "de"
    sections = [
        ("Dein Material" if de else "Your materials",
         "Unter Materialien findest du die Dateien aus deinen Kursen. Suche nach Dateinamen oder Kursen. "
         "Ein Doppelklick oder Enter öffnet die ausgewählte Datei. Über das Filtersymbol neben Datei "
         "kannst du nach Kurs, Dateityp und Größe eingrenzen. Kursbeschreibungen und Links stehen in der Ansicht Kursinformationen."
         if de else
         "Materials contains the files from your courses. Search by filename or course. "
         "Double-click or press Enter to open the selected file. The filter beside File narrows the list by course, "
         "type and size. Course descriptions and links are in the Course information view."),
        ("Änderungen & Hinweise" if de else "Changes & notes",
         "Zuletzt geändert zeigt neue und aktualisierte Materialien, sobald ihre Änderung von dieser App-Version erfasst wurde. "
         "Der Sync-Bericht erklärt nicht verfügbare Downloads und ausgeschlossene Inhalte getrennt. "
         "Eigene Bearbeitungen werden nicht überschrieben: Bei einem Konflikt bleibt deine Datei erhalten und eine separate ILIAS-Kopie wird gespeichert."
         if de else
         "Recent changes shows new and updated materials once a change has been recorded by this app version. "
         "The sync report explains unavailable downloads separately from excluded content. "
         "Local edits are not overwritten: on a conflict, your file is retained and a separate ILIAS copy is saved."),
        ("Nutzung" if de else "Use",
         "IliasSync ist ein unabhängiges Projekt, kein Angebot von ILIAS oder deiner Hochschule. "
         "Lade nur Inhalte herunter, auf die du berechtigt zugreifen darfst. Beachte die Regeln deiner Hochschule "
         "und die Rechte an Kursmaterialien. Eine Softwarelizenz erteilt keine Rechte an diesen Inhalten. "
         "Prüfe vor einer Cloud-Ablage, ob du die Materialien dort speichern und mit wem du sie teilen darfst."
         if de else
         "IliasSync is an independent project, not a service from ILIAS or your university. "
         "Only download content you are entitled to access. Follow your institution's rules and content rights. "
         "The software license grants no rights to course materials. Check permission before storing or sharing them in a cloud folder."),
        ("Server & Hintergrund" if de else "Server & background",
         "Unter Einstellungen → Zeitplan wählst du ein Intervall oder feste tägliche Uhrzeiten. "
         "Standardmäßig wird alle sechs Stunden synchronisiert und im Akkubetrieb pausiert. "
         "Zwischen den Läufen bleibt kein Sync-Prozess aktiv. Der Computer muss wach und angemeldet sein."
         if de else
         "In Settings → Schedule, choose an interval or fixed daily times. "
         "The default is every six hours, pausing on battery power. "
         "No sync process stays active between runs. Your computer must be awake and signed in."),
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
        ("Datenschutz & Lizenz" if de else "Privacy & license",
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
    result += "".join(f"<h3>{escape(title)}</h3><p>{escape(body)}</p>" for title, body in info_sections())
    return result + info_links()


def info_links():
    de = i18n.LANGUAGE == 'de'
    links = [("Projekt / README", "https://github.com/schroedernils/ilias-sync"),
             ("PFERD", "https://github.com/Garmelon/PFERD"),
             ("Ilias Downloader Tool", "https://iliasdownloadertool.de/"),
             ("ILIAS-Sync2Folder", "https://viperinius.github.io/ILIAS-Sync2Folder/")]
    return '<h3>' + ('Projekt & Quellen' if de else 'Project & references') + '</h3><p>' + '<br>'.join(
        f'<a href="{url}">{name}</a>' for name, url in links) + '</p>'
