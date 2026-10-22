"""Short, translated product facts, distinct from a university's own rules."""
from html import escape

from . import __version__, i18n


def info_html():
    de = i18n.LANGUAGE == "de"
    sections = [
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
         "Ein PFERD-Arbeitsslot, eine Sekunde Abstand zwischen Aufgabenstarts. Das ist kein festes HTTP-Anfragelimit. "
         "Automatische Läufe starten frühestens stündlich, standardmäßig alle sechs Stunden und nur im Netzbetrieb. "
         "Zwischen den Läufen bleibt kein Sync-Prozess aktiv. Der Computer muss wach und angemeldet sein."
         if de else
         "One PFERD worker slot, one second between task starts. This is not a fixed HTTP request limit. "
         "Automatic runs are at least one hour apart; the default is six hours, on AC power. "
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
    result = f"<h2>IliasSync {escape(__version__)}</h2>"
    result += "".join(f"<h3>{escape(title)}</h3><p>{escape(body)}</p>" for title, body in sections)
    result += "<h3>" + ("Projekt & Quellen" if de else "Project & references") + "</h3><p>"
    links = [("Projekt / README", "https://github.com/schroedernils/ilias-sync"),
             ("PFERD", "https://github.com/Garmelon/PFERD"),
             ("Ilias Downloader Tool", "https://iliasdownloadertool.de/"),
             ("ILIAS-Sync2Folder", "https://viperinius.github.io/ILIAS-Sync2Folder/")]
    result += "<br>".join(f'<a href="{url}">{name}</a>' for name, url in links)
    return result + "</p>"
