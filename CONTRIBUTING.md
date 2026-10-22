# Mitwirken

Danke für Fehlerberichte, Übersetzungen, Dokumentation und kleine, gezielte Fixes.
Das Repository ist zunächst privat. Die Regeln gelten bereits für die Alpha und
später für öffentliche Beiträge.

## Einen Fehler melden

Nutze die Issue-Vorlage. Nenne App-Version, Betriebssystem, ILIAS-Version (falls
bekannt), Schritte, erwartetes und tatsächliches Verhalten. Eine bereinigte
Installationsadresse kann helfen; keine Zugangstoken oder privaten Kurslinks.

**Nicht hochladen:** Passwörter, Cookies, Zugangstoken, Original-Anmeldeseiten,
private Kursunterlagen, Kontodaten oder ungeschwärzte App-Konfigurationen.
Sicherheitsprobleme gehören nicht in öffentliche Issues: siehe [SECURITY.md](SECURITY.md).

## Einen Beitrag vorbereiten

1. Bei größeren Änderungen zuerst das Problem und den Umfang in einem Issue klären.
2. Einen eigenen Branch verwenden. Änderungen auf das erklärte Problem begrenzen.
3. [Entwicklungsumgebung](docs/DEVELOPMENT.md) einrichten; `ruff check .` und `pytest` ausführen.
4. Parseränderungen mit kleinen synthetischen HTML-Fixtures prüfen. Keine echten
   Hochschuldaten in Tests aufnehmen. GUI-Änderungen auf Lesbarkeit, Fokus,
   Hell/Dunkel und die deutschen und englischen Texte prüfen.
5. Im Pull Request Verhalten, relevante Prüfung und offene Grenzen beschreiben.

Eine grüne CI ist kein Nachweis universeller Hochschulkompatibilität. Sichtbare
Fehler, ausgelassene Inhalte und MFA-Grenzen müssen erkennbar bleiben. Keine
Netzwerkanfragen mit echten Accounts in CI. Keine Datenlöschung als Routinefix.

Dein Beitrag wird unter der bestehenden GPL-3.0-or-later-Lizenz eingereicht.
Keine separaten Rechte an fremden Kursmaterialien oder Marken werden dadurch erteilt.
